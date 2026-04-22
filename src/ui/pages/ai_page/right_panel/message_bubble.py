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
            self.bubble.setStyleSheet("""
                QFrame {
                    background-color: #2A3F5F;
                    border-radius: 12px;
                    border-top-right-radius: 0px;
                }
            """)
            lbl_content.setStyleSheet("color: white; font-size: 14px;")
            lbl_time.setStyleSheet("color: #94a3b8; font-size: 10px;")
            main_layout.addStretch()
            main_layout.addWidget(self.bubble)

        elif self.message.role == MessageRole.AI:
            self.bubble.setStyleSheet("""
                QFrame {
                    background-color: #1E2A3A;
                    border-radius: 12px;
                    border-top-left-radius: 0px;
                    border-left: 3px solid #00C853;
                }
            """)
            lbl_content.setStyleSheet("color: #cbd5e1; font-size: 14px;")
            lbl_time.setStyleSheet("color: #64748b; font-size: 10px;")
            main_layout.addWidget(self.bubble)
            main_layout.addStretch()

        elif self.message.role == MessageRole.SYSTEM:
            self.bubble.setStyleSheet("""
                QFrame {
                    background-color: #2D1F3D;
                    border-radius: 12px;
                    border: 1px solid #a855f7;
                }
            """)
            lbl_header = QLabel("🤖 Otomatik Aktarım")
            lbl_header.setStyleSheet("color: #a855f7; font-weight: bold; font-size: 12px;")
            bubble_layout.addWidget(lbl_header)
            
            lbl_content.setStyleSheet("color: #e2e8f0; font-size: 13px; font-style: italic;")
            lbl_time.setStyleSheet("color: #94a3b8; font-size: 10px;")
            main_layout.addWidget(self.bubble)

        bubble_layout.addWidget(lbl_content)
        bubble_layout.addWidget(lbl_time)
