# src/infrastructure/db/db_config.py

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class SQLiteConfig:
    """SQLite (işlemsel veritabanı) bağlantı parametrelerini taşıyan immutable config nesnesi."""
    db_path: str = "data/portfolio.db"
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    foreign_keys: bool = True


DatabaseConfig = SQLiteConfig
