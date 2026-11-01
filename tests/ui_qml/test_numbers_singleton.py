"""QML `Numbers` tekili Python `parse_decimal_text` ile aynı kurallarla okur; QML'de parseFloat kalmaz."""
from __future__ import annotations

import math
import re
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from src.ui_qml.controllers.number_input import parse_decimal_text

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml"

CASES = [
    "50.000", "1.234,56", "1234.56", "25,5", "10000", "0,25", "1.250,75", " 1 500 ", "", "abc",
    "12,5,3", "1.23.4", "-3,5", ".5", "100.", "1.000.000",
]


@pytest.fixture(scope="module")
def qapp():
    return QGuiApplication.instance() or QGuiApplication([])


def _evaluate(qapp, expression: str):
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    source = f'import QtQuick\nimport "../theme"\nQtObject {{ property var result: {expression} }}\n'
    component = QQmlComponent(engine)
    component.setData(source.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / "components" / "_numbers_probe.qml")))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())
    item = component.create()
    return item.property("result")


@pytest.mark.parametrize("text", CASES)
def test_parse_matches_python(qapp, text):
    value = _evaluate(qapp, f"Numbers.parse({text!r:s})".replace("'", '"'))
    expected = parse_decimal_text(text)
    if expected is None:
        assert math.isnan(value)
    else:
        assert value == pytest.approx(float(expected))


def test_turkish_thousands_are_not_truncated(qapp):
    assert _evaluate(qapp, 'Numbers.parse("50.000")') == 50000


def test_parse_integer_and_fallback(qapp):
    assert _evaluate(qapp, 'Numbers.parseInteger("1.000")') == 1000
    assert math.isnan(_evaluate(qapp, 'Numbers.parseInteger("2,5")'))
    assert _evaluate(qapp, 'Numbers.parseOr("x", 7)') == 7


def test_no_raw_parsefloat_on_user_input():
    offenders = []
    for path in (QML_DIR / "components").glob("*.qml"):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"parseFloat\(\w+\.text|parseInt\(\w+\.text\)|Number\(String\(text\)", line):
                offenders.append(f"{path.name}:{number}")
    assert not offenders, f"Kullanıcı girdisi Numbers.parse ile okunmalı: {offenders}"
