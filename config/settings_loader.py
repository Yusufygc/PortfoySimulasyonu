# config/settings_loader.py

from __future__ import annotations
import os
from dotenv import load_dotenv
from src.infrastructure.db.mysql_connection import MySQLConfig

def load_settings() -> MySQLConfig:
    """
    .env dosyasını okuyarak MySQLConfig nesnesi oluşturur.
    """
    load_dotenv()  # .env otomatik yukarıya doğru taranır (Geliştirme ortamı için)

    # Exe modunda (Nuitka/PyInstaller) .env dosyasını temp klasöründen oku (Gömülü dosya)
    import sys
    if getattr(sys, 'frozen', False):
        # Nuitka onefile modunda dosya temp klasörüne açılır.
        # Bu dosya: config/settings_loader.py. İki üst klasör root'tur.
        base_path = os.path.dirname(os.path.dirname(__file__))
        env_path = os.path.join(base_path, '.env')
        
        if os.path.exists(env_path):
            load_dotenv(env_path)
    
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
