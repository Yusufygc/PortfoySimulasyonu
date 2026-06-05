from types import SimpleNamespace

from src.ui.main_window import MainWindow


class DummySettings:
    def __init__(self):
        self.values = {}
        self.synced = False

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
