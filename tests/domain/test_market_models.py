from datetime import date
from decimal import Decimal

import pytest

from src.domain.models.daily_price import DailyPrice
from src.domain.models.stock import Stock


def test_stock_normalizes_ticker_and_currency():
    stock = Stock(id=None, ticker=" asels.is ", name="ASELS", currency_code=" try ")

    assert stock.ticker == "ASELS.IS"
    assert stock.currency_code == "TRY"


def test_stock_rejects_missing_ticker_or_currency():
    with pytest.raises(ValueError, match="Ticker"):
        Stock(id=None, ticker="")

    with pytest.raises(ValueError, match="Currency"):
        Stock(id=None, ticker="ASELS.IS", currency_code="")


def test_daily_price_normalizes_decimal_currency_and_source():
    price = DailyPrice(
        id=None,
        stock_id=1,
        price_date=date(2026, 1, 1),
        close_price="12.34",
        currency_code=" try ",
        source=" yfinance ",
    )

    assert price.close_price == Decimal("12.34")
    assert price.currency_code == "TRY"
    assert price.source == "yfinance"


def test_daily_price_rejects_invalid_values():
    with pytest.raises(ValueError, match="Stock id"):
        DailyPrice(id=None, stock_id=0, price_date=date(2026, 1, 1), close_price=Decimal("1"))

    with pytest.raises(ValueError, match="Close price"):
        DailyPrice(id=None, stock_id=1, price_date=date(2026, 1, 1), close_price=Decimal("0"))

    with pytest.raises(ValueError, match="Currency"):
        DailyPrice(id=None, stock_id=1, price_date=date(2026, 1, 1), close_price=Decimal("1"), currency_code="")

    with pytest.raises(ValueError, match="source"):
        DailyPrice(id=None, stock_id=1, price_date=date(2026, 1, 1), close_price=Decimal("1"), source="")


def test_daily_price_ohlcv_fields_default_to_none():
    price = DailyPrice(id=None, stock_id=1, price_date=date(2026, 1, 1), close_price=Decimal("1"))

    assert price.open_price is None
    assert price.high_price is None
    assert price.low_price is None
    assert price.volume is None


def test_daily_price_normalizes_ohlcv_fields():
    price = DailyPrice(
        id=None,
        stock_id=1,
        price_date=date(2026, 1, 1),
        close_price=Decimal("12.34"),
        open_price="12.00",
        high_price="12.50",
        low_price="11.90",
        volume=1_000_000,
    )

    assert price.open_price == Decimal("12.00")
    assert price.high_price == Decimal("12.50")
    assert price.low_price == Decimal("11.90")
    assert price.volume == 1_000_000


def test_daily_price_rejects_invalid_ohlcv_values():
    with pytest.raises(ValueError, match="OHLC"):
        DailyPrice(id=None, stock_id=1, price_date=date(2026, 1, 1), close_price=Decimal("1"), high_price=Decimal("0"))

    with pytest.raises(ValueError, match="Volume"):
        DailyPrice(id=None, stock_id=1, price_date=date(2026, 1, 1), close_price=Decimal("1"), volume=-1)
