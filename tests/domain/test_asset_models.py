"""Varlık defteri domain modelleri: Asset, AssetTrade, AssetPosition, AssetLedger, fiyat ve kur kayıtları."""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

import pytest

from src.domain.models.asset import Asset, AssetClass, AssetUnit
from src.domain.models.asset_position import AssetLedger, AssetPosition
from src.domain.models.asset_price import AssetLatestPrice, AssetPrice, FxRate
from src.domain.models.asset_trade import AssetTrade
from src.domain.models.trade import TradeSide

D = Decimal


def make_asset(**overrides) -> Asset:
    values = dict(
        id=1, symbol="btc", name="Bitcoin", asset_class=AssetClass.CRYPTO,
        quote_currency="usd", yf_symbol="BTC-USD",
    )
    values.update(overrides)
    return Asset(**values)


def make_trade(side=TradeSide.BUY, quantity="1", price="100", fx="1", day=date(2026, 1, 1), asset_id=1, trade_time=None, trade_id=None):
    return AssetTrade(
        id=trade_id, asset_id=asset_id, trade_date=day, trade_time=trade_time, side=side,
        quantity=D(quantity), price=D(price), fx_rate_to_try=D(fx),
    )


class TestAsset:
    def test_normalizes_symbol_and_currency(self):
        asset = make_asset(symbol=" btc ", quote_currency="usd")

        assert asset.symbol == "BTC"
        assert asset.quote_currency == "USD"
        assert asset.unit == AssetUnit.UNIT
        assert asset.is_active

    def test_accepts_enum_values_as_strings(self):
        asset = make_asset(asset_class="PRECIOUS_METAL", unit="OUNCE")

        assert asset.asset_class == AssetClass.PRECIOUS_METAL
        assert asset.unit == AssetUnit.OUNCE

    @pytest.mark.parametrize(
        "override",
        [{"symbol": " "}, {"name": ""}, {"quote_currency": "US"}, {"yf_symbol": ""}, {"asset_class": "STOCK"}, {"unit": "KG"}],
    )
    def test_rejects_invalid_fields(self, override):
        with pytest.raises(ValueError):
            make_asset(**override)

    def test_is_try_quoted(self):
        assert make_asset(quote_currency="TRY").is_try_quoted
        assert not make_asset(quote_currency="USD").is_try_quoted


class TestAssetTrade:
    def test_total_amounts(self):
        trade = make_trade(quantity="0.5", price="60000", fx="34")

        assert trade.total_amount == D("30000")
        assert trade.total_amount_try == D("1020000")

    def test_accepts_fractional_quantity(self):
        assert make_trade(quantity="0.00000001").quantity == D("0.00000001")

    def test_rejects_float_inputs(self):
        with pytest.raises(TypeError):
            AssetTrade(id=None, asset_id=1, trade_date=date(2026, 1, 1), trade_time=None, side=TradeSide.BUY, quantity=0.5, price=D("1"))

    @pytest.mark.parametrize("override", [{"quantity": "0"}, {"price": "0"}, {"fx": "0"}, {"quantity": "-1"}])
    def test_rejects_non_positive_values(self, override):
        with pytest.raises(ValueError):
            make_trade(**override)

    def test_rejects_unknown_side(self):
        with pytest.raises(ValueError):
            AssetTrade(id=None, asset_id=1, trade_date=date(2026, 1, 1), trade_time=None, side="HOLD", quantity=D("1"), price=D("1"))


