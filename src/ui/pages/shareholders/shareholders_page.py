"""Ortaklık Yapısı sayfası — KAP pay sahipliği tarihçesi."""
from __future__ import annotations

import logging

from src.qt_compat.qtcore import QThreadPool, Signal
from src.qt_compat.qtwidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)
from src.ui.pages.base_page import BasePage
from src.ui.pages.financials.panels.financials_chart_panel import FinancialsChartPanel
from src.ui.pages.shareholders.utils.dashboard_html import build_dashboard
from src.ui.shared.locale_tr import L10N
from src.ui.worker import Worker

logger = logging.getLogger(__name__)


class ShareholdersPage(BasePage):
    """
    KAP Ortaklık Yapısı sayfası.

    Sorumluluk: layout + wiring + Worker orkestrasyon.
    Veri:   container.shareholder_analysis_service.get_history(ticker)
    Render: dashboard_html.build_dashboard(ticker, snapshots) → WebView
    """

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self.container  = container
        self.page_title = L10N.ORTAKLIK_YAPISI
        self._service   = container.shareholder_analysis_service
        self._pool      = QThreadPool()
        self._active_worker: Worker | None = None
        self._current_ticker: str = ""

        self._init_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        layout = self.main_layout
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Başlık
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        lbl_title = QLabel(L10N.ORTAKLIK_YAPISI)
        lbl_title.setProperty("cssClass", "pageTitle")
        title_col.addWidget(lbl_title)
        lbl_desc = QLabel(L10N.ORTAKLIK_YAPISI_ACIKLAMA)
        lbl_desc.setProperty("cssClass", "pageDescription")
        title_col.addWidget(lbl_desc)
        layout.addLayout(title_col)

        # Ticker giriş bar
        bar = QHBoxLayout()
        bar.addWidget(QLabel(L10N.HISSE_KODU))
        self._ticker_edit = QLineEdit()
        self._ticker_edit.setPlaceholderText(L10N.HISSE_KODU_ORN_THYAO)
        self._ticker_edit.setMaximumWidth(160)
        self._ticker_edit.returnPressed.connect(self._on_fetch)
        bar.addWidget(self._ticker_edit)

        self._btn_fetch = QPushButton(L10N.FINANSALLAR_GETIR)
        self._btn_fetch.setProperty("cssClass", "primaryButton")
        self._btn_fetch.clicked.connect(self._on_fetch)
        bar.addWidget(self._btn_fetch)

        self._btn_refresh = QPushButton(L10N.YENILE)
        self._btn_refresh.clicked.connect(self._on_force_refresh)
        bar.addWidget(self._btn_refresh)

        bar.addStretch()
        layout.addLayout(bar)

        # Durum etiketi
        self._status_label = QLabel("")
        self._status_label.setProperty("cssClass", "pageDescription")
        layout.addWidget(self._status_label)

        # WebView paneli
        self._chart_panel = FinancialsChartPanel()
        layout.addWidget(self._chart_panel, 1)

    # ------------------------------------------------------------------
    # Worker orkestrasyon
    # ------------------------------------------------------------------

    def _on_fetch(self) -> None:
        ticker = self._ticker_edit.text().strip().upper()
        if not ticker:
            return
        self._start_worker(ticker, force_refresh=False)

    def _on_force_refresh(self) -> None:
        ticker = self._current_ticker or self._ticker_edit.text().strip().upper()
        if not ticker:
            return
        self._start_worker(ticker, force_refresh=True)

    def _start_worker(self, ticker: str, force_refresh: bool) -> None:
        self._current_ticker = ticker
        self._set_loading(True)
        self._status_label.setText(L10N.ORTAKLIK_YUKLENIYOR_TMPL.format(ticker=ticker))
        self._chart_panel.clear()

        worker = Worker(self._service.get_history, ticker, force_refresh)
        worker.signals.result.connect(self._on_done)
        worker.signals.error.connect(self._on_error)
        worker.signals.cleanup.connect(self._on_cleanup)
        self._active_worker = worker
        self._pool.start(worker)

    def _on_done(self, snapshots) -> None:
        n = len(snapshots) if snapshots else 0
        self._status_label.setText(
            L10N.ORTAKLIK_TAMAMLANDI_TMPL.format(ticker=self._current_ticker, n=n)
        )
        try:
            html = build_dashboard(self._current_ticker, snapshots)
            self._chart_panel.load_html(html)
        except Exception:
            logger.exception("Ortaklık dashboard HTML üretilemedi")
            self._chart_panel.show_error(L10N.GRAFIK_YUKLENEMEDI)

    def _on_error(self, err_tuple: tuple) -> None:
        exc = err_tuple[1]
        logger.error("Ortaklık analizi hatası: %s", exc)
        self._status_label.setText(L10N.FINANSALLAR_HATA_TMPL.format(exc=exc))
        self._chart_panel.show_error(str(exc))

    def _on_cleanup(self) -> None:
        self._active_worker = None
        self._set_loading(False)

    def _set_loading(self, loading: bool) -> None:
        self._btn_fetch.setEnabled(not loading)
        self._btn_refresh.setEnabled(not loading)
        self._ticker_edit.setEnabled(not loading)
        self._btn_fetch.setText(L10N.YUKLENIYOR if loading else L10N.FINANSALLAR_GETIR)

    # ------------------------------------------------------------------
    # Yaşam döngüsü
    # ------------------------------------------------------------------

    def on_page_enter(self) -> None:
        pass

    def on_page_leave(self) -> None:
        self._chart_panel.cleanup()

    def load_ticker(self, ticker: str) -> None:
        clean = ticker.strip().upper()
        if not clean:
            return
        self._ticker_edit.setText(clean)
        self._on_fetch()

    def closeEvent(self, event) -> None:
        self.on_page_leave()
        super().closeEvent(event)
