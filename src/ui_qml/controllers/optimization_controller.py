"""
OptimizationController — Markowitz Portföy Optimizasyonu ve Efficient Frontier QML Controller'ı.

Sorumluluk:
- Ana portföy veya Model Portföyler üzerinde Markowitz Modern Portföy Teorisi optimizasyonu
- Risk toleransı profilleri (Çok Muhafazakar, Muhafazakar, Dengeli, Büyüme, Agresif, Manuel)
- Tek hisse max ağırlık ve risksiz faiz oranı kısıtları
- Monte Carlo simülasyonu (1.000+ nokta) ve Verimli Sınır (Efficient Frontier) saçılım grafiği
- Mevcut vs Optimize portföy ağırlık karşılaştırması
- Rebalance (yeniden dengeleme) öneri tablosu (hisse, adet, tutar, aksiyon)
- ThreadPoolExecutor ile UI bloklamayan asenkron hesaplama ve Qt Queued Signal yapısı
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List

import numpy as np
from PySide6.QtCore import Property, QObject, Signal, Slot

from src.domain.models.risk_profile import RiskLabel
from src.ui_qml.controllers.optimization_chart_html import build_frontier_chart_html, build_weights_chart_html
from src.ui_qml.controllers.optimization_pipeline import (
    OptimizationInputError,
    OptimizationServices,
    clean_ticker,
    compute_optimization,
)

logger = logging.getLogger(__name__)


def _fmt_pct(val: float | None, with_sign: bool = False) -> str:
    if val is None or not np.isfinite(val):
        return "%0,00"
    num = float(val)
    if abs(num) < 0.0001:
        return "%0,00"
    formatted = f"{abs(num):.2f}".replace(".", ",")
    if num < 0:
        return f"-%{formatted}"
    elif with_sign and num > 0:
        return f"+%{formatted}"
    return f"%{formatted}"


class OptimizationController(QObject):
    """QML context property: optimizationController"""

    # --- Signals ---
    portfolioOptionsChanged = Signal()
    riskProfileOptionsChanged = Signal()
    selectedRiskProfileChanged = Signal()
    maxSingleWeightChanged = Signal()
    riskFreeRateChanged = Signal()
    isLoadingChanged = Signal()
    hasResultsChanged = Signal()
    activeTabChanged = Signal()
    statusMessageChanged = Signal()
    chartHtmlChanged = Signal()
    weightsChartHtmlChanged = Signal()
    kpiMetricsChanged = Signal()
    suggestionsChanged = Signal()
    operationResult = Signal(bool, str, arguments=["success", "message"])

    # Worker Thread Sinyalleri (Qt Queued Connection ile GUI ana thread'ine güvenli iletim)
    _calcFinished = Signal(dict)
    _calcError = Signal(str)

    def __init__(self, container, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._opt_service = getattr(container, "optimization_service", None)
        self._bridge_service = getattr(container, "risk_optimization_bridge_service", None)
        self._portfolio_service = getattr(container, "portfolio_service", None)
        self._model_portfolio_service = getattr(container, "model_portfolio_service", None)
        self._lookup = getattr(container, "stock_lookup_service", None)
        self._risk_profile_service = getattr(container, "risk_profile_service", None)

        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="OptWorker")

        # Worker sinyal bağlantıları
        self._calcFinished.connect(self._on_calc_finished)
        self._calcError.connect(self._on_calc_error)

        self._init_state()
        self._init_risk_profiles()
        self.refreshPortfolios()

    def _init_state(self) -> None:
        self._portfolio_options: List[Dict[str, str]] = []
        self._selected_portfolio_code: str = "dashboard"
        self._selected_risk_profile: str = RiskLabel.DENGELI
        self._max_single_weight: float = 20.0
        self._risk_free_rate: float = 30.0
        self._is_loading: bool = False
        self._has_results: bool = False
        self._active_tab: int = 0
        self._status_message: str = ""
        self._chart_html: str = ""
        self._weights_chart_html: str = ""

        # KPI Değerleri
        self._opt_sharpe: float = 0.0
        self._opt_return: float = 0.0
        self._opt_vol: float = 0.0
        self._min_vol_vol: float = 0.0
        self._min_vol_return: float = 0.0
        self._curr_sharpe: float = 0.0
        self._curr_return: float = 0.0
        self._curr_vol: float = 0.0

        # Sonuç Verileri
        self._suggestions: List[Dict[str, Any]] = []
        self._weights_comparison: List[Dict[str, Any]] = []

    def _init_risk_profiles(self) -> None:
        self._risk_profile_options: List[Dict[str, Any]] = [
            {"code": RiskLabel.COK_MUHAFAZAKAR, "label": "Çok Muhafazakar", "maxWeight": 8.0},
            {"code": RiskLabel.MUHAFAZAKAR, "label": "Muhafazakar", "maxWeight": 10.0},
            {"code": RiskLabel.DENGELI, "label": "Dengeli", "maxWeight": 20.0},
            {"code": RiskLabel.BUYUME_ODAKLI, "label": "Büyüme Odaklı", "maxWeight": 28.0},
            {"code": RiskLabel.AGRESIF, "label": "Agresif", "maxWeight": 35.0},
            {"code": "MANUAL", "label": "Özel / Manuel Kısıt", "maxWeight": self._max_single_weight},
        ]

        # Başlangıçta kayıtlı risk profilini kontrol et
        if self._risk_profile_service:
            try:
                prof = self._risk_profile_service.get_current_profile()
                if prof and prof.risk_label in [r["code"] for r in self._risk_profile_options]:
                    self._selected_risk_profile = prof.risk_label
                    matched = next((r for r in self._risk_profile_options if r["code"] == prof.risk_label), None)
                    if matched:
                        self._max_single_weight = float(matched["maxWeight"])
            except Exception as e:
                logger.debug("Risk profili okunamadı: %s", e)

    # ──────────────────────────── QML Properties ────────────────────────────

    @Property(list, notify=portfolioOptionsChanged)
    def portfolioOptions(self) -> list:
        return self._portfolio_options

    @Property(list, notify=riskProfileOptionsChanged)
    def riskProfileOptions(self) -> list:
        return self._risk_profile_options

    @Property(str, notify=selectedRiskProfileChanged)
    def selectedRiskProfile(self) -> str:
        return self._selected_risk_profile

    @Property(float, notify=maxSingleWeightChanged)
    def maxSingleWeight(self) -> float:
        return self._max_single_weight

    @Property(float, notify=riskFreeRateChanged)
    def riskFreeRate(self) -> float:
        return self._risk_free_rate

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(bool, notify=hasResultsChanged)
    def hasResults(self) -> bool:
        return self._has_results

    @Property(int, notify=activeTabChanged)
    def activeTab(self) -> int:
        return self._active_tab

    @Property(str, notify=statusMessageChanged)
    def statusMessage(self) -> str:
        return self._status_message

    @Property(str, notify=chartHtmlChanged)
    def chartHtml(self) -> str:
        return self._chart_html

    @Property(str, notify=weightsChartHtmlChanged)
    def weightsChartHtml(self) -> str:
        return self._weights_chart_html

    @Property(list, notify=suggestionsChanged)
    def suggestions(self) -> list:
        return self._suggestions

    # --- KPI Properties ---

    @Property(str, notify=kpiMetricsChanged)
    def optimalSharpeFormatted(self) -> str:
        return f"{self._opt_sharpe:.2f}".replace(".", ",")

    @Property(str, notify=kpiMetricsChanged)
    def currentSharpeFormatted(self) -> str:
        return f"{self._curr_sharpe:.2f}".replace(".", ",")

    @Property(str, notify=kpiMetricsChanged)
    def optimalReturnFormatted(self) -> str:
        return _fmt_pct(self._opt_return * 100)

    @Property(str, notify=kpiMetricsChanged)
    def currentReturnFormatted(self) -> str:
        return _fmt_pct(self._curr_return * 100)

    @Property(str, notify=kpiMetricsChanged)
    def optimalVolFormatted(self) -> str:
        return _fmt_pct(self._opt_vol * 100)

    @Property(str, notify=kpiMetricsChanged)
    def currentVolFormatted(self) -> str:
        return _fmt_pct(self._curr_vol * 100)

    @Property(str, notify=kpiMetricsChanged)
    def minVolFormatted(self) -> str:
        return _fmt_pct(self._min_vol_vol * 100)

    @Property(bool, notify=kpiMetricsChanged)
    def isOptimalReturnPositive(self) -> bool:
        return self._opt_return >= 0

    @Property(bool, notify=kpiMetricsChanged)
    def isCurrentReturnPositive(self) -> bool:
        return self._curr_return >= 0

    @Property(bool, notify=kpiMetricsChanged)
    def isOptimalSharpePositive(self) -> bool:
        return self._opt_sharpe >= 0

    # ──────────────────────────── QML Slots ────────────────────────────

    @Slot()
    def refreshPortfolios(self) -> None:
        """Kullanılabilir portföyleri (Ana Portföy + Model Portföyler) yükler."""
        options = [{"code": "dashboard", "label": "Ana Portföy (Canlı)"}]
        if self._model_portfolio_service:
            try:
                models = self._model_portfolio_service.get_all_portfolios()
                for mp in models:
                    options.append({"code": str(mp.id), "label": f"Model: {mp.name}"})
            except Exception as e:
                logger.warning("Model portföyler yüklenemedi: %s", e)
        self._portfolio_options = options
        self.portfolioOptionsChanged.emit()

    @Slot(str)
    def selectPortfolio(self, code: str) -> None:
        if self._selected_portfolio_code != code:
            self._selected_portfolio_code = code

    @Slot()
    def reloadRiskProfile(self) -> None:
        """Kayıtlı risk profili (anket sonucu) değiştiğinde seçimi ve ağırlık kısıtını günceller."""
        if not self._risk_profile_service:
            return
        try:
            prof = self._risk_profile_service.get_current_profile()
        except Exception as exc:
            logger.debug("Risk profili okunamadı: %s", exc)
            return
        if prof and prof.risk_label in [r["code"] for r in self._risk_profile_options]:
            self._selected_risk_profile = ""  # aynı koda dönse bile kısıt ve combo yenilensin
            self.selectRiskProfile(prof.risk_label)

    @Slot(str)
    def selectRiskProfile(self, profile_code: str) -> None:
        if self._selected_risk_profile != profile_code:
            self._selected_risk_profile = profile_code
            self.selectedRiskProfileChanged.emit()

            # Profil seçildiğinde max ağırlık kısıtını otomatik güncelle
            matched = next((r for r in self._risk_profile_options if r["code"] == profile_code), None)
            if matched and profile_code != "MANUAL":
                self._max_single_weight = float(matched["maxWeight"])
                self.maxSingleWeightChanged.emit()

    @Slot(float)
    def setMaxSingleWeight(self, weight: float) -> None:
        val = max(5.0, min(100.0, float(weight)))
        if abs(self._max_single_weight - val) > 0.01:
            self._max_single_weight = val
            self.maxSingleWeightChanged.emit()
            if self._selected_risk_profile != "MANUAL":
                self._selected_risk_profile = "MANUAL"
                self.selectedRiskProfileChanged.emit()

    @Slot(float)
    def setRiskFreeRate(self, rate: float) -> None:
        val = max(0.0, min(100.0, float(rate)))
        if abs(self._risk_free_rate - val) > 0.01:
            self._risk_free_rate = val
            self.riskFreeRateChanged.emit()

    @Slot(int)
    def setActiveTab(self, tab_index: int) -> None:
        if self._active_tab != tab_index:
            self._active_tab = tab_index
            self.activeTabChanged.emit()

    @Slot()
    def runOptimization(self) -> None:
        """Optimizasyonu ve Monte Carlo simülasyonunu arka plan iş parçacığında çalıştırır."""
        if self._is_loading:
            return

        self._is_loading = True
        self._status_message = "Optimizasyon hesaplanıyor..."
        self.isLoadingChanged.emit()
        self.statusMessageChanged.emit()

        # Asenkron Worker
        self._executor.submit(
            self._async_compute_optimization,
            self._selected_portfolio_code,
            self._max_single_weight / 100.0,
            self._risk_free_rate / 100.0,
        )

    # ──────────────────────────── Worker Metodları ────────────────────────────

    def _async_compute_optimization(
        self,
        portfolio_code: str,
        max_single_weight: float,
        risk_free_rate: float,
    ) -> None:
        try:
            services = OptimizationServices(
                self._opt_service, self._portfolio_service, self._model_portfolio_service, self._lookup
            )
            payload = compute_optimization(services, portfolio_code, max_single_weight, risk_free_rate)
            self._calcFinished.emit(payload)
        except OptimizationInputError as exc:
            self._calcError.emit(str(exc))
        except Exception as exc:
            logger.exception("Optimizasyon hesaplama hatası: %s", exc)
            self._calcError.emit(str(exc))

    def _on_calc_finished(self, payload: dict) -> None:
        """Worker tamamlandığında GUI ana thread'inde çalışır."""
        self._apply_kpis(payload["opt_result"], payload["min_vol_metrics"])
        self._apply_tables(payload["rebalance_plan"])
        self._render_charts(payload["mc_points"], payload["frontier_curve"])

        self._is_loading = False
        self._has_results = True
        self._status_message = "Optimizasyon başarıyla tamamlandı."

        self.isLoadingChanged.emit()
        self.hasResultsChanged.emit()
        self.statusMessageChanged.emit()
        self.kpiMetricsChanged.emit()
        self.suggestionsChanged.emit()
        self.chartHtmlChanged.emit()
        self.weightsChartHtmlChanged.emit()
        self.operationResult.emit(True, "Portföy optimizasyonu başarıyla tamamlandı.")

    def _apply_kpis(self, opt_res, min_vol) -> None:
        self._curr_sharpe = float(opt_res.current_metrics.sharpe_ratio)
        self._curr_return = float(opt_res.current_metrics.expected_return)
        self._curr_vol = float(opt_res.current_metrics.volatility)

        self._opt_sharpe = float(opt_res.optimized_metrics.sharpe_ratio)
        self._opt_return = float(opt_res.optimized_metrics.expected_return)
        self._opt_vol = float(opt_res.optimized_metrics.volatility)

        self._min_vol_vol = float(min_vol.volatility)
        self._min_vol_return = float(min_vol.expected_return)

    def _apply_tables(self, rebalance_plan: List[Dict[str, Any]]) -> None:
        self._suggestions = rebalance_plan
        self._weights_comparison = [
            {
                "symbol": clean_ticker(str(item["symbol"])),
                "currentWeight": item["currentWeight"],
                "optimalWeight": item["optimalWeight"],
            }
            for item in rebalance_plan
        ]

    def _render_charts(self, mc_points: List[Dict[str, float]], frontier_curve: List[Dict[str, float]]) -> None:
        curr_pt = {"x": round(self._curr_vol * 100.0, 2), "y": round(self._curr_return * 100.0, 2)}
        opt_pt = {"x": round(self._opt_vol * 100.0, 2), "y": round(self._opt_return * 100.0, 2)}
        min_vol_pt = {"x": round(self._min_vol_vol * 100.0, 2), "y": round(self._min_vol_return * 100.0, 2)}

        self._chart_html = build_frontier_chart_html(
            mc_points=mc_points,
            frontier_curve=frontier_curve,
            curr_pt=curr_pt,
            opt_pt=opt_pt,
            min_vol_pt=min_vol_pt,
        )
        self._weights_chart_html = build_weights_chart_html(self._weights_comparison)

    def _on_calc_error(self, err_msg: str) -> None:
        self._is_loading = False
        self._status_message = err_msg
        self.isLoadingChanged.emit()
        self.statusMessageChanged.emit()
        self.operationResult.emit(False, err_msg)
