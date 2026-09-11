"""AiAdvisorController — d6/e1.3 AiAdvisorView (Gemini tool-calling) köprüsü testleri.

Gerçek Gemini API'ye hiç gidilmez — `GeminiAdvisorChatProvider.generate()` mock'lanır.
Gerçek bir arka plan thread'i de kullanılmaz: `controller._threadpool` sahte bir
nesneyle değiştirilip `worker.run()` senkron çağrılır — bu, `Worker.run()`'ın
gerçek kodunu (fn çağrısı + signal emit) hâlâ tam olarak çalıştırır, sadece
gerçek `QThreadPool` zamanlama belirsizliğini test dışı bırakır.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.infrastructure.ai.gemini_advisor_chat_provider import AdvisorChatResult, AdvisorToolCall
from src.ui_qml.controllers.ai_advisor_controller import AiAdvisorController


class _SyncThreadPool:
    """Gerçek `QThreadPool` yerine — `start(worker)` senkron `worker.run()` çağırır."""

    def start(self, worker) -> None:
        worker.run()


def _make_container(generate_return=None, generate_side_effect=None) -> MagicMock:
    container = MagicMock()
    container.settings.ai.gemini_api_key = "test-key"
    container.ai_advisor_service.tool_declarations = []
    container.ai_advisor_service.call_tool = MagicMock()
    return container


def _make_controller(container=None) -> AiAdvisorController:
    controller = AiAdvisorController(container or _make_container())
    controller._threadpool = _SyncThreadPool()
    return controller


class TestInitialState:
    def test_no_messages_initially(self, qapp):
        controller = _make_controller()
        assert controller.messageRoles == []
        assert controller.messageTexts == []
        assert controller.isLoading is False
        assert controller.errorMessage == ""


class TestSendMessage:
    def test_empty_text_is_ignored(self, qapp):
        controller = _make_controller()
        controller.sendMessage("   ")
        assert controller.messageRoles == []

    def test_user_message_appended_before_response(self, qapp, monkeypatch):
        controller = _make_controller()
        monkeypatch.setattr(
            controller._provider, "generate", lambda *a, **kw: AdvisorChatResult(text="yanıt", tool_calls=[]),
        )

        controller.sendMessage("portföyüm nasıl?")

        assert controller.messageRoles == ["user", "model"]
        assert controller.messageTexts == ["portföyüm nasıl?", "yanıt"]

    def test_ignored_while_already_loading(self, qapp):
        container = _make_container()
        controller = AiAdvisorController(container)
        controller._threadpool = MagicMock()  # start() hiçbir şey yapmaz -> loading takılı kalır

        controller.sendMessage("ilk mesaj")
        assert controller.isLoading is True

        controller.sendMessage("ikinci mesaj")
        assert controller.messageTexts == ["ilk mesaj"]  # ikincisi yok sayıldı

    def test_loading_true_during_call_false_after(self, qapp, monkeypatch):
        controller = _make_controller()
        loading_snapshots = []

        def fake_generate(*_args, **_kwargs):
            loading_snapshots.append(controller.isLoading)
            return AdvisorChatResult(text="yanıt", tool_calls=[])

        monkeypatch.setattr(controller._provider, "generate", fake_generate)
        controller.sendMessage("soru")

        assert loading_snapshots == [True]
        assert controller.isLoading is False

    def test_tool_calls_recorded_as_comma_joined_names(self, qapp, monkeypatch):
        controller = _make_controller()
        result = AdvisorChatResult(
            text="öneri hazır",
            tool_calls=[
                AdvisorToolCall(name="get_portfolio_overview", arguments={}, result={}),
                AdvisorToolCall(name="suggest_optimization", arguments={}, result={}),
            ],
        )
        monkeypatch.setattr(controller._provider, "generate", lambda *a, **kw: result)

        controller.sendMessage("riskimi azalt")

        assert controller.messageToolNames == ["", "get_portfolio_overview, suggest_optimization"]

    def test_history_sent_includes_all_prior_turns(self, qapp, monkeypatch):
        controller = _make_controller()
        captured_turns = []

        def fake_generate(system_prompt, turns):
            captured_turns.append(list(turns))
            return AdvisorChatResult(text="yanıt " + str(len(captured_turns)), tool_calls=[])

        monkeypatch.setattr(controller._provider, "generate", fake_generate)

        controller.sendMessage("ilk soru")
        controller.sendMessage("ikinci soru")

        assert captured_turns[0] == [("user", "ilk soru")]
        assert captured_turns[1] == [("user", "ilk soru"), ("model", "yanıt 1"), ("user", "ikinci soru")]


class TestErrorHandling:
    def test_provider_error_sets_error_message_and_clears_loading(self, qapp, monkeypatch):
        controller = _make_controller()

        def fake_generate(*_args, **_kwargs):
            raise RuntimeError("Yapay zeka anahtarı bulunamadı.")

        monkeypatch.setattr(controller._provider, "generate", fake_generate)
        controller.sendMessage("soru")

        assert controller.errorMessage == "Yapay zeka anahtarı bulunamadı."
        assert controller.isLoading is False
        # Hata durumunda da kullanıcı mesajı listede kalır (kaybolmaz), sadece model yanıtı eklenmez.
        assert controller.messageRoles == ["user"]

    def test_new_successful_message_clears_previous_error(self, qapp, monkeypatch):
        controller = _make_controller()
        monkeypatch.setattr(
            controller._provider, "generate",
            lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("gecici hata")),
        )
        controller.sendMessage("ilk soru")
        assert controller.errorMessage == "gecici hata"

        monkeypatch.setattr(controller._provider, "generate", lambda *a, **kw: AdvisorChatResult(text="tamam", tool_calls=[]))
        controller.sendMessage("ikinci soru")

        assert controller.errorMessage == ""
