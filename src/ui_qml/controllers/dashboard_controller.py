"""
DashboardController — DashboardView'un veri köprüsü (bkz. plan §7.3 madde 1, d2).

4 KPI kartı (Toplam Değer+Günlük %, Toplam K/Z+Toplam Getiri %, Sharpe, XU100
Relatif Getiri) + pozisyon tablosu (`PortfolioController`'a delege) + varlık
dağılım donut segmentleri (mevcut pozisyon ağırlıklarından türetilir).

Backend: `PortfolioAnalyticsService` (§5.2 facade → mevcut `AnalysisService`) +
`ReturnCalcService.compute_return_between()` (günlük değişim için — mevcut haftalık/
aylık getiri hesaplarıyla aynı metod, sadece 1 günlük aralıkla çağrılır). Hesap
mantığı burada yeniden yazılmadı.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import List, Optional

from src.qt_compat.qtcore import Property, QObject, Signal, Slot
from src.application.services.analysis.models import AnalysisFilterState
from src.ui_qml.controllers.portfolio_controller import PortfolioController

_DEFAULT_LOOKBACK_DAYS = 365
_DEFAULT_BENCHMARK = "bist100"


def _to_float(value: Optional[float]) -> float:
    return float(value) if value is not None else 0.0


class DashboardController(QObject):
    """Dashboard KPI'ları + pozisyon tablosu + varlık dağılımı."""

    dailyChangePctChanged = Signal()
    totalReturnPctChanged = Signal()
    sharpeRatioChanged = Signal()
    benchmarkGapPctChanged = Signal()
    benchmarkLabelChanged = Signal()
    allocationChanged = Signal()

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self._container = container
        self._portfolio = PortfolioController(container, parent=self)
        self._daily_change_pct = 0.0
        self._total_return_pct = 0.0
        self._sharpe_ratio = 0.0
        self._benchmark_gap_pct = 0.0
        self._benchmark_label = ""
        self._allocation_labels: List[str] = []
        self._allocation_weights: List[float] = []
        self.refresh()

    # ------------------------------------------------------------------
    # QML'e açılan property'ler
    # ------------------------------------------------------------------

    @Property(QObject, constant=True)
    def portfolio(self) -> PortfolioController:
        return self._portfolio

    @Property(float, notify=dailyChangePctChanged)
    def dailyChangePct(self) -> float:
        return self._daily_change_pct

    @Property(float, notify=totalReturnPctChanged)
    def totalReturnPct(self) -> float:
        return self._total_return_pct

    @Property(float, notify=sharpeRatioChanged)
    def sharpeRatio(self) -> float:
        return self._sharpe_ratio

    @Property(float, notify=benchmarkGapPctChanged)
    def benchmarkGapPct(self) -> float:
        return self._benchmark_gap_pct

    @Property(str, notify=benchmarkLabelChanged)
    def benchmarkLabel(self) -> str:
        return self._benchmark_label

    @Property("QVariantList", notify=allocationChanged)
    def allocationLabels(self) -> List[str]:
        return list(self._allocation_labels)

    @Property("QVariantList", notify=allocationChanged)
    def allocationWeights(self) -> List[float]:
        return list(self._allocation_weights)

    # ------------------------------------------------------------------
    # Veri yenileme
    # ------------------------------------------------------------------

    @Slot()
    def refresh(self) -> None:
        self._portfolio.refresh()
        self._refresh_allocation()
        self._refresh_analytics()
        self._set_daily_change_pct(self._compute_daily_change_pct())

    def _refresh_allocation(self) -> None:
        model = self._portfolio.positionsModel
        labels = [model.row_at(i)["ticker"] for i in range(model.rowCount())]
        weights = [model.row_at(i)["weight_pct"] for i in range(model.rowCount())]
        changed = labels != self._allocation_labels or weights != self._allocation_weights
        self._allocation_labels = labels
        self._allocation_weights = weights
        if changed:
            self.allocationChanged.emit()

    def _refresh_analytics(self) -> None:
        filter_state = self._build_filter_state()
        analytics = self._container.portfolio_analytics_service
        overview = analytics.get_overview(filter_state)
        risk_view = analytics.get_allocation_risk_view(filter_state)

        self._set_total_return_pct(_to_float(overview.period_return_pct))
        self._set_benchmark_gap_pct(_to_float(overview.benchmark_gap_pct))
        self._set_benchmark_label(overview.benchmark_label or "")
        self._set_sharpe_ratio(_to_float(risk_view.sharpe_ratio))

    def _compute_daily_change_pct(self) -> float:
        today = date.today()
        rate, _start, _end = self._container.return_calc_service.compute_return_between(
            today - timedelta(days=1), today,
        )
        return _to_float(rate) * 100.0

    def _build_filter_state(self) -> AnalysisFilterState:
        today = date.today()
        analytics = self._container.portfolio_analytics_service
        start = analytics.get_first_trade_date_for_source("dashboard") or (today - timedelta(days=_DEFAULT_LOOKBACK_DAYS))
        return AnalysisFilterState(
            start_date=start,
            end_date=today,
            portfolio_source="dashboard",
            selected_benchmarks=[_DEFAULT_BENCHMARK],
        )

    def _set_daily_change_pct(self, value: float) -> None:
        if value != self._daily_change_pct:
            self._daily_change_pct = value
            self.dailyChangePctChanged.emit()

    def _set_total_return_pct(self, value: float) -> None:
        if value != self._total_return_pct:
            self._total_return_pct = value
            self.totalReturnPctChanged.emit()

    def _set_sharpe_ratio(self, value: float) -> None:
        if value != self._sharpe_ratio:
            self._sharpe_ratio = value
            self.sharpeRatioChanged.emit()

    def _set_benchmark_gap_pct(self, value: float) -> None:
        if value != self._benchmark_gap_pct:
            self._benchmark_gap_pct = value
            self.benchmarkGapPctChanged.emit()

    def _set_benchmark_label(self, value: str) -> None:
        if value != self._benchmark_label:
            self._benchmark_label = value
            self.benchmarkLabelChanged.emit()
