from decimal import Decimal

from src.ui.shared.price_event_publisher import publish_prices_updated


def test_publish_prices_updated_skips_empty_payload(fake_event_bus):
    assert publish_prices_updated(fake_event_bus, {}) is False
    assert publish_prices_updated(fake_event_bus, None) is False

    assert fake_event_bus.prices_updated.emitted == []


def test_publish_prices_updated_emits_decimal_payload_copy(fake_event_bus):
    payload = {1: Decimal("123.45")}

    assert publish_prices_updated(fake_event_bus, payload) is True

    assert fake_event_bus.prices_updated.emitted == [{1: Decimal("123.45")}]
    assert fake_event_bus.prices_updated.emitted[0] is not payload
