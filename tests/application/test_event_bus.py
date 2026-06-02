from decimal import Decimal

import pytest

pytest.importorskip("PyQt5")

from src.application.container import AppContainer
from src.application.events import GlobalEventBus


def test_global_event_bus_emits_price_payload():
    event_bus = GlobalEventBus()
    received = []

    event_bus.prices_updated.connect(received.append)
    payload = {1: Decimal("123.45")}

    event_bus.prices_updated.emit(payload)

    assert received == [payload]


def test_container_uses_default_global_event_bus(monkeypatch):
    class DummySettings:
        db = object()

    class DummyEngineProvider:
        def __init__(self, db_config):
            self.db_config = db_config

    monkeypatch.setattr("src.application.container.load_app_settings", lambda: DummySettings())
    monkeypatch.setattr("src.application.container.SQLAlchemyEngineProvider", DummyEngineProvider)
    monkeypatch.setattr("src.application.container.build_repositories", lambda _provider: object())
    monkeypatch.setattr("src.application.container.build_market_clients", lambda _provider: object())
    monkeypatch.setattr(
        "src.application.container.build_services",
        lambda repositories, market_clients, event_bus: object(),
    )
    monkeypatch.setattr("src.application.container.fields", lambda _group: [])

    container = AppContainer()

    assert isinstance(container.event_bus, GlobalEventBus)
