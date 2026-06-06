from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import QHBoxLayout, QSizePolicy, QTextEdit, QWidget

from src.application.services.ai.safety_guard import MAX_CHAR_LIMIT
from src.ui.widgets.shared.controls.animated_button import AnimatedButton
from src.ui.shared.locale_tr import L10N


CHAT_PLACEHOLDER = "Mesaj\u0131n\u0131z\u0131 yaz\u0131n... Shift+Enter ile g\u00f6nder"
CHAT_INPUT_TOOLTIP = f"En fazla {MAX_CHAR_LIMIT} karakter"


class ChatTextEdit(QTextEdit):
    send_requested = pyqtSignal()

    def keyPressEvent(self, event):
        is_enter = event.key() in (Qt.Key_Return, Qt.Key_Enter)
        has_shift = bool(event.modifiers() & Qt.ShiftModifier)
        if is_enter and has_shift:
            self.send_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)


class ChatInputBar(QWidget):
    """Sohbet mesaji giris alani."""

    send_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self.text_edit = ChatTextEdit()
        self.text_edit.setPlaceholderText(CHAT_PLACEHOLDER)
        self.text_edit.setToolTip(CHAT_INPUT_TOOLTIP)
        self.text_edit.setFixedHeight(72)
        self.text_edit.setProperty("cssClass", "aiChatInput")
        self.text_edit.textChanged.connect(self._on_text_changed)
        self.text_edit.send_requested.connect(self._on_send)

        self.btn_send = AnimatedButton(L10N.GONDER)
        self.btn_send.setFixedHeight(72)
        self.btn_send.setFixedWidth(104)
        self.btn_send.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.btn_send.setProperty("cssClass", "aiSendBtn")
        self.btn_send.setIconName("send", color="@COLOR_TEXT_WHITE")
        self.btn_send.clicked.connect(self._on_send)

        layout.addWidget(self.text_edit)
        layout.addWidget(self.btn_send)

    def _on_send(self):
        text = self.text_edit.toPlainText().strip()
        if text:
            self.send_requested.emit(text)
            self.text_edit.clear()

    def _on_text_changed(self):
        text = self.text_edit.toPlainText()
        if len(text) > MAX_CHAR_LIMIT:
            self.text_edit.blockSignals(True)
            cursor = self.text_edit.textCursor()
            pos = cursor.position()
            self.text_edit.setPlainText(text[:MAX_CHAR_LIMIT])
            cursor.setPosition(min(pos, MAX_CHAR_LIMIT))
            self.text_edit.setTextCursor(cursor)
            self.text_edit.blockSignals(False)

    def set_loading(self, is_loading: bool):
        self.btn_send.setEnabled(not is_loading)
        if is_loading:
            self.text_edit.setPlaceholderText(L10N.YANIT_BEKLENIYOR)
            self.text_edit.setEnabled(False)
        else:
            self.text_edit.setPlaceholderText(CHAT_PLACEHOLDER)
            self.text_edit.setToolTip(CHAT_INPUT_TOOLTIP)
            self.text_edit.setEnabled(True)
            self.text_edit.setFocus()
