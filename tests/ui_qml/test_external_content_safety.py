"""Dış kaynaklı içerik güvenliği: bağlantı şeması, HTML/JS enjeksiyonu, haber metni temizliği."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from src.infrastructure.news.feed_parser import clean_text
from src.infrastructure.news.kap_news_provider import _to_news_item
from src.ui_qml.controllers import url_opener
from src.ui_qml.controllers.comparison_chart_html import build_periodic_html, build_treemap_html, js_literal


@pytest.fixture
def opened(monkeypatch):
    calls = []
    monkeypatch.setattr(url_opener.QDesktopServices, "openUrl", lambda url: calls.append(url.toString()) or True)
    return calls


@pytest.mark.parametrize(
    "url", ["file:///C:/Windows/system32/calc.exe", "javascript:alert(1)", "ms-settings:", "", "https://", "ftp://x/y"]
)
def test_unsafe_urls_are_rejected(opened, url):
    assert url_opener.open_external_url(url) is False
    assert opened == []


def test_http_urls_open(opened):
    assert url_opener.open_external_url(" https://www.kap.org.tr/tr/Bildirim/1 ")
    assert opened == ["https://www.kap.org.tr/tr/Bildirim/1"]


def test_corporate_candidate_source_uses_safe_opener(opened):
    from src.ui_qml.controllers.corporate_action_controller import CorporateActionController

    ctrl = CorporateActionController(container=None)
    ctrl._candidate_objects = {1: SimpleNamespace(source_url="file:///C:/evil.bat"),
                               2: SimpleNamespace(source_url="https://www.kap.org.tr/tr/Bildirim/2")}
    ctrl.openCandidateSource(1)
    ctrl.openCandidateSource(2)
    assert opened == ["https://www.kap.org.tr/tr/Bildirim/2"]


def test_escaped_tags_in_feed_text_do_not_become_markup():
    text = clean_text('Haber &lt;img src="http://evil/x.png"&gt; &amp;lt;b&amp;gt;kalın&amp;lt;/b&amp;gt; &amp; sonu')
    assert "<" not in text and ">" not in text
    assert text.startswith("Haber") and "kalın" in text and text.endswith("& sonu")


def test_kap_subject_and_summary_are_cleaned():
    item = _to_news_item({
        "publishDate": "01.11.2026 09:30:00", "stockCodes": "THYAO", "disclosureIndex": 1,
        "subject": "<b>Özel</b> Durum", "summary": "&lt;img src=x&gt;özet",
    }, {"THYAO"})
    assert item.title == "Özel Durum" and item.summary == "özet"


def test_js_literal_escapes_quotes_and_script_end():
    literal = js_literal("Ali'nin </script><script>alert(1)</script>")
    assert json.loads(literal.replace("<\\/", "</")) =="Ali'nin </script><script>alert(1)</script>"
    assert "</script>" not in literal


def test_periodic_chart_survives_apostrophe_in_series_name():
    import pandas as pd

    frame = pd.DataFrame({"Ali'nin Portföyü": [1.5, -2.0]}, index=pd.to_datetime(["2026-01-31", "2026-02-28"]))
    html = build_periodic_html(frame)
    assert 'label: "Ali\'nin Portföyü"' in html


def test_treemap_escapes_labels_before_inner_html():
    html = build_treemap_html([{"label": "<img src=x onerror=alert(1)>", "ret": 1, "weight": 1, "value": 1,
                                "vol": 0, "marketValue": 0, "costValue": 0, "code": "x"}], True, "</script>")
    assert "</script>\"" not in html and "esc(r.item.label)" in html and "esc(portfolioName)" in html
