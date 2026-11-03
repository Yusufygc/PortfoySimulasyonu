from __future__ import annotations

from dataclasses import replace
from datetime import date, time
from decimal import Decimal, InvalidOperation
from typing import List, Optional

from src.application.services.assets.asset_catalog import ASSET_CATALOG, CatalogEntry, find_catalog_entry
from src.application.services.portfolio.pooled_cash_movement_repository import ASSET_TRADE_ID_OFFSET
from src.domain.asset_symbols import resolve_yf_symbol
from src.domain.exceptions import MarketDataUnavailableError
from src.domain.market_clock import market_today
from src.domain.models.asset import Asset, AssetClass, AssetUnit
from src.domain.models.asset_position import AssetLedger
from src.domain.models.asset_trade import AssetTrade
from src.domain.models.trade import TradeSide
from src.domain.ports.repositories.i_asset_repo import IAssetRepository
from src.domain.ports.repositories.i_asset_trade_repo import IAssetTradeRepository
from src.domain.ports.services.i_asset_symbol_verifier import IAssetSymbolVerifier


SUPPORTED_QUOTE_CURRENCIES = ("USD", "TRY")   # ortak nakit havuzu yalnızca bu iki para birimini taşır


def _decimal(value, label: str) -> Decimal:
    if isinstance(value, float):
        raise ValueError(f"{label} ondalık sayı (float) olarak verilemez.")
    try:
        return value if isinstance(value, Decimal) else Decimal(str(value).strip().replace(",", "."))
    except InvalidOperation as exc:
        raise ValueError(f"{label} geçerli bir sayı değil.") from exc


