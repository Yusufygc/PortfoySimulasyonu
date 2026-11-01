from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from src.domain.models.asset import Asset
from src.domain.models.asset_position import AssetPosition
from src.domain.models.unified_portfolio import HUNDRED, HoldingValuation, allocation_class_for, daily_gain


class AssetHoldingsReader:
    """Varlık defterinin açık pozisyonlarını TRY değerlemesine çevirir.

    Fiyat: son fiyat (`asset_latest_prices`) ile son günlük kapanıştan tarihi daha yeni olan (eşitse son fiyat) seçilir.
    Değer TRY'ye güncel kurla çevrilir; fiyat ya da kur yoksa pozisyon TRY maliyetiyle değerlenir (`is_priced=False`).
    Gram birimli madenlerde ons fiyatı gram fiyatına çevrilir (`Asset.unit_price`).
    """

    def __init__(self, ledger_service, price_repo, fx_rate_service) -> None:
        self._ledger_service = ledger_service
        self._price_repo = price_repo
        self._fx = fx_rate_service

    def read(self) -> List[HoldingValuation]:
        positions = self._ledger_service.get_ledger().open_positions()
        if not positions:
            return []
        assets = {asset.id: asset for asset in self._ledger_service.list_assets(active_only=False)}
        latest = self._price_repo.get_latest_prices([p.asset_id for p in positions])
        return [
            self._valuate(position, assets[position.asset_id], latest.get(position.asset_id))
            for position in positions
            if position.asset_id in assets
        ]

    def _valuate(self, position: AssetPosition, asset: Asset, latest) -> HoldingValuation:
        allocation_class = allocation_class_for(asset.asset_class)
        base = dict(
            key=f"{allocation_class.value}:{asset.symbol}",
            symbol=asset.symbol,
            name=asset.name,
            allocation_class=allocation_class,
            quantity=position.total_quantity,
            native_currency=asset.quote_currency,
            cost_native=position.total_cost,
            cost_try=position.total_cost_try,
        )
        quoted, reference_date = self._pick_price(asset, latest)
        fx_rate = self._fx.get_rate(asset.quote_currency, "TRY")
        if quoted is None or fx_rate is None:
            return HoldingValuation(**base, value_try=position.total_cost_try, is_priced=False)

        unit_price = asset.unit_price(quoted)
        value_native = position.total_quantity * unit_price
        value_try = value_native * fx_rate
        change = self._daily_change_pct(asset, reference_date, quoted)
        return HoldingValuation(
            **base,
            value_try=value_try,
            price_native=unit_price,
            value_native=value_native,
            daily_change_pct=change,
            daily_gain_try=daily_gain(value_try, change),
        )

    def _pick_price(self, asset: Asset, latest) -> Tuple[Optional[Decimal], Optional[date]]:
        daily = self._price_repo.get_last_daily_price(asset.id)
        latest_date = latest.as_of.date() if latest is not None else None
        if latest is not None and (daily is None or latest_date >= daily.price_date):
            return latest.price, latest_date
        if daily is not None:
            return daily.close_price, daily.price_date
        return None, None

    def _daily_change_pct(self, asset: Asset, reference_date: Optional[date], quoted: Decimal) -> Optional[Decimal]:
        """Seçilen fiyatın gününden önceki son kapanışa göre değişim (varlığın para biriminde)."""
        if reference_date is None:
            return None
        previous = self._price_repo.get_last_daily_price(asset.id, on_or_before=reference_date - timedelta(days=1))
        if previous is None or previous.close_price <= 0:
            return None
        return (quoted - previous.close_price) / previous.close_price * HUNDRED

