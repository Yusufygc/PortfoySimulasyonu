import pytest
import sys
pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication
from src.ui.pages.ai_page.right_panel.chat_input_bar import ChatInputBar
from src.ui.pages.ai_page.right_panel.message_bubble import MessageBubble
from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole, AnalysisResult, Signal
from src.ui.pages.ai_page.ai_page import AIPage

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

def test_chat_input_bar():
    """ChatInputBar arayüzünün doğru çalıştığını test et."""
    bar = ChatInputBar()
    
    assert bar.text_edit.toPlainText() == ""
    assert bar.btn_send.isEnabled() == True
    
    bar.set_loading(True)
    assert bar.btn_send.isEnabled() == False
    assert bar.text_edit.isEnabled() == False

def test_message_bubble():
    """MessageBubble bileşenini test et."""
    msg = ChatMessage(role=MessageRole.USER, content="Test Mesajı")
    bubble = MessageBubble(msg)
    
    assert bubble.message.content == "Test Mesajı"
    assert bubble.message.role == MessageRole.USER

def test_panel_integration():
    """Faz 4: Paneller arası iletişimi (Sinyal gönderimini) test et."""
    page = AIPage()
    
    # Başlangıçta sağ panelde sadece karşılama mesajı olmalı
    assert len(page.right_panel.messages) == 1
    
    # Sol panelden sahte bir analiz sonucu gönderelim
    result = AnalysisResult(
        ticker="GARAN",
        predicted_price=105.0,
        confidence=0.8,
        signal=Signal.BUY,
        signal_strength=0.9,
        xai_features={"RSI": 0.3},
        xai_text="Test"
    )
    
    # Sol paneldeki butona basılmış gibi sinyali tetikle
    page.left_panel.send_to_chat_requested.emit(result)
    
    # Sağ panele yeni bir sistem mesajı eklenmiş olmalı
    assert len(page.right_panel.messages) == 2
    last_msg = page.right_panel.messages[-1]
    
    assert last_msg.role == MessageRole.SYSTEM
    assert "GARAN hissesi için şu analizi yaptı" in last_msg.content
