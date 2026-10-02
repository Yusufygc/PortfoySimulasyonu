"""Son fiyat güncelleme zamanı ve dönemsel getiri değerlerinin kalıcı saklanması.

Eski arayüzle aynı QSettings kayıtlarını kullanır; böylece iki arayüz de aynı "son güncelleme" bilgisini görür.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional, Tuple

from PySide6.QtCore import QSettings

DASHBOARD_LAST_UPDATE_KEY = "dashboard/last_price_update_at"
WEEKLY_RETURN_KEY = "dashboard/weekly_return_pct"
MONTHLY_RETURN_KEY = "dashboard/monthly_return_pct"


def model_portfolio_last_update_key(portfolio_id: int) -> str:
    return f"model_portfolios/{portfolio_id}/last_price_update_at"


def format_last_update(updated_at: Optional[datetime]) -> str:
    return f"Son güncelleme: {updated_at.strftime('%d.%m.%Y %H:%M')}" if updated_at else ""


def format_return_pct(value: Optional[float]) -> str:
    return "-" if value is None else f"%{value:+.2f}".replace(".", ",")


class LastUpdateStore:
    def __init__(self, settings: Optional[QSettings] = None) -> None:
        self._settings = settings or QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")

    # ---- son güncelleme zamanı ----------------------------------------------------------
    def dashboard_last_update(self) -> Optional[datetime]:
        return self._read_time(DASHBOARD_LAST_UPDATE_KEY)

    def save_dashboard_last_update(self, updated_at: Optional[datetime] = None) -> datetime:
        return self._write_time(DASHBOARD_LAST_UPDATE_KEY, updated_at)

    def model_portfolio_last_update(self, portfolio_id: int) -> Optional[datetime]:
        return self._read_time(model_portfolio_last_update_key(portfolio_id))

    def save_model_portfolio_last_update(self, portfolio_id: int, updated_at: Optional[datetime] = None) -> datetime:
        return self._write_time(model_portfolio_last_update_key(portfolio_id), updated_at)

    # ---- dönemsel getiriler -------------------------------------------------------------
    def saved_returns(self) -> Tuple[Optional[float], Optional[float]]:
        return self._read_float(WEEKLY_RETURN_KEY), self._read_float(MONTHLY_RETURN_KEY)

    def save_returns(self, weekly_pct: Optional[float], monthly_pct: Optional[float]) -> None:
        if weekly_pct is not None:
            self._settings.setValue(WEEKLY_RETURN_KEY, weekly_pct)
        if monthly_pct is not None:
            self._settings.setValue(MONTHLY_RETURN_KEY, monthly_pct)
        self._settings.sync()

    # ---- iç yardımcılar -----------------------------------------------------------------
    def _read_time(self, key: str) -> Optional[datetime]:
        value = self._settings.value(key, "", type=str)
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def _write_time(self, key: str, updated_at: Optional[datetime]) -> datetime:
        updated_at = updated_at or datetime.now()
        self._settings.setValue(key, updated_at.isoformat(timespec="seconds"))
        self._settings.sync()
        return updated_at

    def _read_float(self, key: str) -> Optional[float]:
        value = self._settings.value(key, None)
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None
