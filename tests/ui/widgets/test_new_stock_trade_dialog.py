import sys
from datetime import datetime, timezone
from decimal import Decimal

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication

from src.application.services.market.price_lookup_service import PriceLookupResult
from src.ui.widgets.dashboard.dialogs.new_stock_trade_dialog import NewStockTradeDialog


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


def test_new_stock_trade_dialog_uses_lookup_company_name_without_user_input():
    dialog = NewStockTradeDialog(price_lookup_func=None)
    dialog.line_ticker.setText("ASELS")

    dialog._on_price_fetched(
        PriceLookupResult(
            price=Decimal("401.75"),
            as_of=datetime(2026, 5, 26, tzinfo=timezone.utc),
            source="intraday",
            company_name="ASELSAN",
            normalized_ticker="ASELS.IS",
        )
    )
    dialog.edit_price.setText("401.75")
    dialog.accept()

    result = dialog.get_result()

    assert dialog.lbl_company_name.text() == "ASELSAN"
    assert result["ticker"] == "ASELS.IS"
    assert result["name"] == "ASELSAN"


def test_new_stock_trade_dialog_summary_has_no_inline_style_leak():
    dialog = NewStockTradeDialog(price_lookup_func=None)
    dialog.line_ticker.setText("ASELS")
    dialog._on_price_fetched(
        PriceLookupResult(
            price=Decimal("401.75"),
            as_of=datetime(2026, 5, 26, tzinfo=timezone.utc),
            source="last_close",
            company_name="ASELSAN",
            normalized_ticker="ASELS.IS",
        )
    )

    dialog._go_to_page2()

    summary_text = f"{dialog.lbl_summary_ticker.text()} {dialog.lbl_summary_name.text()}"
    assert dialog.lbl_fetched_source.text() == "Son Kapanış (26.05.2026)"
    assert dialog.lbl_summary_ticker.text() == "ASELS"
    assert dialog.lbl_summary_name.text() == "ASELSAN"
    assert "<span" not in summary_text
    assert "font-size" not in summary_text
    assert "color:" not in summary_text
    assert "font-weight" not in summary_text
