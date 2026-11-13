"""Kullanıcı tarih girişi: tek ayrıştırıcı (`date_input`) ve QML eşi (`Dates`); görünen biçim GG.AA.YYYY.

2026-11-08 QA: Hisse Detay emir formu YYYY-AA-GG istiyordu, uygulamanın geri kalanı GG.AA.YYYY kullanıyordu; tarihi 11 ayrı
fonksiyon kendi biçim listesiyle ayrıştırıyordu.
"""
from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from src.ui_qml.controllers.date_input import DATE_HINT, format_date_text, parse_date_text

QML_DIR = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml"


@pytest.mark.parametrize("text,expected", [
    ("14.11.2026", date(2026, 11, 14)),
    ("1.2.2026", date(2026, 2, 1)),            # başındaki sıfır zorunlu değil
    (" 14.11.2026 ", date(2026, 11, 14)),
    ("2026-11-14", date(2026, 11, 14)),         # eski biçim sessizce kabul edilir (yapıştırma, betik)
    ("29.02.2028", date(2028, 2, 29)),
])
def test_parse_accepts_turkish_and_iso(text, expected):
    assert parse_date_text(text) == expected


@pytest.mark.parametrize("text", ["", "   ", None, "abc", "32.01.2026", "29.02.2027", "14/11/2026", "14.11", "2026-13-01", "14.11.26"])
def test_parse_rejects_everything_else(text):
    assert parse_date_text(text) is None


def test_format_is_dd_mm_yyyy_and_round_trips():
    assert format_date_text(date(2026, 2, 1)) == "01.02.2026"
    assert parse_date_text(format_date_text(date(2026, 11, 14))) == date(2026, 11, 14)
    assert DATE_HINT == "GG.AA.YYYY"


@pytest.fixture(scope="module")
def qapp():
    return QGuiApplication.instance() or QGuiApplication([])


def _evaluate(qapp, expression: str):
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    source = f'import QtQuick\nimport "../theme"\nQtObject {{ property var result: {expression} }}\n'
    component = QQmlComponent(engine)
    component.setData(source.encode("utf-8"), QUrl.fromLocalFile(str(QML_DIR / "components" / "_dates_probe.qml")))
    assert component.isReady(), "; ".join(e.toString() for e in component.errors())
    return component.create().property("result")


def test_qml_format_matches_python(qapp):
    assert _evaluate(qapp, "Dates.format(new Date(2026, 10, 14))") == format_date_text(date(2026, 11, 14))
    assert _evaluate(qapp, "Dates.format(new Date(2026, 1, 1))") == "01.02.2026"


def test_qml_today_and_next_year_match_python(qapp):
    now = datetime.now()
    assert _evaluate(qapp, "Dates.today()") == format_date_text(now.date())
    try:
        next_year = now.date().replace(year=now.year + 1)
    except ValueError:  # 29 Şubat: JavaScript setFullYear 1 Mart'a taşar
        next_year = date(now.year + 1, 3, 1)
    assert _evaluate(qapp, "Dates.todayPlusYears(1)") == format_date_text(next_year)
