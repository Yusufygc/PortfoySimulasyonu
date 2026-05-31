from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSplitter
from PyQt5.QtCore import Qt, QThreadPool

from src.ui.worker import Worker

class AIPage(QWidget):
    """
    AI Analiz Sayfası - Ana Kapsayıcı
    Sayfayı QSplitter ile ikiye böler:
    - Sol Panel (%55): Model Analiz Paneli
    - Sağ Panel (%45): Gemini Chatbot Paneli
    """
    def __init__(self, container=None):
        super().__init__()
        self.container = container
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)
        
        self.splitter = QSplitter(Qt.Horizontal)
        
        from src.ui.pages.ai_page.left_panel.model_panel import ModelPanel
        self.left_panel = ModelPanel()
        self.left_panel.setMinimumWidth(560)
        
        from src.ui.pages.ai_page.right_panel.chatbot_panel import ChatbotPanel
        self.right_panel = ChatbotPanel()
        self.right_panel.setMinimumWidth(420)
        
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        
        # Paneller arası iletişimi (Faz 4) kur
        self.left_panel.send_to_chat_requested.connect(self.right_panel.receive_system_message)
        
        # Genişlik oranları (55 - 45)
        self.splitter.setSizes([580, 420])
        self.splitter.setChildrenCollapsible(False)

        layout.addWidget(self.splitter)

    def on_page_enter(self):
        """main_window tarafından sayfa gösterildiğinde çağrılır."""
        if getattr(self, "_is_ai_connected", False):
            return
        if getattr(self, "_connection_in_progress", False):
            return
        self._connection_in_progress = True
        self.left_panel.set_connection_checking()
        worker = Worker(self.left_panel.probe_connection)
        worker.signals.result.connect(self._on_ai_connection_result)
        worker.signals.error.connect(self._on_ai_connection_error)
        QThreadPool.globalInstance().start(worker)

    def _on_ai_connection_result(self, ok):
        self._connection_in_progress = False
        self._is_ai_connected = bool(ok)
        self.left_panel.apply_connection_result(bool(ok))

    def _on_ai_connection_error(self, err):
        self._connection_in_progress = False
        self._is_ai_connected = False
        self.left_panel.apply_connection_result(False)
