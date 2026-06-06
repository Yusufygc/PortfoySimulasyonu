from datetime import date, time

from src.application.services.market.bist_market_session_service import BistMarketSessionService
from src.infrastructure.calendar.bist_holiday_calendar import is_bist_half_trading_day
from src.infrastructure.calendar.bist_trading_calendar_provider import BistTradingCalendarProvider


def _service() -> BistMarketSessionService:
    return BistMarketSessionService(trading_calendar=BistTradingCalendarProvider())


def test_half_day_uses_early_close():
    service = _service()

    assert is_bist_half_trading_day(date(2026, 5, 26))
    assert service.status_for(date(2026, 5, 26), time(12, 45)).is_open
    status = service.status_for(date(2026, 5, 26), time(13, 1))

    assert not status.is_open
    assert status.day_type == "half_day"
    assert status.reason == "outside_session"


def test_closed_holiday_is_warning_not_open():
    service = _service()

    status = service.status_for(date(2026, 5, 27), time(10, 0))

    assert not status.is_open
    assert status.reason == "closed_day"
    assert "manuel" not in status.message.lower()


def test_weekend_is_not_open():
    service = _service()

    status = service.status_for(date(2026, 6, 6), time(11, 0))

    assert not status.is_open
    assert status.reason == "closed_day"


def test_full_day_session_bounds():
    service = _service()

    assert service.status_for(date(2026, 5, 25), time(10, 0)).is_open
    assert service.status_for(date(2026, 5, 25), time(18, 10)).is_open
    assert not service.status_for(date(2026, 5, 25), time(18, 11)).is_open
