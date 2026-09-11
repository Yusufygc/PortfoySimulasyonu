"""SimulationView.qml — gerçek SimulationController ile uçtan uca yükleme testi
(bkz. §7.3 madde 6, d5).

Kök nesne bir `Item` olduğundan pencere AÇILMAZ — headless güvenlidir. Doğrulanan:
ticker/katkı/tarih-aralığı form girdileri + özet kartları + `LineChartItem` +
lot dökümü + context property (`simulationController`) binding'leri hatasız
çalışıyor; `contentArea` gerçek (NaN/negatif olmayan) geometriye sahip (bkz.
Stock360View'daki NaN-yükseklik regresyonu, aynı sınıf hatayı burada da
önceden yakalamak için). Hem boş form durumu hem doldurulmuş sonuç durumu
ayrı ayrı test edilir.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.services.simulation.dca_backtest import DCABacktestResult
from src.qt_compat.qtcore import QObject
from src.qt_compat.qtqml import QQmlApplicationEngine, qmlRegisterType
from src.ui_qml.charts.line_chart_item import LineChartItem
from src.ui_qml.controllers.simulation_controller import SimulationController

_QML_FILE = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "views" / "SimulationView.qml"

_types_registered = False


def _ensure_types_registered() -> None:
    global _types_registered
    if not _types_registered:
        qmlRegisterType(LineChartItem, "PortfoyCharts", 1, 0, "LineChartItem")
        _types_registered = True


def _load(controller):
    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("simulationController", controller)
    engine.load(str(_QML_FILE))
    return engine, warnings_seen


def test_qml_file_exists():
    assert _QML_FILE.exists(), f"SimulationView.qml bulunamadı: {_QML_FILE}"


class TestEmptyFormState:
    @pytest.fixture
    def loaded_engine(self, qapp):
        _ensure_types_registered()
        controller = SimulationController(MagicMock())
        engine, warnings_seen = _load(controller)
        yield engine, controller, warnings_seen
        engine.deleteLater()

    def test_loads_without_warnings(self, loaded_engine):
        engine, _controller, warnings_seen = loaded_engine
        assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
        assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"

    def test_content_area_has_real_positive_geometry(self, loaded_engine):
        engine, _controller, _warnings = loaded_engine
        root = engine.rootObjects()[0]
        root.setProperty("width", 1280)
        root.setProperty("height", 800)

        content_area = root.findChild(QObject, "contentArea")
        assert content_area is not None
        height = content_area.property("height")
        assert height == height  # NaN != NaN
        assert height > 0


class TestWithResult:
    @pytest.fixture
    def loaded_engine(self, qapp):
        _ensure_types_registered()
        container = MagicMock()
        container.dca_backtest_service.run.return_value = DCABacktestResult(
            portfolio_value_series={date(2024, 1, 2): Decimal("1000"), date(2024, 6, 1): Decimal("6684")},
            total_invested=Decimal("6000"),
            final_value=Decimal("6684"),
            shares_by_ticker={"AKBNK": Decimal("12.5"), "FROTO": Decimal("3.2")},
            total_return_pct=11.4,
            contribution_count=6,
        )
        controller = SimulationController(container)
        controller.setTickersText("AKBNK, FROTO")
        controller.runSimulation()

        engine, warnings_seen = _load(controller)
        yield engine, controller, warnings_seen
        engine.deleteLater()

    def test_loads_without_warnings(self, loaded_engine):
        engine, _controller, warnings_seen = loaded_engine
        assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
        assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"

    def test_content_area_has_real_positive_geometry(self, loaded_engine):
        engine, _controller, _warnings = loaded_engine
        root = engine.rootObjects()[0]
        root.setProperty("width", 1280)
        root.setProperty("height", 800)

        content_area = root.findChild(QObject, "contentArea")
        assert content_area is not None
        height = content_area.property("height")
        assert height == height  # NaN != NaN
        assert height > 0
