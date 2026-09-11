# src/infrastructure/db/sqlalchemy/database_engine.py

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, scoped_session
from src.infrastructure.db.db_config import DatabaseConfig, MySQLConfig, SQLiteConfig


class SQLAlchemyEngineProvider:
    """
    SQLAlchemy için Engine ve Session üreten Provider.
    Eski (Ham SQL) 'MySQLConnectionProvider' yapısının ORM muadilidir.
    MySQLConfig ve SQLiteConfig'i dialect'e göre ayırt ederek destekler
    (bkz. TRANSFORMATION_PLAN.md §2 — MySQL ➔ SQLite geçişi).
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
        except Exception:
            pass

    def _create_engine(self):
        if isinstance(self._config, SQLiteConfig):
            return self._create_sqlite_engine(self._config)
        return self._create_mysql_engine(self._config)

    @staticmethod
    def _create_mysql_engine(config: MySQLConfig):
        # Format: mysql+mysqlconnector://user:password@host:port/database
        db_url = f"mysql+mysqlconnector://{config.user}:{config.password}@{config.host}:{config.port}/{config.database}"
        return create_engine(
            db_url,
            pool_recycle=config.pool_recycle_seconds,
            pool_size=config.pool_size,
            pool_pre_ping=config.pool_pre_ping,
            echo=False,
        )

    @staticmethod
    def _create_sqlite_engine(config: SQLiteConfig):
        db_path = Path(config.db_path)
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
