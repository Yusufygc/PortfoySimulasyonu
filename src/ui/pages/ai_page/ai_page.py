from PyQt5.QtWidgets import QWidget, QHBoxLayout, QSplitter, QLabel, QVBoxLayout
from PyQt5.QtCore import Qt

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
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.splitter = QSplitter(Qt.Horizontal)
        
        from src.ui.pages.ai_page.left_panel.model_panel import ModelPanel
        self.left_panel = ModelPanel()
        
        from src.ui.pages.ai_page.right_panel.chatbot_panel import ChatbotPanel
        self.right_panel = ChatbotPanel()
        
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)
        
        # Paneller arası iletişimi (Faz 4) kur
        self.left_panel.send_to_chat_requested.connect(self.right_panel.receive_system_message)
        
        # Genişlik oranları (55 - 45)
        self.splitter.setSizes([550, 450])
        
        layout.addWidget(self.splitter)
