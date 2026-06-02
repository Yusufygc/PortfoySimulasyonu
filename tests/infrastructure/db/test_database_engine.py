from src.infrastructure.db.db_config import MySQLConfig
from src.infrastructure.db.sqlalchemy import database_engine


def test_database_engine_uses_pool_config(monkeypatch):
    calls = []

    def fake_create_engine(db_url, **kwargs):
        calls.append((db_url, kwargs))
        return object()

    monkeypatch.setattr(database_engine, "create_engine", fake_create_engine)

    config = MySQLConfig(
        host="localhost",
        port=3306,
        user="user",
        password="password",
        database="portfoySim",
        pool_name="portfoy_pool",
        pool_size=7,
        pool_recycle_seconds=120,
        pool_pre_ping=False,
    )

    database_engine.SQLAlchemyEngineProvider(config)

    assert calls == [
        (
            "mysql+mysqlconnector://user:password@localhost:3306/portfoySim",
            {
                "pool_recycle": 120,
                "pool_size": 7,
                "pool_pre_ping": False,
                "echo": False,
            },
        )
    ]
