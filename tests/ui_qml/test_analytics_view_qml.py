"""AnalyticsView.qml — gerçek AnalyticsController ile uçtan uca yükleme testi (bkz. §7.3 madde 4, d4).

Kök nesne bir `Item` olduğundan pencere AÇILMAZ — headless güvenlidir. Doğrulanan:
performans/drawdown çizgi grafikleri, dönemsel getiri bar grafiği, risk/getiri
saçılımı, gelişmiş risk paneli ve aylık ısı haritası + context property
(`analyticsController`) binding'leri hatasız çalışıyor; `contentArea` gerçek
(NaN/negatif olmayan) geometriye sahip (bkz. Stock360View'daki NaN-yükseklik
regresyonu, aynı sınıf hatayı burada da önceden yakalamak için).
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

import pandas as pd
import pytest

from src.application.services.analysis.models import BenchmarkSeries, ComparisonMetric, ComparisonViewDTO
from src.application.services.analysis.portfolio_analytics_service import ChartPanelsDTO, ExtendedRiskMetricsDTO
from src.qt_compat.qtcore import QObject
from src.qt_compat.qtqml import QQmlApplicationEngine, qmlRegisterType
from src.ui_qml.charts.bar_chart_item import BarChartItem
from src.ui_qml.charts.line_chart_item import LineChartItem
from src.ui_qml.charts.scatter_chart_item import ScatterChartItem
from src.ui_qml.charts.treemap_chart_item import TreemapChartItem
from src.ui_qml.controllers.analytics_controller import AnalyticsController

_QML_FILE = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "qml" / "views" / "AnalyticsView.qml"

_types_registered = False

_DATES = pd.to_datetime(["2024-01-31", "2024-02-29", "2024-03-31"])


def _ensure_types_registered() -> None:
    global _types_registered
    if not _types_registered:
        qmlRegisterType(LineChartItem, "PortfoyCharts", 1, 0, "LineChartItem")
        qmlRegisterType(BarChartItem, "PortfoyCharts", 1, 0, "BarChartItem")
        qmlRegisterType(ScatterChartItem, "PortfoyCharts", 1, 0, "ScatterChartItem")
        qmlRegisterType(TreemapChartItem, "PortfoyCharts", 1, 0, "TreemapChartItem")
        _types_registered = True


def _make_container() -> MagicMock:
    container = MagicMock()
    container.portfolio_analytics_service.get_first_trade_date_for_source.return_value = date(2024, 1, 1)

    aligned = pd.DataFrame({"Ana Portföy": [200.0, 220.0, 242.0], "BIST 100": [100.0, 105.0, 100.0]}, index=_DATES)
    drawdowns = pd.DataFrame({"Ana Portföy": [0.0, -5.0, -2.0]}, index=_DATES)
    periodic_returns = pd.DataFrame({"Ana Portföy": [10.0, 10.0]}, index=_DATES[1:])
    risk_return = {
        "Ana Portföy": {"annual_volatility_pct": 15.0, "total_return_pct": 21.0},
        "BIST 100": {"annual_volatility_pct": 10.0, "total_return_pct": 0.0},
    }
    container.portfolio_analytics_service.get_chart_panels.return_value = ChartPanelsDTO(
        aligned_series=aligned, drawdowns=drawdowns, periodic_returns=periodic_returns,
        risk_return_metrics=risk_return,
        comparison=ComparisonViewDTO(
            portfolio_series={}, benchmark_series=[BenchmarkSeries(code="bist100", label="BIST 100", points={})],
            stock_series={},
            comparison_metrics=[ComparisonMetric(label="BIST 100", portfolio_return_pct=21.0, benchmark_return_pct=0.0, relative_gap_pct=21.0)],
            comparison_portfolios=[], current_portfolio_label="Ana Portföy", warnings=[],
        ),
    )
    container.portfolio_analytics_service.get_extended_risk_metrics.return_value = ExtendedRiskMetricsDTO(
        sharpe_ratio=1.5, sortino_ratio=2.0, calmar_ratio=0.8, omega_ratio=1.3,
        value_at_risk_95_pct=-3.2, conditional_var_95_pct=-4.5, beta=0.19, alpha=2.1,
        r_squared=0.10, tracking_error_pct=23.1,
        monthly_returns_matrix={2024: {1: 5.0, 3: -2.0}}, benchmark_label="BIST 100",
    )
    return container


@pytest.fixture
def loaded_engine(qapp):
    _ensure_types_registered()
    controller = AnalyticsController(_make_container())

    engine = QQmlApplicationEngine()
    warnings_seen = []
    engine.warnings.connect(lambda warns: warnings_seen.extend(warns))
    engine.rootContext().setContextProperty("analyticsController", controller)

    engine.load(str(_QML_FILE))

    yield engine, controller, warnings_seen
    engine.deleteLater()


def test_qml_file_exists():
    assert _QML_FILE.exists(), f"AnalyticsView.qml bulunamadı: {_QML_FILE}"


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
