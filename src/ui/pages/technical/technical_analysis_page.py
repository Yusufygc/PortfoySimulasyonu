"""Teknik Analiz sayfası — Golden / Death Cross taraması (sidebar)."""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from src.qt_compat.qtcore import QThreadPool, Qt
from src.qt_compat.qtwidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from src.domain.models.golden_cross_event import CrossType
from src.ui.pages.base_page import BasePage
from src.ui.pages.financials.panels.financials_chart_panel import FinancialsChartPanel
from src.ui.pages.technical.utils.detail_chart_html import build_detail_dashboard
from src.ui.shared.locale_tr import L10N
from src.ui.worker import Worker

logger = logging.getLogger(__name__)

_PRICE_LOOKBACK_DAYS = 365 * 5  # detay grafik için 5 yıllık veri


class TechnicalAnalysisPage(BasePage):
    """SMA50/SMA200 cross tarama sayfası — 2 sekme."""

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self.container = container
        self.page_title = L10N.TEKNIK_ANALIZ
        self._service = container.technical_analysis_service
        self._tv_backfill_service = getattr(container, "tv_backfill_service", None)
        self._price_repo = container.price_repo
        self._stock_repo = container.stock_repo
        self._pool = QThreadPool()
        self._active_worker: Worker | None = None
        self._current_ticker: str = ""

        self._init_ui()
        # İlk açılışta otomatik olarak son sinyalleri getir
        self._on_refresh_recent()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        layout = self.main_layout
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        # Başlık
        title = QLabel(L10N.TEKNIK_ANALIZ)
        title.setProperty("cssClass", "pageTitle")
        layout.addWidget(title)
        desc = QLabel(L10N.TEKNIK_ANALIZ_ACIKLAMA)
        desc.setProperty("cssClass", "pageDescription")
        layout.addWidget(desc)

        # Üst kontrol çubuğu — Tarama butonu + Veri Tamamla + status
        top = QHBoxLayout()
        self._btn_scan = QPushButton(L10N.TARAMAYI_CALISTIR)
        self._btn_scan.setProperty("cssClass", "primaryButton")
        self._btn_scan.clicked.connect(self._on_scan_all)
        top.addWidget(self._btn_scan)

        self._btn_backfill = QPushButton(L10N.VERI_TAMAMLA)
        self._btn_backfill.setProperty("cssClass", "secondaryButton")
        self._btn_backfill.clicked.connect(self._on_backfill_all)
        top.addWidget(self._btn_backfill)

        self._btn_tv_backfill = QPushButton(L10N.TV_DEN_YUKLE)
        self._btn_tv_backfill.setProperty("cssClass", "secondaryButton")
        self._btn_tv_backfill.clicked.connect(self._on_tv_backfill)
        if self._tv_backfill_service is None:
            self._btn_tv_backfill.setEnabled(False)
            self._btn_tv_backfill.setToolTip(L10N.TV_KURULU_DEGIL)
        top.addWidget(self._btn_tv_backfill)

        self._status_label = QLabel("")
        self._status_label.setProperty("cssClass", "pageDescription")
        top.addWidget(self._status_label)
        top.addStretch()
        layout.addLayout(top)

        # Sekmeler
        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_recent_tab(), L10N.SON_SINYALLER)
        self._tabs.addTab(self._build_detail_tab(), L10N.TICKER_DETAY)
        layout.addWidget(self._tabs, 1)

    def _build_recent_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(8)

        # Filtre row
        filt = QHBoxLayout()
        filt.addWidget(QLabel(L10N.DONEM + ":"))
        self._days_combo = QComboBox()
        self._days_combo.addItems(["7", "30", "90", "180", "365", "Tümü"])
        self._days_combo.setCurrentIndex(1)
        self._days_combo.setMaximumWidth(80)
        self._days_combo.currentIndexChanged.connect(self._on_refresh_recent)
        filt.addWidget(self._days_combo)

        filt.addWidget(QLabel(L10N.TIP + ":"))
        self._type_combo = QComboBox()
        self._type_combo.addItem(L10N.HEPSI, None)
        self._type_combo.addItem("Golden", CrossType.GOLDEN)
        self._type_combo.addItem("Death", CrossType.DEATH)
        self._type_combo.setMaximumWidth(120)
        self._type_combo.currentIndexChanged.connect(self._on_refresh_recent)
        filt.addWidget(self._type_combo)

        btn_refresh = QPushButton(L10N.YENILE)
        btn_refresh.clicked.connect(self._on_refresh_recent)
        filt.addWidget(btn_refresh)
        filt.addStretch()
        v.addLayout(filt)

        # Tablo
        self._tbl = QTableWidget(0, 5)
        self._tbl.setHorizontalHeaderLabels([
            L10N.TARIH, L10N.HISSE_KODU, L10N.TIP, L10N.KAPANIS, "EMA50 / EMA200",
        ])
        self._tbl.verticalHeader().setVisible(False)
        self._tbl.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._tbl.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._tbl.setSortingEnabled(True)
        hdr = self._tbl.horizontalHeader()
        hdr.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._tbl.cellDoubleClicked.connect(self._on_row_double_clicked)
        v.addWidget(self._tbl, 1)
        return w

    def _build_detail_tab(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(8)

        bar = QHBoxLayout()
        bar.addWidget(QLabel(L10N.HISSE_KODU))
        self._ticker_edit = QLineEdit()
        self._ticker_edit.setPlaceholderText(L10N.HISSE_KODU_ORN_THYAO)
        self._ticker_edit.setMaximumWidth(160)
        self._ticker_edit.returnPressed.connect(self._on_load_detail)
        bar.addWidget(self._ticker_edit)
        self._btn_show = QPushButton(L10N.GOSTER)
        self._btn_show.setProperty("cssClass", "primaryButton")
        self._btn_show.clicked.connect(self._on_load_detail)
        bar.addWidget(self._btn_show)
        bar.addStretch()
        v.addLayout(bar)

        self._chart_panel = FinancialsChartPanel()
        v.addWidget(self._chart_panel, 1)
        return w

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_scan_all(self) -> None:
        self._status_label.setText(L10N.TARAMA_BASLATILDI)
        self._btn_scan.setEnabled(False)
        self._btn_backfill.setEnabled(False)
        worker = Worker(self._service.scan_all)
        worker.signals.result.connect(self._on_scan_done)
        worker.signals.error.connect(self._on_scan_error)
        worker.signals.cleanup.connect(lambda: [self._btn_scan.setEnabled(True), self._btn_backfill.setEnabled(True)])
        self._pool.start(worker)

    def _on_scan_done(self, result) -> None:
        self._status_label.setText(
            L10N.TARAMA_TAMAMLANDI_TMPL.format(
                scanned=result.scanned_count,
                new=result.new_event_count,
                skipped=result.skipped_count,
            )
        )
        self._on_refresh_recent()

    def _on_scan_error(self, err_tuple) -> None:
        self._status_label.setText(L10N.TARAMA_HATA_TMPL.format(exc=err_tuple[1]))

    def _on_backfill_all(self) -> None:
        self._status_label.setText(L10N.VERI_TAMAMLAMA_BASLATILDI)
        self._btn_scan.setEnabled(False)
        self._btn_backfill.setEnabled(False)

        from src.ui.main_window import last_completed_trading_day
        from src.application.services.market.price_data_health_service import PRICE_SCOPE_ALL_BIST

        target_date = last_completed_trading_day(
            date.today(),
            getattr(self.container, "trading_calendar", None),
        )

        service = getattr(self.container, "price_data_health_service", None)
        if service is None:
            self._status_label.setText(L10N.HATA_TEK_SATIR_TMPL.format(exc="PriceDataHealthService not found"))
            self._btn_scan.setEnabled(True)
            self._btn_backfill.setEnabled(True)
            return

        worker = Worker(service.update_from_latest_to_today, target_date, PRICE_SCOPE_ALL_BIST)
        worker.signals.result.connect(self._on_backfill_done)
        worker.signals.error.connect(self._on_backfill_error)
        worker.signals.cleanup.connect(self._on_backfill_cleanup)
        self._pool.start(worker)

    def _on_backfill_done(self, result) -> None:
        updated_count = getattr(result, "updated_count", 0)
        self._status_label.setText(L10N.VERI_TAMAMLAMA_TAMAMLANDI_TMPL.format(count=updated_count))
        self._on_refresh_recent()

    def _on_backfill_error(self, err_tuple) -> None:
        self._status_label.setText(L10N.VERI_TAMAMLAMA_HATA_TMPL.format(exc=err_tuple[1]))

    def _on_backfill_cleanup(self) -> None:
        self._btn_scan.setEnabled(True)
        self._btn_backfill.setEnabled(True)

    # ------------------------------------------------------------------
    # TV Backfill
    # ------------------------------------------------------------------

    def _on_tv_backfill(self) -> None:
        if self._tv_backfill_service is None:
            self._status_label.setText(L10N.TV_KURULU_DEGIL)
            return
        self._status_label.setText(L10N.TV_YUKLEME_BASLATILDI)
        self._btn_scan.setEnabled(False)
        self._btn_backfill.setEnabled(False)
        self._btn_tv_backfill.setEnabled(False)

        from datetime import timedelta
        end = date.today()
        start = end - timedelta(days=int(10 * 365.25))

        worker = Worker(self._tv_backfill_service.backfill_range, start, end)
        worker.signals.result.connect(self._on_tv_backfill_done)
        worker.signals.error.connect(self._on_tv_backfill_error)
        worker.signals.cleanup.connect(self._on_tv_backfill_cleanup)
        self._pool.start(worker)

    def _on_tv_backfill_done(self, count) -> None:
        self._status_label.setText(L10N.TV_YUKLEME_TAMAMLANDI_TMPL.format(count=count))
        self._on_refresh_recent()

    def _on_tv_backfill_error(self, err_tuple) -> None:
        self._status_label.setText(L10N.TV_YUKLEME_HATA_TMPL.format(exc=err_tuple[1]))

    def _on_tv_backfill_cleanup(self) -> None:
        self._btn_scan.setEnabled(True)
        self._btn_backfill.setEnabled(True)
        if self._tv_backfill_service is not None:
            self._btn_tv_backfill.setEnabled(True)

    def _on_row_double_clicked(self, row: int, column: int) -> None:
        ticker_item = self._tbl.item(row, 1)
        if ticker_item is not None:
            ticker = ticker_item.text().strip().upper()
            self._tabs.setCurrentIndex(1)
            self._ticker_edit.setText(ticker)
            self._on_load_detail()

    def _on_refresh_recent(self) -> None:
        sel = self._days_combo.currentText()
        days = 365 * 20 if sel == "Tümü" else int(sel)
        cross_type = self._type_combo.currentData()
        try:
            events = self._service.get_recent_events(days=days, cross_type=cross_type, limit=500)
        except Exception:
            logger.exception("Recent events alınamadı")
            events = []
        self._populate_table(events)

    def _populate_table(self, events) -> None:
        self._tbl.setSortingEnabled(False)
        self._tbl.setRowCount(len(events))
        for row, e in enumerate(events):
            tip_txt = "▲ Golden" if e.cross_type == CrossType.GOLDEN else "▼ Death"
            color = Qt.GlobalColor.green if e.cross_type == CrossType.GOLDEN else Qt.GlobalColor.red
            tip_item = QTableWidgetItem(tip_txt)
            tip_item.setForeground(color)
            ma_txt = f"{_fmt(e.short_ma)} / {_fmt(e.long_ma)}"
            cells = [
                QTableWidgetItem(e.cross_date.strftime("%d/%m/%Y")),
                QTableWidgetItem(e.ticker),
                tip_item,
                QTableWidgetItem(_fmt(e.close_price)),
                QTableWidgetItem(ma_txt),
            ]
            for col, item in enumerate(cells):
                if col >= 3:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self._tbl.setItem(row, col, item)
        self._tbl.setSortingEnabled(True)
        self._status_label.setText(L10N.SINYAL_SAYISI_TMPL.format(n=len(events)))

    def _on_load_detail(self) -> None:
        ticker = self._ticker_edit.text().strip().upper()
        if not ticker:
            return
        self._current_ticker = ticker
        self._btn_show.setEnabled(False)
        self._chart_panel.clear()
        worker = Worker(self._load_detail_data, ticker)
        worker.signals.result.connect(self._on_detail_done)
        worker.signals.error.connect(self._on_detail_error)
        worker.signals.cleanup.connect(lambda: self._btn_show.setEnabled(True))
        self._pool.start(worker)

    def _load_detail_data(self, ticker: str) -> dict:
        stock = self._stock_repo.get_stock_by_ticker(ticker)
        if stock is None or stock.id is None:
            return {"ticker": ticker, "prices": [], "events": []}
        today = date.today()
        start = today - timedelta(days=_PRICE_LOOKBACK_DAYS)
        prices = self._price_repo.get_price_series(stock.id, start, today)
        events = self._service.get_events_for_ticker(ticker)
        return {"ticker": ticker, "prices": prices, "events": events}

    def _on_detail_done(self, data: dict) -> None:
        html = build_detail_dashboard(
            ticker=data["ticker"],
            prices=data["prices"],
            events=data["events"],
        )
        self._chart_panel.load_html(html)

    def _on_detail_error(self, err_tuple) -> None:
        logger.error("Detay grafik hatası: %s", err_tuple[1])
        self._chart_panel.show_error(str(err_tuple[1]))

    # ------------------------------------------------------------------
    # Yaşam döngüsü
    # ------------------------------------------------------------------

    def load_ticker(self, ticker: str) -> None:
        clean = ticker.strip().upper()
        if not clean:
            return
        self._tabs.setCurrentIndex(1)
        self._ticker_edit.setText(clean)
        self._on_load_detail()

    def on_page_leave(self) -> None:
        self._chart_panel.cleanup()


def _fmt(v) -> str:
    if v is None:
        return "—"
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return str(v)
