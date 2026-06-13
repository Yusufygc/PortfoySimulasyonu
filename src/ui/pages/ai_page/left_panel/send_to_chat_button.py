from src.ui.shared.locale_tr import L10N
from src.ui.widgets.shared.controls.animated_button import AnimatedButton
from src.qt_compat.qtcore import Signal
from src.domain.models.ai_analysis import AnalysisResult

class SendToChatButton(AnimatedButton):
    """Analiz sonucunu sağ panele (chat) gönderme butonu"""
    send_requested = Signal(AnalysisResult)

    def __init__(self):
        super().__init__(L10N.DETAYLI_YORUMLAT_CHATBOTA_GONDER)
        self._init_ui()
        self.current_result: AnalysisResult | None = None
        self.clicked.connect(self._on_click)

    def _init_ui(self):
        self.setEnabled(False)
        self.setProperty("cssClass", "aiActionButton")
        self.setIconName("send", color="@COLOR_TEXT_WHITE")

    def set_result(self, result: AnalysisResult):
        self.current_result = result
        self.setEnabled(True)

    def reset(self):
        self.current_result = None
        self.setEnabled(False)

    def _on_click(self):
        if self.current_result:
            self.send_requested.emit(self.current_result)
