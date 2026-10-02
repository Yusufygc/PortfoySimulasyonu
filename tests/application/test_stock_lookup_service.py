"""StockLookupService: arayüz denetleyicileri için salt okunur hisse/fiyat sorguları."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

from src.application.services.market.stock_lookup_service import StockLookupService


def _service(**overrides):
    parts = dict(stock_repo=MagicMock(), price_repo=MagicMock(), latest_price_repo=MagicMock(), market_history_repo=MagicMock())
    parts.update(overrides)
    return StockLookupService(**parts), parts


def test_get_stocks_returns_map_and_skips_missing_ids():
    service, parts = _service()
    parts["stock_repo"].get_stocks_by_ids.return_value = [SimpleNamespace(id=1, ticker="THYAO"), SimpleNamespace(id=2, ticker="ASELS")]

    result = service.get_stocks([1, 2, 2, 3])

    parts["stock_repo"].get_stocks_by_ids.assert_called_once_with([1, 2, 3])
    assert set(result) == {1, 2} and result[2].ticker == "ASELS"
    assert service.get_stocks([]) == {}


def test_repository_errors_return_empty_results_instead_of_raising():
    service, parts = _service()
    parts["stock_repo"].get_stock_by_id.side_effect = RuntimeError("db")
    parts["stock_repo"].get_stock_by_ticker.side_effect = RuntimeError("db")
    parts["stock_repo"].get_all_stocks.side_effect = RuntimeError("db")
    parts["price_repo"].get_price_series.side_effect = RuntimeError("db")
    parts["price_repo"].get_last_price_before.side_effect = RuntimeError("db")
    parts["latest_price_repo"].get_latest_price_map.side_effect = RuntimeError("db")

    assert service.get_stock(1) is None and service.find_stock("THYAO") is None and service.list_stocks() == []
    assert service.get_price_series(1, date(2026, 1, 1), date(2026, 2, 1)) == []
    assert service.get_previous_close(1) is None
    assert service.get_latest_price_map([1]) == {}


def test_previous_close_ignores_non_positive_values():
    service, parts = _service()
    parts["price_repo"].get_last_price_before.return_value = SimpleNamespace(close_price=Decimal("12.5"))
    assert service.get_previous_close(1) == Decimal("12.5")

    parts["price_repo"].get_last_price_before.return_value = SimpleNamespace(close_price=Decimal("0"))
    assert service.get_previous_close(1) is None
    parts["price_repo"].get_last_price_before.return_value = None
    assert service.get_previous_close(1) is None


def test_latest_close_looks_stock_up_by_ticker():
    service, parts = _service()
    parts["stock_repo"].get_stock_by_ticker.return_value = SimpleNamespace(id=5)
    parts["price_repo"].get_last_price_before.return_value = SimpleNamespace(close_price=Decimal("30"))

    assert service.get_latest_close("THYAO.IS") == Decimal("30")
    parts["stock_repo"].get_stock_by_ticker.return_value = None
    assert service.get_latest_close("YOKTUR") is None


def test_market_reads_use_plain_ticker_and_degrade_without_history_repo():
    service, parts = _service()
    parts["market_history_repo"].get_last_bars.return_value = ["bar"]
    parts["market_history_repo"].get_company_name.return_value = "Türk Hava Yolları"

    assert service.get_last_market_bars("thyao.is", 2) == ["bar"]
    parts["market_history_repo"].get_last_bars.assert_called_once_with("THYAO", 2)
    assert service.get_market_company_name("THYAO.IS") == "Türk Hava Yolları"

    bare, _ = _service(market_history_repo=None)
    assert bare.get_market_bars("THYAO", date(2026, 1, 1), date(2026, 2, 1)) == []
    assert bare.get_last_market_bars("THYAO", 2) == [] and bare.get_market_company_name("THYAO") is None
