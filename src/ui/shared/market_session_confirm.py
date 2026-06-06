from __future__ import annotations

from datetime import date, time

from PyQt5.QtWidgets import QMessageBox, QWidget

from src.ui.shared.locale_tr import L10N


def confirm_market_session_if_needed(
    parent: QWidget,
    market_session_service,
    trade_date: date,
    trade_time: time | None,
) -> bool:
    return validate_market_session_open(parent, market_session_service, trade_date, trade_time)


def validate_market_session_open(
    parent: QWidget,
    market_session_service,
    trade_date: date,
    trade_time: time | None,
) -> bool:
    if market_session_service is None:
        return True

    status = market_session_service.status_for(trade_date, trade_time)
    if status.is_open:
        return True

    message = L10N.PIYASA_SEANSI_DISINDA_ISLEM_UYARISI
    if status.message:
        message = f"{status.message}\n\n{message}"
    QMessageBox.warning(
        parent,
        L10N.PIYASA_KAPALI,
        message,
    )
    return False
