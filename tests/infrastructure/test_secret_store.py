"""API anahtarı sır deposu: sır deposu önceliği, .env yedeği, kalıntı temizliği ve güvenli hata davranışı."""
from __future__ import annotations

import os

import pytest

from config import secret_store as secret_store_module
from config import settings_loader
from config.secret_store import KeyringSecretStore


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ("GEMINI_API_KEY", "EVDS_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def test_stored_secret_overrides_env_file_value(tmp_path, monkeypatch, secret_store):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=from-env-file\nEVDS_API_KEY=evds-from-env\n", encoding="utf-8")
    monkeypatch.setattr(settings_loader, "_env_file_path", lambda: env_file)
    secret_store.values["GEMINI_API_KEY"] = "from-keyring"

    ai = settings_loader.load_ai_settings()
    market = settings_loader.load_market_settings()

    assert ai.gemini_api_key == "from-keyring"
    assert market.evds_api_key == "evds-from-env"  # depoda yoksa .env değeri kullanılır


def test_persist_removes_plaintext_remnant_from_env_file(tmp_path, secret_store):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=old-plain\nOTHER=keep\n", encoding="utf-8")

    settings_loader.persist_api_keys(None, gemini_key="new-secret")

    text = env_file.read_text(encoding="utf-8")
    assert secret_store.values["GEMINI_API_KEY"] == "new-secret"
    assert "GEMINI_API_KEY" not in text and "OTHER=keep" in text
    assert os.environ["GEMINI_API_KEY"] == "new-secret"


def test_persist_falls_back_to_env_file_when_store_is_unavailable(tmp_path, secret_store):
    secret_store.fail_writes = True

    env_path = settings_loader.persist_api_keys(None, evds_key="evds-123")

    assert "EVDS_API_KEY=evds-123" in env_path.read_text(encoding="utf-8")
    assert secret_store.values == {}
    assert os.environ["EVDS_API_KEY"] == "evds-123"


def test_persist_empty_value_deletes_from_store_env_file_and_environment(tmp_path, secret_store, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=plain\n", encoding="utf-8")
    secret_store.values["GEMINI_API_KEY"] = "stored"
    monkeypatch.setenv("GEMINI_API_KEY", "stored")

    settings_loader.persist_api_keys(None, gemini_key="  ")

    assert "GEMINI_API_KEY" not in secret_store.values
    assert "GEMINI_API_KEY" not in env_file.read_text(encoding="utf-8")
    assert "GEMINI_API_KEY" not in os.environ


class _BrokenKeyring:
    def get_password(self, *args):
        raise RuntimeError("arka uç yok")

    def set_password(self, *args):
        raise RuntimeError("arka uç yok")

    def delete_password(self, *args):
        raise RuntimeError("arka uç yok")


def test_keyring_store_fails_safely_without_leaking_values(monkeypatch, caplog):
    store = KeyringSecretStore("PortfoySimulasyonu-test")
    monkeypatch.setattr(store, "_keyring", lambda: _BrokenKeyring())

    with caplog.at_level("DEBUG"):
        assert store.get("GEMINI_API_KEY") is None
        assert store.set("GEMINI_API_KEY", "super-secret-value") is False
        assert store.delete("GEMINI_API_KEY") is False

    assert "super-secret-value" not in caplog.text


def test_keyring_store_without_keyring_package_reports_failure(monkeypatch):
    store = KeyringSecretStore("PortfoySimulasyonu-test")
    monkeypatch.setattr(store, "_keyring", lambda: None)

    assert store.get("X") is None and store.set("X", "v") is False and store.delete("X") is False


def test_active_store_in_tests_is_never_the_real_keyring(secret_store):
    assert secret_store_module.get_secret_store() is secret_store
    assert not isinstance(secret_store_module.get_secret_store(), KeyringSecretStore)


@pytest.mark.manual
def test_real_keyring_roundtrip_with_throwaway_service():
    """Gerçek işletim sistemi deposu (Windows Kimlik Bilgisi Yöneticisi) ile yazma/okuma/silme; yalnızca elle koşulur."""
    store = KeyringSecretStore("PortfoySimulasyonu-selftest")

    assert store.set("probe", "v1") is True
    try:
        assert store.get("probe") == "v1"
    finally:
        store.delete("probe")
    assert store.get("probe") is None
