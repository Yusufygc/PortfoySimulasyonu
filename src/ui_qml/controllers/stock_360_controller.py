"""
Stock 360 Controller — Hisse 360 & Temel Analiz Görünümü Denetleyicisi (Faz 5).

Genel Bakış, Teknik Seviyeler, Değerleme Rasyoları, Çeyreklik Bilanço Çubuk Grafiği
ve KAP Ortaklık Yapısı (Donut Grafiği) verilerini yönetir.
Arka plan iş parçacığı (threading) ile UI donmasını engeller.
"""
from __future__ import annotations

import logging
import threading
from datetime import date
from typing import Any, Dict, List, Optional

from PySide6.QtCore import QObject, Property, Signal, Slot, QTimer, QCoreApplication

from src.application.services.analysis.stock_360_service import Stock360Service
from src.domain.models.shareholder import ShareholderSnapshot
from src.ui_qml.controllers.stock_360_formatters import (
    DONUT_COLORS,
    _format_currency,
    _format_price,
    _format_volume,
    format_currency,
    format_price,
    format_volume,
)
from src.ui_qml.controllers.stock_360_fallback import (
    guess_sector,
    get_default_overview,
    get_default_technical,
    get_fallback_financials,
    get_fallback_shareholders,
)
from src.ui_qml.controllers.stock_360_html import (
    generate_financials_html,
    generate_shareholders_html,
    write_temp_html,
    cleanup_temp_files,
)
from src.ui_qml.controllers.stock_360_calc import (
    parse_valuation_ratios,
    compute_financial_bars,
    compute_revenue_chart,
    compute_dupont_data,
    compute_cash_flow_data,
    compute_financial_table_rows,
    compute_shareholder_timeline,
    parse_shareholder_data,
)

logger = logging.getLogger(__name__)


