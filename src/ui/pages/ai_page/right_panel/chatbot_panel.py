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
        lbl_title.setProperty("cssClass", "dialogHeaderTitleLarge")
        
        btn_clear = QPushButton("🗑 Sohbeti Temizle")
        btn_clear.setProperty("cssClass", "outlineDangerBtn")
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
        """Sol panelden gelen analiz sonucunu yapılandırılmış prompt olarak Gemini'ye gönderir."""

        # ── XAI faktörleri formatla ──────────────────────────────────────
        pos_factors = ""
        if result.xai_positive_reasons:
            lines = []
            for f in result.xai_positive_reasons:
                name = getattr(f, "human_label", "") or getattr(f, "feature_name", "")
                imp = getattr(f, "importance", 0)
                lines.append(f"    + {name} (önem: {imp:.3f})")
            pos_factors = "\n".join(lines)

        neg_factors = ""
        if result.xai_negative_reasons:
            lines = []
            for f in result.xai_negative_reasons:
                name = getattr(f, "human_label", "") or getattr(f, "feature_name", "")
                imp = getattr(f, "importance", 0)
                lines.append(f"    - {name} (önem: {imp:.3f})")
            neg_factors = "\n".join(lines)

        # Eski format fallback
        if not pos_factors and not neg_factors and result.xai_features:
            features_formatted = "\n".join([f"    {k}: {v:.2f}" for k, v in result.xai_features.items()])
        else:
            features_formatted = ""

        # ── Prompt oluştur ───────────────────────────────────────────────
        prompt = f"""[OTOMATİK ANALİZ AKTARIMI — API Payload]

Hisse: {result.ticker}
Analiz Durumu: {result.analysis_status}
Oluşturulma: {result.generated_at}

── VERİ ──
Son Kapanış: ₺{result.last_close or '-'}
Son Gözlem Tarihi: {result.last_observed_date or '-'}
Veri Tazeliği: {result.data_freshness} ({result.staleness_days} gün geride)

── MODEL ──
Model Adı: {result.model_name or '-'}
Model Ailesi: {result.model_family or '-'}
Doğrulama Modu: {result.validation_mode or '-'}
Eğitim Tarihi: {result.trained_at or '-'}

── TAHMİN ──
Trend: {result.trend_label or '-'}
Tahmin Horizonu: {result.horizon_days or '-'} gün
Tahmini Fiyat: ₺{result.predicted_price or '-'}
Haftalık Beklenen Getiri: {f'{result.weekly_expected_return*100:.2f}%' if result.weekly_expected_return else '-'}

── GÜVEN ──
Güven Etiketi: {result.confidence_label}
Güven Nedenleri: {', '.join(result.confidence_reasons) if result.confidence_reasons else '-'}
Güven Uyarıları: {', '.join(result.confidence_warnings) if result.confidence_warnings else '-'}

── PERFORMANS ──
Bileşik Skor: {result.composite_score or '-'}
Yön İsabeti: {f'%{result.directional_accuracy:.1f}' if result.directional_accuracy else '-'}
İsabet Oranı: {f'%{result.hit_rate:.1f}' if result.hit_rate else '-'}
Sharpe: {result.sharpe or '-'}
RMSE: {result.rmse or '-'}
MAE: {result.mae or '-'}

── XAI (Açıklanabilirlik) ──
XAI Mevcut: {'Evet' if result.xai_available else 'Hayır'}
Yöntem: {result.xai_method or '-'}
Fiyatı Yukarı Çeken Faktörler:
{pos_factors or '    (veri yok)'}
Fiyata Aşağı Baskı Yapan Faktörler:
{neg_factors or '    (veri yok)'}
{f'Genel Faktörler: {features_formatted}' if features_formatted else ''}
XAI Uyarısı: {result.xai_caveat or '-'}

── UYARI ──
{result.disclaimer or 'Bu çıktı kişisel yatırım tavsiyesi değildir.'}

Lütfen bu analizi değerlendir:
1. Modelin genel durumu ve güvenilirliği hakkında kısa bir özet ver.
2. Tahmin ve trend hakkında ne söylenebilir?
3. XAI faktörleri ne anlama geliyor?
4. Yatırımcının dikkat etmesi gereken riskler neler?
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
