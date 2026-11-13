"""Planlama sayfası bütçe ayı listesi: ilk bütçe/işlem tarihinden bu aya kadar, en yeni ay başta."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)


def budget_months(planning_service, portfolio_service, current_month: str, now: datetime | None = None) -> List[str]:
    """`YYYY-AA` listesi; servisler yoksa son bir yılı üretir, `current_month` her zaman listededir."""
    now = now or datetime.now()
    cur_year, cur_month = now.year, now.month
    start_year, start_month = cur_year - 1, 1

    try:
        if planning_service:
            budgets = planning_service.get_all_budgets()
            if budgets:
                oldest = min(b.month for b in budgets if b.month)
                year, month = oldest.split("-")
                start_year = min(start_year, int(year))
                start_month = min(start_month, int(month))

        first_trade = portfolio_service.get_first_trade_date() if portfolio_service else None
        if first_trade:
            start_year = min(start_year, first_trade.year)
            start_month = min(start_month, first_trade.month)
    except Exception as exc:
        logger.warning("Bütçe ayları listelenirken hata: %s", exc)

    months = []
    year, month = start_year, start_month
    while (year < cur_year) or (year == cur_year and month <= cur_month):
        months.append(f"{year}-{month:02d}")
        month += 1
        if month > 12:
            month = 1
            year += 1

    months.reverse()  # en yeni ay en üstte
    if current_month not in months:
        months.insert(0, current_month)
    return months
