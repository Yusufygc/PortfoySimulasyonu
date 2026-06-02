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


def test_auto_corporate_action_discovery_unavailable_is_silent(monkeypatch):
    successes = []
    window = SimpleNamespace(_settings=DummySettings())
    result = SimpleNamespace(saved_count=0, source_unavailable=True, errors=["KAP source 404"])
    monkeypatch.setattr("src.ui.main_window.Toast.success", lambda _parent, message: successes.append(message))

    MainWindow._on_auto_corporate_action_discovery_success(window, result)

    assert window._settings.synced is True
    assert successes == []
