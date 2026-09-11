"""GeminiAdvisorChatProvider — fonksiyon-çağırma döngüsü testleri (bkz. plan
§6.2, e1.2). Gerçek Gemini API'ye HİÇ gidilmez — `google.genai`/`google.genai.types`
sahte (fake) nesnelerle değiştirilir, sadece BU sınıfın döngü mantığı test edilir
(bkz. plan §6.2.5: "gerçek API çağrıları deterministik değildir").
"""
from __future__ import annotations

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from src.domain.models.ai_tool import ToolDeclaration
from src.infrastructure.ai import gemini_advisor_chat_provider as provider_module
from src.infrastructure.ai.gemini_advisor_chat_provider import GeminiAdvisorChatProvider


# ----------------------------------------------------------------------
# Sahte (fake) google-genai SDK nesneleri
# ----------------------------------------------------------------------

class _FakePart:
    def __init__(self, function_call=None, text=None):
        self.function_call = function_call
        self.text = text

    @classmethod
    def from_text(cls, text):
        return cls(text=text)

    @classmethod
    def from_function_response(cls, name, response):
        part = cls()
        part.function_response = {"name": name, "response": response}
        return part


class _FakeFunctionCall:
    def __init__(self, name: str, args: Dict[str, Any]):
        self.name = name
        self.args = args


class _FakeContent:
    def __init__(self, parts):
        self.parts = parts


class _FakeCandidate:
    def __init__(self, parts):
        self.content = _FakeContent(parts)


class _FakeResponse:
    def __init__(self, *, function_calls=None, text=""):
        function_calls = function_calls or []
        parts = [_FakePart(function_call=fc) for fc in function_calls]
        self.candidates = [_FakeCandidate(parts)]
        self.text = text


class _FakeChat:
    def __init__(self, scripted_responses: List[_FakeResponse]):
        self._scripted_responses = list(scripted_responses)
        self.sent_messages: List[Any] = []

    def send_message(self, message):
        self.sent_messages.append(message)
        if not self._scripted_responses:
            raise AssertionError("Scriptlenen yanıt sayısı yetersiz — test hatalı.")
        return self._scripted_responses.pop(0)


class _FakeChats:
    def __init__(self, chat: _FakeChat):
        self._chat = chat
        self.create_calls: List[Dict[str, Any]] = []

    def create(self, model, config, history):
        self.create_calls.append({"model": model, "config": config, "history": history})
        return self._chat


class _FakeClient:
    def __init__(self, chat: _FakeChat):
        self.chats = _FakeChats(chat)


def _make_fake_genai(chat: _FakeChat):
    fake_client_holder = {}

    class _FakeGenaiModule:
        @staticmethod
        def Client(api_key):
            client = _FakeClient(chat)
            fake_client_holder["client"] = client
            fake_client_holder["api_key"] = api_key
            return client

    return _FakeGenaiModule, fake_client_holder


class _FakeTypes:
    """`google.genai.types`'ın bu sınıfın kullandığı yüzeyinin sahte karşılığı."""

    class HarmCategory:
        HARM_CATEGORY_HATE_SPEECH = "HARM_CATEGORY_HATE_SPEECH"
        HARM_CATEGORY_HARASSMENT = "HARM_CATEGORY_HARASSMENT"
        HARM_CATEGORY_SEXUALLY_EXPLICIT = "HARM_CATEGORY_SEXUALLY_EXPLICIT"
        HARM_CATEGORY_DANGEROUS_CONTENT = "HARM_CATEGORY_DANGEROUS_CONTENT"

    class HarmBlockThreshold:
        BLOCK_MEDIUM_AND_ABOVE = "BLOCK_MEDIUM_AND_ABOVE"

    class SafetySetting:
        def __init__(self, category, threshold):
            self.category = category
            self.threshold = threshold

    class GenerateContentConfig:
        def __init__(self, system_instruction, safety_settings, tools=None):
            self.system_instruction = system_instruction
            self.safety_settings = safety_settings
            self.tools = tools

    class Content:
        def __init__(self, role, parts):
            self.role = role
            self.parts = parts

    Part = _FakePart

    class FunctionDeclaration:
        def __init__(self, name, description, parameters):
            self.name = name
            self.description = description
            self.parameters = parameters

    class Tool:
        def __init__(self, function_declarations):
            self.function_declarations = function_declarations


