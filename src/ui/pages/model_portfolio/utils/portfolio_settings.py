# src/ui/pages/model_portfolio/utils/portfolio_settings.py

import json
from decimal import Decimal
from typing import Dict, Optional
from datetime import datetime
from src.qt_compat.qtcore import QSettings

LAST_SELECTED_PORTFOLIO_KEY = "model_portfolios/last_selected_id"


class PortfolioSettingsManager:
    def __init__(self) -> None:
        self._settings = QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")

    def get_last_selected_portfolio_id(self) -> Optional[int]:
        value = self._settings.value(LAST_SELECTED_PORTFOLIO_KEY, None)
        try:
            return int(value) if value is not None else None
        except (TypeError, ValueError):
            return None

    def set_last_selected_portfolio_id(self, portfolio_id: int) -> None:
        self._settings.setValue(LAST_SELECTED_PORTFOLIO_KEY, portfolio_id)
        self._settings.sync()

    def remove_portfolio_settings(self, portfolio_id: int) -> None:
        self._settings.remove(self._price_map_settings_key(portfolio_id))
        self._settings.remove(self._last_update_settings_key(portfolio_id))
        self._settings.remove(LAST_SELECTED_PORTFOLIO_KEY)
        self._settings.sync()

    def get_last_update_time(self, portfolio_id: int) -> Optional[datetime]:
        value = self._settings.value(
            self._last_update_settings_key(portfolio_id),
            "",
            type=str,
        )
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def save_portfolio_prices_and_time(self, portfolio_id: int, price_map: Dict[int, Decimal], updated_at: datetime) -> None:
        self._settings.setValue(
            self._price_map_settings_key(portfolio_id),
            self._serialize_price_map(price_map),
        )
        self.save_portfolio_last_update_time(portfolio_id, updated_at)

    def save_portfolio_last_update_time(self, portfolio_id: int, updated_at: datetime) -> None:
        self._settings.setValue(
            self._last_update_settings_key(portfolio_id),
            updated_at.isoformat(timespec="seconds"),
        )
        self._settings.sync()

    def load_saved_price_map(self, portfolio_id: int) -> Dict[int, Decimal]:
        value = self._settings.value(self._price_map_settings_key(portfolio_id), "", type=str)
        if not value:
            return {}
        try:
            raw_map = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return {}

        price_map: Dict[int, Decimal] = {}
        for stock_id, price in raw_map.items():
            try:
                price_map[int(stock_id)] = Decimal(str(price))
            except Exception:
                continue
        return price_map

    @staticmethod
    def _serialize_price_map(price_map: Dict[int, Decimal]) -> str:
        return json.dumps({str(stock_id): str(price) for stock_id, price in price_map.items()})

    @staticmethod
    def _price_map_settings_key(portfolio_id: int) -> str:
        return f"model_portfolios/{portfolio_id}/price_map"

    @staticmethod
    def _last_update_settings_key(portfolio_id: int) -> str:
        return f"model_portfolios/{portfolio_id}/last_price_update_at"
