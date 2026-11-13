"""Ücret ayarları (komisyon + BSMV, varsayılan 0) ve işlem servislerinde ücretin uygulanması; değerler elle hesaplanmıştır."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest

from src.application.services.assets.asset_ledger_service import AssetLedgerService
from src.application.services.portfolio.trade_entry_service import TradeEntryService, TradeRequest
from src.application.services.settings.fee_settings_service import FeeSettingsService
from src.domain.models.cash_movement import CashMovement
from src.domain.models.fees import FeeRates, calculate_fee
from src.domain.models.stock import Stock
from src.domain.models.trade import TradeSide
from src.domain.ports.repositories.i_app_settings_repo import IAppSettingsRepository

D = Decimal
DAY = date(2026, 3, 2)


class MemorySettings(IAppSettingsRepository):
    def __init__(self):
        self.values = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value


def test_calculate_fee_is_commission_plus_bsmv_on_commission():
    # 10.000 TL x %0,2 = 20 TL komisyon; BSMV %5 -> 1 TL; toplam 21
    assert calculate_fee(D("10000"), D("0.2"), D("5")) == D("21.0000")
    assert calculate_fee(D("10000"), D("0"), D("5")) == D("0.0000")
    assert calculate_fee(D("333.33"), D("0.15"), D("0")) == D("0.5000")  # 0,499995 -> 0,5000


def test_rates_default_to_zero_and_are_persisted_and_validated():
    settings = MemorySettings()
    service = FeeSettingsService(settings)
    assert service.get_rates() == FeeRates()
    assert service.bist_fee(D("5000")) == D("0.0000")

    service.set_rates(FeeRates(D("0.2"), D("0.1"), D("5")))

    again = FeeSettingsService(settings).get_rates()
    assert (again.bist_commission_pct, again.asset_commission_pct, again.bsmv_pct) == (D("0.2"), D("0.1"), D("5"))
    assert service.bist_fee(D("10000")) == D("21.0000") and service.asset_fee(D("10000")) == D("10.5000")
    with pytest.raises(ValueError):
        FeeRates(D("11"), D("0"), D("0"))
    with pytest.raises(ValueError):
        FeeRates(D("0"), D("0"), D("-1"))


def test_corrupt_settings_fall_back_to_zero_fee():
    settings = MemorySettings()
    settings.values["fee.bist_commission_pct"] = "abc"
    settings.values["fee.bsmv_pct"] = "999"
    assert FeeSettingsService(settings).get_rates() == FeeRates()


class FakeStockRepo:
    def __init__(self):
        self.stock = Stock(id=1, ticker="AAA", name="A", currency_code="TRY")

    def get_stock_by_id(self, stock_id):
        return self.stock

    def get_stock_by_ticker(self, ticker):
        return self.stock

    def insert_stock(self, stock):
        return self.stock


class RecordingPortfolio:
    def __init__(self, cash):
        self.cash = cash
        self.saved = []

    def get_cash_balance(self, as_of=None):
        return self.cash

    def validate_trade(self, trade):
        pass

    def add_trade(self, trade):
        self.saved.append(trade)
        return trade


def _entry(cash, rates):
    settings = MemorySettings()
    fees = FeeSettingsService(settings)
    fees.set_rates(rates)
    portfolio = RecordingPortfolio(cash)
    return TradeEntryService(FakeStockRepo(), portfolio, fee_service=fees), portfolio


def test_bist_trade_is_saved_with_fee_and_cash_check_includes_it():
    entry, portfolio = _entry(D("10020"), FeeRates(D("0.2"), D("0"), D("5")))
    request = TradeRequest("AAA", "BUY", 100, D("100"), DAY)  # 10.000 TL + 21 TL ücret = 10.021 > 10.020

    with pytest.raises(ValueError, match="yeterli sermaye"):
        entry.submit_trade(request)

    entry, portfolio = _entry(D("10021"), FeeRates(D("0.2"), D("0"), D("5")))
    result = entry.submit_trade(request)
    assert result.trade.fee == D("21.0000") and portfolio.saved[0].fee == D("21.0000")
    assert entry.estimate_fee(100, D("100")) == D("21.0000")


def test_no_fee_service_means_zero_fee():
    portfolio = RecordingPortfolio(D("100000"))
    entry = TradeEntryService(FakeStockRepo(), portfolio)
    assert entry.submit_trade(TradeRequest("AAA", "BUY", 10, D("100"), DAY)).trade.fee == D("0")


def test_cash_balance_follows_fee_buy_and_sell():  # gerçek PortfolioService ile
    from unittest.mock import MagicMock

    from src.application.services.portfolio.portfolio_service import PortfolioService
    from src.domain.models.trade import Trade

    repo = MagicMock()
    repo.get_all_trades.return_value = [
        Trade.create_buy(1, DAY, 10, D("100"), fee=D("5")),
        Trade.create_sell(1, date(2026, 3, 3), 4, D("120"), fee=D("3")),
    ]
    cash_repo = SimpleNamespace(
        get_all_movements=lambda: [CashMovement.create_deposit(D("2000"), DAY)],
        get_movements_until=lambda d, t=None: [CashMovement.create_deposit(D("2000"), DAY)],
    )
    service = PortfolioService(repo, MagicMock(), cash_movement_repo=cash_repo)

    # 2000 - (1000 + 5) + (480 - 3) = 1472
    assert service.get_cash_balance() == D("1472")


class _AssetRepo:
    def __init__(self, asset):
        self.asset = asset

    def get_asset(self, asset_id):
        return self.asset


class _TradeRepo:
    def __init__(self):
        self.trades = []

    def list_trades(self, asset_id=None):
        return list(self.trades)

    def add_trade(self, trade):
        self.trades.append(trade)
        return trade


def _ledger(rates):
    from src.domain.models.asset import Asset, AssetClass

    fees = FeeSettingsService(MemorySettings())
    fees.set_rates(rates)
    asset = Asset(id=1, symbol="BTC", name="Bitcoin", asset_class=AssetClass.CRYPTO, quote_currency="USD", yf_symbol="BTC-USD")
    trades = _TradeRepo()
    return AssetLedgerService(_AssetRepo(asset), trades, fee_service=fees), trades


def test_asset_trade_fee_from_settings_or_explicit_override():
    ledger, trades = _ledger(FeeRates(D("0"), D("0.5"), D("5")))

    auto = ledger.record_trade(1, TradeSide.BUY, "2", "1000", trade_date=DAY, fx_rate_to_try="30")
    manual = ledger.record_trade(1, TradeSide.BUY, "1", "1000", trade_date=DAY, fx_rate_to_try="30", fee="7")

    # 2 x 1000 = 2000 USD x %0,5 = 10 USD komisyon + %5 BSMV 0,5 = 10,5
    assert auto.fee == D("10.5000") and manual.fee == D("7")
    with pytest.raises(ValueError):
        ledger.record_trade(1, TradeSide.BUY, "1", "1000", fx_rate_to_try="30", fee="-1")
    assert len(trades.trades) == 2


def test_asset_trade_without_fee_service_has_zero_fee():
    from src.domain.models.asset import Asset, AssetClass

    asset = Asset(id=1, symbol="BTC", name="Bitcoin", asset_class=AssetClass.CRYPTO, quote_currency="USD", yf_symbol="BTC-USD")
    ledger = AssetLedgerService(_AssetRepo(asset), _TradeRepo())
    assert ledger.record_trade(1, TradeSide.BUY, "1", "1000", fx_rate_to_try="30").fee == D("0")
