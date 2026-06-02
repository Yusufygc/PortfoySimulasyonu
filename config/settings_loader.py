from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

from src.infrastructure.db.db_config import MySQLConfig


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
    db: MySQLConfig
    ai: AISettings
    market: MarketSettings


def _env_file_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / ".env"
    return Path(__file__).resolve().parents[1] / ".env"


def _load_project_env() -> None:
    env_path = _env_file_path()
    if env_path.exists():
        load_dotenv(env_path, override=False)


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


def _load_db_settings() -> MySQLConfig:
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


def load_settings() -> MySQLConfig:
    return load_app_settings().db
