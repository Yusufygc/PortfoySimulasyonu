"""Karşılaştırma grafik açıklama kartları ("Nedir / Nasıl Yorumlanır")."""
from __future__ import annotations

from pathlib import Path

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.ui_qml.controllers.comparison_controller import ComparisonController

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"


class _NoExecutor:
    """Gerçek hesaplama iş parçacığı başlatma: test bittikten sonra silinmiş QObject'e sinyal göndermesin."""

    def submit(self, *args, **kwargs):
        return None


def _load_chart_card():
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    controller = ComparisonController(container=MagicMock(), parent=engine)
    controller._executor = controller._executor_ai = _NoExecutor()
    engine.rootContext().setContextProperty("comparisonController", controller)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components" / "ComparisonChartCard.qml")))
    if not component.isReady():
        pytest.fail("; ".join(error.toString() for error in component.errors()))
    card = component.create()
    assert card is not None
    return engine, component, controller, card


def _info_card(card):
    matches = [child for child in card.findChildren(QObject) if child.property("how") is not None and child.property("what") is not None]
    assert len(matches) == 1
    return matches[0]


def test_info_card_follows_chart_tab_and_main_chart_mode(qapp):
    engine, component, controller, card = _load_chart_card()
    info = _info_card(card)

    controller.setActiveChartTab(0)
    controller.setComparisonMode("NORMALIZED")
    assert info.property("title") == "Ana Performans Kıyaslama Grafiği"
    assert "100'e eşitleyerek" in info.property("what") and "Normalize modda" in info.property("how")

    controller.setComparisonMode("RATIO")
    assert "iki varlığın birbirine oranını" in info.property("what")
    assert "pay varlığı" in info.property("how")

    controller.setComparisonMode("NORMAL")
    assert "Normal modda" in info.property("how")

    for tab, title_part in [(1, "Drawdown"), (2, "Getiri Karşılaştırması"), (3, "Risk-Getiri"), (4, "Treemap")]:
        controller.setActiveChartTab(tab)
        assert title_part in info.property("title") and info.property("what") and info.property("how")
        assert "Grafik Modu" in info.property("how")


def test_info_card_is_collapsed_until_header_is_toggled(qapp):
    engine, component, _controller, card = _load_chart_card()
    info = _info_card(card)

    assert info.property("expanded") is False
    info.setProperty("expanded", True)
    assert info.property("expanded") is True
