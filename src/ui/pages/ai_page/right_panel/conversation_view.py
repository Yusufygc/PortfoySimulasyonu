from PyQt5.QtWidgets import QScrollArea, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QTimer
from .message_bubble import MessageBubble
from src.ui.pages.ai_page.core.models import ChatMessage

class ConversationView(QScrollArea):
    """Kaydırılabilir sohbet alanı"""
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setWidgetResizable(True)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setProperty("cssClass", "chatScrollArea")

        self.content_widget = QWidget()
        self.content_widget.setObjectName("scroll_content")
        self.layout = QVBoxLayout(self.content_widget)
        self.layout.setAlignment(Qt.AlignTop)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(10)

        self.setWidget(self.content_widget)

    def add_message(self, message: ChatMessage):
        bubble = MessageBubble(message)
        self.layout.addWidget(bubble)
        # Scroll olayının doğru çalışması için layout'un güncellenmesini bekle
        QTimer.singleShot(50, self._scroll_to_bottom)

    def clear_messages(self):
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

    def _scroll_to_bottom(self):
        scrollbar = self.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
