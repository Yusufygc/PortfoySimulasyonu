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
