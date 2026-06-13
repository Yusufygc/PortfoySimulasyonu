from src.ui.shared.locale_tr import L10N
from datetime import datetime

from src.qt_compat.qtcore import QThreadPool, QPropertyAnimation, QParallelAnimationGroup, QEasingCurve, QRect
from src.qt_compat.qtwidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout

from src.application.services.ai.ai_chat_service import AiChatService
from src.application.services.ai.safety_guard import validate_user_input
from src.domain.models.ai_analysis import ChatMessage, ChatSession, MessageRole, AnalysisResult
from src.infrastructure.ai.gemini_chat_provider import GeminiChatProvider
from src.infrastructure.ai.qsettings_chat_history_repo import QSettingsChatHistoryRepository
from src.ui.core.icon_manager import IconManager
from src.ui.pages.ai_page.labels import outlook_label
from src.ui.widgets.shared.controls.animated_button import AnimatedButton
from src.ui.formatters import display_ticker
from src.ui.worker import Worker
from .chat_session_manager import ChatSessionManager
from .conversation_view import ConversationView
from .chat_input_bar import ChatInputBar
from .chat_history_sidebar import ChatHistorySidebar


class ChatbotPanel(QWidget):
    """Sağ Panel (Chatbot Paneli) Ana Kapsayıcısı."""

    def __init__(self, history_store: ChatSessionManager | None = None, chat_service: AiChatService | None = None):
        super().__init__()
        self.history_store = history_store or ChatSessionManager(QSettingsChatHistoryRepository())
        self._chat_service = chat_service or AiChatService(GeminiChatProvider(api_key=None))
        self.sessions: list[ChatSession] = self.history_store.load_sessions()
        self.active_session_id = None
        self.messages: list[ChatMessage] = []
        self._threadpool = QThreadPool.globalInstance()
        self._request_seq = 0
        self.worker = None
        self._init_ui()
        self._load_initial_session()
        self._position_history_sidebar()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        
        # Add spacing to avoid overlap with the toggle sidebar button (which sits at x=20, y=14)
        header_layout.addSpacing(44)
        
        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconManager.get_icon("bot", color="@COLOR_PRIMARY").pixmap(24, 24))
        
        lbl_title = QLabel(L10N.AI_FINANS_ASISTANI)
        lbl_title.setProperty("cssClass", "dialogHeaderTitleLarge")

        btn_clear = AnimatedButton(L10N.SOHBETI_TEMIZLE)
        btn_clear.setIconName("trash-2", color="@COLOR_DANGER", size=24)
        btn_clear.setProperty("cssClass", "outlineDangerBtn")
        btn_clear.clicked.connect(self.clear_chat)

        self.btn_toggle_sidebar = AnimatedButton("", self)
        self.btn_toggle_sidebar.setIconName("sidebar", color="@COLOR_PRIMARY", size=20)
        self.btn_toggle_sidebar.setProperty("cssClass", "aiHistoryIconButton")
        self.btn_toggle_sidebar.clicked.connect(self.toggle_history_sidebar)

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

        self.history_sidebar = ChatHistorySidebar(self)
        self.history_sidebar.session_selected.connect(self.load_session)
        self.history_sidebar.session_deleted.connect(self.delete_session)
        self.history_sidebar.new_session_requested.connect(self.start_new_session)
        self.history_sidebar.close_requested.connect(self.history_sidebar.hide)

    def _load_initial_session(self) -> None:
        if self.active_session_id:
            session = self._session_by_id(self.active_session_id)
            if session is not None:
                self._set_messages(session.messages)
                self.history_store.set_last_active_session_id(session.id)
                self._refresh_history_sidebar()
                return
        self.active_session_id = None
        self._set_messages(self.history_store.default_messages())
        self.history_store.set_last_active_session_id(None)
        self._refresh_history_sidebar()

    def add_message(self, msg: ChatMessage, persist: bool = True):
        self.messages.append(msg)
        self.conversation_view.add_message(msg)
        if persist:
            self._persist_active_session()

    def clear_chat(self):
        self._cancel_pending_ai()
        self._set_messages([ChatMessage(MessageRole.AI, L10N.SOHBET_GECMISI_TEMIZLENDI_SIZE_NASIL)])
        self._persist_active_session()

    def send_user_message(self, text: str):
        self._ensure_active_session(text)
        is_safe, error_msg = validate_user_input(text)
        if not is_safe:
            user_msg = ChatMessage(MessageRole.USER, text)
            self.add_message(user_msg)
            
            system_msg = ChatMessage(MessageRole.SYSTEM, error_msg)
            self.add_message(system_msg)
            return

        msg = ChatMessage(MessageRole.USER, text)
        self.add_message(msg)
        self._trigger_ai()

    def receive_system_message(self, result: AnalysisResult):
        """Sol panelden gelen analiz sonucunu yapılandırılmış prompt olarak Gemini'ye gönderir."""
        self._ensure_active_session(f"{display_ticker(result.ticker)} analizi")
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
        return f"""[OTOMATİK ANALİZ AKTARIMI - Analiz Özeti]

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
Yön Beklentisi: {outlook_label(result.outlook)}
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
7. ### başlık, tablo ve uzun yıldızlı liste kullanma; başlıkları **Başlık** biçiminde kalın Markdown satırı olarak yaz.
8. Yeni paragrafa geçerken bir boş satır bırak.
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
        horizon = f"{result.horizon_days} günlük" if result.horizon_days else L10N.HORIZON_SONU_1
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
            f"Model: {result.model_name or '-'} · Yön beklentisi: {outlook_label(result.outlook)} · "
            f"{horizon} bileşik getiri: {return_text}\n"
            f"Güven: {result.confidence_label or '-'} · XAI: {xai_state}"
            f"{xai_detail}"
        )

    def _trigger_ai(self):
        self._request_seq += 1
        request_id = self._request_seq
        self.input_bar.set_loading(True)
        self.worker = Worker(self._chat_service.generate, list(self.messages))
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

    def toggle_history_sidebar(self) -> None:
        if not hasattr(self, "history_sidebar"):
            return
            
        sidebar_width = max(260, min(self.width() - 48, 320))
        sidebar_height = self.height()
        
        # Stop any running animation and disconnect old signals to avoid accumulation
        if hasattr(self, "_anim_group"):
            self._anim_group.stop()
            try:
                self._anim_group.finished.disconnect()
            except TypeError:
                pass
        else:
            self._anim_group = QParallelAnimationGroup(self)
            
        # Re-create/update animations
        self._anim_group.clear()
        
        sidebar_anim = QPropertyAnimation(self.history_sidebar, b"geometry", self)
        sidebar_anim.setDuration(250)
        sidebar_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        button_anim = QPropertyAnimation(self.btn_toggle_sidebar, b"geometry", self)
        button_anim.setDuration(250)
        button_anim.setEasingCurve(QEasingCurve.OutCubic)
        
        self._anim_group.addAnimation(sidebar_anim)
        self._anim_group.addAnimation(button_anim)
        
        # Determine target state based on visibility and position
        is_currently_open = self.history_sidebar.isVisible() and self.history_sidebar.x() == 0
        
        if is_currently_open:
            # Closing anim
            sidebar_anim.setStartValue(QRect(0, 0, sidebar_width, sidebar_height))
            sidebar_anim.setEndValue(QRect(-sidebar_width, 0, sidebar_width, sidebar_height))
            
            button_anim.setStartValue(QRect(sidebar_width - 32 - 14, 14, 32, 32))
            button_anim.setEndValue(QRect(20, 14, 32, 32))
            
            self._anim_group.finished.connect(self._on_close_anim_finished)
            self._anim_group.start()
        else:
            # Opening anim
            self._refresh_history_sidebar()
            self.history_sidebar.show()
            self.history_sidebar.raise_()
            self.btn_toggle_sidebar.raise_()
            
            sidebar_anim.setStartValue(QRect(-sidebar_width, 0, sidebar_width, sidebar_height))
            sidebar_anim.setEndValue(QRect(0, 0, sidebar_width, sidebar_height))
            
            button_anim.setStartValue(QRect(20, 14, 32, 32))
            button_anim.setEndValue(QRect(sidebar_width - 32 - 14, 14, 32, 32))
            
            self._anim_group.start()

    def _on_close_anim_finished(self) -> None:
        self.history_sidebar.hide()
        self._position_history_sidebar()

    def start_new_session(self) -> None:
        self._cancel_pending_ai()
        self.active_session_id = None
        self.history_store.set_last_active_session_id(None)
        self._set_messages(self.history_store.default_messages())
        self._refresh_history_sidebar()

    def load_session(self, session_id: str) -> None:
        session = self._session_by_id(session_id)
        if session is None:
            return
        self._cancel_pending_ai()
        self.active_session_id = session.id
        self.history_store.set_last_active_session_id(session.id)
        self._set_messages(session.messages)
        self._refresh_history_sidebar()
        if self.history_sidebar.isVisible():
            self.toggle_history_sidebar()
        else:
            self._position_history_sidebar()

    def delete_session(self, session_id: str) -> None:
        self.sessions = [session for session in self.sessions if session.id != session_id]
        self.history_store.save_sessions(self.sessions)
        if self.active_session_id == session_id:
            self.start_new_session()
        else:
            self._refresh_history_sidebar()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._position_history_sidebar()

    def _resolve_initial_session_id(self) -> str | None:
        # Her açılışta yeni sohbet otomatik başlasın, eski sohbet açık gelmesin
        return None

    def _ensure_active_session(self, title_seed: str | None = None) -> None:
        if self.active_session_id and self._session_by_id(self.active_session_id) is not None:
            return
        title = self.history_store.title_from_message(title_seed or "")
        session = self.history_store.create_session(messages=self.messages, title=title)
        self.sessions.append(session)
        self.active_session_id = session.id
        self.history_store.set_last_active_session_id(session.id)

    def _persist_active_session(self) -> None:
        if not self.active_session_id:
            return
        session = self._session_by_id(self.active_session_id)
        if session is None:
            return
        session.messages = list(self.messages)
        session.updated_at = datetime.now()
        self.history_store.save_sessions(self.sessions)
        self.history_store.set_last_active_session_id(session.id)
        self._refresh_history_sidebar()

    def _set_messages(self, messages: list[ChatMessage]) -> None:
        self.messages = list(messages)
        self.conversation_view.clear_messages()
        for message in self.messages:
            self.conversation_view.add_message(message)

    def _session_by_id(self, session_id: str | None) -> ChatSession | None:
        if not session_id:
            return None
        for session in self.sessions:
            if session.id == session_id:
                return session
        return None

    def _refresh_history_sidebar(self) -> None:
        if hasattr(self, "history_sidebar"):
            self.history_sidebar.refresh(self.sessions, self.active_session_id)

    def _cancel_pending_ai(self) -> None:
        self._request_seq += 1
        self.input_bar.set_loading(False)

    def _position_history_sidebar(self) -> None:
        if not hasattr(self, "history_sidebar"):
            return
        # If animation is running, do not force geometries to prevent layout flickering
        if hasattr(self, "_anim_group") and self._anim_group.state() == QParallelAnimationGroup.Running:
            return
            
        sidebar_width = max(260, min(self.width() - 48, 320))
        sidebar_height = self.height()
        
        if self.history_sidebar.isVisible():
            self.history_sidebar.setGeometry(0, 0, sidebar_width, sidebar_height)
            if hasattr(self, "btn_toggle_sidebar"):
                self.btn_toggle_sidebar.setGeometry(sidebar_width - 32 - 14, 14, 32, 32)
                self.btn_toggle_sidebar.raise_()
            self.history_sidebar.raise_()
            if hasattr(self, "btn_toggle_sidebar"):
                self.btn_toggle_sidebar.raise_()
        else:
            self.history_sidebar.setGeometry(-sidebar_width, 0, sidebar_width, sidebar_height)
            if hasattr(self, "btn_toggle_sidebar"):
                self.btn_toggle_sidebar.setGeometry(20, 14, 32, 32)
                self.btn_toggle_sidebar.raise_()
