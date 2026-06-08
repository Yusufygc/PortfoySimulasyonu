import pytest
import json
import re
import sys
from datetime import datetime

pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication, QLabel, QTextBrowser
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

from src.ui.pages.ai_page.right_panel.chat_input_bar import (
    CHAT_INPUT_TOOLTIP,
    CHAT_PLACEHOLDER,
    ChatInputBar,
)
from src.ui.pages.ai_page.right_panel.chatbot_panel import ChatbotPanel
from src.ui.pages.ai_page.right_panel.message_bubble import MessageBubble, normalize_ai_markdown
from src.ui.pages.ai_page.right_panel.chat_session_manager import ChatSessionManager
from src.application.services.ai.ai_chat_service import SYSTEM_PROMPT
from src.domain.models.ai_analysis import ChatMessage, ChatSession, MessageRole, AnalysisResult, ModelOutlook, XaiFactorItem
from src.infrastructure.ai.ai_core_fastapi_client import _parse_api_response
from src.infrastructure.ai.qsettings_chat_history_repo import (
    QSettingsChatHistoryRepository,
    LAST_ACTIVE_SESSION_KEY,
    SESSIONS_KEY,
)
from src.ui.pages.ai_page.ai_page import AIPage

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class MemorySettings:
    def __init__(self, values=None):
        self.values = dict(values or {})
        self.synced = False

    def value(self, key, default=None, type=None):
        value = self.values.get(key, default)
        if type is not None and value is not None:
            try:
                return type(value)
            except (TypeError, ValueError):
                return default
        return value

    def setValue(self, key, value):
        self.values[key] = value

    def remove(self, key):
        self.values.pop(key, None)

    def sync(self):
        self.synced = True


def make_history_store(values=None):
    return ChatSessionManager(QSettingsChatHistoryRepository(MemorySettings(values)))


def test_chat_input_bar():
    """ChatInputBar arayüzünün doğru çalıştığını test et."""
    bar = ChatInputBar()

    assert bar.text_edit.toPlainText() == ""
    assert bar.btn_send.isEnabled() is True
    assert bar.btn_send.text() == "Gönder"
    assert bar.btn_send.width() == 104
    assert bar.btn_send.property("cssClass") == "aiSendBtn"
    assert bar.text_edit.height() == 72
    assert bar.text_edit.property("cssClass") == "aiChatInput"
    assert bar.text_edit.placeholderText() == CHAT_PLACEHOLDER
    assert bar.text_edit.toolTip() == CHAT_INPUT_TOOLTIP

    bar.set_loading(True)
    assert bar.btn_send.isEnabled() is False
    assert bar.text_edit.isEnabled() is False

    bar.set_loading(False)
    assert bar.text_edit.placeholderText() == CHAT_PLACEHOLDER
    assert bar.text_edit.toolTip() == CHAT_INPUT_TOOLTIP


def test_chat_input_bar_shift_enter_sends_from_text_edit_focus():
    """Shift+Enter odak metin alanındayken mesajı gönderir."""
    bar = ChatInputBar()
    sent_messages = []
    bar.send_requested.connect(sent_messages.append)

    bar.text_edit.setPlainText("Bilanço risklerini açıkla")
    bar.text_edit.setFocus()
    QTest.keyClick(bar.text_edit, Qt.Key_Return, Qt.ShiftModifier)

    assert sent_messages == ["Bilanço risklerini açıkla"]
    assert bar.text_edit.toPlainText() == ""


def test_chat_input_bar_plain_enter_keeps_text_edit_behavior():
    """Normal Enter mesaj göndermez; QTextEdit satır sonu davranışı korunur."""
    bar = ChatInputBar()
    sent_messages = []
    bar.send_requested.connect(sent_messages.append)

    bar.text_edit.setPlainText("İlk satır")
    bar.text_edit.setFocus()
    QTest.keyClick(bar.text_edit, Qt.Key_Return)

    assert sent_messages == []
    assert "\n" in bar.text_edit.toPlainText()


def test_chat_history_store_handles_empty_invalid_and_valid_json():
    invalid_store = make_history_store({SESSIONS_KEY: "{bad json"})
    assert invalid_store.load_sessions() == []

    session = ChatSession(
        id="s1",
        title="Bilanço",
        messages=[ChatMessage(MessageRole.USER, "Bilanço nedir?", timestamp=datetime(2026, 6, 4, 12, 0))],
        created_at=datetime(2026, 6, 4, 12, 0),
        updated_at=datetime(2026, 6, 4, 12, 1),
    )
    settings = MemorySettings()
    store = QSettingsChatHistoryRepository(settings)
    store.save_sessions([session])
    store.set_last_active_session_id("s1")

    loaded = store.load_sessions()

    assert len(loaded) == 1
    assert loaded[0].id == "s1"
    assert loaded[0].messages[0].content == "Bilanço nedir?"
    assert settings.values[LAST_ACTIVE_SESSION_KEY] == "s1"
    assert settings.synced is True


