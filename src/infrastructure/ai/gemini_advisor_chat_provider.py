"""Gemini function-calling (tool-calling) sohbet sağlayıcısı (bkz. plan §6.2, e1.2).

`GeminiChatProvider`'dan (mevcut, düz sohbet) TAMAMEN AYRI, yeni bir sınıf —
mevcut sınıf hiç değiştirilmedi (bkz. plan §6.2.1/§6.2.2: `ai_page`'e
dokunulmuyor). Aracı gerçek dispatch'i (fonksiyonu çalıştırma) bu sınıfın
DIŞINDA kalır — `call_tool` olarak enjekte edilen bir callable'dır
(`AiAdvisorService.call_tool`, application katmanı) — bu sınıf yalnızca
`ToolDeclaration` (domain, saf metadata) bilir, `ToolSpec`'i (application,
handler içerir) hiç import etmez; Clean Architecture bağımlılık yönünü korur.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Sequence, Tuple

from src.domain.models.ai_tool import ToolDeclaration

_MODEL_NAME = "gemini-3-flash-preview"
_MAX_TOOL_ROUNDS = 4

_SAFETY_CATEGORIES = (
    "HARM_CATEGORY_HATE_SPEECH",
    "HARM_CATEGORY_HARASSMENT",
    "HARM_CATEGORY_SEXUALLY_EXPLICIT",
    "HARM_CATEGORY_DANGEROUS_CONTENT",
)


def _load_gemini_sdk():
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai kütüphanesi eksik. Lütfen 'pip install google-genai' çalıştırın."
        ) from exc
    return genai, types


@dataclass(frozen=True)
class AdvisorToolCall:
    """Bir konuşma turunda çağrılan bir aracın izi — UI'da 'kullanılan araçlar'
    rozetleri için (bkz. plan §6.2.6, e1.3)."""
    name: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AdvisorChatResult:
    """`generate()` dönüş değeri — hem final metni hem de model bu yanıta
    ulaşırken hangi araçları hangi argümanlarla çağırdığını taşır."""
    text: str
    tool_calls: List[AdvisorToolCall] = field(default_factory=list)


class GeminiAdvisorChatProvider:
    """Fonksiyon-çağırma destekli Gemini sohbet sağlayıcısı.

    `call_tool`, isim + argüman dict'i alıp JSON-serileştirilebilir bir dict
    dönen herhangi bir callable olabilir (tipik olarak
    `AiAdvisorService.call_tool`) — bu sınıf onun ne yaptığını bilmez, sadece
    modelin `function_call` isteklerini bu callable'a yönlendirir.
    """

    def __init__(
        self,
        api_key: str | None,
        tool_declarations: Sequence[ToolDeclaration],
        call_tool: Callable[[str, Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        self._api_key = api_key
        self._tool_declarations = list(tool_declarations)
        self._call_tool = call_tool

    def generate(self, system_prompt: str, turns: Sequence[Tuple[str, str]]) -> AdvisorChatResult:
        if not self._api_key:
            raise RuntimeError("Yapay zeka anahtarı bulunamadı. Lütfen GEMINI_API_KEY tanımlayın.")
        if not turns:
            raise RuntimeError("Gemini isteği için mesaj bulunamadı.")

        genai, types = _load_gemini_sdk()
        try:
            client = genai.Client(api_key=self._api_key)

            safety_settings = [
                types.SafetySetting(
                    category=getattr(types.HarmCategory, category),
                    threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
                )
                for category in _SAFETY_CATEGORIES
            ]

            config = types.GenerateContentConfig(
                system_instruction=system_prompt,
                safety_settings=safety_settings,
                tools=self._build_tools(types),
            )

            history = [
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
                for role, text in turns[:-1]
            ]

            chat = client.chats.create(model=_MODEL_NAME, config=config, history=history)
            response = chat.send_message(turns[-1][1])

            tool_calls: List[AdvisorToolCall] = []
            for _ in range(_MAX_TOOL_ROUNDS):
                function_calls = self._extract_function_calls(response)
                if not function_calls:
                    break

                response_parts = []
                for function_call in function_calls:
                    call_arguments = dict(function_call.args) if function_call.args else {}
                    call_result = self._call_tool(function_call.name, call_arguments)
                    tool_calls.append(AdvisorToolCall(name=function_call.name, arguments=call_arguments, result=call_result))
                    response_parts.append(types.Part.from_function_response(name=function_call.name, response=call_result))

                response = chat.send_message(response_parts)

            return AdvisorChatResult(text=response.text, tool_calls=tool_calls)
        except Exception as exc:
            raise RuntimeError(f"Yapay zeka danışman yanıtı alınamadı: {exc}") from exc

    def _build_tools(self, types):
        if not self._tool_declarations:
            return None
        function_declarations = [
            types.FunctionDeclaration(
                name=declaration.name,
                description=declaration.description,
                parameters=declaration.parameters_schema,
            )
            for declaration in self._tool_declarations
        ]
        return [types.Tool(function_declarations=function_declarations)]

    @staticmethod
    def _extract_function_calls(response) -> List[Any]:
        candidates = getattr(response, "candidates", None) or []
        if not candidates:
            return []
        content = getattr(candidates[0], "content", None)
        parts = getattr(content, "parts", None) or []
        return [part.function_call for part in parts if getattr(part, "function_call", None)]
