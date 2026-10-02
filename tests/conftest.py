import sys
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


@pytest.fixture(scope="session", autouse=True)
def _isolated_databases(tmp_path_factory):
    """Gerçek `AppContainer()` kullanan testler gerçek veritabanlarına yazmasın.

    Gerçek `data/portfolio.db` (tutarlı SQLite yedekleme API'siyle) ve `data/market_history.duckdb` oturum başına
    geçici bir klasöre kopyalanır; `DB_SQLITE_PATH`/`DUCKDB_PATH` oraya yönlendirilir. Kopya alınamazsa
    (dosya yok/kilitli) boş geçici veritabanları kullanılır; gerçek dosyalara asla yazılmaz.
    """
    import os
    import shutil
    import sqlite3

    from src.infrastructure.db.paths import duckdb_path, sqlite_db_path

    work = tmp_path_factory.mktemp("isolated_db")
    real_sqlite, real_duck = sqlite_db_path(), duckdb_path()
    test_sqlite, test_duck = work / "portfolio.db", work / "market_history.duckdb"
    if real_sqlite.exists():
        try:
            src, dst = sqlite3.connect(real_sqlite), sqlite3.connect(test_sqlite)
            try:
                src.backup(dst)
            finally:
                dst.close()
                src.close()
        except Exception:
            test_sqlite.unlink(missing_ok=True)
    if real_duck.exists():
        try:
            shutil.copy2(real_duck, test_duck)
        except Exception:
            test_duck.unlink(missing_ok=True)

    previous = {key: os.environ.get(key) for key in ("DB_SQLITE_PATH", "DUCKDB_PATH")}
    os.environ["DB_SQLITE_PATH"] = str(test_sqlite)
    os.environ["DUCKDB_PATH"] = str(test_duck)
    yield work
    for key, value in previous.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


@pytest.fixture(autouse=True)
def _isolate_env_file(tmp_path, monkeypatch):
    """Testler gerçek .env dosyasına (API anahtarı kaydı vb.) asla yazmasın."""
    import config.settings_loader as settings_loader

    monkeypatch.setattr(settings_loader, "_env_write_path", lambda: tmp_path / ".env")


def pytest_collection_modifyitems(config, items):
    for item in items:
        path = Path(str(item.fspath)).as_posix()
        if "/tests/ui/" in path or path.startswith("tests/ui/"):
            item.add_marker(pytest.mark.ui)
        if path.endswith("tests/infrastructure/market_data/test_benchmark_fetch_manual.py"):
            item.add_marker(pytest.mark.manual)
            item.add_marker(pytest.mark.network)


@pytest.fixture
def fixed_today() -> date:
    return date(2026, 6, 2)


class _DummySignal:
    def __init__(self):
        self.emitted = []
        self.connected = []

    def connect(self, callback):
        self.connected.append(callback)

    def emit(self, payload):
        self.emitted.append(payload)
        for callback in self.connected:
            callback(payload)


class _FakeEventBus:
    def __init__(self):
        self.prices_updated = _DummySignal()


@pytest.fixture
def fake_event_bus():
    return _FakeEventBus()


@pytest.fixture
def qapp():
    pytest.importorskip("PySide6")
    from src.qt_compat.qtwidgets import QApplication

    return QApplication.instance() or QApplication(sys.argv)


@pytest.fixture
def drain_qt_events(qapp):
    pytest.importorskip("PySide6")
    from src.qt_compat.qtcore import QThreadPool

    def _drain(timeout_ms: int = 1000):
        QThreadPool.globalInstance().waitForDone(timeout_ms)
        qapp.processEvents()
        return qapp

    return _drain


@pytest.fixture
def sample_stock_factory():
    from src.domain.models.stock import Stock

    def _build(stock_id=1, ticker="ASELS.IS", name="ASELS", currency_code="TRY"):
        return Stock(id=stock_id, ticker=ticker, name=name, currency_code=currency_code)

    return _build


@pytest.fixture
def sample_trade_factory(fixed_today):
    from src.domain.models.trade import Trade, TradeSide

    def _build(
        stock_id=1,
        side=TradeSide.BUY,
        quantity=10,
        price=Decimal("12.50"),
        trade_date=None,
        trade_time=None,
        trade_id=None,
    ):
        return Trade(
            id=trade_id,
            stock_id=stock_id,
            trade_date=trade_date or fixed_today,
            trade_time=trade_time,
            side=side,
            quantity=quantity,
            price=Decimal(str(price)),
        )

    return _build


@pytest.fixture
def sample_daily_price_factory(fixed_today):
    from src.domain.models.daily_price import DailyPrice

    def _build(
        stock_id=1,
        price_date=None,
        close_price=Decimal("12.50"),
        currency_code="TRY",
        source="test",
        price_id=None,
    ):
        return DailyPrice(
            id=price_id,
            stock_id=stock_id,
            price_date=price_date or fixed_today,
            close_price=Decimal(str(close_price)),
            currency_code=currency_code,
            source=source,
        )

    return _build
