from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from config import settings_loader
from src.infrastructure.db import paths

OPTIONAL_ENV = {
    "DB_SQLITE_PATH",
    "DUCKDB_PATH",
    "GEMINI_API_KEY",
    "AI_CORE_API_URL",
    "EVDS_API_KEY",
    "TCMB_DEPOSIT_RATE_FALLBACK",
}


def _disable_env_file(monkeypatch, tmp_path):
    monkeypatch.setattr(settings_loader, "_env_file_path", lambda: tmp_path / "missing.env")


def _clear_env(monkeypatch):
    for key in OPTIONAL_ENV:
        monkeypatch.delenv(key, raising=False)


def test_load_settings_defaults_to_sqlite_under_app_root(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_env(monkeypatch)

    config = settings_loader.load_settings()

    assert isinstance(config, settings_loader.SQLiteConfig)
    assert Path(config.db_path) == paths.app_root() / "data" / "portfolio.db"
    assert Path(config.db_path).is_absolute()


def test_load_settings_resolves_relative_sqlite_path_against_app_root(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_env(monkeypatch)
    monkeypatch.setenv("DB_SQLITE_PATH", "custom/path.db")

    config = settings_loader.load_settings()

    assert Path(config.db_path) == paths.app_root() / "custom" / "path.db"


def test_load_settings_keeps_absolute_sqlite_path(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_env(monkeypatch)
    absolute = tmp_path / "abs" / "portfolio.db"
    monkeypatch.setenv("DB_SQLITE_PATH", str(absolute))

    assert Path(settings_loader.load_settings().db_path) == absolute


def test_legacy_mysql_variables_are_ignored(monkeypatch, tmp_path):
    """Eski .env dosyalarındaki MySQL değişkenleri hata üretmez, yok sayılır."""
    _disable_env_file(monkeypatch, tmp_path)
    _clear_env(monkeypatch)
    for key, value in {"DB_ENGINE": "mysql", "DB_HOST": "localhost", "DB_PASSWORD": "x", "POOL_SIZE": "bozuk"}.items():
        monkeypatch.setenv(key, value)

    assert isinstance(settings_loader.load_settings(), settings_loader.SQLiteConfig)


def test_load_app_settings_builds_optional_settings(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_env(monkeypatch)
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("AI_CORE_API_URL", "http://127.0.0.1:9000/")
    monkeypatch.setenv("EVDS_API_KEY", "evds-key")
    monkeypatch.setenv("TCMB_DEPOSIT_RATE_FALLBACK", "42.25")

    settings = settings_loader.load_app_settings()

    assert isinstance(settings.db, settings_loader.SQLiteConfig)
    assert settings.ai.gemini_api_key == "gemini-key"
    assert settings.ai.core_api_url == "http://127.0.0.1:9000"
    assert settings.market.evds_api_key == "evds-key"
    assert settings.market.tcmb_deposit_rate_fallback == Decimal("42.25")


def test_load_ai_settings_rejects_invalid_url(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_env(monkeypatch)
    monkeypatch.setenv("AI_CORE_API_URL", "localhost:8000")

    with pytest.raises(settings_loader.SettingsError, match="AI_CORE_API_URL"):
        settings_loader.load_ai_settings()


def test_load_market_settings_rejects_invalid_decimal(monkeypatch, tmp_path):
    _disable_env_file(monkeypatch, tmp_path)
    _clear_env(monkeypatch)
    monkeypatch.setenv("TCMB_DEPOSIT_RATE_FALLBACK", "not-a-decimal")

    with pytest.raises(settings_loader.SettingsError, match="TCMB_DEPOSIT_RATE_FALLBACK"):
        settings_loader.load_market_settings()


def test_load_settings_dynamic_env_file(monkeypatch, tmp_path):
    (tmp_path / ".env").write_text("DB_SQLITE_PATH=prod.db", encoding="utf-8")
    (tmp_path / ".env.test").write_text("DB_SQLITE_PATH=test.db", encoding="utf-8")

    def dummy_env_file_path():
        import os

        env_name = os.getenv("PORTFOYSIM_ENV", "").lower()
        return tmp_path / (f".env.{env_name}" if env_name else ".env")

    monkeypatch.setattr(settings_loader, "_env_file_path", dummy_env_file_path)

    _clear_env(monkeypatch)
    monkeypatch.delenv("PORTFOYSIM_ENV", raising=False)
    assert Path(settings_loader.load_settings().db_path).name == "prod.db"

    _clear_env(monkeypatch)
    monkeypatch.setenv("PORTFOYSIM_ENV", "test")
    assert Path(settings_loader.load_settings().db_path).name == "test.db"


def test_duckdb_path_defaults_next_to_sqlite_and_honors_override(monkeypatch, tmp_path):
    monkeypatch.delenv("DUCKDB_PATH", raising=False)
    sqlite_file = tmp_path / "veri" / "portfolio.db"

    assert paths.duckdb_path(sqlite_file) == tmp_path / "veri" / "market_history.duckdb"

    monkeypatch.setenv("DUCKDB_PATH", str(tmp_path / "baska" / "piyasa.duckdb"))
    assert paths.duckdb_path(sqlite_file) == tmp_path / "baska" / "piyasa.duckdb"