def _patch_sdk(monkeypatch, chat: _FakeChat):
    fake_genai, client_holder = _make_fake_genai(chat)
    monkeypatch.setattr(provider_module, "_load_gemini_sdk", lambda: (fake_genai, _FakeTypes))
    return client_holder


_DECLARATIONS = [
    ToolDeclaration(name="get_portfolio_overview", description="desc", parameters_schema={"type": "object", "properties": {}}),
]


class TestValidation:
    def test_missing_api_key_raises(self, monkeypatch):
        provider = GeminiAdvisorChatProvider(api_key=None, tool_declarations=[], call_tool=MagicMock())
        with pytest.raises(RuntimeError, match="anahtarı bulunamadı"):
            provider.generate("system", [("user", "merhaba")])

    def test_empty_turns_raises(self, monkeypatch):
        provider = GeminiAdvisorChatProvider(api_key="key", tool_declarations=[], call_tool=MagicMock())
        with pytest.raises(RuntimeError, match="mesaj bulunamadı"):
            provider.generate("system", [])


class TestNoToolCallNeeded:
    def test_plain_response_without_function_call_returns_text_directly(self, monkeypatch):
        chat = _FakeChat([_FakeResponse(text="Merhaba, size nasıl yardımcı olabilirim?")])
        client_holder = _patch_sdk(monkeypatch, chat)
        call_tool = MagicMock()

        provider = GeminiAdvisorChatProvider(api_key="test-key", tool_declarations=_DECLARATIONS, call_tool=call_tool)
        result = provider.generate("system prompt", [("user", "merhaba")])

        assert result.text == "Merhaba, size nasıl yardımcı olabilirim?"
        assert result.tool_calls == []
        call_tool.assert_not_called()
        assert client_holder["api_key"] == "test-key"

    def test_history_excludes_last_turn_and_sends_it_as_message(self, monkeypatch):
        chat = _FakeChat([_FakeResponse(text="yanıt")])
        _patch_sdk(monkeypatch, chat)

        provider = GeminiAdvisorChatProvider(api_key="key", tool_declarations=[], call_tool=MagicMock())
        provider.generate("system", [("user", "ilk mesaj"), ("model", "ilk yanıt"), ("user", "son soru")])

        assert chat.sent_messages == ["son soru"]

    def test_no_tool_declarations_means_no_tools_in_config(self, monkeypatch):
        chat = _FakeChat([_FakeResponse(text="yanıt")])
        client_holder = _patch_sdk(monkeypatch, chat)

        provider = GeminiAdvisorChatProvider(api_key="key", tool_declarations=[], call_tool=MagicMock())
        provider.generate("system", [("user", "soru")])

        create_call = client_holder["client"].chats.create_calls[0]
        assert create_call["config"].tools is None

    def test_tool_declarations_are_translated_to_function_declarations(self, monkeypatch):
        chat = _FakeChat([_FakeResponse(text="yanıt")])
        client_holder = _patch_sdk(monkeypatch, chat)

        provider = GeminiAdvisorChatProvider(api_key="key", tool_declarations=_DECLARATIONS, call_tool=MagicMock())
        provider.generate("system", [("user", "soru")])

        create_call = client_holder["client"].chats.create_calls[0]
        tools = create_call["config"].tools
        assert len(tools) == 1
        declarations = tools[0].function_declarations
        assert len(declarations) == 1
        assert declarations[0].name == "get_portfolio_overview"
        assert declarations[0].parameters == {"type": "object", "properties": {}}


class TestSingleToolCallRound:
    def test_function_call_is_dispatched_and_result_sent_back(self, monkeypatch):
        function_call = _FakeFunctionCall(name="get_portfolio_overview", args={"foo": "bar"})
        chat = _FakeChat([
            _FakeResponse(function_calls=[function_call], text=""),
            _FakeResponse(text="Portföyünüz güzel görünüyor."),
        ])
        _patch_sdk(monkeypatch, chat)
        call_tool = MagicMock(return_value={"total_value_try": 1000.0})

        provider = GeminiAdvisorChatProvider(api_key="key", tool_declarations=_DECLARATIONS, call_tool=call_tool)
        result = provider.generate("system", [("user", "portföyüm nasıl?")])

        call_tool.assert_called_once_with("get_portfolio_overview", {"foo": "bar"})
        assert result.text == "Portföyünüz güzel görünüyor."
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0].name == "get_portfolio_overview"
        assert result.tool_calls[0].arguments == {"foo": "bar"}
        assert result.tool_calls[0].result == {"total_value_try": 1000.0}

    def test_function_call_with_no_args_becomes_empty_dict(self, monkeypatch):
        function_call = _FakeFunctionCall(name="get_portfolio_overview", args=None)
        chat = _FakeChat([
            _FakeResponse(function_calls=[function_call]),
            _FakeResponse(text="tamam"),
        ])
        _patch_sdk(monkeypatch, chat)
        call_tool = MagicMock(return_value={})

        provider = GeminiAdvisorChatProvider(api_key="key", tool_declarations=_DECLARATIONS, call_tool=call_tool)
        provider.generate("system", [("user", "soru")])

        call_tool.assert_called_once_with("get_portfolio_overview", {})


