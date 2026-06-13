from src.qt_compat.qtwidgets import QWidget, QHBoxLayout, QSplitter
from src.qt_compat.qtcore import Qt, QThreadPool

from src.application.services.ai.ai_analysis_service import AiAnalysisService
from src.application.services.ai.ai_chat_service import AiChatService
from src.infrastructure.ai.ai_core_fastapi_client import (
    AICoreFastAPIClient,
    FastAPIAnalysisProvider,
)
from src.infrastructure.ai.gemini_chat_provider import GeminiChatProvider
from src.infrastructure.ai.mock_ai_analysis_provider import MockAIAnalysisProvider
from src.infrastructure.ai.qsettings_chat_history_repo import QSettingsChatHistoryRepository
from src.ui.pages.ai_page.right_panel.chat_session_manager import ChatSessionManager
from src.ui.worker import Worker


def _default_analysis_service() -> AiAnalysisService:
    return AiAnalysisService(
        live_provider=FastAPIAnalysisProvider(AICoreFastAPIClient()),
        fallback_provider=MockAIAnalysisProvider(),
    )


def _default_chat_service() -> AiChatService:
    return AiChatService(GeminiChatProvider(api_key=None))


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
        self._analysis_service = (
            getattr(container, "ai_analysis_service", None) or _default_analysis_service()
        )
        self._chat_service = (
            getattr(container, "ai_chat_service", None) or _default_chat_service()
        )
        self._chat_history_repo = (
            getattr(container, "chat_history_repo", None) or QSettingsChatHistoryRepository()
        )
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)

        from src.ui.pages.ai_page.left_panel.model_panel import ModelPanel
        self.left_panel = ModelPanel(self._analysis_service)
        self.left_panel.setMinimumWidth(560)

        from src.ui.pages.ai_page.right_panel.chatbot_panel import ChatbotPanel
        self.right_panel = ChatbotPanel(
            history_store=ChatSessionManager(self._chat_history_repo),
            chat_service=self._chat_service,
        )
        self.right_panel.setMinimumWidth(420)

        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.right_panel)

        # Paneller arası iletişimi (Faz 4) kur
        self.left_panel.send_to_chat_requested.connect(self.right_panel.receive_system_message)
        self.left_panel.connection_dropped.connect(self._on_connection_dropped)

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
        self._connection_worker = Worker(self.left_panel.probe_connection)
        self._connection_worker.signals.result.connect(self._on_ai_connection_result)
        self._connection_worker.signals.error.connect(self._on_ai_connection_error)
        QThreadPool.globalInstance().start(self._connection_worker)

    def _on_ai_connection_result(self, ok):
        self._connection_in_progress = False
        self._is_ai_connected = bool(ok)
        self.left_panel.apply_connection_result(bool(ok))

    def _on_ai_connection_error(self, err):
        self._connection_in_progress = False
        self._is_ai_connected = False
        self.left_panel.apply_connection_result(False)

    def _on_connection_dropped(self):
        """ModelPanel sunucuya erişemeyince emitler; bir sonraki ziyarette re-probe yapılır."""
        self._is_ai_connected = False
