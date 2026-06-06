import sys

import pytest

pytest.importorskip("PyQt5")
from PyQt5.QtWidgets import QApplication

from src.domain.models.ai_analysis import MessageRole
from src.infrastructure.ai.qsettings_chat_history_repo import QSettingsChatHistoryRepository
from src.ui.pages.ai_page.right_panel.chat_session_manager import ChatSessionManager
from src.ui.pages.ai_page.right_panel.chatbot_panel import ChatbotPanel


app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)


class MemorySettings:
    def __init__(self):
        self.values = {}

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
        pass


def make_panel():
    return ChatbotPanel(
        history_store=ChatSessionManager(QSettingsChatHistoryRepository(MemorySettings()))
    )


def test_chatbot_ignores_stale_ai_response():
    panel = make_panel()
    initial_count = len(panel.messages)
    panel._request_seq = 2

    panel._on_ai_response(1, "old response")
    panel._on_ai_response(2, "current response")

    assert len(panel.messages) == initial_count + 1
    assert panel.messages[-1].role == MessageRole.AI
    assert panel.messages[-1].content == "current response"


def test_chatbot_resets_loading_only_for_current_request():
    panel = make_panel()
    panel._request_seq = 2
    panel.input_bar.set_loading(True)

    panel._on_ai_finished(1)
    assert panel.input_bar.btn_send.isEnabled() is False

    panel._on_ai_finished(2)
    assert panel.input_bar.btn_send.isEnabled() is True
