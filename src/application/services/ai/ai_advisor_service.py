"""
AiAdvisorService — Gemini tool-calling araç kayıt defteri (bkz. plan §6.2,
e1.1). `advisor_tools.build_tool_specs()`'in ürettiği `ToolSpec` listesini
isme göre erişilebilir kılar ve dispatch (isimle çağırma) sağlar.

SDK'dan (google-genai) TAMAMEN bağımsızdır — `gemini_advisor_chat_provider.py`
(e1.2) bu servisi kullanarak SDK'ya özgü `types.Tool`/`types.FunctionDeclaration`
nesnelerini üretecek ve fonksiyon-çağırma döngüsünde `call_tool()`'u çağıracaktır.
Bu ayrım, mevcut `GeminiChatProvider`/`AiChatService` ikilisiyle aynı "SDK
detayı infrastructure'da kalır" ilkesine uyar (bkz. plan §6.2.2).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.application.services.ai.advisor_tools import ToolSpec, build_tool_specs
from src.domain.models.ai_tool import ToolDeclaration


class AiAdvisorService:
    """Portföy danışmanı araçlarının kayıt defteri + dispatch."""

    def __init__(
        self,
        portfolio_analytics_service,
        risk_optimization_bridge_service,
        stock_360_service,
    ) -> None:
        self._tool_specs: List[ToolSpec] = build_tool_specs(
            portfolio_analytics_service, risk_optimization_bridge_service, stock_360_service,
        )
        self._tools_by_name: Dict[str, ToolSpec] = {spec.name: spec for spec in self._tool_specs}

    @property
    def tool_specs(self) -> List[ToolSpec]:
        """Gemini'ye bildirilecek araç listesi (ad/açıklama/parametre şeması)."""
        return list(self._tool_specs)

    @property
    def tool_declarations(self) -> List[ToolDeclaration]:
        """`tool_specs`'in handler'sız, domain-katmanı görünümü — infrastructure
        katmanına (`GeminiAdvisorChatProvider`) bu geçirilir, `ToolSpec` değil
        (bkz. modül yorumu ve `src/domain/models/ai_tool.py`)."""
        return [
            ToolDeclaration(name=spec.name, description=spec.description, parameters_schema=spec.parameters_schema)
            for spec in self._tool_specs
        ]

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """İsimle bir aracı çağırır. Bilinmeyen araç adı veya araç içi hata —
        exception FIRLATMAZ, `{"error": "..."}" döner ki sohbet döngüsü çökmesin
        (bkz. plan §6.2.4: model 'bu araç yok/hata oluştu' bilgisini görür)."""
        spec = self._tools_by_name.get(name)
        if spec is None:
            available = ", ".join(sorted(self._tools_by_name)) or "(yok)"
            return {"error": f"Bilinmeyen araç: '{name}'. Kullanılabilir araçlar: {available}"}

        try:
            return spec.handler(arguments or {})
        except Exception as exc:
            return {"error": str(exc)}
