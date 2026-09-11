"""Bilanço ve Finansallar sayfası — orkestrasyon ve yaşam döngüsü."""
from __future__ import annotations

import logging

from src.qt_compat.qtcore import QThreadPool, Qt
from src.qt_compat.qtwidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QScrollArea, QVBoxLayout, QWidget
from src.ui.pages.base_page import BasePage
from src.ui.pages.financials.panels.ticker_input_panel import TickerInputPanel
from src.ui.pages.financials.panels.financials_chart_panel import FinancialsChartPanel
from src.ui.pages.financials.utils.dashboard_html import build_dashboard
from src.ui.shared.locale_tr import L10N
from src.ui.worker import Worker

logger = logging.getLogger(__name__)

_N_QUARTERS = 12
_N_PERIODS  = 8


class FinancialsPage(BasePage):
    """
    Bilanço ve Finansallar sayfası.

    Sorumluluk: layout + wiring + Worker orchestration.
    Grafik üretimi → dashboard_html.py (build_dashboard).
    Veri alımı     → container.financial_analysis_service (DI).
    """

    def __init__(self, container, parent=None) -> None:
        super().__init__(parent)
        self.container  = container
        self.page_title = L10N.BILANCO_VE_FINANSALLAR
        self._service   = container.financial_analysis_service
        self._pool      = QThreadPool()
        self._active_worker: Worker | None = None

        self._init_ui()

    # ------------------------------------------------------------------
    # UI kurulumu
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        # Başlık
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)

        lbl_title = QLabel(L10N.BILANCO_VE_FINANSALLAR)
        lbl_title.setProperty("cssClass", "pageTitle")
        title_col.addWidget(lbl_title)

        lbl_desc = QLabel(L10N.FINANSALLAR_SAYFA_ACIKLAMA)
        lbl_desc.setProperty("cssClass", "pageDescription")
        title_col.addWidget(lbl_desc)

        header.addLayout(title_col)
        header.addStretch()
        content_layout.addLayout(header)

        # Ticker giriş paneli
        self._input_panel = TickerInputPanel()
        self._input_panel.fetch_requested.connect(self._on_fetch_requested)
        content_layout.addWidget(self._input_panel)

        # Dönem seçici
        period_row = QHBoxLayout()
        period_row.addWidget(QLabel(L10N.DONEM + ":"))
        self._period_combo = QComboBox()
        self._period_combo.setProperty("cssClass", "customComboBox")
        self._period_combo.addItems(["4", "8", "12", "Tümü"])
        self._period_combo.setCurrentIndex(1)
        self._period_combo.setMinimumWidth(100)
        period_row.addWidget(self._period_combo)
        period_row.addStretch()
        content_layout.addLayout(period_row)

        # Durum etiketi
        self._status_label = QLabel("")
        self._status_label.setProperty("cssClass", "pageDescription")
        content_layout.addWidget(self._status_label)

        # Dashboard / WebView paneli
        self._chart_panel = FinancialsChartPanel()
        content_layout.addWidget(self._chart_panel, 1)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(scroll_content)

        self.main_layout.addWidget(self.scroll_area, 1)

    # ------------------------------------------------------------------
    # Worker orkestrasyon
    # ------------------------------------------------------------------

    def _on_fetch_requested(self, ticker: str) -> None:
        """Ticker ile analiz Worker'ı başlat (TRY)."""
        self._cancel_active_worker()
        self._input_panel.set_loading(True)
        self._status_label.setText(L10N.FINANSALLAR_YUKLENIYOR_TMPL.format(ticker=ticker))
        self._chart_panel.clear()

        worker = Worker(
            self._service.analyze,
            ticker,
            _N_QUARTERS,
        )
        worker.signals.result.connect(self._on_analysis_done)
        worker.signals.error.connect(self._on_analysis_error)
        worker.signals.cleanup.connect(self._on_worker_cleanup)
        self._active_worker = worker
        self._pool.start(worker)

    def _on_analysis_done(self, metrics: dict) -> None:
        """Analiz tamamlandı — HTML üret ve WebView'e yükle."""
        ticker = metrics.get("ticker", "")
        all_periods = metrics.get("periods", [])
        self._status_label.setText(
            L10N.FINANSALLAR_TAMAMLANDI_TMPL.format(ticker=ticker, n=len(all_periods))
        )
        try:
            sel = self._period_combo.currentText()
            n_periods = len(all_periods) if sel == "Tümü" else int(sel)
            html = build_dashboard(metrics, n_periods=n_periods)
            self._chart_panel.load_html(html)
        except Exception:
            logger.exception("Dashboard HTML üretilemedi [%s]", ticker)
            self._chart_panel.show_error(L10N.GRAFIK_YUKLENEMEDI)

    def _on_analysis_error(self, err_tuple: tuple) -> None:
        """Analiz hatası."""
        exc = err_tuple[1]
        logger.error("Finansal analiz hatası: %s", exc)
        self._status_label.setText(L10N.FINANSALLAR_HATA_TMPL.format(exc=exc))
        self._chart_panel.show_error(str(exc))

    def _on_worker_cleanup(self) -> None:
        self._active_worker = None
        self._input_panel.set_loading(False)

    def _cancel_active_worker(self) -> None:
        """Çalışan varsa temizle (pool'dan çıkarılamaz ama referansı bırak)."""
        self._active_worker = None

    # ------------------------------------------------------------------
    # Sayfa yaşam döngüsü
    # ------------------------------------------------------------------

    def on_page_enter(self) -> None:
        pass

    def on_page_leave(self) -> None:
        self._cancel_active_worker()
        self._chart_panel.cleanup()

    def load_ticker(self, ticker: str) -> None:
        clean = ticker.strip().upper()
        if not clean:
            return
        if hasattr(self, "_input_panel") and hasattr(self._input_panel, "_input"):
            self._input_panel._input.setText(clean)
        self._on_fetch_requested(clean)

    def closeEvent(self, event) -> None:
        self.on_page_leave()
        super().closeEvent(event)
