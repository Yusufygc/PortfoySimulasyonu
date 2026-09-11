# src/infrastructure/db/sqlalchemy/database_engine.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from src.infrastructure.db.db_config import MySQLConfig


class SQLAlchemyEngineProvider:
    """
    SQLAlchemy için Engine ve Session üreten Provider.
    Eski (Ham SQL) 'MySQLConnectionProvider' yapısının ORM muadilidir.
    """

    def __init__(self, config: MySQLConfig) -> None:
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
        # Format: mysql+mysqlconnector://user:password@host:port/database
        db_url = f"mysql+mysqlconnector://{self._config.user}:{self._config.password}@{self._config.host}:{self._config.port}/{self._config.database}"
        engine = create_engine(
            db_url,
            pool_recycle=self._config.pool_recycle_seconds,
            pool_size=self._config.pool_size,
            pool_pre_ping=self._config.pool_pre_ping,
            echo=False 
        )
        return engine

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
