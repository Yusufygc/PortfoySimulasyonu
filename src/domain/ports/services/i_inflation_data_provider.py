"""Port: Enflasyon (TÜFE) veri sağlayıcı arayüzü."""
from __future__ import annotations

from datetime import date
from typing import Protocol, runtime_checkable


class InflationDataUnavailable(RuntimeError):
    """TÜFE verisi alınamadığında fırlatılır."""


@runtime_checkable
class IInflationDataProvider(Protocol):
    def get_monthly_tufe(self, start: date, end: date) -> dict[str, float]:
        """Aylık TÜFE endeks değerleri. {"YYYY-MM": index_value}"""
        ...
