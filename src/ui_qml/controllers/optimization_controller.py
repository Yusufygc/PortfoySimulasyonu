"""
OptimizationController — OptimizationView'un veri köprüsü (bkz. plan §7.3
madde 5, d5). Markowitz optimizasyonunu (`OptimizationService`, mevcut
QtWidgets `OptimizationPage` ile aynı backend) risk profili köprüsü üzerinden
(`RiskOptimizationBridgeService`, §5.3'te kurulmuştu) QML'e bağlar.

Kapsam notları (plan aslıyla karşılaştırıldığında dürüstçe belirtilen farklar):
* "Hisse bazında min/max ağırlık kısıtları (%5-%25)" — backend yalnızca TEK bir
  global tek-hisse üst sınırı destekliyor (`OptimizationPolicy.max_single_weight`,
  risk etiketine göre belirleniyor); hisse-bazlı ayrı min/max kısıtı YOK, icat
  edilmedi. Slider bu tek global üst sınırı (risk etiketi üzerinden) kontrol eder.
* "Risk Profili Belirteci (slider)" — slider'ın seçtiği etiket kayıtlı anket
  profilini DEĞİŞTİRMEZ/KAYDETMEZ; sadece bu görünüm için geçici bir `policy`
  override'ı üretir (`risk_label_override`, bkz. bridge service). Kayıtlı profil
  varsa slider başlangıçta ona göre konumlanır.
* "Verimli Sınır (Efficient Frontier) Grafiği" — tam bir sınır eğrisi (çok
  noktalı tarama) DEĞİL, üç nokta: Mevcut / Minimum Risk / Maksimum Sharpe
  (backend'in ürettiği tek 3 nokta budur, bkz. `OptimizationResult.
  min_volatility_metrics` — bu adımda eklendi). `ScatterChartItem` (d4'te
  yazılmıştı) yeniden kullanılıyor, yeni bir chart tipi gerekmedi.

Model portföy optimizasyonunda `price_lookup_func=None` geçilir (mevcut DB
fiyatına düşer) — canlı API'ye bağımlılık eklenmez (§9.6 ilkesiyle tutarlı,
Screener/Watchlist controller'larıyla aynı "sadece yerel DB" ilkesi).
"""
from __future__ import annotations

from typing import Any, List, Optional

from src.qt_compat.qtcore import Property, QObject, Signal, Slot
from src.application.services.planning.risk_optimization_bridge_service import RISK_LABELS_ORDERED
from src.domain.models.optimization_result import OptimizationMetrics
from src.ui.formatters import RiskFormatter

_SOURCE_DASHBOARD = "dashboard"


def _to_float(value: Any) -> float:
    return float(value) if value is not None else 0.0


def _empty_metrics() -> OptimizationMetrics:
    return OptimizationMetrics(expected_return=0.0, volatility=0.0, sharpe_ratio=0.0)


