from __future__ import annotations

from datetime import date

from src.infrastructure.calendar.bist_holiday_calendar import (
    is_bist_half_trading_day,
    is_bist_trading_day,
)


class BistTradingCalendarProvider:
    def is_trading_day(self, point_date: date) -> bool:
        return is_bist_trading_day(point_date)

    def is_half_trading_day(self, point_date: date) -> bool:
        return is_bist_half_trading_day(point_date)
