"""Varlık defteri SQLite repository'leri (gerçek geçici veritabanı)."""
from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal

import pytest

from src.domain.models.asset import Asset, AssetClass, AssetUnit
from src.domain.models.asset_price import AssetLatestPrice, AssetPrice, FxRate
from src.domain.models.asset_trade import AssetTrade
from src.domain.models.trade import TradeSide
from src.infrastructure.db.db_config import SQLiteConfig
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.repositories.sa_asset_price_repository import SQLAlchemyAssetPriceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_asset_repository import SQLAlchemyAssetRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_asset_trade_repository import SQLAlchemyAssetTradeRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_fx_rate_repository import SQLAlchemyFxRateRepository

D = Decimal


@pytest.fixture
def provider(tmp_path):
    return SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(tmp_path / "assets.db")))


@pytest.fixture
def asset_repo(provider):
    return SQLAlchemyAssetRepository(provider)


@pytest.fixture
def btc(asset_repo):
    return asset_repo.add_asset(
        Asset(None, "BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD")
    )


class TestAssetRepository:
    def test_add_assigns_autoincrement_ids(self, asset_repo):
        first = asset_repo.add_asset(Asset(None, "BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD"))
        second = asset_repo.add_asset(Asset(None, "ETH", "Ethereum", AssetClass.CRYPTO, "USD", "ETH-USD", AssetUnit.UNIT))

        assert (first.id, second.id) == (1, 2)
        assert first.asset_class == AssetClass.CRYPTO and first.unit == AssetUnit.UNIT

    def test_same_symbol_in_other_class_is_allowed_but_duplicate_in_class_is_not(self, asset_repo, btc):
        asset_repo.add_asset(Asset(None, "BTC", "BTC hissesi", AssetClass.US_STOCK, "USD", "BTC"))

        with pytest.raises(ValueError):
            asset_repo.add_asset(Asset(None, "btc", "Yinelenen", AssetClass.CRYPTO, "USD", "BTC-USD"))

    def test_lookup_by_symbol_is_case_insensitive(self, asset_repo, btc):
        found = asset_repo.get_asset_by_symbol(AssetClass.CRYPTO, " btc ")

        assert found is not None and found.id == btc.id
        assert asset_repo.get_asset_by_symbol(AssetClass.US_STOCK, "BTC") is None

    def test_list_filters_inactive_assets(self, asset_repo, btc):
        eth = asset_repo.add_asset(Asset(None, "ETH", "Ethereum", AssetClass.CRYPTO, "USD", "ETH-USD"))
        asset_repo.set_active(eth.id, False)

        assert [a.symbol for a in asset_repo.list_assets()] == ["BTC"]
        assert {a.symbol for a in asset_repo.list_assets(active_only=False)} == {"BTC", "ETH"}

    def test_delete_cascades_trades_and_prices(self, provider, asset_repo, btc):
        trade_repo = SQLAlchemyAssetTradeRepository(provider)
        price_repo = SQLAlchemyAssetPriceRepository(provider)
        trade_repo.add_trade(AssetTrade(None, btc.id, date(2026, 1, 1), None, TradeSide.BUY, D("1"), D("100"), D("30")))
        price_repo.upsert_daily_prices([AssetPrice(None, btc.id, date(2026, 1, 1), D("100"), "USD", "yfinance")])

        asset_repo.delete_asset(btc.id)

        assert asset_repo.get_asset(btc.id) is None
        assert trade_repo.list_trades() == []
        assert price_repo.get_daily_prices(btc.id) == []


    def test_delete_all_assets_clears_ledger_but_keeps_fx(self, provider, asset_repo, btc):
        trade_repo = SQLAlchemyAssetTradeRepository(provider)
        price_repo = SQLAlchemyAssetPriceRepository(provider)
        fx_repo = SQLAlchemyFxRateRepository(provider)
        trade_repo.add_trade(AssetTrade(None, btc.id, date(2026, 1, 1), None, TradeSide.BUY, D("1"), D("100"), D("30")))
        price_repo.upsert_daily_prices([AssetPrice(None, btc.id, date(2026, 1, 1), D("100"), "USD", "yfinance")])
        fx_repo.upsert_rates([FxRate(None, "USD", "TRY", date(2026, 1, 1), D("40"), "yfinance")])

        asset_repo.delete_all_assets()

        assert asset_repo.list_assets(active_only=False) == [] and trade_repo.list_trades() == []
        assert price_repo.get_daily_prices(btc.id) == []
        assert fx_repo.get_rates("USD", "TRY") != []


