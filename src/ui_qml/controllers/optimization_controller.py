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

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PySide6.QtCore import Property, QObject, Signal, Slot

from src.application.services.planning.frontier_simulation import (
    calculate_efficient_frontier_curve,
    calculate_rebalance_plan,
    simulate_monte_carlo,
)
from src.application.services.planning.optimization_market_data import OptimizationPolicy
from src.application.services.planning.optimization_service import _build_return_model
from src.domain.models.risk_profile import PROFILE_INFO, RiskLabel

logger = logging.getLogger(__name__)

_JS_DIR = Path(__file__).resolve().parent.parent / "assets" / "js"
_CHART_JS: str = ""


def _load_embedded_scripts() -> None:
    global _CHART_JS
    if not _CHART_JS:
        chart_file = _JS_DIR / "chart.umd.min.js"
        if chart_file.exists():
            try:
                _CHART_JS = chart_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("chart.umd.min.js script okunamadı: %s", e)


def _fmt_money(val: float | Decimal | None) -> str:
    if val is None:
        return "0,00 ₺"
    try:
        return f"{float(val):,.2f} ₺".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return f"{val} ₺"


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
    selectedPortfolioChanged = Signal()
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
        self._stock_repo = getattr(container, "stock_repo", None)
        self._risk_profile_service = getattr(container, "risk_profile_service", None)

        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="OptWorker")

        # Worker sinyal bağlantıları
        self._calcFinished.connect(self._on_calc_finished)
        self._calcError.connect(self._on_calc_error)

        # Durum Değişkenleri
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

        # Risk Profili Seçenekleri
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

        self.refreshPortfolios()

    # ──────────────────────────── QML Properties ────────────────────────────

    @Property(list, notify=portfolioOptionsChanged)
    def portfolioOptions(self) -> list:
        return self._portfolio_options

    @Property(str, notify=selectedPortfolioChanged)
    def selectedPortfolioCode(self) -> str:
        return self._selected_portfolio_code

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

    @Property(list, notify=suggestionsChanged)
    def weightsComparison(self) -> list:
        return self._weights_comparison

    # --- KPI Properties ---

    @Property(float, notify=kpiMetricsChanged)
    def optimalSharpe(self) -> float:
        return round(self._opt_sharpe, 2)

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
            self.selectedPortfolioChanged.emit()

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
            if not self._opt_service:
                self._calcError.emit("OptimizationService hazır değil.")
                return

            policy = OptimizationPolicy(
                trading_days_per_year=252,
                risk_free_rate=risk_free_rate,
                max_single_weight=max_single_weight,
            )

            # 1. Hisseleri ve Pozisyonları Çek
            positions: Dict[int, Any] = {}
            total_val: float = 0.0

            if portfolio_code == "dashboard":
                if not self._portfolio_service:
                    self._calcError.emit("PortfolioService bulunamadı.")
                    return
                current_p = self._portfolio_service.get_current_portfolio()
                positions = current_p.active_positions
                if len(positions) < 2:
                    self._calcError.emit("Optimizasyon için portföyde en az 2 farklı hisse bulunmalıdır.")
                    return
                # Toplam piyasa değeri
                for sid, pos in positions.items():
                    price = float(pos.average_cost or 1.0)
                    total_val += pos.total_quantity * price

                opt_result = self._opt_service.optimize_dashboard_portfolio(policy=policy)
            else:
                if not self._model_portfolio_service:
                    self._calcError.emit("ModelPortfolioService bulunamadı.")
                    return
                pid = int(portfolio_code)
                positions = self._model_portfolio_service.get_positions(pid)
                if len(positions) < 2:
                    self._calcError.emit("Optimizasyon için model portföyde en az 2 farklı hisse bulunmalıdır.")
                    return
                for sid, qty in positions.items():
                    total_val += qty * 100.0  # Yaklaşık baz değer

                opt_result = self._opt_service.optimize_model_portfolio(pid, policy=policy)

            # 2. Hisse Sembolleri ve İsimlerini Al
            stock_ids = list(positions.keys())
            stocks = self._stock_repo.get_stocks_by_ids(stock_ids) if self._stock_repo else []
            stock_map = {s.id: s for s in stocks}
            tickers = [stock_map[sid].ticker for sid in stock_ids if sid in stock_map]
            names_map = {stock_map[sid].ticker: getattr(stock_map[sid], "name", stock_map[sid].ticker) for sid in stock_ids if sid in stock_map}

            # 3. Fiyat Geçmişi ve Kovaryans Matrisi
            price_df = self._opt_service._get_historical_prices(tickers, days=504)
            mean_returns, cov_matrix = _build_return_model(price_df, trading_days_per_year=252)

            # 4. Monte Carlo Simülasyonu (1.000 Nokta)
            mc_points = simulate_monte_carlo(
                mean_returns.values,
                cov_matrix.values,
                risk_free_rate=risk_free_rate,
                num_simulations=1000,
            )

            # 5. Efficient Frontier Eğrisi (20 Nokta)
            frontier_curve = calculate_efficient_frontier_curve(
                mean_returns.values,
                cov_matrix.values,
                max_single_weight=max_single_weight,
                points_count=20,
            )

            # 6. Rebalance Planı ve Son Fiyatlar
            last_prices = {}
            for t in tickers:
                p = self._opt_service._get_last_price(t)
                last_prices[t] = float(p) if p else 1.0

            curr_w_map = {s.symbol: s.current_weight for s in opt_result.suggestions}
            opt_w_map = {s.symbol: s.optimal_weight for s in opt_result.suggestions}

            rebalance_plan = calculate_rebalance_plan(
                total_portfolio_value=total_val if total_val > 0 else 100000.0,
                current_weights=curr_w_map,
                optimal_weights=opt_w_map,
                last_prices=last_prices,
                stock_names=names_map,
            )

            # 7. Payload Hazırla
            min_vol_metrics = opt_result.min_volatility_metrics or opt_result.optimized_metrics
            payload = {
                "opt_result": opt_result,
                "mc_points": mc_points,
                "frontier_curve": frontier_curve,
                "rebalance_plan": rebalance_plan,
                "min_vol_metrics": min_vol_metrics,
            }
            self._calcFinished.emit(payload)

        except Exception as exc:
            logger.exception("Optimizasyon hesaplama hatası: %s", exc)
            self._calcError.emit(str(exc))

    def _on_calc_finished(self, payload: dict) -> None:
        """Worker tamamlandığında GUI ana thread'inde çalışır."""
        opt_res = payload["opt_result"]
        min_vol = payload["min_vol_metrics"]
        mc_points = payload["mc_points"]
        frontier_curve = payload["frontier_curve"]
        rebalance_plan = payload["rebalance_plan"]

        # KPI'lar
        self._curr_sharpe = float(opt_res.current_metrics.sharpe_ratio)
        self._curr_return = float(opt_res.current_metrics.expected_return)
        self._curr_vol = float(opt_res.current_metrics.volatility)

        self._opt_sharpe = float(opt_res.optimized_metrics.sharpe_ratio)
        self._opt_return = float(opt_res.optimized_metrics.expected_return)
        self._opt_vol = float(opt_res.optimized_metrics.volatility)

        self._min_vol_vol = float(min_vol.volatility)
        self._min_vol_return = float(min_vol.expected_return)

        # Tablolar
        self._suggestions = rebalance_plan
        self._weights_comparison = [
            {
                "symbol": item["symbol"],
                "currentWeight": item["currentWeight"],
                "optimalWeight": item["optimalWeight"],
            }
            for item in rebalance_plan
        ]

        # Grafikler HTML Üretimi
        curr_pt = {"x": round(self._curr_vol * 100.0, 2), "y": round(self._curr_return * 100.0, 2)}
        opt_pt = {"x": round(self._opt_vol * 100.0, 2), "y": round(self._opt_return * 100.0, 2)}
        min_vol_pt = {"x": round(self._min_vol_vol * 100.0, 2), "y": round(self._min_vol_return * 100.0, 2)}

        self._chart_html = self._build_frontier_chart_html(
            mc_points=mc_points,
            frontier_curve=frontier_curve,
            curr_pt=curr_pt,
            opt_pt=opt_pt,
            min_vol_pt=min_vol_pt,
        )

        self._weights_chart_html = self._build_weights_chart_html(self._weights_comparison)

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

    def _on_calc_error(self, err_msg: str) -> None:
        self._is_loading = False
        self._status_message = err_msg
        self.isLoadingChanged.emit()
        self.statusMessageChanged.emit()
        self.operationResult.emit(False, err_msg)

    # ──────────────────────────── HTML Grafik Üreticileri ────────────────────────────

    def _build_frontier_chart_html(
        self,
        mc_points: List[Dict[str, float]],
        frontier_curve: List[Dict[str, float]],
        curr_pt: Dict[str, float],
        opt_pt: Dict[str, float],
        min_vol_pt: Dict[str, float],
    ) -> str:
        """Verimli Sınır (Efficient Frontier) ve Monte Carlo saçılım grafiği HTML5/Chart.js."""
        _load_embedded_scripts()
        script_tag = f"<script>{_CHART_JS}</script>" if _CHART_JS else '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'

        mc_json = json.dumps(mc_points)
        frontier_json = json.dumps(frontier_curve)

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{script_tag}
<style>
  body {{ margin: 0; padding: 12px; background: #131722; color: #9db2ce; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; overflow: hidden; }}
  #chart-container {{ width: 100%; height: calc(100vh - 24px); position: relative; }}
</style>
</head>
<body>
<div id="chart-container">
  <canvas id="frontierCanvas"></canvas>
</div>
<script>
const mcData = {mc_json};
const frontierData = {frontier_json};

const ctx = document.getElementById('frontierCanvas').getContext('2d');
new Chart(ctx, {{
  type: 'scatter',
  data: {{
    datasets: [
      {{
        label: 'Monte Carlo (1.000 Nokta)',
        data: mcData,
        backgroundColor: 'rgba(41, 98, 255, 0.25)',
        borderColor: 'transparent',
        pointRadius: 2,
        pointHoverRadius: 4,
        order: 5
      }},
      {{
        label: 'Verimli Sınır',
        data: frontierData,
        type: 'line',
        borderColor: '#00e676',
        backgroundColor: 'transparent',
        borderWidth: 3,
        pointRadius: 0,
        tension: 0.35,
        fill: false,
        order: 2
      }},
      {{
        label: 'Maksimum Sharpe',
        data: [{{ x: {opt_pt["x"]}, y: {opt_pt["y"]} }}],
        backgroundColor: '#00e676',
        borderColor: '#ffffff',
        borderWidth: 2,
        pointRadius: 9,
        pointHoverRadius: 13,
        pointStyle: 'circle',
        order: 1
      }},
      {{
        label: 'Minimum Risk',
        data: [{{ x: {min_vol_pt["x"]}, y: {min_vol_pt["y"]} }}],
        backgroundColor: '#00b0ff',
        borderColor: '#ffffff',
        borderWidth: 2,
        pointRadius: 8,
        pointHoverRadius: 12,
        pointStyle: 'triangle',
        order: 1
      }},
      {{
        label: 'Mevcut Portföy',
        data: [{{ x: {curr_pt["x"]}, y: {curr_pt["y"]} }}],
        backgroundColor: '#ff9800',
        borderColor: '#ffffff',
        borderWidth: 2,
        pointRadius: 9,
        pointHoverRadius: 13,
        pointStyle: 'rectRot',
        order: 1
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    layout: {{
      padding: {{ left: 16, right: 20, top: 10, bottom: 10 }}
    }},
    interaction: {{
      mode: 'nearest',
      intersect: true
    }},
    plugins: {{
      legend: {{
        position: 'top',
        align: 'center',
        labels: {{
          color: '#9db2ce',
          font: {{ family: 'Segoe UI', size: 11 }},
          usePointStyle: true,
          boxWidth: 7,
          padding: 12
        }}
      }},
      tooltip: {{
        backgroundColor: '#1e222d',
        titleColor: '#ffffff',
        bodyColor: '#9db2ce',
        borderColor: '#2a2e39',
        borderWidth: 1,
        padding: 10,
        callbacks: {{
          label: function(context) {{
            const p = context.raw;
            function fmtPct(val) {{
              if (val === null || val === undefined || isNaN(val)) return '%0,00';
              const num = Number(val);
              const str = Math.abs(num).toFixed(2).replace('.', ',');
              if (num < 0) return '-%' + str;
              return '%' + str;
            }}
            let str = context.dataset.label + ': ';
            str += 'Risk: ' + fmtPct(p.x) + ' | Getiri: ' + fmtPct(p.y);
            if (p.sharpe !== undefined) {{
              str += ' | Sharpe: ' + Number(p.sharpe).toFixed(2).replace('.', ',');
            }}
            return str;
          }}
        }}
      }}
    }},
    scales: {{
      x: {{
        title: {{
          display: true,
          text: 'Yıllık Volatilite (Oynaklık / Risk %)',
          color: '#9db2ce',
          font: {{ size: 12, weight: 'bold' }}
        }},
        grid: {{ color: '#1e222d' }},
        ticks: {{ color: '#9db2ce' }}
      }},
      y: {{
        title: {{
          display: true,
          text: 'Beklenen Yıllık Getiri (%)',
          color: '#9db2ce',
          font: {{ size: 12, weight: 'bold' }}
        }},
        grid: {{ color: '#1e222d' }},
        ticks: {{ color: '#9db2ce' }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""

    def _build_weights_chart_html(self, comparison: List[Dict[str, Any]]) -> str:
        """Mevcut vs Optimize Ağırlık Karşılaştırması Çubuk Grafiği HTML5/Chart.js."""
        _load_embedded_scripts()
        script_tag = f"<script>{_CHART_JS}</script>" if _CHART_JS else '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'

        labels = [item["symbol"] for item in comparison]
        curr_weights = [item["currentWeight"] for item in comparison]
        opt_weights = [item["optimalWeight"] for item in comparison]

        labels_json = json.dumps(labels)
        curr_json = json.dumps(curr_weights)
        opt_json = json.dumps(opt_weights)

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{script_tag}
<style>
  body {{ margin: 0; padding: 12px; background: #131722; color: #9db2ce; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; overflow: hidden; }}
  #weights-container {{ width: 100%; height: calc(100vh - 24px); position: relative; }}
</style>
</head>
<body>
<div id="weights-container">
  <canvas id="weightsCanvas"></canvas>
</div>
<script>
const ctx = document.getElementById('weightsCanvas').getContext('2d');
new Chart(ctx, {{
  type: 'bar',
  data: {{
    labels: {labels_json},
    datasets: [
      {{
        label: 'Mevcut Ağırlık',
        data: {curr_json},
        backgroundColor: '#ff9800',
        borderRadius: 4,
        barPercentage: 0.75,
        categoryPercentage: 0.65
      }},
      {{
        label: 'Önerilen Optimal Ağırlık',
        data: {opt_json},
        backgroundColor: '#00e676',
        borderRadius: 4,
        barPercentage: 0.75,
        categoryPercentage: 0.65
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    layout: {{
      padding: {{ left: 16, right: 20, top: 10, bottom: 10 }}
    }},
    plugins: {{
      legend: {{
        position: 'top',
        align: 'center',
        labels: {{
          color: '#9db2ce',
          font: {{ family: 'Segoe UI', size: 11 }},
          usePointStyle: true,
          boxWidth: 8,
          padding: 12
        }}
      }},
      tooltip: {{
        backgroundColor: '#1e222d',
        titleColor: '#ffffff',
        bodyColor: '#9db2ce',
        borderColor: '#2a2e39',
        borderWidth: 1,
        padding: 10,
        callbacks: {{
          label: function(context) {{
            const v = Number(context.raw);
            const str = v.toFixed(2).replace('.', ',');
            return context.dataset.label + ': %' + str;
          }}
        }}
      }}
    }},
    scales: {{
      x: {{
        grid: {{ color: '#1e222d' }},
        ticks: {{ color: '#9db2ce' }}
      }},
      y: {{
        title: {{
          display: true,
          text: 'Portföy Ağırlığı (%)',
          color: '#9db2ce',
          font: {{ size: 12, weight: 'bold' }}
        }},
        grid: {{ color: '#1e222d' }},
        ticks: {{ color: '#9db2ce' }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""
