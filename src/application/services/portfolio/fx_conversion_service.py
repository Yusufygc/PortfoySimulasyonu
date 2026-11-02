from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import List, Optional

from src.domain.market_clock import market_time, market_today
from src.domain.models.fx_conversion import FxConversion, FxSide


class FxConversionService:
    """Ortak nakit havuzunda TL ile USD arasında döviz al/sat (iç transfer).

    Kur, kullanıcı tarafından girilir (verilmezse güncel `FxRateService` kuru); alım TL bakiyesini, satım USD bakiyesini
    aşamaz. Hata sessizce yutulmaz: yetersiz bakiye açık mesajla reddedilir.
    """

    def __init__(self, fx_repo, cash_pool, fx_rate_service=None) -> None:
        self._repo = fx_repo
        self._pool = cash_pool
        self._fx_rates = fx_rate_service

    def list_conversions(self) -> List[FxConversion]:
        return self._repo.list_all()

    def buy_usd(self, usd_amount, rate=None, **options) -> FxConversion:
        return self._convert(FxSide.BUY_USD, usd_amount, rate, options)

    def sell_usd(self, usd_amount, rate=None, **options) -> FxConversion:
        return self._convert(FxSide.SELL_USD, usd_amount, rate, options)

    def delete_conversion(self, conversion_id: int) -> None:
        conversion = self._repo.get(conversion_id)
        if conversion is None:
            raise ValueError("Döviz işlemi bulunamadı.")
        if not self._pool.usd_timeline_valid(exclude_fx_id=conversion_id):
            raise ValueError("Bu döviz işlemi silinemez: sonraki USD ile ödenen işlemler yetersiz bakiyeye düşer.")
        self._repo.delete(conversion_id)

    # ---- yardımcılar ------------------------------------------------------------------------------

    def _convert(self, side: FxSide, usd_amount, rate, options: dict) -> FxConversion:
        day: date = options.pop("conversion_date", None) or market_today()
        at: Optional[time] = options.pop("conversion_time", None) or market_time()
        fee, note = options.pop("fee_try", None) or Decimal("0"), options.pop("note", None)
        if options:
            raise TypeError(f"Bilinmeyen döviz işlemi seçeneği: {', '.join(sorted(options))}")
        usd = Decimal(str(usd_amount))
        rate_value = self._resolve_rate(rate)
        conversion = FxConversion(None, day, at, side, usd, rate_value, Decimal(str(fee)), (note or "").strip() or None)
        self._check_balance(conversion)
        return self._repo.add(conversion)

    def _resolve_rate(self, rate) -> Decimal:
        if rate is not None and str(rate).strip() != "":
            return Decimal(str(rate))
        current = self._fx_rates.get_rate("USD", "TRY") if self._fx_rates is not None else None
        if current is None:
            raise ValueError("USD/TRY kuru gerekli.")
        return current

    def _check_balance(self, conversion: FxConversion) -> None:
        as_of = (conversion.conversion_date, conversion.conversion_time)
        if conversion.side == FxSide.BUY_USD:
            needed, available = -conversion.try_effect, self._pool.try_balance(as_of)
            if needed > available:
                raise ValueError(f"Yetersiz TL nakit. Gerekli: {needed:,.2f} TL, Mevcut: {available:,.2f} TL")
        else:
            available = self._pool.usd_balance(as_of)
            if conversion.usd_amount > available:
                raise ValueError(f"Yetersiz USD nakit. Satılacak: {conversion.usd_amount:,.2f} USD, Mevcut: {available:,.2f} USD")
