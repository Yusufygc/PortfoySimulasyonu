from __future__ import annotations

from decimal import Decimal

import pytest

from config import settings_loader


REQUIRED_ENV = {
    "DB_HOST": "localhost",
    "DB_PORT": "3306",
    "DB_USER": "user",
    "DB_PASSWORD": "password",
    "DB_NAME": "portfoySim",
    "POOL_NAME": "portfoy_pool",
    "POOL_SIZE": "5",
}

OPTIONAL_ENV = {
    "GEMINI_API_KEY",
    "AI_CORE_API_URL",
    "EVDS_API_KEY",
    "TCMB_DEPOSIT_RATE_FALLBACK",
}


def _disable_env_file(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_loader, "_env_file_path", lambda: tmp_path / "missing.env")


def _clear_required_env(monkeypatch):
    for key in set(REQUIRED_ENV).union(OPTIONAL_ENV):
        monkeypatch.delenv(key, raising=False)


def test_load_settings_requires_db_password(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_required_env(monkeypatch)

    for key, value in REQUIRED_ENV.items():
        if key != "DB_PASSWORD":
            monkeypatch.setenv(key, value)

    with pytest.raises(settings_loader.SettingsError, match="DB_PASSWORD"):
        settings_loader.load_settings()


def test_load_settings_rejects_invalid_integer(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_required_env(monkeypatch)

    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("POOL_SIZE", "not-an-int")

    with pytest.raises(settings_loader.SettingsError, match="POOL_SIZE"):
        settings_loader.load_settings()


def test_load_settings_builds_mysql_config(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_required_env(monkeypatch)

    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)

    config = settings_loader.load_settings()

    assert config.host == "localhost"
    assert config.port == 3306
    assert config.user == "user"
    assert config.password == "password"
    assert config.database == "portfoySim"
    assert config.pool_name == "portfoy_pool"
    assert config.pool_size == 5


def test_load_app_settings_builds_optional_settings(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_required_env(monkeypatch)

    for key, value in REQUIRED_ENV.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("AI_CORE_API_URL", "http://127.0.0.1:9000/")
    monkeypatch.setenv("EVDS_API_KEY", "evds-key")
    monkeypatch.setenv("TCMB_DEPOSIT_RATE_FALLBACK", "42.25")

    settings = settings_loader.load_app_settings()

    assert settings.db.database == "portfoySim"
    assert settings.ai.gemini_api_key == "gemini-key"
    assert settings.ai.core_api_url == "http://127.0.0.1:9000"
    assert settings.market.evds_api_key == "evds-key"
    assert settings.market.tcmb_deposit_rate_fallback == Decimal("42.25")


def test_load_ai_settings_rejects_invalid_url(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_required_env(monkeypatch)
    monkeypatch.setenv("AI_CORE_API_URL", "localhost:8000")

    with pytest.raises(settings_loader.SettingsError, match="AI_CORE_API_URL"):
        settings_loader.load_ai_settings()


def test_load_market_settings_rejects_invalid_decimal(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_required_env(monkeypatch)
    monkeypatch.setenv("TCMB_DEPOSIT_RATE_FALLBACK", "not-a-decimal")

    with pytest.raises(settings_loader.SettingsError, match="TCMB_DEPOSIT_RATE_FALLBACK"):
        settings_loader.load_market_settings()
