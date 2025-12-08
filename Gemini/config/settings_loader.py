# config/settings_loader.py

from __future__ import annotations
import os
from dotenv import load_dotenv
from src.infrastructure.db.mysql_connection import MySQLConfig

def load_settings() -> MySQLConfig:
    """
    .env dosyasını okuyarak MySQLConfig nesnesi oluşturur.
    """
    load_dotenv()  # .env otomatik yukarıya doğru taranır

    host = os.getenv("DB_HOST", "localhost")
    port = int(os.getenv("DB_PORT", "3306"))
    user = os.getenv("DB_USER", "root")
    password = os.getenv("DB_PASSWORD", "")
    database = os.getenv("DB_NAME", "portfoySim")

    pool_name = os.getenv("POOL_NAME", "portfoy_pool")
    pool_size = int(os.getenv("POOL_SIZE", "5"))

    return MySQLConfig(
        host=host,
        port=port,
        user=user,
        password=password,
        database=database,
        pool_name=pool_name,
        pool_size=pool_size,
    )
