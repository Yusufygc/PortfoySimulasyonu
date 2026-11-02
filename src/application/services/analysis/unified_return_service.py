"""Birleşik portföyün (BIST + varlıklar + nakit havuzu) haftalık ve aylık getirisi.

Getiri, `UnifiedSeriesBuilder` TWR endeksinin dönem başı ve sonu oranıdır: sermaye yatırma/çekme ve havuz içi hareketler
getiriyi bozmaz, kur hareketi ve varlık fiyatları getiriye girer.
"""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Optional, Tuple

WEEK_DAYS = 7
MONTH_DAYS = 30


class UnifiedReturnService:
    def __init__(self, series_builder) -> None:
        self._builder = series_builder

    def returns(self, end: date) -> Tuple[Optional[float], Optional[float]]:
        """(haftalık %, aylık %); dönem başında portföy değeri yoksa o dönem None."""
        series = self._builder.build(end - timedelta(days=MONTH_DAYS), end)
        return self._period(series, end, WEEK_DAYS), self._period(series, end, MONTH_DAYS)

    @staticmethod
    def _period(series, end: date, days: int) -> Optional[float]:
        start = end - timedelta(days=days)
        if start not in series.twr or end not in series.twr or series.values.get(start, Decimal("0")) <= 0:
            return None
        return float((series.twr[end] / series.twr[start] - 1) * 100)