class OptimizationController(QObject):
    """Markowitz optimizasyonu: kaynak seçimi + risk slider + verimli sınır + öneri tablosu."""

    sourcesChanged = Signal()
    sliderIndexChanged = Signal()
    resultChanged = Signal()

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self._container = container

        self._source_labels: List[str] = []
        self._source_codes: List[str] = []
        self._selected_source_code = _SOURCE_DASHBOARD

        self._slider_index = self._default_slider_index()
        self._slider_touched = False  # kullanıcı slider'ı henüz elle değiştirmedi

        self._has_result = False
        self._error_message = ""
        self._active_risk_label_display = ""
        self._used_default_profile = True
        self._is_manual_override = False
        self._max_single_weight_pct = 0.0
        self._equity_ceiling_pct = -1.0

        self._current = _empty_metrics()
        self._optimized = _empty_metrics()
        self._min_vol = _empty_metrics()

        self._suggestion_tickers: List[str] = []
        self._suggestion_current_weight_pct: List[float] = []
        self._suggestion_optimal_weight_pct: List[float] = []
        self._suggestion_change_pct: List[float] = []
        self._suggestion_actions: List[str] = []

        self._load_sources()
        self.runOptimization()

    # ------------------------------------------------------------------
    # Kaynak seçimi (Dashboard / Model Portföyleri)
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=sourcesChanged)
    def sourceLabels(self) -> List[str]:
        return list(self._source_labels)

    @Slot(int)
    def selectSourceByIndex(self, index: int) -> None:
        if 0 <= index < len(self._source_codes):
            self._selected_source_code = self._source_codes[index]

    def _load_sources(self) -> None:
        labels = ["Dashboard Portföyü"]
        codes = [_SOURCE_DASHBOARD]
        try:
            for portfolio in self._container.optimization_service.get_model_portfolios():
                labels.append(portfolio.name)
                codes.append(f"model:{portfolio.id}")
        except Exception:
            pass
        self._source_labels = labels
        self._source_codes = codes
        self.sourcesChanged.emit()

    # ------------------------------------------------------------------
    # Risk Profili Slider'ı (Muhafazakar -> Agresif)
    # ------------------------------------------------------------------

    @Property("QVariantList", constant=True)
    def riskLabelDisplayNames(self) -> List[str]:
        return [RiskFormatter.get_display_name(label) for label in RISK_LABELS_ORDERED]

    @Property(int, notify=sliderIndexChanged)
    def sliderIndex(self) -> int:
        return self._slider_index

    @Slot(int)
    def setSliderIndex(self, index: int) -> None:
        clamped = max(0, min(len(RISK_LABELS_ORDERED) - 1, index))
        self._slider_touched = True
        if clamped != self._slider_index:
            self._slider_index = clamped
            self.sliderIndexChanged.emit()

    def _default_slider_index(self) -> int:
        bridge = self._container.risk_optimization_bridge_service
        profile = bridge.get_active_risk_profile()
        risk_label = profile.risk_label if profile is not None else None
        if risk_label in RISK_LABELS_ORDERED:
            return RISK_LABELS_ORDERED.index(risk_label)
        return RISK_LABELS_ORDERED.index("DENGELI")

    # ------------------------------------------------------------------
    # Uygulanan politika bilgisi
    # ------------------------------------------------------------------

    @Property(str, notify=resultChanged)
    def activeRiskLabelDisplay(self) -> str:
        return self._active_risk_label_display

    @Property(bool, notify=resultChanged)
    def usedDefaultProfile(self) -> bool:
        return self._used_default_profile

    @Property(bool, notify=resultChanged)
    def isManualOverride(self) -> bool:
        return self._is_manual_override

    @Property(float, notify=resultChanged)
    def maxSingleWeightPct(self) -> float:
        return self._max_single_weight_pct

    @Property(float, notify=resultChanged)
    def equityCeilingPct(self) -> float:
        """`-1.0` = bilgi yok (bkz. `RiskAwareOptimizationResult.equity_ceiling_pct is None`)."""
        return self._equity_ceiling_pct

    # ------------------------------------------------------------------
    # Sonuç: hata / boş durum
    # ------------------------------------------------------------------

    @Property(bool, notify=resultChanged)
    def hasResult(self) -> bool:
        return self._has_result

    @Property(str, notify=resultChanged)
    def errorMessage(self) -> str:
        return self._error_message

    # ------------------------------------------------------------------
    # 3 Metrik Kartı (Mevcut / Optimal) + Verimli Sınır'ın 3 Noktası
    # ------------------------------------------------------------------

    @Property(float, notify=resultChanged)
    def currentReturnPct(self) -> float:
        return self._current.expected_return * 100.0

    @Property(float, notify=resultChanged)
    def currentVolatilityPct(self) -> float:
        return self._current.volatility * 100.0

    @Property(float, notify=resultChanged)
    def currentSharpe(self) -> float:
        return self._current.sharpe_ratio

    @Property(float, notify=resultChanged)
    def optimizedReturnPct(self) -> float:
        return self._optimized.expected_return * 100.0

    @Property(float, notify=resultChanged)
    def optimizedVolatilityPct(self) -> float:
        return self._optimized.volatility * 100.0

    @Property(float, notify=resultChanged)
    def optimizedSharpe(self) -> float:
        return self._optimized.sharpe_ratio

    @Property(float, notify=resultChanged)
    def minVolatilityReturnPct(self) -> float:
        return self._min_vol.expected_return * 100.0

    @Property(float, notify=resultChanged)
    def minVolatilityVolatilityPct(self) -> float:
        return self._min_vol.volatility * 100.0

    @Property(float, notify=resultChanged)
    def minVolatilitySharpe(self) -> float:
        return self._min_vol.sharpe_ratio

    @Property("QVariantList", notify=resultChanged)
    def frontierLabels(self) -> List[str]:
        return ["Mevcut", "Min. Risk", "Maks. Sharpe"]

    @Property("QVariantList", notify=resultChanged)
    def frontierVolatilityPct(self) -> List[float]:
        return [self.currentVolatilityPct, self.minVolatilityVolatilityPct, self.optimizedVolatilityPct]

    @Property("QVariantList", notify=resultChanged)
    def frontierReturnPct(self) -> List[float]:
        return [self.currentReturnPct, self.minVolatilityReturnPct, self.optimizedReturnPct]

    # ------------------------------------------------------------------
    # Önerilen Değişiklik Tablosu
    # ------------------------------------------------------------------

    @Property("QVariantList", notify=resultChanged)
    def suggestionTickers(self) -> List[str]:
        return list(self._suggestion_tickers)

    @Property("QVariantList", notify=resultChanged)
    def suggestionCurrentWeightPct(self) -> List[float]:
        return list(self._suggestion_current_weight_pct)

    @Property("QVariantList", notify=resultChanged)
    def suggestionOptimalWeightPct(self) -> List[float]:
        return list(self._suggestion_optimal_weight_pct)

    @Property("QVariantList", notify=resultChanged)
    def suggestionChangePct(self) -> List[float]:
        return list(self._suggestion_change_pct)

    @Property("QVariantList", notify=resultChanged)
    def suggestionActions(self) -> List[str]:
        return list(self._suggestion_actions)

    # ------------------------------------------------------------------
    # Optimizasyonu Çalıştır
    # ------------------------------------------------------------------

    @Slot()
    def runOptimization(self) -> None:
        bridge = self._container.risk_optimization_bridge_service
        # Slider hiç dokunulmadıysa override GEÇİLMEZ — kayıtlı anket profili (varsa)
        # doğal haliyle uygulanır; `isManualOverride` sadece gerçek bir kullanıcı
        # etkileşiminden sonra True olur (bkz. sınıf docstring'i).
        risk_label_override = RISK_LABELS_ORDERED[self._slider_index] if self._slider_touched else None

        try:
            if self._selected_source_code == _SOURCE_DASHBOARD:
                outcome = bridge.optimize_dashboard_portfolio_with_risk_profile(
                    risk_label_override=risk_label_override,
                )
            else:
                portfolio_id = int(self._selected_source_code.split(":", 1)[1])
                outcome = bridge.optimize_model_portfolio_with_risk_profile(
                    portfolio_id=portfolio_id,
                    price_lookup_func=None,
                    risk_label_override=risk_label_override,
                )
        except Exception as exc:
            self._has_result = False
            self._error_message = str(exc)
            self.resultChanged.emit()
            return

        self._apply_outcome(outcome)

    def _apply_outcome(self, outcome) -> None:
        result = outcome.result
        self._current = result.current_metrics
        self._optimized = result.optimized_metrics
        self._min_vol = result.min_volatility_metrics or _empty_metrics()

        self._active_risk_label_display = RiskFormatter.get_display_name(outcome.risk_label)
        self._used_default_profile = outcome.used_default_profile
        self._is_manual_override = outcome.is_manual_override
        self._max_single_weight_pct = outcome.max_single_weight_pct
        self._equity_ceiling_pct = float(outcome.equity_ceiling_pct) if outcome.equity_ceiling_pct is not None else -1.0

        self._suggestion_tickers = [s.symbol for s in result.suggestions]
        self._suggestion_current_weight_pct = [s.current_weight for s in result.suggestions]
        self._suggestion_optimal_weight_pct = [s.optimal_weight for s in result.suggestions]
        self._suggestion_change_pct = [s.change for s in result.suggestions]
        self._suggestion_actions = [s.action for s in result.suggestions]

        self._has_result = True
        self._error_message = ""
        self.resultChanged.emit()
