"""AiAdvisorView.qml — gerçek AiAdvisorController ile uçtan uca yükleme testi
(bkz. plan §6.2, e1.3).

Kök nesne bir `Item` olduğundan pencere AÇILMAZ — headless güvenlidir.
Gerçek Gemini API'ye hiç gidilmez (`gemini_api_key=None`, hiçbir mesaj
gönderilmiyor — sadece boş/dolu durum layout'u doğrulanıyor).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.qt_compat.qtcore import QObject
from src.qt_compat.qtqml import QQmlApplicationEngine
from src.ui_qml.controllers.ai_advisor_controller import AiAdvisorController

_QML_FILE = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "views" / "AiAdvisorView.qml"


def _make_container() -> MagicMock:
    container = MagicMock()
    container.settings.ai.gemini_api_key = None
    container.ai_advisor_service.tool_declarations = []
    container.ai_advisor_service.call_tool = MagicMock()
    return container


def _load(controller):
    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("aiAdvisorController", controller)
    engine.load(str(_QML_FILE))
    return engine, warnings_seen


def test_qml_file_exists():
    assert _QML_FILE.exists(), f"AiAdvisorView.qml bulunamadı: {_QML_FILE}"


class TestEmptyState:
    @pytest.fixture
    def loaded_engine(self, qapp):
        controller = AiAdvisorController(_make_container())
        engine, warnings_seen = _load(controller)
        yield engine, controller, warnings_seen
        engine.deleteLater()

    def test_loads_without_warnings(self, loaded_engine):
        engine, _controller, warnings_seen = loaded_engine
        assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
        assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"

    def test_messages_area_has_real_positive_geometry(self, loaded_engine):
        engine, _controller, _warnings = loaded_engine
        root = engine.rootObjects()[0]
        root.setProperty("width", 1280)
        root.setProperty("height", 800)

        messages_area = root.findChild(QObject, "messagesArea")
        assert messages_area is not None
        height = messages_area.property("height")
        assert height == height  # NaN != NaN
        assert height > 0


class TestWithMessages:
    @pytest.fixture
    def loaded_engine(self, qapp, monkeypatch):
        from src.infrastructure.ai.gemini_advisor_chat_provider import AdvisorChatResult, AdvisorToolCall

        controller = AiAdvisorController(_make_container())
        monkeypatch.setattr(
            controller._provider, "generate",
            lambda *a, **kw: AdvisorChatResult(
                text="Portföyünüz %-13.88 getiri gösteriyor.",
                tool_calls=[AdvisorToolCall(name="get_portfolio_overview", arguments={}, result={})],
            ),
        )
        controller._threadpool = _SyncThreadPool()
        controller.sendMessage("portföyüm nasıl?")

        engine, warnings_seen = _load(controller)
        yield engine, controller, warnings_seen
        engine.deleteLater()

    def test_loads_without_warnings(self, loaded_engine):
        engine, _controller, warnings_seen = loaded_engine
        assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
        assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"

    def test_messages_area_has_real_positive_geometry(self, loaded_engine):
        engine, _controller, _warnings = loaded_engine
        root = engine.rootObjects()[0]
        root.setProperty("width", 1280)
        root.setProperty("height", 800)

        messages_area = root.findChild(QObject, "messagesArea")
        assert messages_area is not None
        height = messages_area.property("height")
        assert height == height  # NaN != NaN
        assert height > 0


class _SyncThreadPool:
    def start(self, worker) -> None:
        worker.run()
