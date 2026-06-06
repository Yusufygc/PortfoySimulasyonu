from __future__ import annotations

from datetime import date, time


TRADE_SESSION_CLOSED_MESSAGE = (
    "Seçilen tarih/saat BIST işlem seansı dışında. "
    "Lütfen işlemin gerçekleştiği açık piyasa tarih ve saatini seçin."
)


def ensure_trade_session_open(
    market_session_service,
    trade_date: date,
    trade_time: time | None,
) -> None:
    if market_session_service is None:
        return

    status = market_session_service.status_for(trade_date, trade_time)
    if not status.is_open:
        raise ValueError(TRADE_SESSION_CLOSED_MESSAGE)
