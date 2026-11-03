"""
Stock 360 Controller — Hisse 360 & Temel Analiz Görünümü Denetleyicisi (Faz 5).

Genel Bakış, Teknik Seviyeler, Değerleme Rasyoları, Çeyreklik Bilanço Çubuk Grafiği
ve KAP Ortaklık Yapısı (Donut Grafiği) verilerini yönetir.
Arka plan iş parçacığı (threading) ile UI donmasını engeller.
"""
from __future__ import annotations

import logging
import threading
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Property, Signal, Slot, QCoreApplication

from src.application.services.analysis.stock_360_service import Stock360Service
from src.domain.models.shareholder import ShareholderSnapshot
from src.ui_qml.controllers.stock_360_fallback import get_default_overview, get_default_technical, get_fallback_financials
from src.ui_qml.controllers.stock_360_overview import overview_fields, resolve_identity, technical_fields
from src.ui_qml.controllers.stock_360_html import (
    generate_financials_html,
    write_temp_html,
    cleanup_temp_files,
)
from src.ui_qml.controllers.stock_360_remote import RemoteResult, fetch_remote_data
from src.ui_qml.controllers.stock_360_calc import compute_revenue_chart, compute_dupont_data, compute_cash_flow_data
from src.ui_qml.controllers.stock_360_state import Stock360StateMixin

logger = logging.getLogger(__name__)


