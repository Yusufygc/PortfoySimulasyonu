import sys

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication

from src.ui.pages.ai_page.core.models import MessageRole
from src.ui.pages.ai_page.right_panel.chatbot_panel import ChatbotPanel


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


def test_chatbot_ignores_stale_ai_response():
    panel = ChatbotPanel()
    initial_count = len(panel.messages)
    panel._request_seq = 2

    panel._on_ai_response(1, "old response")
    panel._on_ai_response(2, "current response")

    assert len(panel.messages) == initial_count + 1
    assert panel.messages[-1].role == MessageRole.AI
    assert panel.messages[-1].content == "current response"


def test_chatbot_resets_loading_only_for_current_request():
    panel = ChatbotPanel()
    panel._request_seq = 2
    panel.input_bar.set_loading(True)

    panel._on_ai_finished(1)
    assert panel.input_bar.btn_send.isEnabled() is False

    panel._on_ai_finished(2)
    assert panel.input_bar.btn_send.isEnabled() is True