class TestAssetPosition:
    def test_weighted_average_cost_in_both_currencies(self):
        position = AssetPosition.from_trades(1, [
            make_trade(quantity="1", price="100", fx="30", day=date(2026, 1, 1)),
            make_trade(quantity="3", price="200", fx="40", day=date(2026, 1, 2)),
        ])

        assert position.total_quantity == D("4")
        assert position.total_cost == D("700")
        assert position.average_cost == D("175")
        assert position.total_cost_try == D("3000") + D("24000")

    def test_sell_realizes_pl_using_average_cost(self):
        position = AssetPosition.from_trades(1, [
            make_trade(quantity="2", price="100", fx="30", day=date(2026, 1, 1)),
            make_trade(TradeSide.SELL, quantity="1", price="150", fx="40", day=date(2026, 1, 2)),
        ])

        assert position.total_quantity == D("1")
        assert position.total_cost == D("100")
        assert position.realized_pl == D("50")
        # satış 150*40=6000 TRY, satılan maliyet 100*30=3000 TRY
        assert position.realized_pl_try == D("3000")
        assert position.total_cost_try == D("3000")

    def test_closing_position_resets_cost(self):
        position = AssetPosition.from_trades(1, [
            make_trade(quantity="1.5", price="10", day=date(2026, 1, 1)),
            make_trade(TradeSide.SELL, quantity="1.5", price="12", day=date(2026, 1, 2)),
        ])

        assert position.total_quantity == D("0")
        assert position.total_cost == D("0")
        assert position.total_cost_try == D("0")
        assert position.average_cost is None
        assert not position.is_open

    def test_oversell_raises(self):
        with pytest.raises(ValueError):
            AssetPosition.from_trades(1, [
                make_trade(quantity="1", day=date(2026, 1, 1)),
                make_trade(TradeSide.SELL, quantity="1.0000001", day=date(2026, 1, 2)),
            ])

    def test_market_value_and_unrealized_pl(self):
        position = AssetPosition.from_trades(1, [make_trade(quantity="2", price="100")])

        assert position.market_value(D("130")) == D("260")
        assert position.unrealized_pl(D("130")) == D("60")

    def test_trades_apply_in_date_then_time_order(self):
        position = AssetPosition.from_trades(1, [
            make_trade(TradeSide.SELL, quantity="1", day=date(2026, 1, 1), trade_time=time(15, 0)),
            make_trade(quantity="1", day=date(2026, 1, 1), trade_time=time(10, 0)),
        ])

        assert position.total_quantity == D("0")

    def test_rejects_trade_of_another_asset(self):
        with pytest.raises(ValueError):
            AssetPosition(asset_id=1).apply_trade(make_trade(asset_id=2))


class TestAssetLedger:
    def test_builds_positions_per_asset(self):
        ledger = AssetLedger.from_trades([
            make_trade(asset_id=1, quantity="1"),
            make_trade(asset_id=2, quantity="5"),
            make_trade(TradeSide.SELL, asset_id=2, quantity="5", day=date(2026, 1, 2)),
        ])

        assert set(ledger.positions) == {1, 2}
        assert [p.asset_id for p in ledger.open_positions()] == [1]
        assert ledger.get_position(3) is None

    def test_empty_ledger(self):
        assert AssetLedger.from_trades([]).open_positions() == []


class TestPriceAndFxRecords:
    def test_asset_price_normalizes_currency_and_rejects_non_positive(self):
        price = AssetPrice(None, 1, date(2026, 1, 1), D("10.5"), "usd", "yfinance")
        assert price.currency_code == "USD"
        with pytest.raises(ValueError):
            AssetPrice(None, 1, date(2026, 1, 1), D("0"), "USD", "yfinance")

    def test_latest_price_requires_source(self):
        now = datetime(2026, 1, 1, 12, 0)
        with pytest.raises(ValueError):
            AssetLatestPrice(None, 1, D("1"), "USD", now, " ", now)

    def test_fx_rate_pair_and_validation(self):
        rate = FxRate(None, "usd", "try", date(2026, 1, 1), D("34.5"), "yfinance")
        assert rate.pair == "USDTRY"
        with pytest.raises(ValueError):
            FxRate(None, "USD", "USD", date(2026, 1, 1), D("1"), "yfinance")
        with pytest.raises(ValueError):
            FxRate(None, "USD", "TRY", date(2026, 1, 1), D("-1"), "yfinance")
