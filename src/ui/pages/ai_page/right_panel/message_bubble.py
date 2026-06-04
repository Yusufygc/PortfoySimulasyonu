from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QFrame, QSizePolicy
from PyQt5.QtCore import Qt

from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole


class MessageBubble(QWidget):
    """Sohbetteki tek bir mesaj balonu (User, AI veya System)."""

    def __init__(self, message: ChatMessage):
        super().__init__()
        self.message = message
        self._width_ratio = 0.82
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(4, 4, 4, 4)

        self.bubble = QFrame()
        self.bubble.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Preferred)
        bubble_layout = QVBoxLayout(self.bubble)
        bubble_layout.setContentsMargins(14, 10, 14, 10)
        bubble_layout.setSpacing(6)

        visible_content = self.message.display_content or self.message.content
        self.lbl_content = QLabel(visible_content)
        self.lbl_content.setWordWrap(True)
        self.lbl_content.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_content.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Preferred)

        time_str = self.message.timestamp.strftime("%H:%M")
        lbl_time = QLabel(time_str)
        lbl_time.setAlignment(Qt.AlignRight)

        if self.message.role == MessageRole.USER:
            self._width_ratio = 0.72
            self._apply_role_style("user", lbl_time)
            main_layout.addStretch()
            main_layout.addWidget(self.bubble)

        elif self.message.role == MessageRole.AI:
            self._width_ratio = 0.82
            self._apply_role_style("ai", lbl_time)
            main_layout.addWidget(self.bubble)
            main_layout.addStretch()

        elif self.message.role == MessageRole.SYSTEM:
            self._width_ratio = 0.94
            self._apply_role_style("system", lbl_time)
            
            header_text = "Otomatik Analiz Aktarımı"
            content_lower = self.message.content.lower()
            if self.message.content.startswith("SİSTEM HATASI"):
                header_text = "Sistem Hatası"
            elif self.message.content.startswith("Güvenlik Uyarısı") or "güvenlik uyarısı" in content_lower:
                header_text = "Güvenlik Uyarısı"
                
            lbl_header = QLabel(header_text)
            lbl_header.setProperty("cssClass", "systemChatHeader")
            bubble_layout.addWidget(lbl_header)
            main_layout.addWidget(self.bubble)

        bubble_layout.addWidget(self.lbl_content)
        bubble_layout.addWidget(lbl_time)
        self._apply_max_width()

    def _apply_role_style(self, state: str, lbl_time: QLabel) -> None:
        self.bubble.setProperty("cssClass", "chatBubble")
        self.bubble.setProperty("cssState", state)
        self.lbl_content.setProperty("cssClass", "chatContent")
        self.lbl_content.setProperty("cssState", state)
        lbl_time.setProperty("cssClass", "chatTime")
        lbl_time.setProperty("cssState", state)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._apply_max_width()

    def _apply_max_width(self) -> None:
        available = max(280, self.width() - 16)
        self.bubble.setMaximumWidth(int(available * self._width_ratio))
