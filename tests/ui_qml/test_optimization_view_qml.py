"""OptimizationView.qml — gerçek OptimizationController ile uçtan uca yükleme testi
(bkz. §7.3 madde 5, d5).

Kök nesne bir `Item` olduğundan pencere AÇILMAZ — headless güvenlidir. Doğrulanan:
kaynak seçici + risk slider'ı + metrik kartları + verimli sınır (`ScatterChartItem`)
+ rebalancing tablosu + context property (`optimizationController`) binding'leri
hatasız çalışıyor; `contentArea` gerçek (NaN/negatif olmayan) geometriye sahip
(bkz. Stock360View'daki NaN-yükseklik regresyonu, aynı sınıf hatayı burada da
önceden yakalamak için).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.application.services.planning.risk_optimization_bridge_service import RiskAwareOptimizationResult
from src.domain.models.optimization_result import OptimizationMetrics, OptimizationResult, OptimizationSuggestion
from src.domain.models.risk_profile import RiskLabel
from src.qt_compat.qtcore import QObject
from src.qt_compat.qtqml import QQmlApplicationEngine, qmlRegisterType
from src.ui_qml.charts.scatter_chart_item import ScatterChartItem
from src.ui_qml.controllers.optimization_controller import OptimizationController

_QML_FILE = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "views" / "OptimizationView.qml"

_types_registered = False


def _ensure_types_registered() -> None:
    global _types_registered
    if not _types_registered:
        qmlRegisterType(ScatterChartItem, "PortfoyCharts", 1, 0, "ScatterChartItem")
        _types_registered = True


def _make_container(raises=None) -> MagicMock:
    container = MagicMock()
    container.risk_optimization_bridge_service.get_active_risk_profile.return_value = None
    container.optimization_service.get_model_portfolios.return_value = []

    if raises is not None:
        container.risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.side_effect = raises
        return container

    result = OptimizationResult(
        current_metrics=OptimizationMetrics(expected_return=0.10, volatility=0.25, sharpe_ratio=0.40),
        optimized_metrics=OptimizationMetrics(expected_return=0.18, volatility=0.22, sharpe_ratio=0.82),
        suggestions=[
            OptimizationSuggestion(symbol="AKBNK", current_weight=60.0, optimal_weight=40.0, change=-20.0, action="AZALT"),
            OptimizationSuggestion(symbol="THYAO", current_weight=40.0, optimal_weight=60.0, change=20.0, action="EKLE"),
        ],
        min_volatility_metrics=OptimizationMetrics(expected_return=0.08, volatility=0.15, sharpe_ratio=0.53),
    )
    outcome = RiskAwareOptimizationResult(
        result=result, risk_label=RiskLabel.DENGELI, max_single_weight_pct=20.0,
        equity_ceiling_pct=30, used_default_profile=True, is_manual_override=False,
    )
    container.risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile.return_value = outcome
    return container


@pytest.fixture
def loaded_engine(qapp):
    _ensure_types_registered()
    controller = OptimizationController(_make_container())

    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("optimizationController", controller)

    engine.load(str(_QML_FILE))

    yield engine, controller, warnings_seen
    engine.deleteLater()


def test_qml_file_exists():
    assert _QML_FILE.exists(), f"OptimizationView.qml bulunamadı: {_QML_FILE}"


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


def test_error_state_also_loads_without_warnings(qapp):
    # hasResult=False durumu (yetersiz pozisyon vb.) da headless yüklenebilmeli.
    _ensure_types_registered()
    controller = OptimizationController(_make_container(raises=ValueError("Optimizasyon icin portfoyde en az 2 farkli hisse olmalidir.")))

    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("optimizationController", controller)
    engine.load(str(_QML_FILE))

    assert engine.rootObjects(), "QML kök nesnesi oluşturulamadı"
    assert not warnings_seen, f"QML uyarı/hata verdi: {warnings_seen}"
    engine.deleteLater()
