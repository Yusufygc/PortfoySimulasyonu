from __future__ import annotations

from datetime import date
from typing import Set

from src.infrastructure.calendar.bist_holiday_calendar import get_bist_holidays


class BistHolidayProvider:
    def get_holidays(self, start_date: date, end_date: date) -> Set[date]:
        return get_bist_holidays(start_date, end_date)
