from src.ui.shared.locale_tr import L10N
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLineEdit
from PyQt5.QtCore import pyqtSignal
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.shared.controls.animated_button import AnimatedButton

class TickerInputBar(QWidget):
    """Hisse kodu giriş alanı ve analiz butonu"""
    analyze_requested = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(L10N.HISSE_KODU_ORN_THYAO)
        self.input_field.setProperty("cssClass", "aiInput")
        self.input_field.addAction(IconManager.get_icon("search", color="@COLOR_TEXT_SECONDARY"), QLineEdit.LeadingPosition)
        self.input_field.returnPressed.connect(self._on_analyze)
        self.input_field.textChanged.connect(self._on_text_changed)

        self.btn_analyze = AnimatedButton(L10N.ANALIZ_ET)
        self.btn_analyze.setEnabled(False)
        self.btn_analyze.setProperty("cssClass", "aiPrimaryBtn")
        self.btn_analyze.setIconName("zap", color="@COLOR_TEXT_WHITE")
        self.btn_analyze.clicked.connect(self._on_analyze)

        layout.addWidget(self.input_field)
        layout.addWidget(self.btn_analyze)

    def _on_text_changed(self, text):
        # Otomatik büyük harfe çevir
        cursor_pos = self.input_field.cursorPosition()
        upper_text = text.upper()
        if text != upper_text:
            self.input_field.setText(upper_text)
            self.input_field.setCursorPosition(cursor_pos)
            
        self.btn_analyze.setEnabled(bool(upper_text.strip()))

    def _on_analyze(self):
        ticker = self.input_field.text().strip().upper()
        if ticker:
            self.analyze_requested.emit(ticker)
