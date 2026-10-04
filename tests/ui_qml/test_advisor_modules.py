"""AI Danışman yardımcı modülleri: sağlık skoru, yerel analiz motoru, sohbet yardımcıları."""
from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest

from src.domain.models.ai_analysis import ChatMessage, ChatSession, MessageRole
from src.ui_qml.controllers import advisor_chat_support as chat
from src.ui_qml.controllers import advisor_health as health
from src.ui_qml.controllers import advisor_local_analysis as local


# ----------------------------- sağlık skoru -----------------------------

def test_health_perfect_portfolio_scores_100():
    score, label, factors = health.compute_health(
        {"top_three_weight_pct": 40.0, "volatility_pct": 22.0, "sharpe_ratio": 1.5, "max_drawdown_pct": -15.0}
    )
    assert (score, label) == (100, "Çok Güçlü")
    assert [f["score"] for f in factors] == [25, 25, 25, 25]
    assert all(f["isGood"] for f in factors)
    assert factors[3]["value"] == "-%15.0"


def test_health_worst_portfolio_hits_default_bands():
    score, label, factors = health.compute_health(
        {"top_three_weight_pct": 99.0, "volatility_pct": 60.0, "sharpe_ratio": -0.3, "max_drawdown_pct": -55.0}
    )
    assert (score, label) == (30, "Yüksek Risk")
    assert [f["status"] for f in factors] == [
        "Yüksek Yoğunlaşma Riski", "Aşırı Riskli", "Düşük Getiri Verimi", "Kritik Düşüş Seviyesi"]
    assert not any(f["isGood"] for f in factors)


def test_health_missing_data_uses_moderate_defaults():
    score, label, factors = health.compute_health({})
    assert factors[0]["value"] == "%50.0 (İlk 3)"
    assert factors[2]["value"] == "0.80"
    assert (score, label) == (20 + 20 + 14 + 20, "Dengeli")


@pytest.mark.parametrize("score, label", [(80, "Çok Güçlü"), (79, "Dengeli"), (65, "Dengeli"), (64, "Orta Risk"), (50, "Orta Risk"), (49, "Yüksek Risk")])
def test_health_overall_label_boundaries(score, label):
    assert health._overall_label(score) == label


def test_health_invalid_input_raises_for_caller_to_fallback():
    with pytest.raises(ValueError):
        health.compute_health({"top_three_weight_pct": "abc"})


def test_default_health_is_stable_summary():
    score, label, factors = health.default_health()
    assert (score, label, len(factors)) == (70, "Dengeli", 4)


# ----------------------------- yerel analiz -----------------------------

class _Advisor:
    def __init__(self, data, fail=()):
        self.data, self.fail, self.calls = data, set(fail), []

    def call_tool(self, name, args):
        self.calls.append(name)
        if name in self.fail:
            raise RuntimeError("araç hatası")
        return self.data.get(name, {})


def test_money_and_percent_formats_follow_turkish_conventions():
    assert local.fmt_money_tr(1234567.891) == "1.234.567,89 ₺"
    assert local.fmt_money_tr(None) == "0,00 ₺"
    assert local.fmt_pct_tr(12.345, with_sign=True) == "+%12,35"
    assert local.fmt_pct_tr(-3.2) == "-%3,20"
    assert local.fmt_pct_tr(0.00001) == "%0,00"


def test_general_report_flags_concentration_and_lists_tools():
    advisor = _Advisor({
        "get_portfolio_overview": {"total_value_try": 1000.0, "largest_position_label": "THYAO.IS"},
        "get_allocation_and_risk": {"top_three_weight_pct": 75.0, "sharpe_ratio": 1.4},
    })
    text, tools = local.generate_local_portfolio_analysis(advisor, "portföyüm nasıl")
    assert "Yüksek Yoğunlaşma Riski" in text and "Güçlü Risk-Getiri Dengesi" in text
    assert "**THYAO**" in text and text.rstrip().endswith("**Yatırım Tavsiyesi Değildir (YTD).**")
    assert [t["name"] for t in tools] == ["get_portfolio_overview", "get_allocation_and_risk"]
    assert tools[0]["label"] == "Portföy Genel Özeti"