def test_chatbot_creates_session_from_first_user_message_and_persists():
    store = make_history_store()
    panel = ChatbotPanel(history_store=store)
    panel._trigger_ai = lambda: None

    panel.send_user_message("Bilançoda kritik başlıklar nedir?")

    assert len(panel.sessions) == 1
    assert panel.active_session_id == panel.sessions[0].id
    assert panel.sessions[0].title == "Bilançoda kritik başlıklar nedir?"
    assert [msg.role for msg in panel.sessions[0].messages] == [MessageRole.AI, MessageRole.USER]

    saved = json.loads(store.repo._settings.values[SESSIONS_KEY])
    assert saved[0]["title"] == "Bilançoda kritik başlıklar nedir?"
    assert saved[0]["messages"][-1]["content"] == "Bilançoda kritik başlıklar nedir?"


def test_chatbot_loads_deletes_and_starts_sessions_without_layout_shrink():
    store = make_history_store()
    first = store.create_session(
        title="İlk sohbet",
        messages=[ChatMessage(MessageRole.USER, "İlk soru")],
    )
    second = store.create_session(
        title="İkinci sohbet",
        messages=[ChatMessage(MessageRole.USER, "İkinci soru")],
    )
    store.save_sessions([first, second])
    store.set_last_active_session_id(first.id)

    panel = ChatbotPanel(history_store=store)

    assert panel.active_session_id is None
    assert panel.messages[0].role == MessageRole.AI

    panel.load_session(first.id)
    assert panel.active_session_id == first.id
    assert panel.messages[0].content == "İlk soru"

    panel.load_session(second.id)
    assert panel.active_session_id == second.id
    assert panel.messages[0].content == "İkinci soru"

    layout_count = panel.layout().count()
    panel.resize(500, 600)
    assert panel.history_sidebar.isHidden() is True
    panel.toggle_history_sidebar()

    assert panel.history_sidebar.isHidden() is False
    assert panel.layout().count() == layout_count
    assert panel.history_sidebar.parent() is panel
    assert panel.history_sidebar.geometry().width() <= 320

    panel.delete_session(second.id)
    assert panel.active_session_id is None
    assert panel.messages[0].role == MessageRole.AI
    assert all(session.id != second.id for session in panel.sessions)


def test_chatbot_session_switch_marks_pending_worker_stale():
    store = make_history_store()
    session = store.create_session(title="Kayıtlı", messages=[ChatMessage(MessageRole.USER, "Eski soru")])
    store.save_sessions([session])

    panel = ChatbotPanel(history_store=store)
    panel._request_seq = 10
    panel.input_bar.set_loading(True)

    panel.load_session(session.id)
    panel._on_ai_response(10, "stale response")

    assert panel._request_seq == 11
    assert panel.input_bar.btn_send.isEnabled() is True
    assert all(message.content != "stale response" for message in panel.messages)


def test_message_bubble():
    """MessageBubble bilesenini test et."""
    msg = ChatMessage(role=MessageRole.USER, content="Test Mesaj?")
    bubble = MessageBubble(msg)

    assert bubble.message.content == "Test Mesaj?"
    assert bubble.message.role == MessageRole.USER
    assert bubble.bubble.property("cssClass") == "chatBubble"
    assert bubble.bubble.property("cssState") == "user"


def test_ai_message_renders_markdown_without_bubble_frame():
    """AI cevabi kutusuz Markdown renderer ile gosterilir."""
    msg = ChatMessage(role=MessageRole.AI, content="**Nasdaq** ?nemli bir endekstir.")
    bubble = MessageBubble(msg)

    assert bubble.bubble is None
    assert bubble.markdown_content is not None
    assert isinstance(bubble.markdown_content, QTextBrowser)
    assert bubble.markdown_content.toPlainText() == "Nasdaq ?nemli bir endekstir."
    assert "**Nasdaq**" not in bubble.markdown_content.toPlainText()
    assert bubble._message_container.property("cssClass") == "aiChatAnswer"
    assert bubble._message_container.property("centered") is True
    assert bubble._width_ratio == 0.94
    assert bubble._fill_available_width is True
    assert "margin-bottom" in bubble.markdown_content.document().defaultStyleSheet()
    assert "font-weight: 700" in bubble.markdown_content.document().defaultStyleSheet()


