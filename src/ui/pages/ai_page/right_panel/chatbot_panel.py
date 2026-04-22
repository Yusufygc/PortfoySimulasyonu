from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt
from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole, AnalysisResult
from src.ui.pages.ai_page.core.gemini_service import GeminiWorker
from .conversation_view import ConversationView
from .chat_input_bar import ChatInputBar

class ChatbotPanel(QWidget):
    """Sağ Panel (Chatbot Paneli) Ana Kapsayıcısı"""
    def __init__(self):
        super().__init__()
        self.messages: list[ChatMessage] = []
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 0, 0, 0) # Sol boşluk bırak
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()
        lbl_title = QLabel("💬 AI Finans Asistanı")
        lbl_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #f8fafc;")
        
        btn_clear = QPushButton("🗑 Sohbeti Temizle")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #ef4444;
                border: 1px solid #ef4444;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #ef4444; color: white; }
        """)
        btn_clear.clicked.connect(self.clear_chat)

        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(btn_clear)
        layout.addLayout(header_layout)

        # Conversation View
        self.conversation_view = ConversationView()
        layout.addWidget(self.conversation_view)

        # Input Bar
        self.input_bar = ChatInputBar()
        self.input_bar.send_requested.connect(self.send_user_message)
        layout.addWidget(self.input_bar)

        # Başlangıç mesajı
        self.add_message(ChatMessage(MessageRole.AI, "Merhaba! Borsa İstanbul ve portföy yönetimi hakkında size nasıl yardımcı olabilirim?"))

    def add_message(self, msg: ChatMessage):
        self.messages.append(msg)
        self.conversation_view.add_message(msg)

    def clear_chat(self):
        self.messages.clear()
        self.conversation_view.clear_messages()
        self.add_message(ChatMessage(MessageRole.AI, "Sohbet geçmişi temizlendi. Size nasıl yardımcı olabilirim?"))

    def send_user_message(self, text: str):
        msg = ChatMessage(MessageRole.USER, text)
        self.add_message(msg)
        self._trigger_ai()

    def receive_system_message(self, result: AnalysisResult):
        features_formatted = "\n".join([f"  - {k}: {v:.2f}" for k, v in result.xai_features.items()])
        prompt = f"""[OTOMATİK ANALİZ AKTARIMI]

Modelimiz {result.ticker} hissesi için şu analizi yaptı:
- Sinyal       : {result.signal.value} (Güç: {int(result.signal_strength*100)}%)
- Tahmini Fiyat: ₺{result.predicted_price}
- Model Güveni : {int(result.confidence*100)}%
- Önemli Faktörler:
{features_formatted}

Model Yorumu: {result.xai_text}

Lütfen bu analizi değerlendir:
1. Bu sinyalin güçlü ve zayıf yönleri neler?
2. Bu faktörlerin {result.ticker} için önemi nedir?
3. Yatırımcının dikkat etmesi gereken ek riskler var mı?
"""
        msg = ChatMessage(MessageRole.SYSTEM, prompt)
        self.add_message(msg)
        self._trigger_ai()

    def _trigger_ai(self):
        self.input_bar.set_loading(True)
        self.worker = GeminiWorker(self.messages)
        self.worker.response_ready.connect(self._on_ai_response)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished.connect(lambda: self.input_bar.set_loading(False))
        self.worker.start()

    def _on_ai_response(self, text: str):
        msg = ChatMessage(MessageRole.AI, text)
        self.add_message(msg)

    def _on_error(self, err: str):
        msg = ChatMessage(MessageRole.SYSTEM, f"SİSTEM HATASI: {err}")
        self.add_message(msg)
