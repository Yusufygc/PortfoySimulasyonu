from __future__ import annotations

from datetime import date, time

from PyQt5.QtWidgets import QMessageBox, QWidget


def confirm_market_session_if_needed(
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

    reply = QMessageBox.question(
        parent,
        "Piyasa Kapali",
        (
            f"{status.message}\n\n"
            "Nakit ve lot kontrolleri yine uygulanacak. "
            "Manuel kayit olarak devam etmek istiyor musunuz?"
        ),
        QMessageBox.Yes | QMessageBox.No,
        QMessageBox.No,
    )
    return reply == QMessageBox.Yes
