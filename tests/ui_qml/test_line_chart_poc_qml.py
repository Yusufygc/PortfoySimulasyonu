"""LineChartPoc.qml — gerçek QQmlApplicationEngine ile uçtan uca yükleme testi (bkz. §9.4 d0).

Kök nesne bir `Rectangle` (QQuickWindow değil) olduğundan pencere AÇILMAZ — headless
güvenlidir. Burada doğrulanan: type registration + `import PortfoyCharts 1.0` +
context property binding (`values: chartValues`) hatasız çalışıyor mu.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from src.qt_compat.qtqml import QQmlApplicationEngine, qmlRegisterType
from src.ui_qml.charts.line_chart_item import LineChartItem

_QML_FILE = (
    Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "poc" / "LineChartPoc.qml"
)

_type_registered = False


def _ensure_type_registered() -> None:
    global _type_registered
    if not _type_registered:
        qmlRegisterType(LineChartItem, "PortfoyCharts", 1, 0, "LineChartItem")
        _type_registered = True


@pytest.fixture
def loaded_engine(qapp):
    _ensure_type_registered()
    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("chartValues", [10.0, 40.0, 25.0, 60.0])

    engine.load(str(_QML_FILE))

    yield engine, warnings_seen
    engine.deleteLater()


def test_qml_file_exists():
    assert _QML_FILE.exists(), f"POC QML dosyası bulunamadı: {_QML_FILE}"


def test_qml_loads_without_warnings_and_creates_root_object(loaded_engine):
    engine, warnings_seen = loaded_engine

    assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
    assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"


def test_root_object_has_expected_size_from_qml(loaded_engine):
    engine, _ = loaded_engine
    root = engine.rootObjects()[0]

    assert root.property("width") == 640
    assert root.property("height") == 360