def test_failed_tool_is_skipped_and_not_reported_as_used():
    advisor = _Advisor({}, fail=("get_allocation_and_risk",))
    text, tools = local.generate_local_portfolio_analysis(advisor, "risk")
    assert [t["name"] for t in tools] == ["get_portfolio_overview"]
    assert "N/A" in text


def test_optimization_report_limits_rows_and_handles_empty_suggestions():
    suggestions = [{"symbol": f"S{i}.IS", "current_weight_pct": 10.0, "optimal_weight_pct": 12.0,
                    "change_pct": 2.0, "action": "AL"} for i in range(9)]
    advisor = _Advisor({"suggest_optimization": {"suggestions": suggestions}})
    text, tools = local.generate_local_portfolio_analysis(advisor, "Hangi hisseyi satmalıyım?")
    assert text.count("| **S") == 6
    assert tools[-1]["name"] == "suggest_optimization"
    empty_text, _ = local.generate_local_portfolio_analysis(_Advisor({}), "rebalance yap")
    assert "optimizasyon matrisi oluşturulamadı" in empty_text


def test_no_advisor_still_returns_report_without_tools():
    text, tools = local.generate_local_portfolio_analysis(None, "risk")
    assert tools == [] and "Portföy Sağlık & Risk Durumu Raporu" in text


# ----------------------------- sohbet yardımcıları -----------------------------

def test_welcome_message_and_quick_prompts():
    welcome = chat.build_welcome_message()
    assert welcome["id"] == "msg-0" and welcome["isWelcome"] is True and welcome["role"] == "ai"
    prompts = chat.default_quick_prompts()
    assert len(prompts) == 4
    prompts[0]["title"] = "değişti"
    assert chat.default_quick_prompts()[0]["title"] == "Portföy Risk Analizi"  # her çağrı yeni liste


def test_messages_to_persist_skips_welcome_system_and_unknown_roles():
    entries = [
        {"role": "ai", "content": "hoş geldin", "isWelcome": True},
        {"role": "system", "content": "sistem"},
        {"role": "bilinmeyen", "content": "x"},
        {"role": "user", "content": "soru"},
        {"role": "ai", "content": "cevap"},
    ]
    persisted = chat.messages_to_persist(entries)
    assert [(m.role.value, m.content) for m in persisted] == [("user", "soru"), ("ai", "cevap")]


def test_session_list_item_defaults_title_and_counts_user_messages():
    session = ChatSession(id="s1", title="", messages=[
        ChatMessage(role=MessageRole.USER, content="a"), ChatMessage(role=MessageRole.USER, content="b")])
    session.updated_at = datetime(2026, 1, 2, 3, 4)
    item = chat.session_list_item(session)
    assert item == {"id": "s1", "title": "Yeni Sohbet", "updatedText": "02.01.2026 03:04", "messageCount": 2}


def test_try_gemini_chat_maps_roles_and_tool_labels():
    seen = {}

    class Service:
        def chat(self, key, prompt, turns):
            seen.update(key=key, turns=turns)
            return SimpleNamespace(text="yanıt", tool_calls=[SimpleNamespace(name="suggest_optimization"), SimpleNamespace(name="zzz")])

    result = chat.try_gemini_chat(Service(), "KEY", [("user", "a"), ("ai", "b")])
    assert seen["turns"] == [("user", "a"), ("model", "b")]
    assert result == {"content": "yanıt", "toolCalls": [
        {"name": "suggest_optimization", "label": "Markowitz Optimizasyonu"}, {"name": "zzz", "label": "zzz"}]}


def test_try_gemini_chat_returns_none_on_failure():
    class Broken:
        def chat(self, *args):
            raise RuntimeError("ağ")

    assert chat.try_gemini_chat(Broken(), "KEY", []) is None
