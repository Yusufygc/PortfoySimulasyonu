"""Genel Bakış grafik şablonu: sayılar Türkçe biçimlenir (toFixed ondalık noktası kullanılmaz)."""
from __future__ import annotations

from pathlib import Path

TEMPLATE = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "assets" / "templates" / "tradingview_chart.html"


def test_template_formats_numbers_with_turkish_helpers():
    html = TEMPLATE.read_text(encoding="utf-8")

    assert ".toFixed(" not in html
    for helper in ("function trFixed", "function trPrice", "function trPct", "function trVolume", "locale: 'tr-TR'"):
        assert helper in html
    # fiyat ekseni ve hacim ekseni Türkçe biçimleyiciyle çalışır
    assert html.count("priceFormat: TR_PRICE") >= 5 and "formatter: trVolume" in html
