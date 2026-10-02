from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv, set_key

from src.infrastructure.db.db_config import DatabaseConfig, SQLiteConfig
from src.infrastructure.db.paths import DEFAULT_SQLITE_RELATIVE, sqlite_db_path


class SettingsError(RuntimeError):
    pass


@dataclass(frozen=True)
class AISettings:
    gemini_api_key: str | None
    core_api_url: str


@dataclass(frozen=True)
class MarketSettings:
    evds_api_key: str | None
    tcmb_deposit_rate_fallback: Decimal


@dataclass(frozen=True)
class AppSettings:
    db: DatabaseConfig
    ai: AISettings
    market: MarketSettings


def _env_file_path() -> Path:
    env_name = os.getenv("PORTFOYSIM_ENV", "").lower()
    filename = f".env.{env_name}" if env_name else ".env"
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / filename
    return Path(__file__).resolve().parents[1] / filename


# Veritabanı yolları: kabuktan/test ortamından açıkça verilen değer `.env` dosyasıyla ezilmez
# (kopya veritabanı üzerinde betik çalıştırmak ve testleri izole etmek için).
_PROTECTED_PATH_ENV = ("DB_SQLITE_PATH", "DUCKDB_PATH")


def _load_project_env() -> None:
    env_path = _env_file_path()
    if env_path.exists():
        preset = {key: os.environ[key] for key in _PROTECTED_PATH_ENV if os.environ.get(key)}
        load_dotenv(env_path, override=True)
        os.environ.update(preset)


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise SettingsError(f"Missing required environment variable: {name}")
    return value.strip()


def _optional_env(name: str) -> str | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    return value.strip()


def _decimal_env(name: str, default: str) -> Decimal:
    raw_value = _optional_env(name) or default
    try:
        return Decimal(raw_value)
    except (InvalidOperation, ValueError) as exc:
        raise SettingsError(f"Environment variable {name} must be a decimal number.") from exc


def _url_env(name: str, default: str) -> str:
    value = _optional_env(name) or default
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SettingsError(f"Environment variable {name} must be a valid http(s) URL.")
    return value.rstrip("/")


def _load_db_settings() -> DatabaseConfig:
    """SQLite yolu `DB_SQLITE_PATH` ile verilir (göreli yol uygulama köküne göre çözülür)."""
    return SQLiteConfig(db_path=str(sqlite_db_path(_optional_env("DB_SQLITE_PATH") or DEFAULT_SQLITE_RELATIVE)))


def load_ai_settings() -> AISettings:
    _load_project_env()
    return AISettings(
        gemini_api_key=_optional_env("GEMINI_API_KEY"),
        core_api_url=_url_env("AI_CORE_API_URL", "http://localhost:8000"),
    )


def load_market_settings() -> MarketSettings:
    _load_project_env()
    return MarketSettings(
        evds_api_key=_optional_env("EVDS_API_KEY"),
        tcmb_deposit_rate_fallback=_decimal_env("TCMB_DEPOSIT_RATE_FALLBACK", "45.0"),
    )


def load_app_settings() -> AppSettings:
    _load_project_env()
    return AppSettings(
        db=_load_db_settings(),
        ai=load_ai_settings(),
        market=load_market_settings(),
    )


def load_settings() -> DatabaseConfig:
    return load_app_settings().db


def _env_write_path() -> Path:
    """persist_api_keys'in yazdığı dosya (testlerde gerçek .env'den ayrıştırılabilsin diye ayrı)."""
    return _env_file_path()


def persist_api_keys(settings: AppSettings | None, gemini_key: str | None = None, evds_key: str | None = None) -> Path:
    """API anahtarlarını .env dosyasına yazar, ortam değişkenlerini ve (verilmişse) çalışan ayarları günceller.

    `AISettings` / `MarketSettings` frozen olduğundan çalışma anı güncellemesi
    `object.__setattr__` ile yapılır; böylece ayarları okuyan servisler yeniden başlatma
    gerektirmeden yeni değeri görür. `None` verilen anahtara dokunulmaz.
    """
    env_path = _env_write_path()
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.touch()

    updates = {"GEMINI_API_KEY": gemini_key, "EVDS_API_KEY": evds_key}
    for name, value in updates.items():
        if value is None:
            continue
        clean = value.strip()
        set_key(str(env_path), name, clean, quote_mode="never")
        if clean:
            os.environ[name] = clean
        else:
            os.environ.pop(name, None)

    if settings is not None:
        if gemini_key is not None:
            object.__setattr__(settings.ai, "gemini_api_key", gemini_key.strip() or None)
        if evds_key is not None:
            object.__setattr__(settings.market, "evds_api_key", evds_key.strip() or None)
    return env_path
