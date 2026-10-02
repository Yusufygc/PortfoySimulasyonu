"""Sohbet oturum servisi ve AI danışman denetleyicisinde sohbet geçmişi."""
from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.application.services.ai.chat_session_service import DEFAULT_TITLE, MAX_TITLE_LENGTH, ChatSessionService
from src.domain.models.ai_analysis import ChatMessage, ChatSession, MessageRole
from src.domain.ports.repositories.i_chat_history_repo import IChatHistoryRepository
from src.ui_qml.controllers.ai_advisor_controller import AiAdvisorController

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"


class MemoryRepo(IChatHistoryRepository):
    def __init__(self):
        self.sessions: list[ChatSession] = []
        self.last_id = None

    def load_sessions(self):
        return list(self.sessions)

    def save_sessions(self, sessions):
        self.sessions = list(sessions)

    def get_last_active_session_id(self):
        return self.last_id

    def set_last_active_session_id(self, session_id):
        self.last_id = session_id


def _user(text):
    return ChatMessage(MessageRole.USER, text)


def _ai(text):
    return ChatMessage(MessageRole.AI, text)


def test_session_without_user_message_is_not_saved():
    repo = MemoryRepo()
    service = ChatSessionService(repo)
    session = service.create_session([_ai("Merhaba")])

    assert service.save_session(session) is False
    assert repo.sessions == [] and repo.last_id is None


def test_save_derives_title_orders_by_recency_and_marks_active():
    repo = MemoryRepo()
    service = ChatSessionService(repo)
    first = service.create_session([_user("Portföyümün riski nedir?"), _ai("Orta")])
    second = service.create_session([_user("x" * 120), _ai("...")])

    assert service.save_session(first) and service.save_session(second)

    assert first.title == "Portföyümün riski nedir?"
    assert len(second.title) == MAX_TITLE_LENGTH and second.title.endswith("…")
    assert [s.id for s in service.list_sessions()] == [second.id, first.id]
    assert repo.last_id == second.id and service.get_last_active_session().id == second.id
    assert service.title_from_message("   ") == DEFAULT_TITLE


def test_resaving_updates_same_session_and_delete_clears_active():
    repo = MemoryRepo()
    service = ChatSessionService(repo)
    session = service.create_session([_user("soru")])
    service.save_session(session)
    session.messages.append(_ai("cevap"))
    service.save_session(session)

    assert len(repo.sessions) == 1 and len(repo.sessions[0].messages) == 2

    service.delete_session(session.id)
    assert repo.sessions == [] and repo.last_id is None


def test_session_count_is_capped():
    repo = MemoryRepo()
    service = ChatSessionService(repo, max_sessions=3)
    for index in range(5):
        session = service.create_session([_user(f"soru {index}")])
        session.updated_at = datetime.now() + timedelta(seconds=index)
        service.save_session(session)

    assert len(repo.sessions) == 3


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _controller(qapp, repo=None):
    repo = repo or MemoryRepo()
    container = SimpleNamespace(chat_session_service=ChatSessionService(repo))
    ctrl = AiAdvisorController(container=container)
    ctrl._executor = ImmediateExecutor()
    return ctrl, repo


def _exchange(ctrl, question, answer):
    ctrl._messages.append({"id": f"msg-{len(ctrl._messages) + 1}", "role": "user", "content": question,
                           "timestamp": "10:00", "toolCalls": []})
    ctrl._on_async_response_ready({"content": answer, "toolCalls": []})


def test_controller_persists_exchange_and_skips_welcome(qapp):
    ctrl, repo = _controller(qapp)
    assert ctrl.messages[0].get("isWelcome") and ctrl.sessions == []

    _exchange(ctrl, "Risk nasıl?", "Orta düzey.")

    saved = repo.sessions[0]
    assert [m.role for m in saved.messages] == [MessageRole.USER, MessageRole.AI]  # karşılama kaydedilmez
    assert ctrl.sessions[0]["title"] == "Risk nasıl?" and ctrl.sessions[0]["messageCount"] == 1
    assert ctrl.activeSessionId == saved.id


def test_new_chat_keeps_history_and_select_restores_messages(qapp):
    ctrl, repo = _controller(qapp)
    _exchange(ctrl, "Birinci soru", "Birinci cevap")
    first_id = ctrl.activeSessionId

    ctrl.newChat()
    assert ctrl.activeSessionId != first_id and ctrl.messages[0].get("isWelcome")
    _exchange(ctrl, "İkinci soru", "İkinci cevap")
    assert len(ctrl.sessions) == 2

    ctrl.selectSession(first_id)

    assert ctrl.activeSessionId == first_id
    assert [m["content"] for m in ctrl.messages] == ["Birinci soru", "Birinci cevap"]


def test_delete_active_session_starts_fresh_chat(qapp):
    ctrl, repo = _controller(qapp)
    _exchange(ctrl, "Soru", "Cevap")
    active = ctrl.activeSessionId

    ctrl.deleteSession(active)

    assert ctrl.sessions == [] and repo.sessions == []
    assert ctrl.activeSessionId != active and ctrl.messages[0].get("isWelcome")


def test_controller_restores_last_active_session_on_startup(qapp):
    repo = MemoryRepo()
    ctrl, _ = _controller(qapp, repo)
    _exchange(ctrl, "Kalıcı soru", "Kalıcı cevap")

    reopened, _ = _controller(qapp, repo)

    assert [m["content"] for m in reopened.messages] == ["Kalıcı soru", "Kalıcı cevap"]
    assert reopened.historyAvailable is True


def test_switching_is_blocked_while_loading_and_errors_are_not_persisted(qapp):
    ctrl, repo = _controller(qapp)
    _exchange(ctrl, "Soru", "Cevap")
    first = ctrl.activeSessionId
    ctrl._set_loading(True)

    ctrl.newChat()
    ctrl.deleteSession(first)
    assert ctrl.activeSessionId == first and len(repo.sessions) == 1

    ctrl._set_loading(False)
    ctrl._on_async_error_ready("ağ yok")
    ctrl._persist_session()
    assert all(m.role != MessageRole.SYSTEM for m in repo.sessions[0].messages)


def test_controller_without_history_service_still_works(qapp):
    ctrl = AiAdvisorController(container=None)

    ctrl.clearChat()
    ctrl.newChat()

    assert ctrl.historyAvailable is False and ctrl.sessions == [] and ctrl.messages[0].get("isWelcome")


def test_chat_history_dialog_compiles_and_lists_sessions(qapp):
    ctrl, _ = _controller(qapp)
    _exchange(ctrl, "Listede görünsün", "Tamam")
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    engine.rootContext().setContextProperty("aiAdvisorController", ctrl)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components/ChatHistoryDialog.qml")))
    if not component.isReady():
        pytest.fail("; ".join(e.toString() for e in component.errors()))

    item = component.create()
    QMetaObject.invokeMethod(item, "open")

    assert item is not None and item.property("isOpen") is True
    assert warnings == [], "; ".join(warnings)