class TestMultipleToolCallRounds:
    def test_two_sequential_tool_calls_before_final_text(self, monkeypatch):
        first_call = _FakeFunctionCall(name="get_portfolio_overview", args={})
        second_call = _FakeFunctionCall(name="suggest_optimization", args={"risk_label": "AGRESIF"})
        chat = _FakeChat([
            _FakeResponse(function_calls=[first_call]),
            _FakeResponse(function_calls=[second_call]),
            _FakeResponse(text="İşte analiz sonucu."),
        ])
        _patch_sdk(monkeypatch, chat)
        call_tool = MagicMock(side_effect=[{"a": 1}, {"b": 2}])

        provider = GeminiAdvisorChatProvider(api_key="key", tool_declarations=_DECLARATIONS, call_tool=call_tool)
        result = provider.generate("system", [("user", "riskimi azalt")])

        assert result.text == "İşte analiz sonucu."
        assert [c.name for c in result.tool_calls] == ["get_portfolio_overview", "suggest_optimization"]
        assert call_tool.call_count == 2

    def test_multiple_function_calls_in_single_response_all_dispatched(self, monkeypatch):
        call_a = _FakeFunctionCall(name="get_portfolio_overview", args={})
        call_b = _FakeFunctionCall(name="get_stock_overview", args={"ticker": "AKBNK"})
        chat = _FakeChat([
            _FakeResponse(function_calls=[call_a, call_b]),
            _FakeResponse(text="iki araç da çalıştı"),
        ])
        _patch_sdk(monkeypatch, chat)
        call_tool = MagicMock(return_value={"ok": True})

        provider = GeminiAdvisorChatProvider(api_key="key", tool_declarations=_DECLARATIONS, call_tool=call_tool)
        result = provider.generate("system", [("user", "soru")])

        assert call_tool.call_count == 2
        assert len(result.tool_calls) == 2


class TestMaxToolRoundsSafety:
    def test_loop_stops_after_max_rounds_even_if_model_keeps_calling_tools(self, monkeypatch):
        endless_call = _FakeFunctionCall(name="get_portfolio_overview", args={})
        # _MAX_TOOL_ROUNDS kadar (+1 fazladan, hiç tüketilmeyecek) function-call yanıtı scriptlenir.
        responses = [_FakeResponse(function_calls=[endless_call]) for _ in range(provider_module._MAX_TOOL_ROUNDS + 1)]
        chat = _FakeChat(responses)
        _patch_sdk(monkeypatch, chat)
        call_tool = MagicMock(return_value={})

        provider = GeminiAdvisorChatProvider(api_key="key", tool_declarations=_DECLARATIONS, call_tool=call_tool)
        result = provider.generate("system", [("user", "soru")])

        assert call_tool.call_count == provider_module._MAX_TOOL_ROUNDS
        assert len(result.tool_calls) == provider_module._MAX_TOOL_ROUNDS


class TestErrorHandling:
    def test_sdk_error_is_wrapped_as_runtime_error(self, monkeypatch):
        class _ExplodingChat:
            def send_message(self, message):
                raise ValueError("ağ hatası")

        class _ExplodingChats:
            def create(self, model, config, history):
                return _ExplodingChat()

        class _ExplodingClient:
            def __init__(self):
                self.chats = _ExplodingChats()

        class _ExplodingGenai:
            @staticmethod
            def Client(api_key):
                return _ExplodingClient()

        monkeypatch.setattr(provider_module, "_load_gemini_sdk", lambda: (_ExplodingGenai, _FakeTypes))

        provider = GeminiAdvisorChatProvider(api_key="key", tool_declarations=[], call_tool=MagicMock())
        with pytest.raises(RuntimeError, match="Yapay zeka danışman yanıtı alınamadı"):
            provider.generate("system", [("user", "soru")])
