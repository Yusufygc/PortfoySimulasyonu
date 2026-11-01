"""AssetLedgerService: varlık ekleme, katalog, işlem doğrulama ve defter hesabı (bellek içi sahte repo'larla)."""
from __future__ import annotations

from dataclasses import replace
from datetime import date
from decimal import Decimal
from typing import List, Optional

import pytest

from src.application.services.assets.asset_catalog import ASSET_CATALOG, find_catalog_entry
from src.application.services.assets.asset_ledger_service import AssetLedgerService
from src.domain.exceptions import MarketDataUnavailableError
from src.domain.models.asset import Asset, AssetClass, AssetUnit
from src.domain.models.asset_trade import AssetTrade
from src.domain.models.trade import TradeSide
from src.domain.ports.repositories.i_asset_repo import IAssetRepository
from src.domain.ports.repositories.i_asset_trade_repo import IAssetTradeRepository
from src.domain.ports.services.i_asset_symbol_verifier import IAssetSymbolVerifier

D = Decimal


class FakeAssetRepo(IAssetRepository):
    def delete_all_assets(self):
        self.assets.clear()

    def __init__(self):
        self.assets: dict[int, Asset] = {}

    def add_asset(self, asset):
        saved = replace(asset, id=len(self.assets) + 1)
        self.assets[saved.id] = saved
        return saved

    def get_asset(self, asset_id):
        return self.assets.get(asset_id)

    def get_asset_by_symbol(self, asset_class, symbol):
        return next((a for a in self.assets.values() if a.asset_class == asset_class and a.symbol == symbol.upper()), None)

    def list_assets(self, active_only=True):
        return [a for a in self.assets.values() if a.is_active or not active_only]

    def set_active(self, asset_id, is_active):
        self.assets[asset_id] = replace(self.assets[asset_id], is_active=is_active)

    def delete_asset(self, asset_id):
        self.assets.pop(asset_id, None)


class FakeTradeRepo(IAssetTradeRepository):
    def __init__(self):
        self.trades: List[AssetTrade] = []

    def add_trade(self, trade):
        saved = replace(trade, id=len(self.trades) + 1)
        self.trades.append(saved)
        return saved

    def get_trade(self, trade_id):
        return next((t for t in self.trades if t.id == trade_id), None)

    def list_trades(self, asset_id: Optional[int] = None):
        return [t for t in self.trades if asset_id is None or t.asset_id == asset_id]

    def delete_trade(self, trade_id):
        self.trades = [t for t in self.trades if t.id != trade_id]


class StubVerifier(IAssetSymbolVerifier):
    def __init__(self, valid: bool = True):
        self.valid = valid
        self.checked: list[str] = []

    def verify(self, yf_symbol):
        self.checked.append(yf_symbol)
        return self.valid


@pytest.fixture
def repos():
    return FakeAssetRepo(), FakeTradeRepo()


@pytest.fixture
def service(repos):
    return AssetLedgerService(asset_repo=repos[0], trade_repo=repos[1])


@pytest.fixture
def btc(service):
    return service.add_catalog_asset("btc")


@pytest.fixture
def gold_try(service):
    return service.add_asset("GAU", "Gram altın", AssetClass.PRECIOUS_METAL, "TRY", yf_symbol="GRAM-ALTIN", unit=AssetUnit.GRAM)


class TestCatalog:
    def test_catalog_has_metals_and_crypto_with_unique_keys(self):
        keys = [entry.key for entry in ASSET_CATALOG]

        assert len(keys) == len(set(keys))
        assert {"XAU", "XAG", "XPT", "BTC"} <= set(keys)
        assert find_catalog_entry(" xau ").yf_symbol == "GC=F"
        assert find_catalog_entry("YOK") is None

    def test_add_catalog_asset_uses_entry_data(self, service):
        asset = service.add_catalog_asset("XAU")

        assert (asset.symbol, asset.yf_symbol, asset.quote_currency) == ("XAU", "GC=F", "USD")
        assert asset.asset_class == AssetClass.PRECIOUS_METAL
        assert asset.unit == AssetUnit.OUNCE

    def test_unknown_catalog_key_is_rejected(self, service):
        with pytest.raises(ValueError, match="Katalogda"):
            service.add_catalog_asset("DOGE2")


class TestAddAsset:
    def test_duplicate_active_asset_is_rejected(self, service, btc):
        with pytest.raises(ValueError, match="zaten ekli"):
            service.add_catalog_asset("BTC")

    def test_readding_inactive_asset_reactivates_it(self, service, btc):
        service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 1), fx_rate_to_try="30")
        service.remove_asset(btc.id)
        assert service.list_assets() == []

        again = service.add_catalog_asset("BTC")

        assert again.id == btc.id and again.is_active

    def test_invalid_asset_data_is_reported_in_turkish(self, service):
        with pytest.raises(ValueError, match="Varlık bilgisi geçersiz"):
            service.add_asset("AAPL", "Apple", AssetClass.US_STOCK, "DOLAR")

    def test_symbol_is_verified_online_when_verifier_given(self, repos):
        verifier = StubVerifier(valid=True)
        service = AssetLedgerService(repos[0], repos[1], verifier)

        asset = service.add_asset("aapl", "Apple", AssetClass.US_STOCK, "USD")

        assert verifier.checked == ["AAPL"]
        assert asset.symbol == "AAPL" and asset.yf_symbol == "AAPL"

    def test_crypto_symbol_defaults_to_usd_pair_without_bist_suffix(self, repos):
        verifier = StubVerifier()
        service = AssetLedgerService(repos[0], repos[1], verifier)

        asset = service.add_asset("sol", "Solana", AssetClass.CRYPTO, "USD")

        assert asset.yf_symbol == "SOL-USD"
        assert verifier.checked == ["SOL-USD"]

    def test_unreachable_price_source_is_reported_as_validation_error(self, repos):
        class Offline(IAssetSymbolVerifier):
            def verify(self, yf_symbol):
                raise MarketDataUnavailableError("ağ yok")

        service = AssetLedgerService(repos[0], repos[1], Offline())

        with pytest.raises(ValueError, match="ulaşılamıyor"):
            service.add_asset("AAPL", "Apple", AssetClass.US_STOCK, "USD")
        assert repos[0].list_assets() == []

    def test_unverifiable_symbol_is_rejected(self, repos):
        service = AssetLedgerService(repos[0], repos[1], StubVerifier(valid=False))

        with pytest.raises(ValueError, match="fiyat verisi bulunamadı"):
            service.add_asset("ZZZZ", "Yok", AssetClass.US_STOCK, "USD")
        assert repos[0].list_assets() == []


