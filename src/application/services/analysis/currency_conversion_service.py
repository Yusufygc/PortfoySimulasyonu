from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict


class CurrencyConversionService:
    def apply_currency_mode(
        self,
        series: Dict[date, Decimal],
        currency_mode: str,
        usd_try_series: Dict[date, Decimal],
        cpi_series: Dict[date, Decimal],
        is_normalized: bool = False,
    ) -> Dict[date, Decimal]:
        if not series or currency_mode == "TL":
            return series

        result: Dict[date, Decimal] = {}
        if currency_mode == "USD":
            result = self._to_usd(series, usd_try_series)
        elif currency_mode == "REAL":
            result = self._to_real(series, cpi_series)

        if is_normalized and result:
            return self._normalize_to_100(result)
        return result

    @staticmethod
    def _to_usd(
        series: Dict[date, Decimal],
        usd_try_series: Dict[date, Decimal],
    ) -> Dict[date, Decimal]:
        return {
            point_date: value / usd_try_series[point_date]
            for point_date, value in series.items()
            if point_date in usd_try_series and usd_try_series[point_date]
        }

    @staticmethod
    def _to_real(
        series: Dict[date, Decimal],
        cpi_series: Dict[date, Decimal],
    ) -> Dict[date, Decimal]:
        if not cpi_series:
            return series
        base_cpi = cpi_series[min(cpi_series.keys())]
        if base_cpi == 0:
            return series
        return {
            point_date: value / (cpi_series[point_date] / base_cpi)
            for point_date, value in series.items()
            if point_date in cpi_series
        }

    @staticmethod
    def _normalize_to_100(series: Dict[date, Decimal]) -> Dict[date, Decimal]:
        base_value = series[min(series.keys())]
        if not base_value:
            return series
        return {
            point_date: (value / base_value) * Decimal("100")
            for point_date, value in series.items()
        }
