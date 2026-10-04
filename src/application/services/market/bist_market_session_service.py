from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Optional, Tuple

from src.application.services.market.trading_calendar import MarketTradingCalendar, WeekdayTradingCalendar

# Seans kapanışından sonra kesin kapanış fiyatının veri kaynağında (yfinance ~15 dk gecikmeli) görünmesi için beklenen süre
CLOSE_DATA_DELAY = timedelta(minutes=20)


@dataclass(frozen=True)
class MarketSessionStatus:
    is_open: bool
    day_type: str
    reason: str
    message: str
    open_time: time | None = None
    close_time: time | None = None


class BistMarketSessionService:
    """BIST equity-market session check used for trade-entry guards."""

    FULL_DAY_OPEN = time(10, 0)
    FULL_DAY_CLOSE = time(18, 10)
    HALF_DAY_OPEN = time(10, 0)
    HALF_DAY_CLOSE = time(13, 0)

    def __init__(self, trading_calendar: MarketTradingCalendar | None = None) -> None:
        self._trading_calendar = trading_calendar or WeekdayTradingCalendar()

    def _is_half_day(self, day: date) -> bool:
        is_half = getattr(self._trading_calendar, "is_half_trading_day", None)
        return bool(is_half(day)) if is_half is not None else False

    def session_window(self, day: date) -> Optional[Tuple[datetime, datetime]]:
        """İşlem günü için (seans açılışı, kapanış verisinin hazır olduğu an); işlem günü değilse None.

        Canlı fiyatın geçerli sayıldığı aralık budur: kapanış verisi hazır olduktan sonra o günün günlük barı esastır.
        """
        if not self._trading_calendar.is_trading_day(day):
            return None
        half = self._is_half_day(day)
        open_time = self.HALF_DAY_OPEN if half else self.FULL_DAY_OPEN
        close_time = self.HALF_DAY_CLOSE if half else self.FULL_DAY_CLOSE
        return datetime.combine(day, open_time), datetime.combine(day, close_time) + CLOSE_DATA_DELAY

    def last_completed_trading_day(self, now: datetime) -> date:
        """Kapanış verisi hazır olan son işlem günü: bugün işlem günüyse ve kapanış verisi hazırsa bugün, değilse önceki."""
        window = self.session_window(now.date())
        if window is not None and now >= window[1]:
            return now.date()
        candidate = now.date() - timedelta(days=1)
        while not self._trading_calendar.is_trading_day(candidate):
            candidate -= timedelta(days=1)
        return candidate

    def status_for(self, trade_date: date, trade_time: time | None = None) -> MarketSessionStatus:
        if not self._trading_calendar.is_trading_day(trade_date):
            return MarketSessionStatus(
                is_open=False,
                day_type="closed",
                reason="closed_day",
                message=(
                    f"{trade_date.strftime('%d.%m.%Y')} BIST icin islem gunu degil. "
                    "Lutfen islemin gerceklestigi acik piyasa tarihini secin."
                ),
            )

        is_half_day = self._is_half_day(trade_date)
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
