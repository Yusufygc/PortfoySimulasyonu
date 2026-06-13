from decimal import Decimal

import pytest

pytest.importorskip("PySide6")
from src.qt_compat.qtcore import Qt
from src.qt_compat.qttest import QTest

from src.ui.widgets.shared import CurrencySpinBox


def _currency_box(qapp, value: float = 1234.56) -> CurrencySpinBox:
    box = CurrencySpinBox()
    box.setRange(0, 10_000_000)
    box.setDecimals(2)
    box.setSuffix(" TL")
    box.setValue(value)
    box.show()
    box.clearFocus()
    qapp.processEvents()
    return box


def test_currency_spin_box_displays_turkish_format_when_not_focused(qapp):
    box = CurrencySpinBox()
    box.setRange(0, 10_000_000)
    box.setDecimals(2)
    box.setSuffix(" TL")
    box.setValue(1234.56)

    assert box.text() == "1.234,56 TL"
    assert box.decimal_value() == Decimal("1234.56")


def test_currency_spin_box_edits_raw_value_on_focus_and_formats_on_blur(qapp):
    box = _currency_box(qapp)

    box.setFocus()
    qapp.processEvents()

    assert box.text() == "1.234,56"

    box.clear()
    QTest.keyClicks(box.lineEdit(), "9876,5")
    qapp.processEvents()
    box.clearFocus()
    qapp.processEvents()

    assert box.value() == 9876.5
    assert box.text() == "9.876,50 TL"


def test_currency_spin_box_backspace_never_deletes_suffix(qapp):
    box = _currency_box(qapp)

    box.setFocus()
    qapp.processEvents()
    box.lineEdit().setCursorPosition(len(box.text()))
    QTest.keyClick(box.lineEdit(), Qt.Key_Backspace)
    qapp.processEvents()

    assert box.text() == "1.234,5"


def test_currency_spin_box_rejects_letters(qapp):
    box = _currency_box(qapp, 99)

    box.setFocus()
    box.lineEdit().setText("abc")
    qapp.processEvents()

    assert box.has_valid_input(require_positive=True) is False

    box.clearFocus()
    qapp.processEvents()

    assert box.value() == 99


@pytest.mark.parametrize("raw_text", ["-1000", "-", "abc", "100abc", "", ".", ","])
def test_currency_spin_box_rejects_invalid_raw_amounts_without_minimum_fallback(qapp, raw_text):
    box = _currency_box(qapp, 123.45)
    box.lineEdit().setText(raw_text)

    assert box.has_valid_input(require_positive=True) is False
    assert box.valueFromText(raw_text) != pytest.approx(box.minimum())


@pytest.mark.parametrize(
    ("raw_text", "expected"),
    [
        ("1000", Decimal("1000")),
        ("1000,50", Decimal("1000.50")),
        ("1000.50", Decimal("1000.50")),
        ("1.000,50", Decimal("1000.50")),
    ],
)
def test_currency_spin_box_parses_supported_money_formats(qapp, raw_text, expected):
    box = _currency_box(qapp, 123.45)
    box.lineEdit().setText(raw_text)

    assert box.has_valid_input(require_positive=True) is True
    assert box.input_decimal_value() == expected


def test_currency_spin_box_keeps_invalid_raw_text_after_focus_out(qapp):
    box = _currency_box(qapp, 123.45)
    box.setFocus()
    qapp.processEvents()
    box.lineEdit().setText("-1000")
    box._remember_user_text("-1000")

    box.clearFocus()
    qapp.processEvents()

    assert box.value() == pytest.approx(123.45)
    assert box.has_valid_input(require_positive=True) is False


def test_currency_spin_box_accepts_one_billion_when_in_range(qapp):
    box = _currency_box(qapp, 123.45)
    box.setRange(0, 1_000_000_000)

    box.lineEdit().setText("1000000000")

    assert box.has_valid_input() is True
    assert box.input_decimal_value() == Decimal("1000000000")


def test_currency_spin_box_rejects_above_max_without_maximum_clamp(qapp):
    box = _currency_box(qapp, 123.45)
    box.setRange(0, 1_000_000_000)

    box.lineEdit().setText("1000000001")

    assert box.has_valid_input() is False
    assert box.valueFromText("1000000001") != pytest.approx(box.maximum())
