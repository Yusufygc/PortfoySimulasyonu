from __future__ import annotations

from dataclasses import dataclass

from config.settings_loader import AISettings
from src.application.services.ai.ai_advisor_service import AiAdvisorService
from src.application.services.ai.ai_analysis_service import AiAnalysisService
from src.application.services.ai.ai_chat_service import AiChatService
from src.domain.ports.repositories.i_chat_history_repo import IChatHistoryRepository
from src.infrastructure.ai.ai_core_fastapi_client import (
    AICoreFastAPIClient,
    FastAPIAnalysisProvider,
)
from src.infrastructure.ai.gemini_chat_provider import GeminiChatProvider
from src.infrastructure.ai.mock_ai_analysis_provider import MockAIAnalysisProvider
from src.infrastructure.ai.qsettings_chat_history_repo import QSettingsChatHistoryRepository


@dataclass(frozen=True)
class AiSet:
    ai_analysis_service: AiAnalysisService
    ai_chat_service: AiChatService
    chat_history_repo: IChatHistoryRepository
    ai_advisor_service: AiAdvisorService


def build_ai(
    ai_settings: AISettings,
    portfolio_analytics_service,
    risk_optimization_bridge_service,
    stock_360_service,
) -> AiSet:
    live_provider = FastAPIAnalysisProvider(
        AICoreFastAPIClient(base_url=ai_settings.core_api_url)
    )
    return AiSet(
        ai_analysis_service=AiAnalysisService(
            live_provider=live_provider,
            fallback_provider=MockAIAnalysisProvider(),
        ),
        ai_chat_service=AiChatService(GeminiChatProvider(api_key=ai_settings.gemini_api_key)),
        chat_history_repo=QSettingsChatHistoryRepository(),
        # Yeni, ayrı "AI Danışman" özelliği (bkz. plan §6.2, e1.1) — mevcut
        # ai_chat_service/ai_page HİÇ değiştirilmedi, tamamen additive.
        ai_advisor_service=AiAdvisorService(
            portfolio_analytics_service=portfolio_analytics_service,
            risk_optimization_bridge_service=risk_optimization_bridge_service,
            stock_360_service=stock_360_service,
        ),
    )
