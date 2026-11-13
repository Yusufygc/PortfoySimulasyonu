"""
ToolDeclaration — bir LLM fonksiyon-çağırma (function-calling) API'sine
bildirilecek aracın adı/açıklaması/JSON Schema parametre şeması (bkz. plan §6.2,
e1.2). Handler/callable İÇERMEZ — dispatch application katmanında kalır
(`AiAdvisorService.call_tool()`), bu sınıf sadece infrastructure katmanının
(`GeminiAdvisorChatProvider`) bilmesi gereken METADATA'yı taşır.

Bu ayrım Clean Architecture bağımlılık yönünü korur: infrastructure sadece
domain'e bağımlı olabilir, application'a değil (bkz. CLAUDE.md "UI → Application
→ Infrastructure → Domain"). `AiAdvisorService` (application) zaten var olan
`ToolSpec`'ten (handler dahil) bu hafif görünümü üretip infrastructure'a geçer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass(frozen=True)
class ToolDeclaration:
    name: str
    description: str
    parameters_schema: Dict[str, Any]
