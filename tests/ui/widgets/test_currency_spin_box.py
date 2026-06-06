from decimal import Decimal

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

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
    box = _currency_box(qapp, 0)

    box.setFocus()
    box.clear()
    QTest.keyClicks(box.lineEdit(), "12a3b.4")
    qapp.processEvents()

    assert box.text() == "123,4"


def test_currency_spin_box_groups_thousands_while_typing(qapp):
    box = _currency_box(qapp, 0)
    box.setRange(0, 1_000_000_000)

    box.setFocus()
    box.clear()
    QTest.keyClicks(box.lineEdit(), "111111111")
    qapp.processEvents()

    assert box.text() == "111.111.111"
    box.clearFocus()
    qapp.processEvents()
    assert box.value() == 111_111_111
    assert box.text() == "111.111.111,00 TL"