class TestRemoveAsset:
    def test_asset_without_trades_is_deleted(self, service, btc):
        service.remove_asset(btc.id)

        assert service.list_assets(active_only=False) == []

    def test_asset_with_trades_is_only_deactivated(self, service, btc):
        service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 1), fx_rate_to_try="30")

        service.remove_asset(btc.id)

        assert service.list_assets() == []
        assert len(service.list_assets(active_only=False)) == 1
        assert len(service.get_trades(btc.id)) == 1

    def test_unknown_asset_raises(self, service):
        with pytest.raises(ValueError, match="bulunamadı"):
            service.remove_asset(99)


class TestRecordTrade:
    def test_records_buy_and_builds_ledger(self, service, btc):
        service.record_trade(btc.id, TradeSide.BUY, "0.5", "60000", trade_date=date(2026, 1, 1), fx_rate_to_try="34")
        service.record_trade(btc.id, TradeSide.SELL, "0.2", "70000", trade_date=date(2026, 1, 5), fx_rate_to_try="35")

        position = service.get_ledger().get_position(btc.id)
        assert position.total_quantity == D("0.3")
        assert position.realized_pl == D("0.2") * D("70000") - D("0.2") * D("60000")

    def test_try_quoted_asset_ignores_fx_rate(self, service, gold_try):
        trade = service.record_trade(gold_try.id, TradeSide.BUY, "10", "2500", trade_date=date(2026, 1, 1))

        assert trade.fx_rate_to_try == D("1")

    def test_foreign_asset_requires_fx_rate(self, service, btc):
        with pytest.raises(ValueError, match="kuru gerekli"):
            service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 1))

    def test_accepts_decimal_comma_strings(self, service, btc):
        trade = service.record_trade(btc.id, TradeSide.BUY, "0,25", "100,5", trade_date=date(2026, 1, 1), fx_rate_to_try="34,2")

        assert (trade.quantity, trade.price, trade.fx_rate_to_try) == (D("0.25"), D("100.5"), D("34.2"))

    @pytest.mark.parametrize("quantity,price,message", [("0", "1", "Miktar"), ("1", "0", "Fiyat"), ("abc", "1", "geçerli bir sayı")])
    def test_rejects_invalid_numbers(self, service, btc, quantity, price, message):
        with pytest.raises(ValueError, match=message):
            service.record_trade(btc.id, TradeSide.BUY, quantity, price, trade_date=date(2026, 1, 1), fx_rate_to_try="30")

    def test_rejects_float_input(self, service, btc):
        with pytest.raises(ValueError, match="float"):
            service.record_trade(btc.id, TradeSide.BUY, 0.5, "1", trade_date=date(2026, 1, 1), fx_rate_to_try="30")

    def test_cannot_sell_more_than_held(self, service, btc):
        service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 1), fx_rate_to_try="30")

        with pytest.raises(ValueError, match="yeterli miktar"):
            service.record_trade(btc.id, TradeSide.SELL, "1.5", "100", trade_date=date(2026, 1, 2), fx_rate_to_try="30")
        assert len(service.get_trades(btc.id)) == 1

    def test_backdated_sell_before_purchase_is_rejected(self, service, btc):
        service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 2, 1), fx_rate_to_try="30")

        with pytest.raises(ValueError, match="yeterli miktar"):
            service.record_trade(btc.id, TradeSide.SELL, "1", "100", trade_date=date(2026, 1, 1), fx_rate_to_try="30")

    def test_inactive_or_missing_asset_is_rejected(self, service, btc):
        service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 1), fx_rate_to_try="30")
        service.remove_asset(btc.id)

        with pytest.raises(ValueError, match="pasif"):
            service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 2), fx_rate_to_try="30")
        with pytest.raises(ValueError, match="Varlık bulunamadı"):
            service.record_trade(99, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 2), fx_rate_to_try="30")


class TestDeleteTrade:
    def test_delete_removes_trade(self, service, btc):
        trade = service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 1), fx_rate_to_try="30")

        service.delete_trade(trade.id)

        assert service.get_trades(btc.id) == []

    def test_cannot_delete_buy_that_backs_a_later_sell(self, service, btc):
        buy = service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 1), fx_rate_to_try="30")
        service.record_trade(btc.id, TradeSide.SELL, "1", "120", trade_date=date(2026, 1, 2), fx_rate_to_try="30")

        with pytest.raises(ValueError, match="yeterli miktar"):
            service.delete_trade(buy.id)
        assert len(service.get_trades(btc.id)) == 2

    def test_unknown_trade_raises(self, service):
        with pytest.raises(ValueError, match="İşlem bulunamadı"):
            service.delete_trade(42)