class AssetLedgerService:
    """
    BIST dışı varlık defterinin iş mantığı: varlık tanımı, alım/satım kaydı ve defterin yeniden hesaplanması.

    Defter BIST nakit defterinden bağımsızdır; alım/satım BIST nakdini etkilemez.
    """

    def __init__(
        self,
        asset_repo: IAssetRepository,
        trade_repo: IAssetTradeRepository,
        symbol_verifier: Optional[IAssetSymbolVerifier] = None,
        fee_service=None,
        cash_pool=None,
    ) -> None:
        self._asset_repo = asset_repo
        self._trade_repo = trade_repo
        self._symbol_verifier = symbol_verifier
        self._fee_service = fee_service
        self._cash_pool = cash_pool

    # ---------- Varlık tanımı ---------- #

    @property
    def catalog(self) -> tuple[CatalogEntry, ...]:
        return ASSET_CATALOG

    def list_assets(self, active_only: bool = True) -> List[Asset]:
        return self._asset_repo.list_assets(active_only=active_only)

    def get_asset(self, asset_id: int) -> Optional[Asset]:
        return self._asset_repo.get_asset(asset_id)

    def add_asset(self, symbol: str, name: str, asset_class: AssetClass, quote_currency: str, **options) -> Asset:
        """`options`: `yf_symbol` (varsayılan sınıfa göre çözülür) ve `unit` (varsayılan `AssetUnit.UNIT`).

        `quote_currency` yedektir: fiyat kaynağı sembolün para birimini bildirirse o geçerli olur."""
        yf_symbol, unit = options.pop("yf_symbol", None), options.pop("unit", AssetUnit.UNIT)
        trade_currency = options.pop("trade_currency", "")
        if options:
            raise TypeError(f"Bilinmeyen varlık seçeneği: {', '.join(sorted(options))}")
        try:
            asset = Asset(
                id=None,
                symbol=symbol,
                name=name,
                asset_class=asset_class,
                quote_currency=quote_currency,
                yf_symbol=(yf_symbol or resolve_yf_symbol(AssetClass(asset_class), symbol)),
                unit=unit,
                trade_currency=trade_currency,
            )
        except ValueError as exc:
            raise ValueError(f"Varlık bilgisi geçersiz: {exc}") from exc

        existing = self._asset_repo.get_asset_by_symbol(asset.asset_class, asset.symbol)
        if existing is not None:
            if existing.is_active:
                raise ValueError(f"{asset.symbol} zaten ekli.")
            self._asset_repo.set_active(existing.id, True)
            return self._asset_repo.get_asset(existing.id)

        self._ensure_price_symbol_unused(asset)
        detected = self._verify_symbol(asset)
        if detected and detected != asset.quote_currency:
            asset = replace(asset, quote_currency=detected)
        return self._asset_repo.add_asset(asset)

    def add_catalog_asset(self, key: str) -> Asset:
        entry = find_catalog_entry(key)
        if entry is None:
            raise ValueError(f"Katalogda {key} adlı varlık yok.")
        return self.add_asset(
            symbol=entry.key,
            name=entry.name,
            asset_class=entry.asset_class,
            quote_currency=entry.quote_currency,
            yf_symbol=entry.yf_symbol,
            unit=entry.unit,
            trade_currency=entry.trade_currency,
        )

    def remove_asset(self, asset_id: int) -> None:
        """İşlem geçmişi varsa varlık pasife alınır (geçmiş korunur); yoksa silinir."""
        if self._asset_repo.get_asset(asset_id) is None:
            raise ValueError("Varlık bulunamadı.")
        if self._trade_repo.list_trades(asset_id):
            self._asset_repo.set_active(asset_id, False)
        else:
            self._asset_repo.delete_asset(asset_id)

    # ---------- İşlemler ---------- #

    def get_trades(self, asset_id: Optional[int] = None) -> List[AssetTrade]:
        return self._trade_repo.list_trades(asset_id)

    def get_ledger(self) -> AssetLedger:
        return AssetLedger.from_trades(self._trade_repo.list_trades())

    def record_trade(self, asset_id: int, side: TradeSide, quantity, price, **options) -> AssetTrade:
        """`options`: `trade_date` (varsayılan bugün), `trade_time` (`time`), `fx_rate_to_try` (boşsa kur 1), `note` ve
        `fee` (işlem para biriminde; verilmezse ayarlardaki komisyon/BSMV oranlarıyla hesaplanır, ayar yoksa 0)."""
        trade_date: date = options.pop("trade_date", None) or market_today()
        fee_option = options.pop("fee", None)
        trade_time: Optional[time] = options.pop("trade_time", None)
        fx_rate_to_try, note = options.pop("fx_rate_to_try", None), options.pop("note", None)
        if options:
            raise TypeError(f"Bilinmeyen işlem seçeneği: {', '.join(sorted(options))}")
        asset = self._asset_repo.get_asset(asset_id)
        if asset is None:
            raise ValueError("Varlık bulunamadı.")
        if not asset.is_active:
            raise ValueError(f"{asset.symbol} pasif; işlem girmek için önce yeniden ekleyin.")

        quantity_value = _decimal(quantity, "Miktar")
        price_value = _decimal(price, "Fiyat")
        fx_value = self._resolve_fx_rate(asset, fx_rate_to_try)
        if quantity_value <= 0:
            raise ValueError("Miktar sıfırdan büyük olmalı.")
        if price_value <= 0:
            raise ValueError("Fiyat sıfırdan büyük olmalı.")

        fee_value = self._resolve_fee(fee_option, quantity_value * price_value)

        trade = AssetTrade(
            id=None,
            asset_id=asset_id,
            trade_date=trade_date,
            trade_time=trade_time,
            side=side,
            quantity=quantity_value,
            price=price_value,
            fx_rate_to_try=fx_value,
            note=(note or "").strip() or None,
            fee=fee_value,
            cash_linked=self._cash_pool is not None,
        )
        self._ensure_ledger_valid(self._trade_repo.list_trades(asset_id) + [trade], asset)
        self._ensure_cash_available(asset, trade)
        return self._trade_repo.add_trade(trade)

    def delete_trade(self, trade_id: int) -> None:
        trade = self._trade_repo.get_trade(trade_id)
        if trade is None:
            raise ValueError("İşlem bulunamadı.")
        asset = self._asset_repo.get_asset(trade.asset_id)
        remaining = [t for t in self._trade_repo.list_trades(trade.asset_id) if t.id != trade_id]
        self._ensure_ledger_valid(remaining, asset)
        self._ensure_cash_after_delete(trade, asset)
        self._trade_repo.delete_trade(trade_id)

    # ---------- Yardımcılar ---------- #

    def _ensure_price_symbol_unused(self, asset: Asset) -> None:
        """Aynı fiyat sembolü iki varlık olarak eklenemez (ör. katalogdaki BTC ile elle girilen BTC-USD)."""
        for other in self._asset_repo.list_assets(active_only=True):
            if other.yf_symbol == asset.yf_symbol:
                raise ValueError(f"{asset.yf_symbol} fiyat sembolü zaten {other.symbol} olarak ekli.")

    def _verify_symbol(self, asset: Asset) -> Optional[str]:
        """Sembolü çevrimiçi doğrular; kaynak para birimini bildiriyorsa döner. USD/TRY dışı para birimi reddedilir."""
        if self._symbol_verifier is None:
            return None
        try:
            valid = self._symbol_verifier.verify(asset.yf_symbol)
        except MarketDataUnavailableError as exc:
            raise ValueError(f"{asset.yf_symbol} sembolü doğrulanamadı: fiyat kaynağına ulaşılamıyor.") from exc
        if not valid:
            raise ValueError(f"{asset.yf_symbol} sembolü için fiyat verisi bulunamadı.")
        currency = (self._symbol_verifier.currency_of(asset.yf_symbol) or "").strip()
        if currency and currency.upper() not in SUPPORTED_QUOTE_CURRENCIES:
            raise ValueError(
                f"{asset.yf_symbol} {currency} cinsinden işlem görüyor; yalnızca USD ve TRY cinsi varlıklar desteklenir."
            )
        return currency.upper() or None

    def _ensure_cash_available(self, asset: Asset, trade: AssetTrade) -> None:
        """Alım, ortak nakit havuzundaki ödeme para birimi bakiyesini aşamaz (satış nakit ekler)."""
        if self._cash_pool is None or trade.side != TradeSide.BUY:
            return
        currency = asset.settlement_currency
        available = self._cash_pool.balance(currency, as_of=(trade.trade_date, trade.trade_time))
        if trade.cash_amount > available:
            hint = " Önce Döviz Al ile TL'den USD alın." if currency == "USD" else ""
            raise ValueError(
                f"Yetersiz {currency} nakit. Gerekli: {trade.cash_amount:,.2f} {currency}, Mevcut: {available:,.2f} {currency}.{hint}"
            )

    def _ensure_cash_after_delete(self, trade: AssetTrade, asset: Optional[Asset]) -> None:
        """Nakde bağlı satışı silmek, sonraki aynı para birimli ödemeleri (USD) ya da TL kullanımını eksiye düşürmemeli."""
        if self._cash_pool is None or not trade.cash_linked or asset is None or trade.side != TradeSide.SELL:
            return
        if asset.settlement_currency == "USD":
            if not self._cash_pool.usd_timeline_valid(exclude_trade_id=trade.id):
                raise ValueError("Bu satış silinemez: sonraki USD ile ödenen işlemler yetersiz bakiyeye düşer.")
        elif asset.is_try_settled:
            self._cash_pool.ensure_try_after_removal(
                ASSET_TRADE_ID_OFFSET - trade.id,
                "Bu satış silinemez: sonraki TL ile yapılan alım veya çekim yetersiz bakiyeye düşer.",
            )

    def estimate_fee(self, quantity, price) -> Decimal:
        """Ayarlardaki oranlarla tahmini ücret (işlem para biriminde); arayüz ön izlemesi içindir."""
        gross = _decimal(quantity, "Miktar") * _decimal(price, "Fiyat")
        return self._fee_service.asset_fee(gross) if self._fee_service is not None else Decimal("0")

    def _resolve_fee(self, fee_option, gross_amount: Decimal) -> Decimal:
        """Elle girilen ücret varsa o, yoksa ayardaki oranlarla hesaplanan (ayar yoksa 0)."""
        if fee_option is not None:
            fee = _decimal(fee_option, "Ücret")
            if fee < 0:
                raise ValueError("Ücret negatif olamaz.")
            return fee
        return self._fee_service.asset_fee(gross_amount) if self._fee_service is not None else Decimal("0")

    @staticmethod
    def _resolve_fx_rate(asset: Asset, fx_rate_to_try) -> Decimal:
        if asset.is_try_settled:
            return Decimal("1")
        if fx_rate_to_try is None:
            raise ValueError(f"{asset.settlement_currency}/TRY kuru gerekli.")
        rate = _decimal(fx_rate_to_try, "Kur")
        if rate <= 0:
            raise ValueError("Kur sıfırdan büyük olmalı.")
        return rate

    @staticmethod
    def _ensure_ledger_valid(trades: List[AssetTrade], asset: Optional[Asset]) -> None:
        """Tarih sırasıyla uygulandığında elden fazla satış oluşuyorsa işlem reddedilir."""
        try:
            AssetLedger.from_trades(trades)
        except ValueError as exc:
            symbol = asset.symbol if asset is not None else "Varlık"
            raise ValueError(f"{symbol}: işlem sonrası elde yeterli miktar kalmıyor.") from exc
