"""ScreenerView.qml — gerçek ScreenerController ile uçtan uca yükleme testi (bkz. §7.3).

Kök nesne bir `Item` olduğundan pencere AÇILMAZ — headless güvenlidir. Doğrulanan:
filtre çipleri + sonuç listesi (`MouseArea`+`Repeater`) + `LineChartItem` sparkline +
context property (`screenerController`) binding'leri hatasız çalışıyor; `contentArea`
gerçek (NaN/negatif olmayan) geometriye sahip (bkz. Stock360View'daki NaN-yükseklik
regresyonu, aynı sınıf hatayı burada da önceden yakalamak için).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.qt_compat.qtcore import QObject
from src.qt_compat.qtqml import QQmlApplicationEngine, qmlRegisterType
from src.ui_qml.charts.line_chart_item import LineChartItem
from src.ui_qml.controllers.screener_controller import ScreenerController

_QML_FILE = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "views" / "ScreenerView.qml"

_types_registered = False


def _ensure_types_registered() -> None:
    global _types_registered
    if not _types_registered:
        qmlRegisterType(LineChartItem, "PortfoyCharts", 1, 0, "LineChartItem")
        _types_registered = True


@pytest.fixture
def loaded_engine(qapp):
    _ensure_types_registered()
    container = MagicMock()
    container.screener_service.scan.return_value = []
    controller = ScreenerController(container)  # boş tarama sonucu, çökmemeli

    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("screenerController", controller)

    engine.load(str(_QML_FILE))

    yield engine, controller, warnings_seen
    engine.deleteLater()


def test_qml_file_exists():
    assert _QML_FILE.exists(), f"ScreenerView.qml bulunamadı: {_QML_FILE}"


def test_loads_without_warnings_and_creates_root_object(loaded_engine):
    engine, _controller, warnings_seen = loaded_engine

    assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
    assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"


def test_content_area_has_real_positive_geometry(loaded_engine):
    engine, _controller, _warnings = loaded_engine
    root = engine.rootObjects()[0]
    root.setProperty("width", 1280)
    root.setProperty("height", 800)

    content_area = root.findChild(QObject, "contentArea")
    assert content_area is not None
    height = content_area.property("height")
    assert height == height  # NaN != NaN
    assert height > 0
