"""
AiAdvisorController — Gemini AI Karar Destek ve Portföy Danışmanı QML Controller'ı (Faz 10).

Sorumluluklar:
- Gemini 2.5 Flash LLM ile interaktif sohbet ve portföy danışmanlığı yönetimi
- Function Calling araçları (get_portfolio_overview, get_allocation_and_risk, suggest_optimization, get_stock_overview)
- Portföy Sağlık Skoru (0-100) ve XAI Risk Faktörleri analizi
- ThreadPoolExecutor ile UI bloklamayan asenkron sorgulama ve Qt Queued Signal yapısı
- API anahtarı yokluğunda veya ağ kesintisinde yerel analiz motoru fallback'i
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from PySide6.QtCore import Property, QObject, Signal, Slot

from config.settings_loader import persist_api_keys
from src.application.services.ai.ai_advisor_service import AiAdvisorService
from src.application.services.ai.safety_guard import MAX_CHAR_LIMIT, validate_user_input
from src.domain.models.ai_analysis import ChatMessage, ChatSession, MessageRole
from src.ui_qml.controllers.advisor_health import compute_health, default_health
from src.ui_qml.controllers.advisor_chat_support import (
    build_welcome_message,
    default_quick_prompts,
    message_to_dict,
    messages_to_persist,
    session_list_item,
    try_gemini_chat,
)
from src.ui_qml.controllers.advisor_local_analysis import TOOL_LABELS, generate_local_portfolio_analysis

logger = logging.getLogger(__name__)

class AiAdvisorController(QObject):
    """QML AiAdvisorView için veri ve etkileşim köprüsü."""

    # QML Property Sinyalleri
    isLoadingChanged = Signal(bool)
    statusMessageChanged = Signal(str)
    messagesChanged = Signal()
    portfolioHealthScoreChanged = Signal(int)
    healthScoreLabelChanged = Signal(str)
    healthFactorsChanged = Signal()
    quickPromptsChanged = Signal()
    hasApiKeyChanged = Signal(bool)
    modelNameChanged = Signal(str)
    sessionsChanged = Signal()

    # Bildirim Sinyalleri
    messageReceived = Signal(str, str)  # role, content (otomatik kaydırma için)
    aiErrorOccurred = Signal(str)       # Toast bildirimi için

    # İç iş parçacığı sinyalleri (Qt Queued Connection garantisi)
    _asyncResponseReady = Signal(dict)
    _asyncErrorReady = Signal(str)

    def __init__(self, container=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._container = container
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="AiAdvisorWorker")

        # Dahili durumlar
        self._is_loading = False
        self._status_message = "Hazır"
        self._model_name = "Gemini 2.5 Flash"
        self._messages: List[Dict[str, Any]] = []
        self._session: Optional[ChatSession] = None  # etkin sohbet oturumu
        self._sessions: List[Dict[str, Any]] = []

        # Portföy Sağlık Metrikleri
        self._portfolio_health_score = 75
        self._health_score_label = "Dengeli"
        self._health_factors: List[Dict[str, Any]] = []

        # Hızlı Soru Önerileri
        self._quick_prompts: List[Dict[str, Any]] = default_quick_prompts()

        # İç sinyal bağlantıları
        self._asyncResponseReady.connect(self._on_async_response_ready)
        self._asyncErrorReady.connect(self._on_async_error_ready)

        # Son aktif sohbeti yükle (yoksa karşılama mesajıyla yeni sohbet) ve sağlık skorunu hesapla
        self._restore_last_session()
        self.refreshHealthScore()

    # -------------------------------------------------------------------------
    # QML Property'leri
    # -------------------------------------------------------------------------

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property("QVariantList", notify=messagesChanged)
    def messages(self) -> List[Dict[str, Any]]:
        return self._messages

    @Property("QVariantList", notify=sessionsChanged)
    def sessions(self) -> List[Dict[str, Any]]:
        return self._sessions

    @Property(str, notify=sessionsChanged)
    def activeSessionId(self) -> str:
        return self._session.id if self._session else ""

    @Property(bool, constant=True)
    def historyAvailable(self) -> bool:
        return self._get_session_service() is not None

    @Property(int, notify=portfolioHealthScoreChanged)
    def portfolioHealthScore(self) -> int:
        return self._portfolio_health_score

    @Property(str, notify=healthScoreLabelChanged)
    def healthScoreLabel(self) -> str:
        return self._health_score_label

    @Property("QVariantList", notify=healthFactorsChanged)
    def healthFactors(self) -> List[Dict[str, Any]]:
        return self._health_factors

    @Property("QVariantList", notify=quickPromptsChanged)
    def quickPrompts(self) -> List[Dict[str, Any]]:
        return self._quick_prompts

    @Property(bool, notify=hasApiKeyChanged)
    def hasApiKey(self) -> bool:
        key = self._get_api_key()
        return bool(key and len(key.strip()) > 5)

    @Property(str, notify=modelNameChanged)
    def modelName(self) -> str:
        return self._model_name

    # -------------------------------------------------------------------------
    # Yardımcı Servis Erişimleri
    # -------------------------------------------------------------------------

    def _get_api_key(self) -> Optional[str]:
        if not self._container:
            return None
        settings = getattr(self._container, "settings", None)
        if settings and hasattr(settings, "ai"):
            return getattr(settings.ai, "gemini_api_key", None)
        return None

    def _get_session_service(self):
        return getattr(self._container, "chat_session_service", None) if self._container else None

    def _get_advisor_service(self) -> Optional[AiAdvisorService]:
        if not self._container:
            return None
        return getattr(self._container, "ai_advisor_service", None)

    # -------------------------------------------------------------------------
    # Karşılama ve Sıfırlama
    # -------------------------------------------------------------------------

    def _init_welcome_message(self) -> None:
        self._messages = [build_welcome_message()]
        self.messagesChanged.emit()

    # -------------------------------------------------------------------------
    # Sohbet Geçmişi (oturumlar)
    # -------------------------------------------------------------------------

    def _restore_last_session(self) -> None:
        service = self._get_session_service()
        last = None
        if service is not None:
            try:
                last = service.get_last_active_session()
            except Exception as exc:
                logger.warning("Son sohbet yüklenemedi: %s", exc)
        if isinstance(last, ChatSession) and last.messages:
            self._open_session(last)
        else:
            self._start_new_session()
        self._refresh_sessions()

    def _start_new_session(self) -> None:
        service = self._get_session_service()
        self._session = service.create_session() if service is not None else None
        self._init_welcome_message()

    def _open_session(self, session: ChatSession) -> None:
        self._session = session
        self._messages = [message_to_dict(i, m) for i, m in enumerate(session.messages)]
        self.messagesChanged.emit()

    def _persist_session(self) -> None:
        """Kullanıcı mesajı içeren etkin sohbeti kalıcı kaydeder (karşılama mesajı kaydedilmez)."""
        service = self._get_session_service()
        if service is None or self._session is None:
            return
        persisted = messages_to_persist(self._messages)
        self._session.messages = persisted
        try:
            service.save_session(self._session)
        except Exception as exc:
            logger.warning("Sohbet kaydedilemedi: %s", exc)
        self._refresh_sessions()

    def _refresh_sessions(self) -> None:
        service = self._get_session_service()
        items: List[Dict[str, Any]] = []
        if service is not None:
            try:
                for s in service.list_sessions():
                    items.append(session_list_item(s))
            except Exception as exc:
                logger.warning("Sohbet listesi okunamadı: %s", exc)
        self._sessions = items
        self.sessionsChanged.emit()

    @Slot()
    def newChat(self) -> None:
        """Yeni (boş) sohbet başlatır; mevcut sohbet geçmişte kalır."""
        if self._is_loading:
            return
        self._start_new_session()
        self._refresh_sessions()
        self._set_status("Yeni sohbet")

    @Slot(str)
    def selectSession(self, session_id: str) -> None:
        service = self._get_session_service()
        if service is None or self._is_loading or (self._session and self._session.id == session_id):
            return
        session = service.get_session(session_id)
        if session is None:
            return
        service.set_active(session_id)
        self._open_session(session)
        self._refresh_sessions()

    @Slot(str)
    def deleteSession(self, session_id: str) -> None:
        service = self._get_session_service()
        if service is None or self._is_loading:
            return
        service.delete_session(session_id)
        if self._session and self._session.id == session_id:
            self._start_new_session()
        self._refresh_sessions()

    @Slot()
    def clearChat(self) -> None:
        """Eski ad: yeni sohbet başlatır (geçmiş korunur)."""
        if self._session is None or self._get_session_service() is None:
            self._init_welcome_message()
            self._set_status("Sohbet sıfırlandı")
            return
        self.newChat()

    # -------------------------------------------------------------------------
    # Mesaj Gönderme ve Asenkron Çalıştırma
    # -------------------------------------------------------------------------

    @Slot(int)
    def sendQuickPrompt(self, prompt_index: int) -> None:
        """Belirtilen hızlı soru şablonunu gönderir."""
        if 0 <= prompt_index < len(self._quick_prompts):
            text = self._quick_prompts[prompt_index]["prompt"]
            self.sendMessage(text)

    @Property(int, constant=True)
    def maxInputLength(self) -> int:
        """Kullanıcı mesajı için karakter sınırı (güvenlik süzgeciyle aynı değer)."""
        return MAX_CHAR_LIMIT

    @Slot(str, result=bool)
    def submitUserMessage(self, text: str) -> bool:
        """Kullanıcının yazdığı mesajı güvenlik süzgecinden geçirip gönderir.

        Enjeksiyon, kapsam dışı kod talebi veya aşırı uzunluk varsa mesaj gönderilmez, neden toast ile bildirilir
        ve False döner (arayüz yazılan metni silmez). Hızlı soru ve model analizi gibi sistemin ürettiği istemler
        `sendMessage` ile doğrudan gider."""
        is_safe, error_message = validate_user_input(text)
        if not is_safe:
            self.aiErrorOccurred.emit(error_message)
            return False
        if self._is_loading or not (text or "").strip():
            return False
        self.sendMessage(text)
        return True

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        """Güvenilir (sistem üretimi) mesajı gönderir ve asenkron yanıt sürecini başlatır."""
        query = (text or "").strip()
        if not query or self._is_loading:
            return

        now_str = datetime.now().strftime("%H:%M")
        user_msg = {
            "id": f"msg-{len(self._messages) + 1}",
            "role": "user",
            "content": query,
            "timestamp": now_str,
            "toolCalls": [],
        }
        self._messages.append(user_msg)
        self.messagesChanged.emit()
        self.messageReceived.emit("user", query)

        self._set_loading(True)
        self._set_status("Gemini analiz ediyor ve portföy verilerini inceliyor...")

        # Asenkron arka plan görevi
        history_tuples = [(m["role"], m["content"]) for m in self._messages if m["role"] in ("user", "ai")]
        self._executor.submit(self._run_advisor_worker, query, history_tuples)

    def _run_advisor_worker(self, query: str, history: List[Tuple[str, str]]) -> None:
        """Arka planda Gemini API veya yerel simülasyon motorunu çalıştırır."""
        try:
            api_key = self._get_api_key()
            advisor_service = self._get_advisor_service()

            # 1. Gerçek Gemini API + Function Calling Denemesi
            if api_key and advisor_service:
                response = try_gemini_chat(advisor_service, api_key, history)
                if response is not None:
                    self._asyncResponseReady.emit(response)
                    return

            # 2. Yerel Akıllı Analiz Fallback'i (Gerçek Portföy Verileri ile)
            fallback_response, used_tools = self._generate_local_portfolio_analysis(query)
            self._asyncResponseReady.emit({
                "content": fallback_response,
                "toolCalls": used_tools,
            })

        except Exception as e:
            logger.exception("Danışman yanıtı üretilirken beklenmeyen hata: %s", e)
            self._asyncErrorReady.emit(str(e))

    def _tool_name_to_label(self, name: str) -> str:
        return TOOL_LABELS.get(name, name)

    # -------------------------------------------------------------------------
    # Yerel Akıllı Analiz Fallback Motoru (Gerçek Portföy Verilerine Dayanır)
    # -------------------------------------------------------------------------

    def _generate_local_portfolio_analysis(self, query: str) -> Tuple[str, List[Dict[str, str]]]:
        """API anahtarı yokken veya ağ hatasında reel portföy verileriyle zengin karar desteği sunar."""
        return generate_local_portfolio_analysis(self._get_advisor_service(), query)

    # -------------------------------------------------------------------------
    # Yanıt ve Hata Geri Çağrıları (Qt Ana İş Parçacığı)
    # -------------------------------------------------------------------------

    def _on_async_response_ready(self, result: Dict[str, Any]) -> None:
        now_str = datetime.now().strftime("%H:%M")
        ai_msg = {
            "id": f"msg-{len(self._messages) + 1}",
            "role": "ai",
            "content": result.get("content", ""),
            "timestamp": now_str,
            "toolCalls": result.get("toolCalls", []),
        }
        self._messages.append(ai_msg)
        self.messagesChanged.emit()
        self.messageReceived.emit("ai", ai_msg["content"])
        self._set_loading(False)
        self._set_status("Hazır")
        self._persist_session()

    def _on_async_error_ready(self, error_msg: str) -> None:
        now_str = datetime.now().strftime("%H:%M")
        err_entry = {
            "id": f"msg-{len(self._messages) + 1}",
            "role": "system",
            "content": f"Yanıt alınırken bir hata oluştu: {error_msg}",
            "timestamp": now_str,
            "toolCalls": [],
        }
        self._messages.append(err_entry)
        self.messagesChanged.emit()
        self.aiErrorOccurred.emit(error_msg)
        self._set_loading(False)
        self._set_status("Hata oluştu")

    # -------------------------------------------------------------------------
    # Portföy Sağlık Skoru & XAI Risk Faktörleri Hesaplama
    # -------------------------------------------------------------------------

    @Slot()
    def refreshHealthScore(self) -> None:
        """Portföyün gerçek analitik verilerinden 0-100 sağlık skoru ve risk faktörlerini hesaplar."""
        advisor = self._get_advisor_service()
        if not advisor:
            self._set_default_health_metrics()
            return

        try:
            score, label, factors = compute_health(advisor.call_tool("get_allocation_and_risk", {}))
            self._portfolio_health_score, self._health_score_label, self._health_factors = score, label, factors
        except Exception as exc:
            logger.warning("Portföy sağlık skoru hesaplanırken hata: %s", exc)
            self._set_default_health_metrics()

        self.portfolioHealthScoreChanged.emit(self._portfolio_health_score)
        self.healthScoreLabelChanged.emit(self._health_score_label)
        self.healthFactorsChanged.emit()

    def _set_default_health_metrics(self) -> None:
        self._portfolio_health_score, self._health_score_label, self._health_factors = default_health()

    # -------------------------------------------------------------------------
    # API Anahtarı Yönetimi
    # -------------------------------------------------------------------------

    @Slot(str)
    def saveApiKey(self, key: str) -> None:
        """Kullanıcının girdiği API anahtarını kaydeder."""
        clean_key = (key or "").strip()
        if not clean_key or not self._container:
            return
        settings = getattr(self._container, "settings", None)
        if settings and hasattr(settings, "ai"):
            try:
                persist_api_keys(settings, gemini_key=clean_key)
            except Exception as exc:
                logger.exception("Gemini API anahtarı kaydedilemedi: %s", exc)
                self._set_status(f"API anahtarı kaydedilemedi: {exc}")
                return
            self.hasApiKeyChanged.emit(True)
            self._set_status("Gemini API Anahtarı kaydedildi")
            self._messages.append({
                "id": f"msg-{len(self._messages) + 1}",
                "role": "system",
                "content": "Google Gemini API anahtarınız başarıyla tanımlandı. Gemini 2.5 Flash ile tam etkileşimli danışmanlık aktif.",
                "timestamp": datetime.now().strftime("%H:%M"),
                "toolCalls": [],
            })
            self.messagesChanged.emit()

    # -------------------------------------------------------------------------
    # Durum ve Yardımcılar
    # -------------------------------------------------------------------------

    def _set_loading(self, val: bool) -> None:
        if self._is_loading != val:
            self._is_loading = val
            self.isLoadingChanged.emit(val)

    def _set_status(self, msg: str) -> None:
        if self._status_message != msg:
            self._status_message = msg
            self.statusMessageChanged.emit(msg)