class Stock360Controller(Stock360StateMixin, QObject):
    """
    QML Stock360View için ViewModel denetleyicisi.
    Yerel DB verilerini anında gösterir, derin bilanço ve KAP verilerini
    arka plan thread'inde çeker.
    """

    # --- Sinyaller ---
    currentTickerChanged = Signal()
    companyNameChanged = Signal()
    sectorChanged = Signal()
    loadingChanged = Signal(bool)
    errorMessageChanged = Signal(str)

    # 1. Genel Bakış Sinyalleri
    overviewChanged = Signal()

    # 2. Teknik Seviyeler Sinyalleri
    technicalChanged = Signal()

    # 3. Finansallar & Rasyolar Sinyalleri
    financialsChanged = Signal()
    activeFinancialTabChanged = Signal(str)
    financialBarsChanged = Signal()

    # 4. Ortaklık Yapısı Sinyalleri
    shareholdersChanged = Signal()

    # Faz 5.1 & 5.2 — HTML Dashboard, Finansal Tablolar ve Fintech Modelleri
    financialsHtmlUrlChanged = Signal()
    shareholdersHtmlUrlChanged = Signal()
    periodsCountChanged = Signal(int)
    viewModeChanged = Signal(int)
    revenueChartChanged = Signal()
    dupontChanged = Signal()
    cashFlowChanged = Signal()
    financialTableChanged = Signal()
    shareholderTimelineChanged = Signal()

    # Arka plan iş parçacığı güvenli sinyali
    _remoteDataReady = Signal(object)

    def __init__(self, container=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._container = container

        self._init_identity_state()
        self._init_overview_and_technical_state()
        self._init_financial_state()
        self._init_shareholder_state()
        self._init_html_and_fintech_state()

        # Sinyal bağlantısı
        self._remoteDataReady.connect(self._apply_remote_results)

        # Varsayılan başlangıç verisi (Hızlı açılış)
        self._set_default_overview(self._current_ticker)
        self._set_default_technical()
        self._set_fallback_financials(self._current_ticker)
        self._set_fallback_shareholders(self._current_ticker)

        # Uygulama kapanırken geçici dosyaları temizle
        app = QCoreApplication.instance()
        if app:
            app.aboutToQuit.connect(self._cleanup_temp_files)

        self._has_loaded_data = False

    # ------------------------------------------------------------------
    # QML Property Tanımları
    # ------------------------------------------------------------------

    @Property(str, notify=currentTickerChanged)
    def currentTicker(self) -> str:
        return self._current_ticker

    @Property(str, notify=companyNameChanged)
    def companyName(self) -> str:
        return self._company_name

    @Property(str, notify=sectorChanged)
    def sector(self) -> str:
        return self._sector

    @Property(bool, notify=loadingChanged)
    def isLoading(self) -> bool:
        return self._is_loading

    # Genel Bakış
    @Property(str, notify=overviewChanged)
    def lastPrice(self) -> str:
        return self._last_price_str

    @Property(str, notify=overviewChanged)
    def dailyChange(self) -> str:
        return self._daily_change_str

    @Property(bool, notify=overviewChanged)
    def isDailyPositive(self) -> bool:
        return self._is_daily_positive

    @Property(str, notify=overviewChanged)
    def volume(self) -> str:
        return self._volume_str

    @Property(str, notify=overviewChanged)
    def week52Low(self) -> str:
        return self._week52_low_str

    @Property(str, notify=overviewChanged)
    def week52High(self) -> str:
        return self._week52_high_str

    @Property(float, notify=overviewChanged)
    def week52RangePct(self) -> float:
        return self._week52_range_pct

    # Teknik Seviyeler
    @Property(str, notify=technicalChanged)
    def rsi14(self) -> str:
        return self._rsi14_str

    @Property(str, notify=technicalChanged)
    def rsiStatus(self) -> str:
        return self._rsi_status

    @Property(str, notify=technicalChanged)
    def macdLine(self) -> str:
        return self._macd_line_str

    @Property(str, notify=technicalChanged)
    def macdSignal(self) -> str:
        return self._macd_signal_str

    @Property(str, notify=technicalChanged)
    def sma50(self) -> str:
        return self._sma50_str

    @Property(str, notify=technicalChanged)
    def sma200(self) -> str:
        return self._sma200_str

    @Property(str, notify=technicalChanged)
    def ema20(self) -> str:
        return self._ema20_str

    @Property(str, notify=technicalChanged)
    def support(self) -> str:
        return self._support_str

    @Property(str, notify=technicalChanged)
    def resistance(self) -> str:
        return self._resistance_str

    @Property(str, notify=technicalChanged)
    def trendStatus(self) -> str:
        return self._trend_status

    # Finansallar & Rasyolar
    @Property(str, notify=financialsChanged)
    def peRatio(self) -> str:
        return self._pe_ratio

    @Property(str, notify=financialsChanged)
    def pbRatio(self) -> str:
        return self._pb_ratio

    @Property(str, notify=financialsChanged)
    def evEbitda(self) -> str:
        return self._ev_ebitda

    @Property(str, notify=financialsChanged)
    def divYield(self) -> str:
        return self._div_yield

    @Property(str, notify=financialsChanged)
    def roe(self) -> str:
        return self._roe

    @Property(str, notify=financialsChanged)
    def netDebtEbitda(self) -> str:
        return self._net_debt_ebitda

    @Property(str, notify=financialsChanged)
    def piotroskiScore(self) -> str:
        return self._piotroski_score

    @Property(str, notify=financialsChanged)
    def currentRatio(self) -> str:
        return self._current_ratio

    @Property(str, notify=activeFinancialTabChanged)
    def activeFinancialTab(self) -> str:
        return self._active_financial_tab

    @Property("QVariantList", notify=financialBarsChanged)
    def financialBars(self) -> List[Dict[str, Any]]:
        return self._financial_bars

    @Property(str, notify=financialBarsChanged)
    def financialSummary(self) -> str:
        return self._financial_summary

    # Ortaklık Yapısı
    @Property("QVariantList", notify=shareholdersChanged)
    def shareholdersList(self) -> List[Dict[str, Any]]:
        return self._shareholders_list

    @Property("QVariantList", notify=shareholdersChanged)
    def shareholderSlices(self) -> List[Dict[str, Any]]:
        return self._shareholder_slices

    @Property(str, notify=shareholdersChanged)
    def freeFloatRatio(self) -> str:
        return self._free_float_ratio_str

    @Property(float, notify=shareholdersChanged)
    def freeFloatPct(self) -> float:
        return self._free_float_pct

    @Property(str, notify=shareholdersChanged)
    def paidCapital(self) -> str:
        return self._paid_capital_str

    @Property(str, notify=shareholdersChanged)
    def shareholderDate(self) -> str:
        return self._shareholder_date_str

    # Faz 5.1 & 5.2 Property'leri

    @Property(int, notify=periodsCountChanged)
    def periodsCount(self) -> int:
        return self._current_periods_count

    @Property(int, notify=viewModeChanged)
    def viewMode(self) -> int:
        return self._current_view_mode

    @Property(int, notify=shareholdersChanged)
    def kapSnapshotCount(self) -> int:
        return self._kap_snapshot_count

    @Property(str, notify=shareholdersChanged)
    def lastKapFilingDate(self) -> str:
        return self._last_kap_filing_date

    @Property("QVariantList", notify=revenueChartChanged)
    def revenueChartData(self) -> List[Dict[str, Any]]:
        return self._revenue_chart_data

    @Property(str, notify=revenueChartChanged)
    def revenueYoYGrowth(self) -> str:
        return self._revenue_yoy_growth

    @Property(bool, notify=revenueChartChanged)
    def isRevenueYoYPositive(self) -> bool:
        return self._is_revenue_yoy_positive

    @Property(str, notify=revenueChartChanged)
    def latestQuarterRevenue(self) -> str:
        return self._latest_quarter_revenue

    @Property(str, notify=revenueChartChanged)
    def latestQuarterNetIncome(self) -> str:
        return self._latest_quarter_net_income

    @Property(str, notify=revenueChartChanged)
    def latestQuarterMargin(self) -> str:
        return self._latest_quarter_margin

    @Property("QVariantMap", notify=dupontChanged)
    def dupontData(self) -> Dict[str, Any]:
        return self._dupont_data

    @Property("QVariantMap", notify=cashFlowChanged)
    def cashFlowData(self) -> Dict[str, Any]:
        return self._cash_flow_data

    @Property("QVariantList", notify=financialTableChanged)
    def activeStatementPeriods(self) -> List[str]:
        return self._active_statement_periods

    @Property("QVariantList", notify=financialTableChanged)
    def financialTableRows(self) -> List[Dict[str, Any]]:
        return self._financial_table_rows

    @Property(str, notify=financialTableChanged)
    def statementType(self) -> str:
        return self._statement_type

    @Property(str, notify=financialTableChanged)
    def statementSearchQuery(self) -> str:
        return self._statement_search_query

    @Property("QVariantList", notify=shareholderTimelineChanged)
    def shareholderTimeline(self) -> List[Dict[str, Any]]:
        return self._shareholder_timeline

    # ------------------------------------------------------------------
    # QML Slotları
    # ------------------------------------------------------------------

    @Slot()
    def ensureLoaded(self) -> None:
        """QML sayfası ilk açıldığında veya geçiş yapıldığında çağrılır."""
        if not self._has_loaded_data:
            self.loadStock(self._current_ticker)

    @Slot(str)
    def searchTicker(self, ticker: str) -> None:
        """Kullanıcının girdiği veya listeden seçtiği sembolü yükler."""
        if not ticker:
            return
        self.loadStock(ticker.strip().upper())

    @Slot()
    def refreshData(self) -> None:
        """Mevcut hisse verilerini internetten ve yerel DB'den yeniden yükler."""
        self.loadStock(self._current_ticker, force_refresh_shareholders=False)

    @Slot(str)
    def setFinancialTab(self, tab: str) -> None:
        """Çeyreklik bilanço çubuk grafik sekmesini değiştirir ('satis', 'brut_kar', 'favok', 'net_kar')."""
        if self._active_financial_tab != tab:
            self._active_financial_tab = tab
            self.activeFinancialTabChanged.emit(tab)
            self._recalculate_financial_bars()

    @Slot()
    def refreshShareholders(self) -> None:
        """KAP ortaklık yapısını internetten zorla tazeler."""
        self.loadStock(self._current_ticker, force_refresh_shareholders=True)

    @Slot(int)
    def setViewMode(self, mode: int) -> None:
        """0: Native Fintech Kartları (QML), 1: Etkileşimli HTML Dashboard (WebEngine)."""
        if self._current_view_mode != mode:
            self._current_view_mode = mode
            self.viewModeChanged.emit(mode)

    @Slot(str)
    def setStatementType(self, statement_type: str) -> None:
        """Bilanço detay tablosu sekmesini ('bilanco', 'gelir', 'nakit_akim') ayarlar."""
        if self._statement_type != statement_type:
            self._statement_type = statement_type
            self._recalculate_financial_table()
            self.financialTableChanged.emit()

    @Slot(str)
    def setStatementSearchQuery(self, query: str) -> None:
        """Bilanço tablosunda kalem arama filtresini günceller."""
        if self._statement_search_query != query:
            self._statement_search_query = query
            self._recalculate_financial_table()
            self.financialTableChanged.emit()

    @Slot(int)
    def setFinancialsPeriods(self, periods: int) -> None:
        """Kapsamlı bilanço ve grafikler için dönem sayısını (4, 8, 12, 0=Tümü) ayarlar ve yeniler."""
        self._current_periods_count = periods
        self.periodsCountChanged.emit(periods)
        if self._cached_metrics:
            self._recalculate_all_fintech_models()
            self._refresh_financials_html(periods)
        else:
            self.refreshData()

    def _refresh_financials_html(self, periods: int) -> None:
        all_periods = self._cached_metrics.get("periods", [])
        n_p = len(all_periods) if periods == 0 else periods
        try:
            html = generate_financials_html(self._cached_metrics, n_periods=n_p)
            url, f_path = write_temp_html(f"fin_{periods}", self._current_ticker, html)
            if f_path:
                self._temp_files.append(f_path)
            self._financials_html_url = url
            self.financialsHtmlUrlChanged.emit()
        except Exception as exc:
            logger.exception("Finansal HTML yenilenemedi: %s", exc)

    @Slot()
    def refreshShareholdersHistory(self) -> None:
        """KAP ortaklık geçmişini internet üzerinden zorla yeniler."""
        self.loadStock(self._current_ticker, force_refresh_shareholders=True)

    # ------------------------------------------------------------------
    # Geçici Dosya Yönetimi
    # ------------------------------------------------------------------

    def _cleanup_temp_files(self) -> None:
        cleanup_temp_files(self._temp_files)
        self._temp_files.clear()

    def __del__(self):
        try:
            self._cleanup_temp_files()
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Data Loading Strategy
    # ------------------------------------------------------------------

    def loadStock(self, ticker: str, force_refresh_shareholders: bool = False) -> None:
        self._has_loaded_data = True
        norm_ticker = ticker.strip().upper().replace(".IS", "")
        if not norm_ticker:
            return

        self._current_ticker = norm_ticker
        self.currentTickerChanged.emit()

        self._is_loading = True
        self._error_message = ""
        self.loadingChanged.emit(True)
        self.errorMessageChanged.emit("")

        # 1. Aşama: Anında yerel DB verilerini yükle ve UI'yı güncelle (Gecikmesiz)
        self._load_local_overview_and_technical(norm_ticker)

        # 2. Aşama: Arka plan iş parçacığında derin finansal ve KAP verilerini çek
        worker_thread = threading.Thread(
            target=self._remote_fetch_worker,
            args=(norm_ticker, force_refresh_shareholders),
            daemon=True,
        )
        worker_thread.start()

    def _load_local_overview_and_technical(self, ticker: str) -> None:
        """Yerel veritabanından şirket adı, sektör, fiyat ve TA seviyelerini yükler (`stock_360_overview`)."""
        s360_service: Optional[Stock360Service] = getattr(
            getattr(self._container, "services", None), "stock_360_service", None
        )
        self._company_name, self._sector = resolve_identity(self._container, s360_service, ticker)

        if s360_service:
            overview = s360_service.get_overview(ticker) or s360_service.get_overview(f"{ticker}.IS")
            self._apply_overview(overview_fields(overview) if overview else get_default_overview(ticker))
            tech = s360_service.get_technical_levels(ticker) or s360_service.get_technical_levels(f"{ticker}.IS")
            self._apply_technical(technical_fields(tech) if tech else get_default_technical())
        else:
            self._set_default_overview(ticker)
            self._set_default_technical()

        self.overviewChanged.emit()
        self.technicalChanged.emit()

    def _remote_fetch_worker(self, ticker: str, force_refresh_shareholders: bool) -> None:
        """Ağ üzerinden finansal bilanço ve KAP ortaklık verilerini çeker."""
        s360_service: Optional[Stock360Service] = getattr(
            getattr(self._container, "services", None), "stock_360_service", None
        )
        result = fetch_remote_data(s360_service, ticker, self._current_periods_count, force_refresh_shareholders)
        self._temp_files.extend(result.temp_files)

        # UI Thread'e güvenli bildirim gönder (Qt queued connection)
        try:
            self._remoteDataReady.emit(result)
        except RuntimeError:
            pass

    def _apply_remote_results(self, result: RemoteResult) -> None:
        if self._current_ticker != result.ticker:
            return

        self._is_loading = False
        self._error_message = result.error
        self.loadingChanged.emit(False)

        self._cached_metrics = result.financials
        self._cached_snapshots = result.shareholders

        self._apply_financials_result(result.ticker, result.financials, result.fin_html_url)
        self._apply_shareholders_result(result.ticker, result.shareholders, result.sh_html_url)

        self.financialsChanged.emit()
        self.shareholdersChanged.emit()
        self.financialsHtmlUrlChanged.emit()
        self.shareholdersHtmlUrlChanged.emit()

        # Fintech Modellerini Yenile
        self._recalculate_all_fintech_models()

    def _apply_financials_result(self, ticker: str, financials: Optional[Dict[str, Any]], html_url: str) -> None:
        if financials and "periods" in financials and financials["periods"]:
            self._financial_raw_data = financials
            self._has_financials = True
            self._is_financials_ready = True
            self._financial_periods = financials.get("periods", [])
            self._financials_html_url = html_url
            self._parse_valuation_ratios(financials)
            self._recalculate_financial_bars()
        else:
            self._has_financials = False
            self._is_financials_ready = False
            self._financials_html_url = ""
            self._set_fallback_financials(ticker)

    def _apply_shareholders_result(
        self, ticker: str, shareholders: Optional[List[ShareholderSnapshot]], html_url: str
    ) -> None:
        if shareholders and len(shareholders) > 0:
            self._has_shareholders = True
            self._is_shareholders_ready = True
            self._shareholders_html_url = html_url
            self._kap_snapshot_count = len(shareholders)
            self._last_kap_filing_date = (
                shareholders[0].creation_date.strftime("%d.%m.%Y")
                if getattr(shareholders[0], "creation_date", None)
                else "—"
            )
            self._parse_shareholder_data(shareholders[0])
        else:
            self._has_shareholders = False
            self._is_shareholders_ready = False
            self._shareholders_html_url = ""
            self._kap_snapshot_count = 0
            self._last_kap_filing_date = "—"
            self._set_fallback_shareholders(ticker)

    # ------------------------------------------------------------------
    # Fintech Calculation Engines
    # ------------------------------------------------------------------

    def _recalculate_all_fintech_models(self) -> None:
        """Kullanıcının seçtiği dönem sayısına göre tüm Fintech modellerini hesaplar."""
        if not self._cached_metrics:
            return

        m = self._cached_metrics
        all_periods = m.get("periods", [])
        if not all_periods:
            return

        n = len(all_periods) if self._current_periods_count == 0 else min(self._current_periods_count, len(all_periods))
        active_periods = all_periods[:n]
        self._active_statement_periods = active_periods

        # 1. Gelir & Kârlılık Grafik Verisi
        chart_items, kpis = compute_revenue_chart(m, active_periods)
        self._revenue_chart_data = chart_items
        self._latest_quarter_revenue = kpis["latest_quarter_revenue"]
        self._latest_quarter_net_income = kpis["latest_quarter_net_income"]
        self._latest_quarter_margin = kpis["latest_quarter_margin"]
        self._revenue_yoy_growth = kpis["revenue_yoy_growth"]
        self._is_revenue_yoy_positive = kpis["is_revenue_yoy_positive"]

        # 2. DuPont Kârlılık Kırılımı
        self._dupont_data = compute_dupont_data(m, active_periods)

        # 3. Nakit Akışı & Borçluluk
        self._cash_flow_data = compute_cash_flow_data(m, active_periods)

        self._recalculate_financial_table()
        self._recalculate_shareholder_timeline()

        self.revenueChartChanged.emit()
        self.dupontChanged.emit()
        self.cashFlowChanged.emit()
        self.financialTableChanged.emit()
        self.shareholderTimelineChanged.emit()
        self.financialsChanged.emit()

    # ------------------------------------------------------------------
    # Defaults & Fallbacks (Zarif Çökmesiz Deneyim)
    # ------------------------------------------------------------------

    def _set_fallback_financials(self, ticker: str) -> None:
        fb = get_fallback_financials(ticker)
        self._apply_ratios(fb["ratios"])

        self._financial_raw_data = fb["raw_data"]
        self._financial_periods = self._financial_raw_data.get("periods", [])
        self._has_financials = True
        self._recalculate_financial_bars()
        self._cached_metrics = self._financial_raw_data
        self._recalculate_all_fintech_models()
