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
        """(haftalık %, aylık %); dönem içinde değerli gün yoksa None, portföy dönem içinde başladıysa ilk değerli günden hesaplanır."""
        series = self._builder.build(end - timedelta(days=MONTH_DAYS), end)
        return self._period(series, end, WEEK_DAYS), self._period(series, end, MONTH_DAYS)

    @staticmethod
    def _period(series, end: date, days: int) -> Optional[float]:
        """Dönem başı yoksa (portföy dönem içinde başladıysa) ilk değerli günden başlar; tek günlük dönem None."""
        start = end - timedelta(days=days)
        funded = [day for day in sorted(series.twr) if start <= day <= end and series.values.get(day, Decimal("0")) > 0]
        if not funded or funded[0] >= end or end not in series.twr:
            return None
        return float((series.twr[end] / series.twr[funded[0]] - 1) * 100)
