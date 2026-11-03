from decimal import Decimal

import threading

from src.application.container import AppContainer
from src.application.events import GlobalEventBus


def test_global_event_bus_emits_price_payload():
    event_bus = GlobalEventBus()
    received = []

    event_bus.prices_updated.connect(received.append)
    payload = {1: Decimal("123.45")}

    event_bus.prices_updated.emit(payload)

    assert received == [payload]


def test_event_bus_is_qt_free_and_isolates_failing_subscribers():
    import src.application.events.event_bus as module

    assert "PySide6" not in open(module.__file__, encoding="utf-8").read()
    bus = GlobalEventBus()
    received = []
    bus.prices_updated.connect(lambda payload: 1 / 0)
    bus.prices_updated.connect(received.append)
    worker = threading.Thread(target=bus.prices_updated.emit, args=({1: Decimal("1")},))
    worker.start()
    worker.join()
    assert received == [{1: Decimal("1")}]


def test_container_uses_default_global_event_bus(monkeypatch):
    class DummySettings:
        db = object()
        ai = object()

    class DummyEngineProvider:
        def __init__(self, db_config):
            self.db_config = db_config

    monkeypatch.setattr("src.application.container.load_app_settings", lambda: DummySettings())
    monkeypatch.setattr("src.application.container.SQLAlchemyEngineProvider", DummyEngineProvider)
    class DummyServices:
        portfolio_analytics_service = object()
        risk_optimization_bridge_service = object()
        stock_360_service = object()
        unified_portfolio_service = object()

    monkeypatch.setattr("src.application.container.build_repositories", lambda _provider: object())
    monkeypatch.setattr("src.application.container.build_market_clients", lambda _provider: object())
    monkeypatch.setattr(
        "src.application.container.build_services",
        lambda repositories, market_clients: DummyServices(),
    )
    monkeypatch.setattr(
        "src.application.container.build_ai",
        lambda _ai, portfolio_analytics_service, risk_optimization_bridge_service, stock_360_service, unified_portfolio_service: object(),
    )
    monkeypatch.setattr("src.application.container.fields", lambda _group: [])

    container = AppContainer()

    assert isinstance(container.event_bus, GlobalEventBus)
