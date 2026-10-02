from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv, set_key

from src.infrastructure.db.db_config import DatabaseConfig, MySQLConfig, SQLiteConfig


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


def _load_project_env() -> None:
    env_path = _env_file_path()
    if env_path.exists():
        load_dotenv(env_path, override=True)


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


def _required_int_env(name: str, minimum: int = 1) -> int:
    raw_value = _required_env(name)
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise SettingsError(f"Environment variable {name} must be an integer.") from exc
    if value < minimum:
        raise SettingsError(f"Environment variable {name} must be >= {minimum}.")
    return value


def _optional_int_env(name: str, default: int, minimum: int = 1) -> int:
    raw_value = _optional_env(name)
    if raw_value is None:
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise SettingsError(f"Environment variable {name} must be an integer.") from exc
    if value < minimum:
        raise SettingsError(f"Environment variable {name} must be >= {minimum}.")
    return value


def _bool_env(name: str, default: bool) -> bool:
    raw_value = _optional_env(name)
    if raw_value is None:
        return default
    normalized = raw_value.lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise SettingsError(f"Environment variable {name} must be a boolean.")


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


def _load_mysql_settings() -> MySQLConfig:
    return MySQLConfig(
        host=_required_env("DB_HOST"),
        port=_required_int_env("DB_PORT"),
        user=_required_env("DB_USER"),
        password=_required_env("DB_PASSWORD"),
        database=_required_env("DB_NAME"),
        pool_name=_required_env("POOL_NAME"),
        pool_size=_required_int_env("POOL_SIZE"),
        pool_recycle_seconds=_optional_int_env("DB_POOL_RECYCLE_SECONDS", 3600),
        pool_pre_ping=_bool_env("DB_POOL_PRE_PING", True),
    )


def _load_sqlite_settings() -> SQLiteConfig:
    return SQLiteConfig(
        db_path=_optional_env("DB_SQLITE_PATH") or "data/portfolio.db",
    )


def _load_db_settings() -> DatabaseConfig:
    # DB_ENGINE="sqlite" -> SQLiteConfig, aksi halde (varsayılan) MySQLConfig.
    # Bkz. TRANSFORMATION_PLAN.md §2/§9.1 — migration doğrulanana kadar varsayılan mysql kalır.
    engine_name = (_optional_env("DB_ENGINE") or "mysql").lower()
    if engine_name == "sqlite":
        return _load_sqlite_settings()
    return _load_mysql_settings()


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
