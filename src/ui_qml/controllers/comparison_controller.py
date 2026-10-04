"""
ComparisonController — Karşılaştırma Laboratuvarı QML controller'ı.

Sorumluluk:
- analysis_service.get_portfolio_options() ve get_benchmark_definitions() ile varlık listesi
- analysis_service.get_comparison_view(filter_state) ile çoklu portföy ve benchmark serisi
- Asenkron ThreadPoolExecutor ile UI bloklamayan akıcı hesaplama
- 3 Karşılaştırma Modu: Normal, Normalize (Baz 100), Rasyo (A / B)
- 4 Grafik Görünümü:
    1. Kümülatif Getiri (Normal / Normalize / Rasyo)
    2. Maksimum Değer Kaybı (Drawdown %)
    3. Aylık Dönemsel Getiriler (Bar Chart)
    4. Risk / Getiri Saçılımı (Scatter Plot)
- Risk-Getiri metrik tablosu (Toplam Getiri %, Yıllık Volatilite %)
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Any, Dict, List, Optional

import pandas as pd
from PySide6.QtCore import Property, QObject, Signal, Slot

from src.application.services.analysis.comparison_chart_series import ComparisonSeriesBuilder
from src.application.services.analysis.comparison_service import ComparisonService
from src.domain.models.ai_analysis import ChatMessage, MessageRole
from src.ui_qml.controllers.comparison_chart_html import (
    build_drawdown_html,
    build_line_chart_html,
    build_periodic_html,
    build_scatter_html,
    build_treemap_html,
    treemap_items_from_metrics,
)
from src.ui_qml.controllers.comparison_support import (
    build_commentary_prompt,
    build_filter_state,
    build_risk_return_metrics,
    fetch_portfolio_holdings,
    find_column,
    parse_date,
    resolve_range,
)

logger = logging.getLogger(__name__)


class ComparisonController(QObject):
    """QML context property: comparisonController"""

    # --- Signals ---
    assetOptionsChanged = Signal()
    selectedAssetsChanged = Signal()
    chartHtmlChanged = Signal()
    metricsListChanged = Signal()
    isLoadingChanged = Signal()
    periodLabelChanged = Signal()
    comparisonModeChanged = Signal()
    activeChartTabChanged = Signal()
    ratioAssetsChanged = Signal()
    treemapModeChanged = Signal()
    treemapPortfolioChanged = Signal()
    treemapPortfolioOptionsChanged = Signal()
    customRangeChanged = Signal()
    currencyModeChanged = Signal()
    aiCommentChanged = Signal()
    operationResult = Signal(bool, str, arguments=["success", "message"])

    # Worker Thread Signals (Qt QueuedConnection ile GUI ana thread'ine güvenli iletim)
    _calcFinished = Signal(object, object, object)
    _calcEmpty = Signal()
    _calcError = Signal(str)
    _aiFinished = Signal(str, str)  # (yorum, hata)

    def __init__(self, container, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._container = container
        self._analysis_service = container.analysis_service
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ComparisonWorker")
        self._executor_ai = ThreadPoolExecutor(max_workers=1, thread_name_prefix="ComparisonAI")

        # Worker sinyal bağlantıları (ana GUI thread'inde çalışır)
        self._calcFinished.connect(self._apply_calculation_result)
        self._calcEmpty.connect(self._apply_empty_result)
        self._calcError.connect(self._apply_error_result)
        self._aiFinished.connect(self._apply_ai_result)

        # State
        self._asset_options: List[Dict[str, str]] = []
        self._selected_codes: List[str] = ["dashboard", "bist100"]
        self._chart_html: str = ""
        self._metrics_list: List[Dict[str, Any]] = []
        self._is_loading: bool = False
        self._period_label: str = "3A"
        self._custom_start: str = ""
        self._custom_end: str = ""
        self._currency_mode: str = "TL"  # "TL", "USD", "REAL" (enflasyondan arındırılmış)
        self._ai_comment: str = ""
        self._ai_busy: bool = False
        self._last_range: tuple = (None, None)
        self._comparison_mode: str = "NORMALIZED"  # "NORMALIZED", "NORMAL", "RATIO"
        self._active_chart_tab: int = 0  # 0: Getiri, 1: Drawdown, 2: Aylık, 3: Saçılım, 4: Treemap
        self._ratio_numerator: str = "dashboard"
        self._ratio_denominator: str = "bist100"
        self._treemap_mode: str = "HOLDINGS"  # "HOLDINGS" (Portföy Hisseleri) | "ASSETS" (Seçilen Varlıklar)
        self._treemap_portfolio_code: str = "dashboard"
        self._treemap_portfolio_options: List[Dict[str, str]] = [{"code": "dashboard", "label": "Ana Portföy"}]

        # Cache of aligned data
        self._cached_aligned: Optional[pd.DataFrame] = None
        self._cached_labels: Dict[str, str] = {}

    # ──────────────────────────── QML Properties ────────────────────────────

    @Property(str, notify=treemapModeChanged)
    def treemapMode(self) -> str:
        return self._treemap_mode

    @Property(str, notify=treemapPortfolioChanged)
    def treemapPortfolio(self) -> str:
        return self._treemap_portfolio_code

    @Property(list, notify=treemapPortfolioOptionsChanged)
    def treemapPortfolioOptions(self) -> list:
        return self._treemap_portfolio_options

    @Property(list, notify=assetOptionsChanged)
    def assetOptions(self) -> list:
        return self._asset_options

    @Property(list, notify=selectedAssetsChanged)
    def selectedAssets(self) -> list:
        return self._selected_codes

    @Property(str, notify=chartHtmlChanged)
    def chartHtml(self) -> str:
        return self._chart_html

    @Property(list, notify=metricsListChanged)
    def metricsList(self) -> list:
        return self._metrics_list

    @Property(bool, notify=isLoadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    @Property(str, notify=periodLabelChanged)
    def periodLabel(self) -> str:
        return self._period_label

    @Property(str, notify=customRangeChanged)
    def customStart(self) -> str:
        return self._custom_start

    @Property(str, notify=customRangeChanged)
    def customEnd(self) -> str:
        return self._custom_end

    @Property(str, notify=currencyModeChanged)
    def currencyMode(self) -> str:
        return self._currency_mode

    @Property(str, notify=aiCommentChanged)
    def aiComment(self) -> str:
        return self._ai_comment

    @Property(bool, notify=aiCommentChanged)
    def aiBusy(self) -> bool:
        return self._ai_busy

    @Property(str, notify=comparisonModeChanged)
    def comparisonMode(self) -> str:
        return self._comparison_mode

    @Property(int, notify=activeChartTabChanged)
    def activeChartTab(self) -> int:
        return self._active_chart_tab

    @Property(str, notify=ratioAssetsChanged)
    def ratioNumerator(self) -> str:
        return self._ratio_numerator

    @Property(str, notify=ratioAssetsChanged)
    def ratioDenominator(self) -> str:
        return self._ratio_denominator

    # ──────────────────────────── QML Slots ────────────────────────────

    def _collect_asset_options(self) -> tuple:
        """Portföy (ana + model, hisseleriyle) ve benchmark seçeneklerini ve portföy listesini döndürür."""
        options: List[Dict[str, str]] = []
        portfolio_opts: List[Dict[str, str]] = []
        for p in self._analysis_service.get_portfolio_options():
            options.append({"code": p.code, "label": p.label, "kind": p.kind})
            options.append({"code": f"holdings:{p.code}", "label": f"{p.label} + Hisseleri", "kind": "HİSSELER"})
            portfolio_opts.append({"code": p.code, "label": p.label})
        for b in self._analysis_service.get_benchmark_definitions():
            options.append({"code": b.code, "label": b.label, "kind": b.kind})
        return options, portfolio_opts

    @Slot()
    def loadAssetOptions(self) -> None:
        """Portföy ve benchmark seçeneklerini yükler."""
        try:
            options, portfolio_opts = self._collect_asset_options()
            self._asset_options = options
            self.assetOptionsChanged.emit()

            if portfolio_opts:
                self._treemap_portfolio_options = portfolio_opts
                self.treemapPortfolioOptionsChanged.emit()

            valid_codes = {o["code"] for o in options}
            self._selected_codes = [c for c in self._selected_codes if c in valid_codes]
            if not self._selected_codes and options:
                self._selected_codes = [o["code"] for o in options[:2]]

            self.selectedAssetsChanged.emit()
        except Exception as exc:
            logger.exception("Varlık seçenekleri yüklenemedi: %s", exc)

    @Slot(str, bool)
    def toggleAsset(self, code: str, selected: bool) -> None:
        """Bir varlığı seçili listeye ekler veya çıkarır."""
        if selected and code not in self._selected_codes:
            self._selected_codes.append(code)
        elif not selected and code in self._selected_codes:
            self._selected_codes.remove(code)
        self.selectedAssetsChanged.emit()

    @Slot(str)
    def setPeriod(self, label: str) -> None:
        """Dönem butonundan seçim yapar."""
        self._period_label = label
        self.periodLabelChanged.emit()
        self.runComparison()

    @Slot(str, str, result=bool)
    def setCustomRange(self, start_text: str, end_text: str) -> bool:
        """Serbest tarih aralığı (GG.AA.YYYY veya YYYY-AA-GG) seçer ve karşılaştırmayı çalıştırır."""
        start, end = parse_date(start_text), parse_date(end_text)
        if start is None or end is None:
            self.operationResult.emit(False, "Tarih biçimi geçersiz. Biçim: GG.AA.YYYY")
            return False
        if start >= end:
            self.operationResult.emit(False, "Başlangıç tarihi bitiş tarihinden önce olmalıdır.")
            return False
        if end > date.today():
            end = date.today()
        self._custom_start = start.strftime("%d.%m.%Y")
        self._custom_end = end.strftime("%d.%m.%Y")
        self.customRangeChanged.emit()
        self._period_label = "ÖZEL"
        self.periodLabelChanged.emit()
        self.runComparison()
        return True

    @Slot(str)
    def setCurrencyMode(self, mode: str) -> None:
        """Para birimi modu: TL, USD veya REAL (enflasyondan arındırılmış)."""
        mode = mode.strip().upper()
        if mode in ("TL", "USD", "REAL") and mode != self._currency_mode:
            self._currency_mode = mode
            self.currencyModeChanged.emit()
            self.runComparison()

    @Slot()
    def generateAiComment(self) -> None:
        """Seçili varlıkların performans özetini Gemini ile yorumlatır (arka planda)."""
        chat_service = getattr(self._container, "ai_chat_service", None)
        if chat_service is None:
            self.operationResult.emit(False, "Yapay zeka servisi bulunamadı.")
            return
        if self._ai_busy:
            return
        if not self._metrics_list:
            self.operationResult.emit(False, "Analiz edilecek veri bulunamadı. Önce karşılaştırmayı çalıştırın.")
            return
        prompt = build_commentary_prompt(
            self._last_range, self._metrics_list, self._comparison_mode, self._currency_mode
        )
        self._ai_busy = True
        self._ai_comment = ""
        self.aiCommentChanged.emit()

        def work() -> None:
            try:
                text = chat_service.generate([ChatMessage(role=MessageRole.USER, content=prompt)])
                self._aiFinished.emit(text, "")
            except Exception as exc:
                logger.warning("Karşılaştırma AI yorumu üretilemedi: %s", exc)
                self._aiFinished.emit("", str(exc))

        self._executor_ai.submit(work)

    @Slot(str)
    def setComparisonMode(self, mode: str) -> None:
        """Karşılaştırma modunu ayarlar: NORMALIZED, NORMAL, RATIO."""
        if mode in ("NORMALIZED", "NORMAL", "RATIO"):
            self._comparison_mode = mode
            self.comparisonModeChanged.emit()
            self._render_current_chart()

    @Slot(int)
    def setActiveChartTab(self, tab_index: int) -> None:
        """Aktif grafik sekmesini ayarlar: 0: Getiri, 1: Drawdown, 2: Aylık, 3: Saçılım, 4: Treemap."""
        if 0 <= tab_index <= 4:
            self._active_chart_tab = tab_index
            self.activeChartTabChanged.emit()
            self._render_current_chart()

    @Slot(str, str)
    def setRatioAssets(self, num_code: str, den_code: str) -> None:
        """Rasyo modu için pay ve payda varlıklarını ayarlar."""
        self._ratio_numerator = num_code
        self._ratio_denominator = den_code
        self.ratioAssetsChanged.emit()
        if self._comparison_mode == "RATIO":
            self._render_current_chart()

    @Slot(str)
    def setTreemapMode(self, mode: str) -> None:
        """Treemap modunu ayarlar: 'HOLDINGS' (Portföy Hisseleri) veya 'ASSETS' (Varlık Kıyaslaması)."""
        mode = mode.strip().upper()
        if mode in ["HOLDINGS", "ASSETS"] and mode != self._treemap_mode:
            self._treemap_mode = mode
            self.treemapModeChanged.emit()
            if self._active_chart_tab == 4:
                self._render_current_chart()

    @Slot(str)
    def setTreemapPortfolio(self, code: str) -> None:
        """Treemap'te görüntülenecek portföyü ayarlar (Ana Portföy veya Model Portföyler)."""
        code = str(code).strip()
        if code and code != self._treemap_portfolio_code:
            self._treemap_portfolio_code = code
            self.treemapPortfolioChanged.emit()
            if self._active_chart_tab == 4 and self._treemap_mode == "HOLDINGS":
                self._render_current_chart()

    @Slot()
    def runComparison(self) -> None:
        """Asenkron arka plan iş parçacığında karşılaştırmayı çalıştırır."""
        if not self._selected_codes:
            self._chart_html = ""
            self._metrics_list = []
            self.chartHtmlChanged.emit()
            self.metricsListChanged.emit()
            return

        self._is_loading = True
        self.isLoadingChanged.emit()

        selected_codes = list(self._selected_codes)
        start_dt, end_dt = self._resolve_range()
        self._last_range = (start_dt, end_dt)

        self._executor.submit(self._worker_calculate, selected_codes, start_dt, end_dt, self._currency_mode)

    def _resolve_range(self) -> tuple:
        return resolve_range(self._period_label, self._custom_start, self._custom_end)

    def _worker_calculate(self, selected_codes: List[str], start_dt: date, end_dt: date, currency_mode: str = "TL") -> None:
        """Arka plan thread'inde veri çekimi ve hizalama hesabı."""
        try:
            filter_state = build_filter_state(
                selected_codes, start_dt, end_dt, currency_mode, self._analysis_service.get_stock_map_for_source
            )
            dto = self._analysis_service.get_comparison_view(filter_state)
            series_dict, code_to_label = ComparisonSeriesBuilder.build_global_series(dto, filter_state.selected_stock_ids)

            if not series_dict:
                self._calcEmpty.emit()
                return

            aligned = ComparisonService.align_financial_series(series_dict)
            if aligned.empty or len(aligned) < 2:
                self._calcEmpty.emit()
                return

            metrics = build_risk_return_metrics(aligned, ComparisonService.calculate_risk_return_metrics(aligned))
            # Ana GUI thread'ine Qt QueuedConnection ile aktar
            self._calcFinished.emit(aligned, code_to_label, metrics)
        except Exception as exc:
            logger.exception("Arka plan karşılaştırma hatası: %s", exc)
            self._calcError.emit(str(exc))

    def _apply_empty_result(self) -> None:
        self._cached_aligned = None
        self._chart_html = ""
        self._metrics_list = []
        self._is_loading = False
        self.isLoadingChanged.emit()
        self.chartHtmlChanged.emit()
        self.metricsListChanged.emit()

    def _apply_error_result(self, err_msg: str) -> None:
        self._is_loading = False
        self.isLoadingChanged.emit()
        self.operationResult.emit(False, err_msg)

    def _apply_calculation_result(self, aligned: pd.DataFrame, code_to_label: Dict[str, str], metrics: List[Dict[str, Any]]) -> None:
        self._cached_aligned = aligned
        self._cached_labels = code_to_label
        self._metrics_list = metrics
        self._metrics_list_changed = True
        self.metricsListChanged.emit()
        self._is_loading = False
        self.isLoadingChanged.emit()
        self._render_current_chart()

    def _apply_ai_result(self, text: str, error: str) -> None:
        self._ai_busy = False
        if error:
            self._ai_comment = ""
            self.operationResult.emit(False, f"Yapay zeka yorumu üretilemedi: {error}")
        else:
            self._ai_comment = text
        self.aiCommentChanged.emit()

    # ──────────────────────────── Grafik Üretimi ────────────────────────────

    def _render_current_chart(self) -> None:
        """Mevcut sekme ve moda göre aktif grafiğin HTML'ini üretir."""
        aligned = self._cached_aligned
        if aligned is None or aligned.empty:
            self._chart_html = ""
        elif self._active_chart_tab == 0:
            self._chart_html = self._build_returns_html(aligned)
        elif self._active_chart_tab == 1:
            self._chart_html = build_drawdown_html(ComparisonService.calculate_drawdowns(aligned))
        elif self._active_chart_tab == 2:
            monthly = ComparisonService.calculate_periodic_returns(aligned, freq="ME")
            self._chart_html = build_periodic_html(monthly)
        elif self._active_chart_tab == 3:
            self._chart_html = build_scatter_html(self._metrics_list)
        elif self._active_chart_tab == 4:
            self._chart_html = self._build_treemap_html()
        self.chartHtmlChanged.emit()

    def _build_returns_html(self, aligned: pd.DataFrame) -> str:
        """Sekme 0: Kümülatif getiri (Rasyo / Normal / Normalize Baz 100)."""
        if self._comparison_mode == "RATIO":
            num_col = find_column(aligned, self._ratio_numerator)
            den_col = find_column(aligned, self._ratio_denominator)
            if num_col and den_col and num_col in aligned and den_col in aligned:
                ratio_series = ComparisonService.calculate_asset_ratio(aligned[num_col], aligned[den_col])
                return build_line_chart_html(pd.DataFrame({f"{num_col} / {den_col}": ratio_series}), is_ratio=True)
            return build_line_chart_html(aligned, is_ratio=False)
        if self._comparison_mode == "NORMAL":
            return build_line_chart_html(aligned, is_normal=True)
        norm = (aligned.divide(aligned.iloc[0])) * 100.0
        norm = norm.replace([float('inf'), float('-inf')], float('nan')).ffill().bfill()
        return build_line_chart_html(norm, is_normalized=True)

    def _get_portfolio_label(self, code: str) -> str:
        for p in self._treemap_portfolio_options:
            if p.get("code") == code:
                return str(p.get("label", code))
        if code == "dashboard":
            return "Ana Portföy"
        return code

    def _get_portfolio_holdings(self, portfolio_code: Optional[str] = None) -> List[Dict[str, Any]]:
        code = portfolio_code or self._treemap_portfolio_code or "dashboard"
        return fetch_portfolio_holdings(self._analysis_service, code, self._period_label)

    def _build_treemap_html(self) -> str:
        """HOLDINGS: seçilen portföyün hisse haritası; ASSETS: seçilen varlıkların getiri katkı haritası."""
        is_holdings = self._treemap_mode == "HOLDINGS"
        if is_holdings:
            items = self._get_portfolio_holdings(self._treemap_portfolio_code)
        else:
            items = treemap_items_from_metrics(self._metrics_list)
        return build_treemap_html(items, is_holdings, self._get_portfolio_label(self._treemap_portfolio_code))