class Stock360Controller(QObject):
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

    # 5. Ekstra Liste / Navigasyon Sinyalleri
    availableStocksChanged = Signal()

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
    _remoteDataReady = Signal(str, object, object, str, str, str)

    def __init__(self, container=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._container = container

        # Temel durum
        self._current_ticker: str = "BIMAS"
        self._company_name: str = "BİM Birleşik Mağazalar A.Ş."
        self._sector: str = "Perakende Ticaret"
        self._is_loading: bool = False
        self._error_message: str = ""
        self._available_stocks: List[str] = []

        # Genel Bakış
        self._last_price_str: str = "₺0.00"
        self._last_price_raw: float = 0.0
        self._last_price_date_str: str = "—"
        self._daily_change_str: str = "%0.00"
        self._daily_change_raw: float = 0.0
        self._is_daily_positive: bool = True
        self._volume_str: str = "0"
        self._week52_low_str: str = "₺0.00"
        self._week52_high_str: str = "₺0.00"
        self._week52_range_pct: float = 0.5

        # Teknik Seviyeler
        self._rsi14_str: str = "—"
        self._rsi_status: str = "Nötr"
        self._macd_line_str: str = "—"
        self._macd_signal_str: str = "—"
        self._sma50_str: str = "—"
        self._sma200_str: str = "—"
        self._ema20_str: str = "—"
        self._support_str: str = "—"
        self._resistance_str: str = "—"
        self._trend_status: str = "Dengeli"

        # Finansallar & Rasyolar
        self._pe_ratio: str = "—"
        self._pb_ratio: str = "—"
        self._ev_ebitda: str = "—"
        self._div_yield: str = "—"
        self._roe: str = "—"
        self._net_debt_ebitda: str = "—"
        self._piotroski_score: str = "—"
        self._current_ratio: str = "—"
        self._market_cap_str: str = "—"

        self._active_financial_tab: str = "satis"
        self._financial_raw_data: Dict[str, Any] = {}
        self._financial_periods: List[str] = []
        self._financial_bars: List[Dict[str, Any]] = []
        self._financial_summary: str = ""
        self._has_financials: bool = False

        # Ortaklık Yapısı
        self._shareholders_list: List[Dict[str, Any]] = []
        self._shareholder_slices: List[Dict[str, Any]] = []
        self._free_float_ratio_str: str = "—"
        self._free_float_pct: float = 0.0
        self._paid_capital_str: str = "—"
        self._shareholder_date_str: str = "—"
        self._has_shareholders: bool = False

        # Faz 5.1 & 5.2 — HTML Dashboard ve Fintech Durumu
        self._financials_html_url: str = ""
        self._shareholders_html_url: str = ""
        self._current_periods_count: int = 8
        self._current_view_mode: int = 0
        self._is_financials_ready: bool = False
        self._is_shareholders_ready: bool = False
        self._kap_snapshot_count: int = 0
        self._last_kap_filing_date: str = "—"
        self._temp_files: List[str] = []

        # Fintech Gelişmiş Modeller
        self._cached_metrics: Optional[Dict[str, Any]] = None
        self._cached_snapshots: Optional[List[ShareholderSnapshot]] = None
        self._revenue_chart_data: List[Dict[str, Any]] = []
        self._revenue_yoy_growth: str = "—"
        self._is_revenue_yoy_positive: bool = True
        self._latest_quarter_revenue: str = "—"
        self._latest_quarter_net_income: str = "—"
        self._latest_quarter_margin: str = "—"

        self._dupont_data: Dict[str, Any] = {}
        self._cash_flow_data: Dict[str, Any] = {}
        self._financial_table_rows: List[Dict[str, Any]] = []
        self._active_statement_periods: List[str] = []
        self._statement_type: str = "bilanco"
        self._statement_search_query: str = ""
        self._shareholder_timeline: List[Dict[str, Any]] = []

        # Sinyal bağlantısı
        self._remoteDataReady.connect(self._apply_remote_results)

        # Hızlı seçim hisseleri
        self._load_available_stocks()

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

    @Property(str, notify=errorMessageChanged)
    def errorMessage(self) -> str:
        return self._error_message

    # Genel Bakış
    @Property(str, notify=overviewChanged)
    def lastPrice(self) -> str:
        return self._last_price_str

    @Property(float, notify=overviewChanged)
    def lastPriceRaw(self) -> float:
        return self._last_price_raw

    @Property(str, notify=overviewChanged)
    def lastPriceDate(self) -> str:
        return self._last_price_date_str

    @Property(str, notify=overviewChanged)
    def dailyChange(self) -> str:
        return self._daily_change_str

    @Property(float, notify=overviewChanged)
    def dailyChangeRaw(self) -> float:
        return self._daily_change_raw

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

    @Property(str, notify=financialsChanged)
    def marketCap(self) -> str:
        return self._market_cap_str

    @Property(str, notify=activeFinancialTabChanged)
    def activeFinancialTab(self) -> str:
        return self._active_financial_tab

    @Property("QVariantList", notify=financialBarsChanged)
    def financialBars(self) -> List[Dict[str, Any]]:
        return self._financial_bars

    @Property(str, notify=financialBarsChanged)
    def financialSummary(self) -> str:
        return self._financial_summary

    @Property(bool, notify=financialsChanged)
    def hasFinancials(self) -> bool:
        return self._has_financials

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

    @Property(bool, notify=shareholdersChanged)
    def hasShareholders(self) -> bool:
        return self._has_shareholders

    # Hızlı Hisse Listesi
    @Property("QVariantList", notify=availableStocksChanged)
    def availableStocks(self) -> List[str]:
        return self._available_stocks

    # Faz 5.1 & 5.2 Property'leri
    @Property(str, notify=financialsHtmlUrlChanged)
    def financialsHtmlUrl(self) -> str:
        return self._financials_html_url

    @Property(str, notify=shareholdersHtmlUrlChanged)
    def shareholdersHtmlUrl(self) -> str:
        return self._shareholders_html_url

    @Property(int, notify=periodsCountChanged)
    def periodsCount(self) -> int:
        return self._current_periods_count

    @Property(int, notify=viewModeChanged)
    def viewMode(self) -> int:
        return self._current_view_mode

    @Property(bool, notify=financialsChanged)
    def isFinancialsReady(self) -> bool:
        return self._is_financials_ready

    @Property(bool, notify=shareholdersChanged)
    def isShareholdersReady(self) -> bool:
        return self._is_shareholders_ready

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
            self._load_available_stocks()
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
        else:
            self.refreshData()

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

    def _load_available_stocks(self) -> None:
        """Kullanıcının portföyündeki veya DB'de en çok fiyatı olan hisseleri listeler."""
        candidates = ["BIMAS", "ADEL", "AKCNS", "ALBRK", "AYGAZ", "BRSAN", "CLEBI", "THYAO", "ASELS", "KCHOL"]
        if self._container:
            try:
                stocks = []
                s360_service = getattr(self._container, "stock_360_service", None)
                if not s360_service and hasattr(self._container, "services"):
                    s360_service = getattr(self._container.services, "stock_360_service", None)

                if s360_service and hasattr(s360_service, "get_all_stocks"):
                    stocks = s360_service.get_all_stocks()
                elif hasattr(self._container, "repositories") and hasattr(self._container.repositories, "stock_repo"):
                    stocks = self._container.repositories.stock_repo.get_all_stocks()

                tickers = [s.ticker.replace(".IS", "") for s in stocks if getattr(s, "ticker", None)]
                if tickers:
                    sorted_tickers = []
                    for c in candidates:
                        if c in tickers:
                            sorted_tickers.append(c)
                    for t in tickers:
                        if t not in sorted_tickers:
                            sorted_tickers.append(t)
                    self._available_stocks = sorted_tickers[:12]
                    self.availableStocksChanged.emit()
                    return
            except Exception as exc:
                logger.warning("Available stocks yüklenirken hata: %s", exc)

        self._available_stocks = candidates
        self.availableStocksChanged.emit()

    def _load_local_overview_and_technical(self, ticker: str) -> None:
        """Yerel SQLite veritabanından şirket adı, sektör, fiyat ve TA seviyelerini yükler."""
        stock_name = ticker
        sector_name = "BIST Şirketi"

        s360_service: Optional[Stock360Service] = getattr(
            getattr(self._container, "services", None), "stock_360_service", None
        )

        stock = None
        if s360_service and hasattr(s360_service, "get_stock_by_ticker"):
            stock = s360_service.get_stock_by_ticker(ticker) or s360_service.get_stock_by_ticker(f"{ticker}.IS")
        elif hasattr(self._container, "repositories") and hasattr(self._container.repositories, "stock_repo"):
            stock_repo = self._container.repositories.stock_repo
            stock = stock_repo.get_stock_by_ticker(ticker) or stock_repo.get_stock_by_ticker(f"{ticker}.IS")

        if stock:
            stock_name = stock.name or ticker
            if hasattr(stock, "sector") and stock.sector:
                sector_name = stock.sector
            else:
                sector_name = guess_sector(ticker)
        elif s360_service and hasattr(s360_service, "get_company_name"):
            # Portföyde (SQLite) olmayan hisse: DuckDB piyasa kataloğundaki ad
            catalog_name = s360_service.get_company_name(ticker)
            if isinstance(catalog_name, str) and catalog_name:
                stock_name = catalog_name
            sector_name = guess_sector(ticker)

        self._company_name = stock_name
        self._sector = sector_name

        if s360_service:
            # Genel Bakış
            ov = s360_service.get_overview(ticker) or s360_service.get_overview(f"{ticker}.IS")
            if ov:
                self._last_price_raw = float(ov.last_price)
                self._last_price_str = format_price(ov.last_price)
                self._last_price_date_str = ov.last_price_date.strftime("%d.%m.%Y")
                chg = ov.daily_change_pct or 0.0
                self._daily_change_raw = float(chg)
                self._daily_change_str = f"{'+' if chg >= 0 else ''}{chg:.2f}%"
                self._is_daily_positive = chg >= 0
                self._volume_str = format_volume(ov.volume)
                self._week52_low_str = format_price(ov.week52_low)
                self._week52_high_str = format_price(ov.week52_high)

                low_f = float(ov.week52_low)
                high_f = float(ov.week52_high)
                if high_f > low_f:
                    self._week52_range_pct = max(0.0, min(1.0, (self._last_price_raw - low_f) / (high_f - low_f)))
                else:
                    self._week52_range_pct = 0.5
            else:
                self._set_default_overview(ticker)

            # Teknik Seviyeler
            tech = s360_service.get_technical_levels(ticker) or s360_service.get_technical_levels(f"{ticker}.IS")
            if tech:
                if tech.rsi14 is not None:
                    self._rsi14_str = f"{tech.rsi14:.1f}"
                    if tech.rsi14 >= 70:
                        self._rsi_status = "Aşırı Alım"
                    elif tech.rsi14 <= 30:
                        self._rsi_status = "Aşırı Satım"
                    else:
                        self._rsi_status = "Dengeli"
                else:
                    self._rsi14_str = "—"
                    self._rsi_status = "Nötr"

                self._macd_line_str = f"{tech.macd_line:.2f}" if tech.macd_line is not None else "—"
                self._macd_signal_str = f"{tech.macd_signal:.2f}" if tech.macd_signal is not None else "—"
                self._sma50_str = format_price(tech.sma50) if tech.sma50 is not None else "—"
                self._sma200_str = format_price(tech.sma200) if tech.sma200 is not None else "—"
                self._ema20_str = format_price(tech.ema20) if tech.ema20 is not None else "—"
                self._support_str = format_price(tech.support) if tech.support is not None else "—"
                self._resistance_str = format_price(tech.resistance) if tech.resistance is not None else "—"

                # Trend sinyali
                if tech.sma50 is not None and tech.sma200 is not None:
                    if tech.sma50 > tech.sma200:
                        self._trend_status = "Boğa / Golden Trend"
                    else:
                        self._trend_status = "Ayı / Baskılı"
                else:
                    self._trend_status = "Dengeli"
            else:
                self._set_default_technical()
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
        financials_data = None
        shareholders_data = None
        fin_html_url = ""
        sh_html_url = ""
        err_msg = ""
        new_temp_files = []

        if s360_service:
            # 1. Finansallar
            try:
                financials_data = s360_service.get_financials(ticker, n_quarters=12)
                if financials_data:
                    all_periods = financials_data.get("periods", [])
                    n_p = len(all_periods) if self._current_periods_count == 0 else self._current_periods_count
                    html = generate_financials_html(financials_data, n_periods=n_p)
                    url, f_path = write_temp_html(f"fin_{self._current_periods_count}", ticker, html)
                    fin_html_url = url
                    if f_path:
                        new_temp_files.append(f_path)
            except Exception as exc:
                logger.warning("Finansal veri çekilemedi [%s]: %s", ticker, exc)
                err_msg = f"Finansal veriler alınamadı ({exc})"

            # 2. KAP Ortaklık
            try:
                shareholders_data = s360_service.get_shareholders(ticker, force_refresh=force_refresh_shareholders)
                if shareholders_data:
                    sh_html = generate_shareholders_html(ticker, shareholders_data)
                    url, f_path = write_temp_html("sh", ticker, sh_html)
                    sh_html_url = url
                    if f_path:
                        new_temp_files.append(f_path)
            except Exception as exc:
                logger.warning("KAP ortaklık verisi çekilemedi [%s]: %s", ticker, exc)

        self._temp_files.extend(new_temp_files)

        # UI Thread'e güvenli bildirim gönder (Qt queued connection)
        try:
            self._remoteDataReady.emit(ticker, financials_data, shareholders_data, fin_html_url, sh_html_url, err_msg)
        except RuntimeError:
            pass

    def _apply_remote_results(
        self,
        ticker: str,
        financials: Optional[Dict[str, Any]],
        shareholders: Optional[List[ShareholderSnapshot]],
        fin_html_url: str,
        sh_html_url: str,
        error: str,
    ) -> None:
        if self._current_ticker != ticker:
            return

        self._is_loading = False
        self._error_message = error
        self.loadingChanged.emit(False)

        self._cached_metrics = financials
        self._cached_snapshots = shareholders

        # Finansalları işle
        if financials and "periods" in financials and financials["periods"]:
            self._financial_raw_data = financials
            self._has_financials = True
            self._is_financials_ready = True
            self._financial_periods = financials.get("periods", [])
            self._financials_html_url = fin_html_url
            self._parse_valuation_ratios(financials)
            self._recalculate_financial_bars()
        else:
            self._has_financials = False
            self._is_financials_ready = False
            self._financials_html_url = ""
            self._set_fallback_financials(ticker)

        # Ortaklık yapısını işle
        if shareholders and len(shareholders) > 0:
            self._has_shareholders = True
            self._is_shareholders_ready = True
            self._shareholders_html_url = sh_html_url
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

        self.financialsChanged.emit()
        self.shareholdersChanged.emit()
        self.financialsHtmlUrlChanged.emit()
        self.shareholdersHtmlUrlChanged.emit()

        # Fintech Modellerini Yenile
        self._recalculate_all_fintech_models()

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

    def _recalculate_financial_table(self) -> None:
        if not self._cached_metrics:
            self._financial_table_rows = []
            return
        periods = self._active_statement_periods or self._cached_metrics.get("periods", [])[:8]
        self._financial_table_rows = compute_financial_table_rows(
            self._cached_metrics,
            self._statement_type,
            self._statement_search_query,
            periods,
        )

    def _recalculate_shareholder_timeline(self) -> None:
        self._shareholder_timeline = compute_shareholder_timeline(self._cached_snapshots or [])

    def _parse_valuation_ratios(self, f: Dict[str, Any]) -> None:
        """Değerleme ve rasyo göstergelerini ayrıştırır."""
        parsed = parse_valuation_ratios(f)
        self._pe_ratio = parsed["pe_ratio"]
        self._pb_ratio = parsed["pb_ratio"]
        self._ev_ebitda = parsed["ev_ebitda"]
        self._div_yield = parsed["div_yield"]
        self._market_cap_str = parsed["market_cap_str"]
        self._roe = parsed["roe"]
        self._net_debt_ebitda = parsed["net_debt_ebitda"]
        self._piotroski_score = parsed["piotroski_score"]
        self._current_ratio = parsed["current_ratio"]

    def _recalculate_financial_bars(self) -> None:
        """Seçili sekmeye göre çubuk grafik verisini hazırlar."""
        bars, summary = compute_financial_bars(
            self._financial_raw_data,
            self._financial_periods,
            self._active_financial_tab,
        )
        self._financial_bars = bars
        self._financial_summary = summary

    def _parse_shareholder_data(self, snap: ShareholderSnapshot) -> None:
        """KAP pay sahipliği snapshot'ını Donut dilimleri ve listesine dönüştürür."""
        res = parse_shareholder_data(snap)
        self._shareholder_date_str = res["date_str"]
        self._shareholders_list = res["shareholders_list"]
        self._shareholder_slices = res["shareholder_slices"]
        self._free_float_ratio_str = res["free_float_ratio_str"]
        self._free_float_pct = res["free_float_pct"]
        self._paid_capital_str = res["paid_capital_str"]

    # ------------------------------------------------------------------
    # Defaults & Fallbacks (Zarif Çökmesiz Deneyim)
    # ------------------------------------------------------------------

    def _set_default_overview(self, ticker: str) -> None:
        ov = get_default_overview(ticker)
        self._last_price_str = ov["last_price_str"]
        self._last_price_raw = ov["last_price_raw"]
        self._last_price_date_str = ov["last_price_date_str"]
        self._daily_change_str = ov["daily_change_str"]
        self._daily_change_raw = ov["daily_change_raw"]
        self._is_daily_positive = ov["is_daily_positive"]
        self._volume_str = ov["volume_str"]
        self._week52_low_str = ov["week52_low_str"]
        self._week52_high_str = ov["week52_high_str"]
        self._week52_range_pct = ov["week52_range_pct"]

    def _set_default_technical(self) -> None:
        tech = get_default_technical()
        self._rsi14_str = tech["rsi14_str"]
        self._rsi_status = tech["rsi_status"]
        self._macd_line_str = tech["macd_line_str"]
        self._macd_signal_str = tech["macd_signal_str"]
        self._sma50_str = tech["sma50_str"]
        self._sma200_str = tech["sma200_str"]
        self._ema20_str = tech["ema20_str"]
        self._support_str = tech["support_str"]
        self._resistance_str = tech["resistance_str"]
        self._trend_status = tech["trend_status"]

    def _set_fallback_financials(self, ticker: str) -> None:
        fb = get_fallback_financials(ticker)
        ratios = fb["ratios"]
        self._pe_ratio = ratios["pe_ratio"]
        self._pb_ratio = ratios["pb_ratio"]
        self._ev_ebitda = ratios["ev_ebitda"]
        self._div_yield = ratios["div_yield"]
        self._roe = ratios["roe"]
        self._net_debt_ebitda = ratios["net_debt_ebitda"]
        self._piotroski_score = ratios["piotroski_score"]
        self._current_ratio = ratios["current_ratio"]
        self._market_cap_str = ratios["market_cap_str"]

        self._financial_raw_data = fb["raw_data"]
        self._financial_periods = self._financial_raw_data.get("periods", [])
        self._has_financials = True
        self._recalculate_financial_bars()
        self._cached_metrics = self._financial_raw_data
        self._recalculate_all_fintech_models()

    def _set_fallback_shareholders(self, ticker: str) -> None:
        fb = get_fallback_shareholders(ticker)
        self._shareholder_date_str = fb["date_str"]
        self._free_float_ratio_str = fb["free_float_ratio_str"]
        self._free_float_pct = fb["free_float_pct"]
        self._paid_capital_str = fb["paid_capital_str"]
        self._shareholders_list = fb["shareholders_list"]
        self._shareholder_slices = fb["shareholder_slices"]
        self._has_shareholders = True
        if not self._shareholder_timeline:
            self._shareholder_timeline = fb["shareholder_timeline"]
