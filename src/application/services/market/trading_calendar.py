from __future__ import annotations

from datetime import date
from typing import Protocol


class MarketTradingCalendar(Protocol):
    def is_trading_day(self, point_date: date) -> bool:
        ...

    def is_half_trading_day(self, point_date: date) -> bool:
        ...


class WeekdayTradingCalendar:
    def is_trading_day(self, point_date: date) -> bool:
        return point_date.weekday() < 5

    def is_half_trading_day(self, point_date: date) -> bool:
        return False
