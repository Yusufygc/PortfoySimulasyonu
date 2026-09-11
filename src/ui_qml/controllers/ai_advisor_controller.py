"""
AiAdvisorController — AiAdvisorView'un veri köprüsü (bkz. plan §6.2, e1.3).

9. QML görünümü, "AI Danışman" — GERÇEK Gemini tool-calling. Mevcut `ai_page`
(mock sol `ModelPanel` + gerçek düz-sohbet sağ `ChatbotPanel`) ile HİÇ ilişkili
değildir, tamamen ayrı bir özellik (bkz. plan §6.2.1 kararı — kullanıcıyla
netleştirildi: mevcut sayfaya dokunulmayacak).

`GeminiAdvisorChatProvider` (e1.2, fonksiyon-çağırma döngüsü) + `AiAdvisorService`
(e1.1, araç kayıt defteri) buraya bağlanır. Diğer QML controller'ların aksine
GERÇEK BİR AĞ ÇAĞRISI (Gemini API) yapıldığından — yerel/CPU-bound hesaplama
değil — mevcut `ChatbotPanel`'in kullandığı aynı `Worker`/`QThreadPool` deseniyle
arka planda çalıştırılır; UI thread'i bloklanmaz (bkz. `src/ui/worker.py`,
Qt-framework-jenerik, QtWidgets'a özgü değil — burada da doğrudan kullanılabilir).
"""
from __future__ import annotations

from typing import Any, List, Optional, Tuple

from src.qt_compat.qtcore import Property, QObject, QThreadPool, Signal, Slot
from src.infrastructure.ai.gemini_advisor_chat_provider import GeminiAdvisorChatProvider
from src.ui.worker import Worker

ROLE_USER = "user"
ROLE_MODEL = "model"

_SYSTEM_PROMPT = (
    "Sen bu uygulamanın Yatırım & Portföy Danışmanısın. Kullanıcının gerçek "
    "portföy verilerine (get_portfolio_overview, get_allocation_and_risk, "
    "suggest_optimization, get_stock_overview) araç çağrısıyla erişebilirsin. "
    "Yanıtların Türkçe, kısa ve rasyonel olsun. ÖNEMLİ: Bu bir yatırım tavsiyesi "
    "değildir, bilgilendirme amaçlıdır — kararları kullanıcı kendi verir. Hiçbir "
    "işlem/emir yürütme yetkin yok, sadece mevcut verileri analiz edip önerebilirsin."
)


class AiAdvisorController(QObject):
    """Gemini tool-calling sohbeti: mesaj listesi + yükleniyor/hata durumu."""

    messagesChanged = Signal()
    isLoadingChanged = Signal()
    errorMessageChanged = Signal()

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        advisor_service = container.ai_advisor_service
        self._provider = GeminiAdvisorChatProvider(
            api_key=container.settings.ai.gemini_api_key,
            tool_declarations=advisor_service.tool_declarations,
            call_tool=advisor_service.call_tool,
        )
        self._threadpool = QThreadPool.globalInstance()
        self._worker: Optional[Worker] = None
        self._request_seq = 0

        self._message_roles: List[str] = []
        self._message_texts: List[str] = []
        self._message_tool_names: List[str] = []  # her mesaj için virgülle ayrılmış araç adları (kullanıcı mesajında "")

        self._is_loading = False
        self._error_message = ""

    # ------------------------------------------------------------------
    # QML'e açılan property'ler
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=messagesChanged)
    def messageRoles(self) -> List[str]:
        return list(self._message_roles)

    @Property("QVariantList", notify=messagesChanged)
    def messageTexts(self) -> List[str]:
        return list(self._message_texts)

    @Property("QVariantList", notify=messagesChanged)
    def messageToolNames(self) -> List[str]:
        return list(self._message_tool_names)

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    # ------------------------------------------------------------------
    # Mesaj gönderme
    # ------------------------------------------------------------------

    @Slot(str)
    def sendMessage(self, text: str) -> None:
        text = (text or "").strip()
        if not text or self._is_loading:
            return

        self._append_message(ROLE_USER, text, [])
        self._set_error("")
        self._set_loading(True)

        self._request_seq += 1
        request_id = self._request_seq
        turns: List[Tuple[str, str]] = list(zip(self._message_roles, self._message_texts))

        self._worker = Worker(self._provider.generate, _SYSTEM_PROMPT, turns)
        self._worker.signals.result.connect(lambda result, rid=request_id: self._on_result(rid, result))
        self._worker.signals.error.connect(lambda err, rid=request_id: self._on_error(rid, err))
        self._threadpool.start(self._worker)

    def _on_result(self, request_id: int, result: Any) -> None:
        if request_id != self._request_seq:
            return
        tool_names = [call.name for call in result.tool_calls]
        self._append_message(ROLE_MODEL, result.text, tool_names)
        self._set_loading(False)

    def _on_error(self, request_id: int, err_tuple: tuple) -> None:
        if request_id != self._request_seq:
            return
        self._set_error(str(err_tuple[1]))
        self._set_loading(False)

    def _append_message(self, role: str, text: str, tool_names: List[str]) -> None:
        self._message_roles.append(role)
        self._message_texts.append(text)
        self._message_tool_names.append(", ".join(tool_names))
        self.messagesChanged.emit()

    def _set_loading(self, value: bool) -> None:
        if value != self._is_loading:
            self._is_loading = value
            self.isLoadingChanged.emit()

    def _set_error(self, message: str) -> None:
        if message != self._error_message:
            self._error_message = message
            self.errorMessageChanged.emit()
