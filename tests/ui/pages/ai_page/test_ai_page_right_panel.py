import pytest
import re
import sys

pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication

from src.ui.pages.ai_page.right_panel.chat_input_bar import ChatInputBar
from src.ui.pages.ai_page.right_panel.message_bubble import MessageBubble
from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole, AnalysisResult, ModelOutlook, XaiFactorItem
from src.ui.pages.ai_page.core.model_interface import _parse_api_response
from src.ui.pages.ai_page.core.gemini_service import SYSTEM_PROMPT
from src.ui.pages.ai_page.ai_page import AIPage

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


def test_chat_input_bar():
    """ChatInputBar arayüzünün doğru çalıştığını test et."""
    bar = ChatInputBar()

    assert bar.text_edit.toPlainText() == ""
    assert bar.btn_send.isEnabled() is True
    assert bar.btn_send.text() == "Gönder"

    bar.set_loading(True)
    assert bar.btn_send.isEnabled() is False
    assert bar.text_edit.isEnabled() is False


def test_message_bubble():
    """MessageBubble bileşenini test et."""
    msg = ChatMessage(role=MessageRole.USER, content="Test Mesajı")
    bubble = MessageBubble(msg)

    assert bubble.message.content == "Test Mesajı"
    assert bubble.message.role == MessageRole.USER


def test_message_bubble_uses_display_content_for_visual_text():
    """Sistem mesajı raw prompt'u saklar ama ekranda kısa özeti gösterir."""
    msg = ChatMessage(
        role=MessageRole.SYSTEM,
        content="[RAW API PAYLOAD]",
        display_content="GARAN analizi chat'e gönderildi.",
    )
    bubble = MessageBubble(msg)

    assert bubble.message.content == "[RAW API PAYLOAD]"
    assert bubble.lbl_content.text() == "GARAN analizi chat'e gönderildi."


def test_panel_integration():
    """Paneller arası analiz aktarımını test et."""
    page = AIPage()

    assert page.left_panel.minimumWidth() == 560
    assert page.right_panel.minimumWidth() == 420
    assert len(page.right_panel.messages) == 1

    result = AnalysisResult(
        ticker="GARAN",
        predicted_price=105.0,
        confidence=0.8,
        outlook=ModelOutlook.UP,
        outlook_strength=0.9,
        xai_features={"RSI": 0.3},
        xai_positive_reasons=[
            XaiFactorItem(
                feature_name="RSI_14",
                human_label="RSI 14",
                importance=0.3,
                direction="positive",
                feature_group="technical",
                reason="RSI momentum tarafındaki güçlenmeyi gösterdi.",
                method="sequence",
                contribution=0.05,
                approximate=True,
            )
        ],
        xai_text="Test",
        model_name="LSTM Lite",
        horizon_days=5,
        weekly_expected_return=0.025,
        disclaimer="Bu çıktı kişisel yatırım tavsiyesi değildir.",
    )

    page.left_panel._on_result_ready(result)
    assert page.left_panel.lbl_disclaimer.isHidden() is False
    assert "yatırım tavsiyesi değildir" in page.left_panel.lbl_disclaimer.text()

    page.right_panel._trigger_ai = lambda: None
    page.left_panel.send_to_chat_requested.emit(result)

    assert len(page.right_panel.messages) == 2
    last_msg = page.right_panel.messages[-1]

    assert last_msg.role == MessageRole.SYSTEM
    assert "OTOMATİK ANALİZ AKTARIMI" in last_msg.content
    assert last_msg.display_content is not None
    assert "GARAN analizi chat'e gönderildi" in last_msg.display_content
    assert "RSI momentum" in last_msg.content
    assert "grup: technical" in last_msg.content
    assert "Ana XAI faktörü: RSI 14" in last_msg.display_content
    assert "Yön beklentisi: Yükseliş eğilimi" in last_msg.display_content
    assert "Yön Beklentisi: Yükseliş eğilimi" in last_msg.content
    assert "Sinyal:" not in last_msg.display_content
    assert "Sinyal:" not in last_msg.content
    assert not re.search(r"\b(AL|SAT|TUT)\b", last_msg.display_content)
    assert not re.search(r"\b(AL|SAT|TUT)\b", last_msg.content)
    assert "Gündelik Özet" in last_msg.content
    assert "### başlık" in last_msg.content


def test_gemini_prompt_requires_plain_daily_summary():
    """Gemini sistem prompt'u okunabilir metin ve gündelik özet formatını zorlar."""
    assert "Gündelik Özet" in SYSTEM_PROMPT
    assert "###" in SYSTEM_PROMPT
    assert "tablo kullanma" in SYSTEM_PROMPT


def test_fastapi_adapter_maps_extended_xai_fields():
    """FastAPI payload'ındaki detaylı XAI alanları UI modeline taşınır."""
    result = _parse_api_response(
        {
            "symbol": "ASELS",
            "analysis_status": "ok",
            "data": {},
            "model": {},
            "forecast": {"points": []},
            "performance": {},
            "confidence": {"label": "medium"},
            "xai": {
                "available": True,
                "method": "Feature Importance",
                "top_positive_reasons": [
                    {
                        "feature_name": "USDTRY_Return",
                        "human_label": "USDTRY kur hareketi",
                        "importance": 0.42,
                        "direction": "positive",
                        "feature_group": "macro",
                        "reason": "Kur tarafındaki hareket modelde yukarı katkı verdi.",
                        "method": "sequence",
                        "contribution": 0.08,
                        "approximate": True,
                    }
                ],
                "top_negative_reasons": [],
            },
        }
    )

    factor = result.xai_positive_reasons[0]
    assert factor.feature_group == "macro"
    assert factor.reason == "Kur tarafındaki hareket modelde yukarı katkı verdi."
    assert factor.method == "sequence"
    assert factor.contribution == 0.08
    assert factor.approximate is True


@pytest.mark.parametrize(
    ("trend_label", "expected"),
    [
        ("up", ModelOutlook.UP),
        ("down", ModelOutlook.DOWN),
        ("flat", ModelOutlook.NEUTRAL),
        ("neutral", ModelOutlook.NEUTRAL),
        (None, ModelOutlook.NEUTRAL),
    ],
)
def test_fastapi_adapter_maps_trend_to_outlook(trend_label, expected):
    """Trend etiketi AL/SAT/TUT yerine kullanıcı-facing yön beklentisine dönüşür."""
    result = _parse_api_response(
        {
            "symbol": "ASELS",
            "analysis_status": "ok",
            "data": {},
            "model": {},
            "forecast": {"trend_label": trend_label, "weekly_expected_return": 0.04, "points": []},
            "performance": {},
            "confidence": {"label": "medium"},
            "xai": {},
        }
    )

    assert result.outlook == expected
    assert result.outlook_strength == 0.4
