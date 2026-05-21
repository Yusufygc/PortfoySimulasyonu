from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from src.infrastructure.db.db_config import MySQLConfig


class SettingsError(RuntimeError):
    pass


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


def _required_int_env(name: str, minimum: int = 1) -> int:
    raw_value = _required_env(name)
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise SettingsError(f"Environment variable {name} must be an integer.") from exc
    if value < minimum:
        raise SettingsError(f"Environment variable {name} must be >= {minimum}.")
    return value


def load_settings() -> MySQLConfig:
    _load_project_env()

    return MySQLConfig(
        host=_required_env("DB_HOST"),
        port=_required_int_env("DB_PORT"),
        user=_required_env("DB_USER"),
        password=_required_env("DB_PASSWORD"),
        database=_required_env("DB_NAME"),
        pool_name=_required_env("POOL_NAME"),
        pool_size=_required_int_env("POOL_SIZE"),
    )
