from __future__ import annotations

from typing import Protocol


class FinancialStatementProviderUnavailable(RuntimeError):
    """Raised when the external financial statement source is unavailable."""


class IFinancialStatementProvider(Protocol):
    """Port: isyatirim.com.tr mali tablo verisi sağlayıcısı."""

    def get_financial_data(
        self,
        ticker: str,
        n_quarters: int = 12,
        currency: str = "TRY",
    ) -> dict:
        """
        Ticker için finansal tablo verisi döndür.

        Returns:
            {
              "ticker":   str,
              "periods":  list[str],        # newest first: ["2026/3", ...]
              "currency": str,
              "sections": {
                "bilanco":    {kalem: {period: float|None}},
                "gelir":      {kalem: {period: float|None}},
                "dipnot":     {kalem: {period: float|None}},
                "nakit_akim": {kalem: {period: float|None}},
              }
            }

        Raises:
            FinancialStatementProviderUnavailable: ağ/parse hatası.
        """
        ...
