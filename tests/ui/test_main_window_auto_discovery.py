from datetime import date
from types import SimpleNamespace

from src.ui.main_window import MainWindow


class DummySettings:
    def __init__(self):
        self.values = {}
        self.synced = False

    def value(self, key, default=None, type=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value

    def sync(self):
        self.synced = True


class DummySignal:
    def __init__(self):
        self.connected = []

    def connect(self, callback):
        self.connected.append(callback)


def test_auto_corporate_action_discovery_unavailable_is_silent(monkeypatch):
    successes = []
    window = SimpleNamespace(_settings=DummySettings())
    result = SimpleNamespace(saved_count=0, source_unavailable=True, errors=["KAP source 404"])
    monkeypatch.setattr("src.ui.main_window.Toast.success", lambda _parent, message: successes.append(message))

    MainWindow._on_auto_corporate_action_discovery_success(window, result)

    assert window._settings.synced is True
    assert successes == []


def test_main_window_connects_model_portfolio_price_persister():
    signal = DummySignal()
    window = MainWindow.__new__(MainWindow)
    window.container = SimpleNamespace(
        event_bus=SimpleNamespace(prices_updated=signal),
        model_portfolio_service=object(),
    )

    MainWindow._connect_model_portfolio_price_persister(window)

    assert len(signal.connected) == 1
    assert signal.connected[0] == window._model_portfolio_price_event_persister.on_prices_updated


def test_auto_price_backfill_uses_last_completed_trading_day(monkeypatch):
    started_workers = []

    class DummyWorker:
        def __init__(self, fn, *args):
            self.fn = fn
            self.args = args
            self.signals = SimpleNamespace(
                result=SimpleNamespace(connect=lambda callback: None),
                error=SimpleNamespace(connect=lambda callback: None),
            )

    class DummyThreadPool:
        def start(self, worker):
            started_workers.append(worker)

    class DummyTradingCalendar:
        def is_trading_day(self, point_date):
            return point_date.weekday() < 5

    monkeypatch.setattr("src.ui.main_window.Worker", DummyWorker)
    monkeypatch.setattr("src.ui.main_window.date", SimpleNamespace(today=lambda: date(2026, 6, 8)))

    window = MainWindow.__new__(MainWindow)
    window._settings = DummySettings()
    window._threadpool = DummyThreadPool()
    window.container = SimpleNamespace(
        price_data_health_service=SimpleNamespace(update_from_latest_to_today=lambda target_date: None),
        trading_calendar=DummyTradingCalendar(),
    )

    MainWindow._start_auto_price_backfill_once(window)

    assert len(started_workers) == 1
    assert started_workers[0].args == (date(2026, 6, 5),)
