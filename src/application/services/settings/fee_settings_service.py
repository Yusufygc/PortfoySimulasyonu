from __future__ import annotations

from decimal import Decimal, InvalidOperation

from src.domain.models.fees import FeeRates, calculate_fee
from src.domain.ports.repositories.i_app_settings_repo import IAppSettingsRepository

_KEYS = {
    "bist_commission_pct": "fee.bist_commission_pct",
    "asset_commission_pct": "fee.asset_commission_pct",
    "bsmv_pct": "fee.bsmv_pct",
}


class FeeSettingsService:
    """Komisyon ve BSMV oranları (kullanıcı ayarı, varsayılan 0) ile işlem ücreti hesabı.

    Ücret işlem anında hesaplanıp işlemle birlikte saklanır; oran sonradan değişse eski işlemler aynı kalır.
    """

    def __init__(self, settings_repo: IAppSettingsRepository) -> None:
        self._repo = settings_repo

    def get_rates(self) -> FeeRates:
        values = {}
        for field, key in _KEYS.items():
            raw = self._repo.get(key)
            try:
                values[field] = Decimal(raw) if raw is not None else Decimal("0")
            except InvalidOperation:
                values[field] = Decimal("0")
        try:
            return FeeRates(**values)
        except ValueError:  # bozuk kayıt ücretsiz çalışmaya düşer; işlem engellenmez
            return FeeRates()

    def set_rates(self, rates: FeeRates) -> None:
        for field, key in _KEYS.items():
            self._repo.set(key, str(getattr(rates, field)))

    def bist_fee(self, gross_amount: Decimal) -> Decimal:
        rates = self.get_rates()
        return calculate_fee(gross_amount, rates.bist_commission_pct, rates.bsmv_pct)

    def asset_fee(self, gross_amount: Decimal) -> Decimal:
        rates = self.get_rates()
        return calculate_fee(gross_amount, rates.asset_commission_pct, rates.bsmv_pct)
