from PyQt5.QtCore import QThreadPool
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout

from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole, AnalysisResult
from src.ui.pages.ai_page.core.gemini_service import generate_gemini_response
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.shared.controls.animated_button import AnimatedButton
from src.ui.formatters import display_ticker
from src.ui.worker import Worker
from .conversation_view import ConversationView
from .chat_input_bar import ChatInputBar


class ChatbotPanel(QWidget):
    """Sağ Panel (Chatbot Paneli) Ana Kapsayıcısı."""

    def __init__(self):
        super().__init__()
        self.messages: list[ChatMessage] = []
        self._threadpool = QThreadPool.globalInstance()
        self._request_seq = 0
        self.worker = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        
        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconManager.get_icon("bot", color="@COLOR_PRIMARY").pixmap(24, 24))
        
        lbl_title = QLabel("AI Finans Asistanı")
        lbl_title.setProperty("cssClass", "dialogHeaderTitleLarge")

        btn_clear = AnimatedButton("Sohbeti Temizle")
        btn_clear.setIconName("trash-2", color="@COLOR_DANGER", size=24)
        btn_clear.setProperty("cssClass", "outlineDangerBtn")
        btn_clear.clicked.connect(self.clear_chat)

        header_layout.addWidget(lbl_icon)
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        header_layout.addWidget(btn_clear)
        layout.addLayout(header_layout)

        self.conversation_view = ConversationView()
        layout.addWidget(self.conversation_view, 1)

        self.input_bar = ChatInputBar()
        self.input_bar.send_requested.connect(self.send_user_message)
        layout.addWidget(self.input_bar)

        self.add_message(
            ChatMessage(
                MessageRole.AI,
                "Merhaba! Borsa İstanbul ve portföy yönetimi hakkında size nasıl yardımcı olabilirim?",
            )
        )

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
        pos_factors = self._format_positive_factors(result)
        neg_factors = self._format_negative_factors(result)
        features_formatted = self._format_fallback_features(result, pos_factors, neg_factors)

        prompt = self._build_prompt_template(result, pos_factors, neg_factors, features_formatted)

        msg = ChatMessage(
            MessageRole.SYSTEM,
            prompt,
            display_content=self._build_analysis_display_summary(result),
        )
        self.add_message(msg)
        self._trigger_ai()

    def _format_positive_factors(self, result: AnalysisResult) -> str:
        if not result.xai_positive_reasons:
            return ""
        lines = []
        for f in result.xai_positive_reasons:
            lines.append(f"    + {self._format_xai_factor_for_prompt(f)}")
        return "\n".join(lines)

    def _format_negative_factors(self, result: AnalysisResult) -> str:
        if not result.xai_negative_reasons:
            return ""
        lines = []
        for f in result.xai_negative_reasons:
            lines.append(f"    - {self._format_xai_factor_for_prompt(f)}")
        return "\n".join(lines)

    def _format_fallback_features(self, result: AnalysisResult, pos_factors: str, neg_factors: str) -> str:
        if not pos_factors and not neg_factors and result.xai_features:
            return "\n".join([f"    {k}: {v:.2f}" for k, v in result.xai_features.items()])
        return ""

    def _build_prompt_template(
        self,
        result: AnalysisResult,
        pos_factors: str,
        neg_factors: str,
        features_formatted: str,
    ) -> str:
        return f"""[OTOMATİK ANALİZ AKTARIMI — API Payload]

Hisse: {display_ticker(result.ticker)}
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
Yön Beklentisi: {result.outlook.value}
Tahmin Horizonu: {result.horizon_days or '-'} gün
Tahmini Fiyat: ₺{result.predicted_price or '-'}
{f'{result.horizon_days} Günlük' if result.horizon_days else 'Horizon Sonu'} Bileşik Beklenen Getiri: {f'{result.weekly_expected_return*100:.2f}%' if result.weekly_expected_return is not None else '-'}

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
1. Önce 2-3 cümlelik net bir genel yorum ver.
2. Tahmin, güven ve performansı ayrı kısa paragraflarla açıkla.
3. XAI faktörlerini "yukarı destek" ve "aşağı baskı" olarak sadeleştir; teknik/makro/model faktör grubunun neyi temsil ettiğini belirt.
4. En önemli riskleri kısa maddelerle yaz.
5. En sonda mutlaka "Gündelik Özet" başlığı aç ve teknik olmayan 2-3 cümleyle anlat.
6. Cevap rapor gibi uzun olmasın; okunabilir, kullanıcıya dönük ve sade olsun.
7. ### başlık, tablo ve uzun yıldızlı liste kullanma; başlıkları düz metin olarak yaz.
"""
        msg = ChatMessage(
            MessageRole.SYSTEM,
            prompt,
            display_content=self._build_analysis_display_summary(result),
        )
        self.add_message(msg)
        self._trigger_ai()

    @staticmethod
    def _format_xai_factor_for_prompt(f) -> str:
        name = getattr(f, "human_label", "") or getattr(f, "feature_name", "")
        feature = getattr(f, "feature_name", "")
        imp = getattr(f, "importance", 0) or 0
        group = getattr(f, "feature_group", None)
        reason = getattr(f, "reason", None)
        method = getattr(f, "method", None)
        contribution = getattr(f, "contribution", None)
        approximate = getattr(f, "approximate", None)
        parts = [f"{name}"]
        if feature and feature != name:
            parts.append(f"özellik: {feature}")
        if group:
            parts.append(f"grup: {group}")
        parts.append(f"önem: {float(imp):.3f}")
        if contribution is not None:
            parts.append(f"katkı: {float(contribution):+.4f}")
        if method:
            parts.append(f"yöntem: {method}")
        if approximate is True:
            parts.append("yaklaşık")
        text = " (" + ", ".join(parts[1:]) + ")" if len(parts) > 1 else ""
        if reason:
            text += f" — {reason}"
        return f"{parts[0]}{text}"

    @staticmethod
    def _build_analysis_display_summary(result: AnalysisResult) -> str:
        horizon = f"{result.horizon_days} günlük" if result.horizon_days else "Horizon sonu"
        return_text = f"{result.weekly_expected_return * 100:.2f}%" if result.weekly_expected_return is not None else "-"
        xai_state = "mevcut" if result.xai_available else "yok"
        xai_detail = ""
        top_factor = (result.xai_positive_reasons or result.xai_negative_reasons or [None])[0]
        if top_factor is not None:
            factor_name = getattr(top_factor, "human_label", "") or getattr(top_factor, "feature_name", "")
            factor_group = getattr(top_factor, "feature_group", None)
            group_text = f" · XAI ana grup: {factor_group}" if factor_group else ""
            xai_detail = f"\nAna XAI faktörü: {factor_name}{group_text}"
        return (
            f"{display_ticker(result.ticker)} analizi chat'e gönderildi.\n"
            f"Model: {result.model_name or '-'} · Yön beklentisi: {result.outlook.value} · "
            f"{horizon} bileşik getiri: {return_text}\n"
            f"Güven: {result.confidence_label or '-'} · XAI: {xai_state}"
            f"{xai_detail}"
        )

    def _trigger_ai(self):
        self._request_seq += 1
        request_id = self._request_seq
        self.input_bar.set_loading(True)
        self.worker = Worker(generate_gemini_response, list(self.messages))
        self.worker.signals.result.connect(lambda text, rid=request_id: self._on_ai_response(rid, text))
        self.worker.signals.error.connect(lambda err, rid=request_id: self._on_error(rid, err))
        self.worker.signals.finished.connect(lambda rid=request_id: self._on_ai_finished(rid))
        self._threadpool.start(self.worker)

    def _on_ai_response(self, request_id: int, text: str):
        if request_id != self._request_seq:
            return
        msg = ChatMessage(MessageRole.AI, text)
        self.add_message(msg)

    def _on_error(self, request_id: int, err_tuple):
        if request_id != self._request_seq:
            return
        msg = ChatMessage(MessageRole.SYSTEM, f"SİSTEM HATASI: {err_tuple[1]}")
        self.add_message(msg)

    def _on_ai_finished(self, request_id: int):
        if request_id == self._request_seq:
            self.input_bar.set_loading(False)
