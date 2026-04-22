from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame
from PyQt5.QtCore import Qt
from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole

class MessageBubble(QWidget):
    """Sohbetteki tek bir mesaj balonu (User, AI veya System)"""
    def __init__(self, message: ChatMessage):
        super().__init__()
        self.message = message
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        self.bubble = QFrame()
        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(15, 12, 15, 12)
        bubble_layout.setSpacing(5)

        lbl_content = QLabel(self.message.content)
        lbl_content.setWordWrap(True)
        lbl_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        
        time_str = self.message.timestamp.strftime("%H:%M")
        lbl_time = QLabel(time_str)
        lbl_time.setAlignment(Qt.AlignRight)

        # Mesaj tipine göre stil
        if self.message.role == MessageRole.USER:
            self.bubble.setProperty("cssClass", "chatBubble")
            self.bubble.setProperty("cssState", "user")
            lbl_content.setProperty("cssClass", "chatContent")
            lbl_content.setProperty("cssState", "user")
            lbl_time.setProperty("cssClass", "chatTime")
            lbl_time.setProperty("cssState", "user")
            main_layout.addStretch()
            main_layout.addWidget(self.bubble)

        elif self.message.role == MessageRole.AI:
            self.bubble.setProperty("cssClass", "chatBubble")
            self.bubble.setProperty("cssState", "ai")
            lbl_content.setProperty("cssClass", "chatContent")
            lbl_content.setProperty("cssState", "ai")
            lbl_time.setProperty("cssClass", "chatTime")
            lbl_time.setProperty("cssState", "ai")
            main_layout.addWidget(self.bubble)
            main_layout.addStretch()

        elif self.message.role == MessageRole.SYSTEM:
            self.bubble.setProperty("cssClass", "chatBubble")
            self.bubble.setProperty("cssState", "system")
            lbl_header = QLabel("🤖 Otomatik Aktarım")
            lbl_header.setProperty("cssClass", "systemChatHeader")
            bubble_layout.addWidget(lbl_header)
            
            lbl_content.setProperty("cssClass", "chatContent")
            lbl_content.setProperty("cssState", "system")
            lbl_time.setProperty("cssClass", "chatTime")
            lbl_time.setProperty("cssState", "system")
            main_layout.addWidget(self.bubble)

        bubble_layout.addWidget(lbl_content)
        bubble_layout.addWidget(lbl_time)
