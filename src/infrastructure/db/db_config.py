# src/infrastructure/db/db_config.py

from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class MySQLConfig:
    """
    Veritabanı bağlantı parametrelerini taşıyan immutable config nesnesi.
    Tüm değerler .env dosyasından settings_loader aracılığıyla sağlanmalıdır.
    """
    host: str
    port: int
    user: str
    password: str
    database: str
    pool_name: str
    pool_size: int
    pool_recycle_seconds: int = 3600
    pool_pre_ping: bool = True


@dataclass(frozen=True)
class SQLiteConfig:
    """
    SQLite bağlantı parametrelerini taşıyan immutable config nesnesi.
    Bkz. TRANSFORMATION_PLAN.md §2 — MySQL ➔ SQLite geçişi.
    """
    db_path: str = "data/portfolio.db"
    journal_mode: str = "WAL"
    synchronous: str = "NORMAL"
    foreign_keys: bool = True


DatabaseConfig = MySQLConfig | SQLiteConfig
