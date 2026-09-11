from src.infrastructure.db.db_config import MySQLConfig, SQLiteConfig
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


def test_database_engine_uses_sqlite_url_and_connect_args(monkeypatch, tmp_path):
    calls = []

    def fake_create_engine(db_url, **kwargs):
        calls.append((db_url, kwargs))
        return object()

    monkeypatch.setattr(database_engine, "create_engine", fake_create_engine)
    monkeypatch.setattr(database_engine, "event", type("_E", (), {"listen": staticmethod(lambda *a, **k: None)}))

    db_path = tmp_path / "portfolio.db"
    config = SQLiteConfig(db_path=str(db_path))

    database_engine.SQLAlchemyEngineProvider(config)

    assert calls == [
        (
            f"sqlite:///{db_path}",
            {"connect_args": {"check_same_thread": False}, "echo": False},
        )
    ]
    assert db_path.parent.exists()


def test_sqlite_pragma_listener_applies_configured_pragmas():
    config = SQLiteConfig(journal_mode="WAL", synchronous="NORMAL", foreign_keys=True)
    listener = database_engine.SQLAlchemyEngineProvider._make_sqlite_pragma_listener(config)

    executed = []

    class FakeCursor:
        def execute(self, sql):
            executed.append(sql)

        def close(self):
            pass

    class FakeConnection:
        def cursor(self):
            return FakeCursor()

    listener(FakeConnection(), connection_record=None)

    assert executed == [
        "PRAGMA journal_mode = WAL;",
        "PRAGMA synchronous = NORMAL;",
        "PRAGMA foreign_keys = ON;",
    ]


def test_sqlite_engine_creates_real_schema(tmp_path):
    db_path = tmp_path / "real_portfolio.db"
    config = SQLiteConfig(db_path=str(db_path))

    provider = database_engine.SQLAlchemyEngineProvider(config)

    assert db_path.exists()

    from sqlalchemy import inspect
    inspector = inspect(provider._engine)
    table_names = inspector.get_table_names()
    assert "stocks" in table_names
    assert "trades" in table_names

    provider.dispose()
