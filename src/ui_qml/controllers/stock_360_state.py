"""Hisse 360 görünüm durumu: başlangıç değerleri ve hesaplanmış sonuçların duruma yazılması (sinyal yayınlamaz, Qt'siz)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.domain.models.shareholder import ShareholderSnapshot
from src.ui_qml.controllers.stock_360_calc import parse_valuation_ratios, compute_financial_bars, compute_financial_table_rows, compute_shareholder_timeline, parse_shareholder_data
from src.ui_qml.controllers.stock_360_fallback import get_default_overview, get_default_technical, get_fallback_shareholders
from src.ui_qml.messages import msg



class Stock360StateMixin:
    def _init_identity_state(self) -> None:
        self._current_ticker: str = "BIMAS"
        self._company_name: str = msg("stock360.bim_birlesik_magazalar_a_s")
        self._sector: str = "Perakende Ticaret"
        self._is_loading: bool = False
        self._error_message: str = ""
        self._available_stocks: List[str] = []

    def _init_overview_and_technical_state(self) -> None:
        # Genel Bakış
        self._last_price_str: str = "₺0,00"
        self._last_price_raw: float = 0.0
        self._last_price_date_str: str = "—"
        self._daily_change_str: str = "%0,00"
        self._daily_change_raw: float = 0.0
        self._is_daily_positive: bool = True
        self._volume_str: str = "0"
        self._week52_low_str: str = "₺0,00"
        self._week52_high_str: str = "₺0,00"
        self._week52_range_pct: float = 0.5

        # Teknik Seviyeler
        self._rsi14_str: str = "—"
        self._rsi_status: str = msg("stock360.notr")
        self._macd_line_str: str = "—"
        self._macd_signal_str: str = "—"
        self._sma50_str: str = "—"
        self._sma200_str: str = "—"
        self._ema20_str: str = "—"
        self._support_str: str = "—"
        self._resistance_str: str = "—"
        self._trend_status: str = "Dengeli"

    def _init_financial_state(self) -> None:
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

    def _init_shareholder_state(self) -> None:
        self._shareholders_list: List[Dict[str, Any]] = []
        self._shareholder_slices: List[Dict[str, Any]] = []
        self._free_float_ratio_str: str = "—"
        self._free_float_pct: float = 0.0
        self._paid_capital_str: str = "—"
        self._shareholder_date_str: str = "—"
        self._has_shareholders: bool = False

    def _init_html_and_fintech_state(self) -> None:
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
        self._apply_ratios(parse_valuation_ratios(f))

    def _apply_ratios(self, ratios: Dict[str, str]) -> None:
        self._pe_ratio = ratios["pe_ratio"]
        self._pb_ratio = ratios["pb_ratio"]
        self._ev_ebitda = ratios["ev_ebitda"]
        self._div_yield = ratios["div_yield"]
        self._market_cap_str = ratios["market_cap_str"]
        self._roe = ratios["roe"]
        self._net_debt_ebitda = ratios["net_debt_ebitda"]
        self._piotroski_score = ratios["piotroski_score"]
        self._current_ratio = ratios["current_ratio"]

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

    def _apply_overview(self, ov: Dict[str, Any]) -> None:
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

    def _apply_technical(self, tech: Dict[str, Any]) -> None:
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

    def _set_default_overview(self, ticker: str) -> None:
        self._apply_overview(get_default_overview(ticker))

    def _set_default_technical(self) -> None:
        self._apply_technical(get_default_technical())

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