class TestAssetTradeRepository:
    def test_roundtrips_fractional_values(self, provider, btc):
        repo = SQLAlchemyAssetTradeRepository(provider)

        saved = repo.add_trade(AssetTrade(
            None, btc.id, date(2026, 2, 3), time(10, 30), TradeSide.BUY,
            D("0.12345678"), D("65432.1"), D("34.25"), "ilk alım",
        ))

        loaded = repo.get_trade(saved.id)
        assert loaded.quantity == D("0.12345678")
        assert loaded.price == D("65432.1")
        assert loaded.fx_rate_to_try == D("34.25")
        assert loaded.side == TradeSide.BUY
        assert loaded.trade_time == time(10, 30)
        assert loaded.note == "ilk alım"

    def test_lists_in_date_order_and_filters_by_asset(self, provider, asset_repo, btc):
        eth = asset_repo.add_asset(Asset(None, "ETH", "Ethereum", AssetClass.CRYPTO, "USD", "ETH-USD"))
        repo = SQLAlchemyAssetTradeRepository(provider)
        later = repo.add_trade(AssetTrade(None, btc.id, date(2026, 3, 1), None, TradeSide.SELL, D("1"), D("2"), D("1")))
        earlier = repo.add_trade(AssetTrade(None, btc.id, date(2026, 1, 1), None, TradeSide.BUY, D("1"), D("1"), D("1")))
        repo.add_trade(AssetTrade(None, eth.id, date(2026, 2, 1), None, TradeSide.BUY, D("1"), D("1"), D("1")))

        assert [t.id for t in repo.list_trades(btc.id)] == [earlier.id, later.id]
        assert len(repo.list_trades()) == 3

    def test_delete_trade(self, provider, btc):
        repo = SQLAlchemyAssetTradeRepository(provider)
        saved = repo.add_trade(AssetTrade(None, btc.id, date(2026, 1, 1), None, TradeSide.BUY, D("1"), D("1"), D("1")))

        repo.delete_trade(saved.id)

        assert repo.get_trade(saved.id) is None


class TestAssetPriceRepository:
    def test_daily_prices_upsert_updates_existing_day(self, provider, btc):
        repo = SQLAlchemyAssetPriceRepository(provider)
        repo.upsert_daily_prices([
            AssetPrice(None, btc.id, date(2026, 1, 1), D("100"), "USD", "yfinance"),
            AssetPrice(None, btc.id, date(2026, 1, 2), D("110"), "USD", "yfinance"),
        ])

        repo.upsert_daily_prices([AssetPrice(None, btc.id, date(2026, 1, 2), D("115.5"), "USD", "yfinance")])

        series = repo.get_daily_prices(btc.id)
        assert [(p.price_date, p.close_price) for p in series] == [
            (date(2026, 1, 1), D("100")), (date(2026, 1, 2), D("115.5")),
        ]

    def test_daily_price_range_and_last_price(self, provider, btc):
        repo = SQLAlchemyAssetPriceRepository(provider)
        repo.upsert_daily_prices([
            AssetPrice(None, btc.id, date(2026, 1, day), D(str(day)), "USD", "yfinance") for day in (1, 2, 3, 4)
        ])

        assert [p.price_date.day for p in repo.get_daily_prices(btc.id, start=date(2026, 1, 2), end=date(2026, 1, 3))] == [2, 3]
        assert repo.get_last_daily_price(btc.id).close_price == D("4")
        assert repo.get_last_daily_price(btc.id, on_or_before=date(2026, 1, 2)).close_price == D("2")
        assert repo.get_last_daily_price(btc.id, on_or_before=date(2025, 12, 31)) is None

    def test_latest_price_upsert_keeps_single_row_per_asset(self, provider, btc):
        repo = SQLAlchemyAssetPriceRepository(provider)
        first = datetime(2026, 1, 1, 10, 0)
        second = datetime(2026, 1, 1, 11, 0)
        repo.upsert_latest_prices([AssetLatestPrice(None, btc.id, D("100"), "USD", first, "intraday", first)])
        repo.upsert_latest_prices([AssetLatestPrice(None, btc.id, D("105.25"), "USD", second, "intraday", second)])

        latest = repo.get_latest_prices([btc.id])
        assert latest[btc.id].price == D("105.25")
        assert latest[btc.id].as_of == second
        assert repo.get_latest_price_map([btc.id]) == {btc.id: D("105.25")}
        assert repo.get_latest_price_map([]) == {}


class TestFxRateRepository:
    def test_upsert_and_query(self, provider):
        repo = SQLAlchemyFxRateRepository(provider)
        repo.upsert_rates([
            FxRate(None, "USD", "TRY", date(2026, 1, 1), D("34.1"), "yfinance"),
            FxRate(None, "USD", "TRY", date(2026, 1, 3), D("34.3"), "yfinance"),
        ])
        repo.upsert_rates([FxRate(None, "USD", "TRY", date(2026, 1, 3), D("34.4"), "yfinance")])

        assert [r.rate for r in repo.get_rates("usd", "try")] == [D("34.1"), D("34.4")]
        assert [r.rate_date.day for r in repo.get_rates("USD", "TRY", start=date(2026, 1, 2))] == [3]

    def test_rate_on_or_before_carries_forward(self, provider):
        repo = SQLAlchemyFxRateRepository(provider)
        repo.upsert_rates([FxRate(None, "USD", "TRY", date(2026, 1, 1), D("34.1"), "yfinance")])

        assert repo.get_rate_on_or_before("USD", "TRY", date(2026, 1, 5)).rate == D("34.1")
        assert repo.get_rate_on_or_before("USD", "TRY", date(2025, 12, 31)) is None
        assert repo.get_rate_on_or_before("EUR", "TRY", date(2026, 1, 5)) is None
