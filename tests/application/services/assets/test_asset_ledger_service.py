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
    def __init__(self, valid: bool = True, currency: str | None = None):
        self.valid = valid
        self.currency = currency
        self.checked: list[str] = []

    def verify(self, yf_symbol):
        self.checked.append(yf_symbol)
        return self.valid

    def currency_of(self, yf_symbol):
        return self.currency


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
        assert asset.unit == AssetUnit.GRAM and asset.trade_currency == "TRY" and asset.settlement_currency == "TRY"
        assert asset.is_try_settled and not asset.is_try_quoted  # fiyat USD/gram, işlem ve nakit TL

    def test_precious_metals_are_gold_silver_platinum_only(self):
        metals = {e.key for e in ASSET_CATALOG if e.asset_class == AssetClass.PRECIOUS_METAL}

        assert metals == {"XAU", "XAG", "XPT"}

    def test_popular_nasdaq_list_is_usd_priced_plain_symbols(self, service):
        stocks = [e for e in ASSET_CATALOG if e.asset_class == AssetClass.US_STOCK]

        assert len(stocks) >= 20 and {"AAPL", "MSFT", "NVDA", "QQQ"} <= {e.key for e in stocks}
        assert all(e.quote_currency == "USD" and e.yf_symbol == e.key and not e.trade_currency for e in stocks)
        assert service.add_catalog_asset("nvda").yf_symbol == "NVDA"

    def test_unknown_catalog_key_is_rejected(self, service):
        with pytest.raises(ValueError, match="Katalogda"):
            service.add_catalog_asset("DOGE2")


class TestAddAsset:
    def test_duplicate_active_asset_is_rejected(self, service, btc):
        with pytest.raises(ValueError, match="zaten ekli"):
            service.add_catalog_asset("BTC")

    def test_readding_inactive_asset_reactivates_it(self, service, btc):
        service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 1), fx_rate_to_try="30")
        service.record_trade(btc.id, TradeSide.SELL, "1", "110", trade_date=date(2026, 1, 2), fx_rate_to_try="30")
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


class TestSymbolAndCurrencyValidation:
    @pytest.mark.parametrize("symbol", ["AAPL MSFT", "MSFT,GOOG", "AA;PL", "A" * 25, "-AAPL"])
    def test_multi_symbol_or_malformed_text_is_rejected(self, service, symbol):
        with pytest.raises(ValueError, match="tek sembol"):
            service.add_asset(symbol, "X", AssetClass.US_STOCK, "USD")
        assert service.list_assets(active_only=False) == []

    def test_index_symbol_is_rejected_with_etf_hint(self, service):
        with pytest.raises(ValueError, match="ETF"):
            service.add_asset("^IXIC", "Nasdaq", AssetClass.US_STOCK, "USD")

    def test_share_class_dot_becomes_yahoo_dash_but_exchange_suffix_is_kept(self, repos):
        service = AssetLedgerService(repos[0], repos[1], StubVerifier())

        brk = service.add_asset("brk.b", "Berkshire", AssetClass.US_STOCK, "USD")
        asml = service.add_asset("ASML.AS", "ASML", AssetClass.US_STOCK, "USD")

        assert (brk.symbol, brk.yf_symbol) == ("BRK.B", "BRK-B")
        assert asml.yf_symbol == "ASML.AS"

    def test_source_reported_currency_overrides_user_guess(self, repos):
        service = AssetLedgerService(repos[0], repos[1], StubVerifier(currency="TRY"))

        asset = service.add_asset("THYAO.IS", "THY", AssetClass.US_STOCK, "USD")

        assert asset.quote_currency == "TRY" and asset.is_try_quoted

    def test_unsupported_currency_is_rejected_before_saving(self, repos):
        service = AssetLedgerService(repos[0], repos[1], StubVerifier(currency="EUR"))

        with pytest.raises(ValueError, match="yalnızca USD ve TRY"):
            service.add_asset("ASML.AS", "ASML", AssetClass.US_STOCK, "EUR")
        assert repos[0].list_assets() == []

    def test_pence_quoted_symbol_is_not_mistaken_for_gbp(self, repos):
        service = AssetLedgerService(repos[0], repos[1], StubVerifier(currency="GBp"))

        with pytest.raises(ValueError, match="GBp"):
            service.add_asset("VOD.L", "Vodafone", AssetClass.US_STOCK, "USD")

    def test_unknown_source_currency_keeps_given_currency(self, repos):
        service = AssetLedgerService(repos[0], repos[1], StubVerifier(currency=None))

        assert service.add_asset("MSFT", "Microsoft", AssetClass.US_STOCK, "USD").quote_currency == "USD"

    def test_same_price_symbol_cannot_be_added_twice_under_another_name(self, service, btc):
        with pytest.raises(ValueError, match="BTC-USD fiyat sembolü zaten BTC"):
            service.add_asset("BTC-USD", "Bitcoin", AssetClass.CRYPTO, "USD")
        with pytest.raises(ValueError, match="zaten"):
            service.add_asset("btc", "Bitcoin", AssetClass.CRYPTO, "USD")

    def test_inactive_duplicate_does_not_block_a_new_symbol(self, service, btc):
        service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 1), fx_rate_to_try="30")
        service.record_trade(btc.id, TradeSide.SELL, "1", "110", trade_date=date(2026, 1, 2), fx_rate_to_try="30")
        service.remove_asset(btc.id)

        assert service.add_asset("BTC-USD", "Bitcoin", AssetClass.CRYPTO, "USD").yf_symbol == "BTC-USD"


class TestRemoveAsset:
    def test_asset_without_trades_is_deleted(self, service, btc):
        service.remove_asset(btc.id)

        assert service.list_assets(active_only=False) == []

    def test_asset_with_trades_is_only_deactivated(self, service, btc):
        service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 1), fx_rate_to_try="30")
        service.record_trade(btc.id, TradeSide.SELL, "1", "110", trade_date=date(2026, 1, 2), fx_rate_to_try="30")

        service.remove_asset(btc.id)

        assert service.list_assets() == []
        assert len(service.list_assets(active_only=False)) == 1
        assert len(service.get_trades(btc.id)) == 2

    def test_asset_with_open_position_cannot_be_removed(self, service, btc):
        service.record_trade(btc.id, TradeSide.BUY, "1", "100", trade_date=date(2026, 1, 1), fx_rate_to_try="30")

        reason = service.remove_block_reason(btc.id)

        assert "açık pozisyon" in reason and "BTC" in reason and "(1 adet)" in reason
        with pytest.raises(ValueError, match="açık pozisyon"):
            service.remove_asset(btc.id)
        assert service.list_assets() == [btc]

    def test_closed_or_empty_asset_has_no_block_reason(self, service, btc):
        assert service.remove_block_reason(btc.id) == ""
        assert service.remove_block_reason(99) == "Varlık bulunamadı."

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
        service.record_trade(btc.id, TradeSide.SELL, "1", "110", trade_date=date(2026, 1, 2), fx_rate_to_try="30")
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
