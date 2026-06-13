from datetime import datetime, timezone
from decimal import Decimal

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtwidgets import QMessageBox

from src.application.services.market.price_lookup_service import PriceLookupResult
from src.ui.shared.locale_tr import L10N
from src.ui.widgets.dashboard.dialogs.new_stock_trade_dialog import NewStockTradeDialog


class _FakeThreadPool:
    def __init__(self):
        self.started = []

    def start(self, worker):
        self.started.append(worker)

def test_new_stock_trade_dialog_uses_lookup_company_name_without_user_input(qapp):
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


def test_new_stock_trade_dialog_summary_has_no_inline_style_leak(qapp):
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


def test_new_stock_trade_dialog_begin_lookup_clears_previous_price_state(qapp):
    dialog = NewStockTradeDialog(price_lookup_func=None)
    dialog.current_price = Decimal("401.75")
    dialog.fetched_stock_name = "ASELSAN"
    dialog.edit_price.setText("401.75")
    dialog.edit_amount.setText("401.75")
    dialog._last_lookup_ticker = "ASELS.IS"
    dialog._last_lookup_succeeded = True

    dialog._begin_lookup("THYAO.IS")

    assert dialog.current_price is None
    assert dialog.fetched_stock_name is None
    assert dialog.edit_price.text() == ""
    assert dialog.edit_amount.text() == ""
    assert dialog._last_lookup_ticker == "THYAO.IS"
    assert dialog._last_lookup_succeeded is False
    assert dialog.lbl_company_name.text() == L10N.HISSE_KODU_GIRILDIGINDE_OTOMATIK_ALINACAK


def test_new_stock_trade_dialog_validate_page1_prompts_only_after_failed_lookup(qapp, monkeypatch):
    dialog = NewStockTradeDialog(price_lookup_func=lambda ticker: None)
    dialog.line_ticker.setText("ASELS")
    dialog._last_lookup_ticker = "ASELS.IS"
    dialog._last_lookup_succeeded = False
    dialog._price_lookup_in_flight = False

    prompts = []

    def fake_question(*args, **kwargs):
        prompts.append((args, kwargs))
        return QMessageBox.No

    monkeypatch.setattr(QMessageBox, "question", fake_question)

    assert dialog._validate_page1() is False
    assert len(prompts) == 1


def test_new_stock_trade_dialog_ignores_stale_lookup_results(qapp):
    dialog = NewStockTradeDialog(price_lookup_func=None)
    dialog.line_ticker.setText("THYAO")
    dialog._begin_lookup("THYAO.IS")

    dialog._on_price_fetched(
        PriceLookupResult(
            price=Decimal("401.75"),
            as_of=datetime(2026, 5, 26, tzinfo=timezone.utc),
            source="intraday",
            company_name="ASELSAN",
            normalized_ticker="ASELS.IS",
        ),
        requested_ticker="ASELS.IS",
    )

    assert dialog.current_price is None
    assert dialog.fetched_stock_name is None
    assert dialog.lbl_fetched_price.text() == "-"

    dialog._on_price_fetched(
        PriceLookupResult(
            price=Decimal("278.00"),
            as_of=datetime(2026, 5, 26, tzinfo=timezone.utc),
            source="intraday",
            company_name="Türk Hava Yolları",
            normalized_ticker="THYAO.IS",
        ),
        requested_ticker="THYAO.IS",
    )

    assert dialog.current_price == Decimal("278.00")
    assert dialog.fetched_stock_name == "Türk Hava Yolları"
    assert dialog.lbl_company_name.text() == "Türk Hava Yolları"
