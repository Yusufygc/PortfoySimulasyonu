from PyQt5.QtWidgets import QWidget, QHBoxLayout, QTextEdit, QPushButton
from PyQt5.QtCore import pyqtSignal, Qt

class ChatInputBar(QWidget):
    """Sohbet mesajı giriş alanı"""
    send_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Mesajınızı yazın... (Göndermek için Shift+Enter)")
        self.text_edit.setFixedHeight(60)
        self.text_edit.setProperty("cssClass", "aiInput")

        self.btn_send = QPushButton("▶\nGönder")
        self.btn_send.setFixedHeight(60)
        self.btn_send.setFixedWidth(70)
        self.btn_send.setProperty("cssClass", "aiPrimaryBtn")
        self.btn_send.clicked.connect(self._on_send)

        layout.addWidget(self.text_edit)
        layout.addWidget(self.btn_send)

    def _on_send(self):
        text = self.text_edit.toPlainText().strip()
        if text:
            self.send_requested.emit(text)
            self.text_edit.clear()

    def keyPressEvent(self, event):
        # Shift+Enter ile gönderim
        if event.key() == Qt.Key_Return and event.modifiers() == Qt.ShiftModifier:
            self._on_send()
        else:
            super().keyPressEvent(event)

    def set_loading(self, is_loading: bool):
        self.btn_send.setEnabled(not is_loading)
        if is_loading:
            self.text_edit.setPlaceholderText("Yanıt bekleniyor...")
            self.text_edit.setEnabled(False)
        else:
            self.text_edit.setPlaceholderText("Mesajınızı yazın... (Göndermek için Shift+Enter)")
            self.text_edit.setEnabled(True)
            self.text_edit.setFocus()
