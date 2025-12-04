# src/infrastructure/db/mysql_connection.py

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Generator, Optional

import mysql.connector
from mysql.connector import pooling


@dataclass
class MySQLConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    pool_name: str = "portfoy_pool"
    pool_size: int = 5


class MySQLConnectionProvider:
    """
    MySQL connection pool wrapper.
    Uygulamanın tamamında tek bir instance kullanacaksın.
    """

    def __init__(self, config: MySQLConfig) -> None:
        self._config = config
        self._pool: Optional[pooling.MySQLConnectionPool] = None
        self._init_pool()

    def _init_pool(self) -> None:
        self._pool = pooling.MySQLConnectionPool(
            pool_name=self._config.pool_name,
            pool_size=self._config.pool_size,
            pool_reset_session=True,
            host=self._config.host,
            port=self._config.port,
            user=self._config.user,
            password=self._config.password,
            database=self._config.database,
        )

    @contextmanager
    def get_connection(self) -> Generator[mysql.connector.MySQLConnection, None, None]:
        """
        with provider.get_connection() as conn: şeklinde kullan.
        """
        if self._pool is None:
            self._init_pool()

        conn = self._pool.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
