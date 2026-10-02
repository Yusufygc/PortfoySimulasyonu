import logging
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from src.infrastructure.db.db_config import DatabaseConfig, SQLiteConfig
from src.infrastructure.db.paths import resolve_data_path

logger = logging.getLogger(__name__)


class SQLAlchemyEngineProvider:
    """
    SQLite (işlemsel veritabanı) için SQLAlchemy Engine ve Session üreten Provider.
    """

    def __init__(self, config: DatabaseConfig) -> None:
        self._config = config
        self._engine = self._create_engine()
        self._init_db_schema()
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False)
        self.Session = scoped_session(self._session_factory)

    def _init_db_schema(self) -> None:
        try:
            from src.infrastructure.db.sqlalchemy.orm_models import Base
            Base.metadata.create_all(bind=self._engine, checkfirst=True)
            # Türetilmiş veri: eski stock_id anahtarlı Golden Cross tablosu yerine ticker anahtarlı `cross_events` kullanılır
            with self._engine.begin() as conn:
                conn.exec_driver_sql("DROP TABLE IF EXISTS golden_cross_events")
                # Kanonik ticker uzantısızdır: eski `.IS` kayıtlar çakışma yoksa uzantısıza çevrilir (idempotent)
                conn.exec_driver_sql(
                    "UPDATE stocks SET ticker = substr(ticker, 1, length(ticker) - 3) "
                    "WHERE upper(ticker) LIKE '%.IS' AND NOT EXISTS ("
                    "SELECT 1 FROM stocks s2 WHERE s2.ticker = substr(stocks.ticker, 1, length(stocks.ticker) - 3))"
                )
        except Exception as exc:
            logger.warning("Tablo şemaları oluşturulurken hata veya uyarı: %s", exc)

    def _create_engine(self):
        return self._create_sqlite_engine(self._config)

    @staticmethod
    def _create_sqlite_engine(config: SQLiteConfig):
        db_path = resolve_data_path(config.db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
            echo=False,
        )
        event.listen(
            engine,
            "connect",
            SQLAlchemyEngineProvider._make_sqlite_pragma_listener(config),
        )
        return engine

    @staticmethod
    def _make_sqlite_pragma_listener(config: SQLiteConfig):
        def _apply_pragmas(dbapi_connection, connection_record) -> None:
            cursor = dbapi_connection.cursor()
            cursor.execute(f"PRAGMA journal_mode = {config.journal_mode};")
            cursor.execute(f"PRAGMA synchronous = {config.synchronous};")
            cursor.execute(f"PRAGMA foreign_keys = {'ON' if config.foreign_keys else 'OFF'};")
            cursor.close()
        return _apply_pragmas

    def get_session(self):
        """
        Her repository operasyonunda kullanmak üzere thread-safe bir veritabanı oturumu döner.
        """
        return self.Session()

    def remove_session(self) -> None:
        self.Session.remove()

    def dispose(self) -> None:
        self.remove_session()
        self._engine.dispose()
