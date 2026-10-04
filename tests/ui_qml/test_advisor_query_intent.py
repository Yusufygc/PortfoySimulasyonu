"""Yerel danışman motoru: sorgu niyeti tespiti (alt dize yerine sözcük eşleşmesi, Türkçe büyük harf)."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.ui_qml.controllers.advisor_query_intent import is_optimization_query, turkish_lower
from src.ui_qml.controllers.ai_advisor_controller import AiAdvisorController


@pytest.mark.parametrize(
    "query",
    [
        "Portföyümü optimize eder misin?",
        "Optimizasyon yap",
        "Hangi hisseyi satmalıyım?",
        "Ne kadar al, ne kadar sat?",
        "REBALANCE önerisi ver",
        "ÖNERİ ver",
        "SATIŞ planı hazırla",
        "OPTIMIZASYON sonucu nedir",
        "Dengeleme yapalım mı?",
    ],
)
def test_optimization_queries_are_detected(query):
    assert is_optimization_query(query)


@pytest.mark.parametrize(
    "query",
    [
        "Portföyümün maliyeti nedir?",
        "Risk analizi yap",
        "Altın hakkında ne düşünüyorsun?",
        "Dağılımı göster",
        "RİSK durumum nasıl?",
        "Satranç oynayalım mı?",
        "Genel durum nedir",
    ],
)
def test_other_queries_are_not_treated_as_optimization(query):
    assert not is_optimization_query(query)


def test_turkish_lower_handles_dotted_and_dotless_i():
    assert turkish_lower("RİSK") == "risk"
    assert turkish_lower("SATIŞ") == "satış"
    assert "RİSK".lower() != "risk"


def _controller_with_advisor():
    ctrl = AiAdvisorController(container=None)
    advisor = MagicMock()
    advisor.call_tool.return_value = {}
    ctrl._get_advisor_service = lambda: advisor
    return ctrl, advisor


def _called_tools(advisor):
    return [call.args[0] for call in advisor.call_tool.call_args_list]


def test_local_analysis_skips_optimization_tool_for_unrelated_question():
    ctrl, advisor = _controller_with_advisor()

    text, _tools = ctrl._generate_local_portfolio_analysis("Portföyümün maliyeti nedir?")

    assert "suggest_optimization" not in _called_tools(advisor)
    assert "Risk Durumu" in text


def test_local_analysis_runs_optimization_tool_for_sell_question():
    ctrl, advisor = _controller_with_advisor()

    text, tools = ctrl._generate_local_portfolio_analysis("Hangi hisseyi satmalıyım?")

    assert "suggest_optimization" in _called_tools(advisor)
    assert "Yeniden Dengeleme" in text
    assert any(tool["name"] == "suggest_optimization" for tool in tools)
