from __future__ import annotations

from dataclasses import dataclass
from datetime import date, time

from src.infrastructure.calendar.bist_holiday_calendar import (
    is_bist_half_trading_day,
    is_bist_trading_day,
)


@dataclass(frozen=True)
class MarketSessionStatus:
    is_open: bool
    day_type: str
    reason: str
    message: str
    open_time: time | None = None
    close_time: time | None = None


class BistMarketSessionService:
    """BIST equity-market session check used for trade-entry warnings."""

    FULL_DAY_OPEN = time(10, 0)
    FULL_DAY_CLOSE = time(18, 10)
    HALF_DAY_OPEN = time(10, 0)
    HALF_DAY_CLOSE = time(13, 0)

    def status_for(self, trade_date: date, trade_time: time | None = None) -> MarketSessionStatus:
        if not is_bist_trading_day(trade_date):
            return MarketSessionStatus(
                is_open=False,
                day_type="closed",
                reason="closed_day",
                message=(
                    f"{trade_date.strftime('%d.%m.%Y')} BIST icin islem gunu degil. "
                    "Bu islemi manuel kayit olarak ekleyebilirsiniz."
                ),
            )

        is_half_day = is_bist_half_trading_day(trade_date)
        open_time = self.HALF_DAY_OPEN if is_half_day else self.FULL_DAY_OPEN
        close_time = self.HALF_DAY_CLOSE if is_half_day else self.FULL_DAY_CLOSE
        day_type = "half_day" if is_half_day else "full_day"

        if trade_time is None:
            return MarketSessionStatus(
                is_open=True,
                day_type=day_type,
                reason="date_only",
                message="Islem tarihi BIST islem gunu.",
                open_time=open_time,
                close_time=close_time,
            )

        if open_time <= trade_time <= close_time:
            return MarketSessionStatus(
                is_open=True,
                day_type=day_type,
                reason="open",
                message="BIST seansi acik.",
                open_time=open_time,
                close_time=close_time,
            )

        session_label = "yarim gun" if is_half_day else "normal gun"
        return MarketSessionStatus(
            is_open=False,
            day_type=day_type,
            reason="outside_session",
            message=(
                f"{trade_date.strftime('%d.%m.%Y')} {session_label} seans saati "
                f"{open_time.strftime('%H:%M')}-{close_time.strftime('%H:%M')}. "
                f"Secilen saat {trade_time.strftime('%H:%M')} seans disinda."
            ),
            open_time=open_time,
            close_time=close_time,
        )