def test_ai_markdown_normalizes_plain_headings_and_spacing():
    """Kisa duz baslik satirlari kalin Markdown basliga donusur."""
    text = "Gann Filtresi Nedir?\nGann filtresi fiyat dalgalanmalarini sadeleştirir."

    normalized = normalize_ai_markdown(text)

    assert normalized.startswith("**Gann Filtresi Nedir?**\n\n")
    assert "\n\nGann filtresi" in normalized


def test_ai_markdown_does_not_double_bold_or_rewrite_lists():
    """Mevcut Markdown, liste maddeleri ve uzun paragraflar korunur."""
    long_paragraph = (
        "Bu satir baslik degil cunku cok uzun bir aciklama olarak finansal "
        "baglami detayli sekilde anlatmaya devam eder"
    )
    text = "\n".join(
        [
            "**Nasdaq**",
            "- Trend Yonu: fiyat filtrenin uzerindeyse yukselis sinyali olusur.",
            "1. Riskleri not et.",
            long_paragraph,
        ]
    )

    normalized = normalize_ai_markdown(text)

    assert "****Nasdaq****" not in normalized
    assert "**Nasdaq**\n\n" in normalized
    assert "- Trend Yonu" in normalized
    assert "**- Trend Yonu" not in normalized
    assert "1. Riskleri not et." in normalized
    assert f"**{long_paragraph}**" not in normalized


def test_message_bubble_uses_display_content_for_visual_text():
    """Sistem mesaji raw prompt'u saklar ama ekranda kisa ozeti gosterir."""
    msg = ChatMessage(
        role=MessageRole.SYSTEM,
        content="[RAW API PAYLOAD]",
        display_content="GARAN analizi chat'e g?nderildi.",
    )
    bubble = MessageBubble(msg)

    assert bubble.message.content == "[RAW API PAYLOAD]"
    assert bubble.lbl_content.text() == "GARAN analizi chat'e g?nderildi."
    assert bubble.bubble.property("cssClass") == "chatBubble"
    assert bubble.bubble.property("cssState") == "system"
    assert any(label.property("cssClass") == "systemChatHeader" for label in bubble.findChildren(QLabel))


def test_panel_integration(monkeypatch):
    """Paneller arası analiz aktarımını test et."""
    monkeypatch.setattr(
        "src.ui.pages.ai_page.ai_page.QSettingsChatHistoryRepository",
        lambda: QSettingsChatHistoryRepository(MemorySettings()),
    )
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
    assert "API Payload" not in last_msg.content
    assert "AI_Core" not in last_msg.content
    assert last_msg.display_content is not None
    assert "GARAN analizi chat'e gönderildi" in last_msg.display_content
    assert "RSI momentum" in last_msg.content
    assert "grup: technical" in last_msg.content
    assert "Ana XAI faktörü: RSI 14" in last_msg.display_content
    assert "Yön beklentisi: Yükseliş Eğilimi" in last_msg.display_content
    assert "Yön Beklentisi: Yükseliş Eğilimi" in last_msg.content
    assert "Sinyal:" not in last_msg.display_content
    assert "Sinyal:" not in last_msg.content
    assert not re.search(r"\b(AL|SAT|TUT)\b", last_msg.display_content)
    assert not re.search(r"\b(AL|SAT|TUT)\b", last_msg.content)
    assert "Gündelik Özet" in last_msg.content
    assert "### başlık" in last_msg.content
    assert "**Başlık**" in last_msg.content
    assert "Yeni paragrafa" in last_msg.content
    assert "düz metin" not in last_msg.content


def test_gemini_prompt_requires_markdown_daily_summary():
    """Gemini sistem prompt'u Markdown başlık ve gündelik özet formatını zorlar."""
    assert "Gündelik Özet" in SYSTEM_PROMPT
    assert "###" in SYSTEM_PROMPT
    assert "**Başlık**" in SYSTEM_PROMPT
    assert "Yeni paragrafa" in SYSTEM_PROMPT
    assert "tablo kullanma" in SYSTEM_PROMPT
    assert "düz metin" not in SYSTEM_PROMPT
    assert "AI_Core" not in SYSTEM_PROMPT
    assert "gereksiz yere BIST'e bağlamazsın" in SYSTEM_PROMPT


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
