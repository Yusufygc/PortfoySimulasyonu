"""Ortak nakit havuzu (TL + USD): döviz al/sat, nakde bağlı varlık işlemleri ve BIST alım gücü.

Gerçek geçici SQLite ve gerçek servislerle; beklenen değerler elle hesaplanmıştır.
"""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal

import pytest

from src.application.container import AppContainer
from src.domain.models.asset import Asset, AssetClass, AssetUnit
from src.domain.models.fx_conversion import FxConversion, FxSide
from src.domain.models.trade import Trade, TradeSide

D = Decimal
DAY = date(2026, 1, 5)


@pytest.fixture
def container(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_SQLITE_PATH", str(tmp_path / "pool.db"))
    return AppContainer()


@pytest.fixture
def btc(container):
    return container.asset_repo.add_asset(Asset(None, "BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD"))


@pytest.fixture
def gold_try(container):
    return container.asset_repo.add_asset(
        Asset(None, "GAU", "Gram altın", AssetClass.PRECIOUS_METAL, "TRY", "GC=F", AssetUnit.GRAM))


def _deposit(container, amount="10000"):
    container.cash_movement_service.add_deposit(D(amount), movement_date=date(2026, 1, 1))


def test_fx_conversion_effects_are_hand_calculated():
    buy = FxConversion(None, DAY, None, FxSide.BUY_USD, D("100"), D("30"), fee_try=D("5"))
    sell = FxConversion(None, DAY, None, FxSide.SELL_USD, D("40"), D("31"), fee_try=D("2"))
    assert (buy.try_effect, buy.usd_effect) == (D("-3005"), D("100"))
    assert (sell.try_effect, sell.usd_effect) == (D("1238"), D("-40"))
    with pytest.raises(ValueError):
        FxConversion(None, DAY, None, FxSide.BUY_USD, D("0"), D("30"))


def test_buy_usd_moves_value_from_try_to_usd_pool(container):
    _deposit(container)

    container.fx_conversion_service.buy_usd(100, rate=30, conversion_date=DAY)

    assert container.cash_pool_service.balances() == {"TRY": D("7000"), "USD": D("100")}
    assert container.portfolio_service.get_cash_balance() == D("7000")   # BIST alım gücü de havuzdan düşer


def test_buy_usd_without_enough_try_is_rejected(container):
    _deposit(container, "2000")
    with pytest.raises(ValueError, match="Yetersiz TL nakit"):
        container.fx_conversion_service.buy_usd(100, rate=30, conversion_date=DAY)
    assert container.cash_pool_service.balances()["USD"] == D("0")


def test_sell_usd_returns_try_and_cannot_exceed_usd_balance(container):
    _deposit(container)
    container.fx_conversion_service.buy_usd(100, rate=30, conversion_date=DAY)

    container.fx_conversion_service.sell_usd(40, rate=31, conversion_date=DAY)  # +1240 TL, -40 USD
    assert container.cash_pool_service.balances() == {"TRY": D("8240"), "USD": D("60")}

    with pytest.raises(ValueError, match="Yetersiz USD nakit"):
        container.fx_conversion_service.sell_usd(61, rate=31, conversion_date=DAY)


def test_usd_asset_buy_is_paid_from_usd_cash_with_fee(container, btc):
    _deposit(container)
    container.fx_conversion_service.buy_usd(100, rate=30, conversion_date=DAY, conversion_time=time(10, 0))

    trade = container.asset_ledger_service.record_trade(
        btc.id, TradeSide.BUY, "2", "40", trade_date=DAY, trade_time=time(11, 0), fx_rate_to_try="30", fee="1")

    assert trade.cash_linked
    assert container.cash_pool_service.usd_balance() == D("19")           # 100 - (2 x 40 + 1)
    assert container.cash_pool_service.try_balance() == D("7000")          # TL'ye dokunmaz

    container.asset_ledger_service.record_trade(btc.id, TradeSide.SELL, "1", "50", trade_date=DAY, trade_time=time(15, 0), fx_rate_to_try="30", fee="0.5")
    assert container.cash_pool_service.usd_balance() == D("68.5")         # 19 + (50 - 0,5)


def test_usd_asset_buy_without_usd_cash_points_to_fx_buy(container, btc):
    _deposit(container)
    with pytest.raises(ValueError, match="Döviz Al"):
        container.asset_ledger_service.record_trade(btc.id, TradeSide.BUY, "1", "40", trade_date=DAY, fx_rate_to_try="30")
    assert container.asset_ledger_service.get_trades(btc.id) == []


def test_try_settled_asset_uses_shared_try_pool_and_blocks_bist_buying_power(container, gold_try):
    _deposit(container, "10000")

    container.asset_ledger_service.record_trade(gold_try.id, TradeSide.BUY, "2", "3000", trade_date=DAY, trade_time=time(11, 0), fee="10")

    assert container.cash_pool_service.try_balance() == D("3990")          # 10.000 - 6.010
    movements = container.pooled_cash_repo.get_all_movements()
    assert [(m.type.value, m.amount) for m in movements][-1] == ("WITHDRAW", D("6010"))
    with pytest.raises(ValueError, match="Yetersiz nakit"):                 # BIST alımı kalan 3.990 TL'yi aşamaz
        container.portfolio_service.validate_trade(Trade.create_buy(1, DAY, 100, D("50")))

    container.asset_ledger_service.record_trade(gold_try.id, TradeSide.SELL, "1", "3500", trade_date=DAY, trade_time=time(15, 0))
    assert container.cash_pool_service.try_balance() == D("7490")


def test_legacy_unlinked_asset_trade_does_not_touch_cash(container, btc):
    container.asset_trade_repo.add_trade(
        __import__("src.domain.models.asset_trade", fromlist=["AssetTrade"]).AssetTrade(
            None, btc.id, DAY, None, TradeSide.BUY, D("1"), D("60000"), fx_rate_to_try=D("30")))

    assert container.cash_pool_service.balances() == {"TRY": D("0"), "USD": D("0")}


def test_deleting_fx_that_funds_a_usd_trade_is_rejected(container, btc):
    _deposit(container)
    fx = container.fx_conversion_service.buy_usd(100, rate=30, conversion_date=DAY)
    container.asset_ledger_service.record_trade(btc.id, TradeSide.BUY, "1", "40", trade_date=DAY, fx_rate_to_try="30")

    with pytest.raises(ValueError, match="silinemez"):
        container.fx_conversion_service.delete_conversion(fx.id)
    assert len(container.fx_conversion_service.list_conversions()) == 1


def test_deleting_unneeded_fx_restores_try(container):
    _deposit(container)
    fx = container.fx_conversion_service.buy_usd(100, rate=30, conversion_date=DAY)

    container.fx_conversion_service.delete_conversion(fx.id)

    assert container.cash_pool_service.balances() == {"TRY": D("10000"), "USD": D("0")}


def test_reset_clears_conversions_and_pool(container, btc):
    _deposit(container)
    container.fx_conversion_service.buy_usd(100, rate=30, conversion_date=DAY)

    container.reset_service.reset_all()

    assert container.fx_conversion_service.list_conversions() == []
    assert container.cash_pool_service.balances() == {"TRY": D("0"), "USD": D("0")}


def test_unsupported_settlement_currency_is_rejected(container):
    euro = container.asset_repo.add_asset(Asset(None, "XYZ", "Euro varlık", AssetClass.US_STOCK, "EUR", "XYZ"))
    with pytest.raises(ValueError, match="EUR"):
        container.asset_ledger_service.record_trade(euro.id, TradeSide.BUY, "1", "10", trade_date=DAY, fx_rate_to_try="35")
