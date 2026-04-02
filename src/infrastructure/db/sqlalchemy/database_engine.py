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
        self._session_factory = sessionmaker(bind=self._engine, autoflush=False)
        self.Session = scoped_session(self._session_factory)

    def _create_engine(self):
        # Format: mysql+mysqlconnector://user:password@host:port/database
        db_url = f"mysql+mysqlconnector://{self._config.user}:{self._config.password}@{self._config.host}:{self._config.port}/{self._config.database}"
        engine = create_engine(
            db_url,
            pool_recycle=3600,
            pool_size=self._config.pool_size,
            pool_pre_ping=True, # Bağlantı kopmalarını otomatik canlandır
            echo=False 
        )
        return engine

    def get_session(self):
        """
        Her repository operasyonunda kullanmak üzere thread-safe bir veritabanı oturumu döner.
        """
        return self.Session()
