# src/ui/pages/optimization_page.py

from __future__ import annotations

from typing import Optional

from PyQt5.QtWidgets import (
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QFrame,
    QProgressBar,
    QMessageBox,
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal

from .base_page import BasePage
from src.domain.models.optimization_result import OptimizationResult
from src.ui.widgets.cards import MetricCard
from src.ui.widgets.tables.suggestions_table import SuggestionsTable
from src.ui.widgets.toast import Toast


class _OptimizationWorker(QThread):
    """
    Arka plan thread'inde optimizasyon çalıştırır.
    Ağır scipy hesaplaması ve yfinance ağ çağrıları UI'ı bloklamasın diye ayrı thread.
    """
    finished = pyqtSignal(object)   # OptimizationResult veya Exception
    error = pyqtSignal(str)

    def __init__(self, func, parent=None):
        super().__init__(parent)
        self._func = func

    def run(self):
        try:
            result = self._func()
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))


class OptimizationPage(BasePage):
    """
    Portföy Optimizasyonu sayfası.
    Markowitz Modern Portföy Teorisi ile Sharpe Oranını maximize eden
    optimal dağılımı hesaplar. Dashboard veya model portföyler üzerinde çalışır.
    """

    SOURCE_DASHBOARD = "dashboard"
    SOURCE_MODEL = "model"

    def __init__(self, container, price_lookup_func=None, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Portföy Optimizasyonu"
        self._optimization_service = container.optimization_service
        self._price_lookup_func = price_lookup_func
        self._worker: Optional[_OptimizationWorker] = None
        self._model_portfolios: list = []
        self._init_ui()

    # ------------------------------------------------------------------
    # UI Kurulumu
    # ------------------------------------------------------------------

    def _init_ui(self):
        # Başlık
        header = QHBoxLayout()
        lbl_title = QLabel("⚡ Portföy Optimizasyonu")
        lbl_title.setProperty("cssClass", "pageTitle")
        header.addWidget(lbl_title)
        header.addStretch()
        self.main_layout.addLayout(header)

        lbl_desc = QLabel(
            "Markowitz Modern Portföy Teorisi kullanarak Sharpe Oranını\n"
            "maksimize eden optimal portföy ağırlıklarını hesaplar."
        )
        lbl_desc.setProperty("cssClass", "pageDescription")
        self.main_layout.addWidget(lbl_desc)

        # Kaynak seçimi paneli
        self.main_layout.addWidget(self._build_source_panel())

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setMaximumHeight(4)
        self.progress_bar.setProperty("cssClass", "optimizationProgressBar")
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)

        # Metrik kartları
        self.main_layout.addWidget(self._build_metrics_panel())

        # Öneriler başlığı + tablo
        self.lbl_suggestions = QLabel("📋 Önerilen Dağılım")
        self.lbl_suggestions.setProperty("cssClass", "tableTitle")
        self.lbl_suggestions.setVisible(False)
        self.main_layout.addWidget(self.lbl_suggestions)

        self.suggestions_table = SuggestionsTable()
        self.suggestions_table.setVisible(False)
        self.main_layout.addWidget(self.suggestions_table)

        # Boş durum
        self.lbl_empty = QLabel("Bir portföy kaynağı seçin ve 'Optimize Et' butonuna tıklayın.")
        self.lbl_empty.setProperty("cssClass", "emptyStateText")
        self.lbl_empty.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.lbl_empty)

        self.main_layout.addStretch()

    def _build_source_panel(self) -> QFrame:
        """Kaynak seçimi ve Optimize Et butonu paneli."""
        frame = QFrame()
        frame.setProperty("cssClass", "panelFramePadded")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(15)

        lbl = QLabel("📂 Kaynak:")
        lbl.setProperty("cssClass", "panelTitle")
        layout.addWidget(lbl)

        self.combo_source = QComboBox()
        self.combo_source.setMinimumWidth(280)
        self.combo_source.setMinimumHeight(38)
        self.combo_source.setProperty("cssClass", "customComboBox")
        layout.addWidget(self.combo_source)
        layout.addStretch()

        self.btn_optimize = QPushButton("🚀 Optimize Et")
        self.btn_optimize.setCursor(Qt.PointingHandCursor)
        self.btn_optimize.setMinimumHeight(42)
        self.btn_optimize.setMinimumWidth(160)
        self.btn_optimize.setProperty("cssClass", "primaryButtonLarge")
        self.btn_optimize.clicked.connect(self._on_optimize)
        layout.addWidget(self.btn_optimize)

        return frame

    def _build_metrics_panel(self) -> QFrame:
        """Üç MetricCard widget'ını içeren panel."""
        self.metrics_frame = QFrame()
        metrics_layout = QHBoxLayout(self.metrics_frame)
        metrics_layout.setContentsMargins(0, 0, 0, 0)
        metrics_layout.setSpacing(15)

        self.card_return = MetricCard("📈 Beklenen Yıllık Getiri")
        self.card_risk   = MetricCard("📊 Risk (Volatilite)")
        self.card_sharpe = MetricCard("⭐ Sharpe Oranı")

        metrics_layout.addWidget(self.card_return)
        metrics_layout.addWidget(self.card_risk)
        metrics_layout.addWidget(self.card_sharpe)

        self.metrics_frame.setVisible(False)
        return self.metrics_frame

    # ------------------------------------------------------------------
    # Sayfa Yaşam Döngüsü
    # ------------------------------------------------------------------

    def on_page_enter(self):
        self._load_sources()

    def refresh_data(self):
        self._load_sources()

    def _load_sources(self):
        self.combo_source.clear()
        self.combo_source.addItem("🏠 Dashboard Portföyü", self.SOURCE_DASHBOARD)
        try:
            self._model_portfolios = self._optimization_service.get_model_portfolios()
            for mp in self._model_portfolios:
                self.combo_source.addItem(f"📊 {mp.name}", f"{self.SOURCE_MODEL}:{mp.id}")
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Optimizasyon İşlemi
    # ------------------------------------------------------------------

    def _on_optimize(self):
        source_data = self.combo_source.currentData()
        if source_data is None:
            Toast.warning(self, "Lütfen bir portföy kaynağı seçin.")
            return

        self._set_loading(True)

        if source_data == self.SOURCE_DASHBOARD:
            func = self._optimization_service.optimize_dashboard_portfolio
        else:
            portfolio_id = int(source_data.split(":")[1])
            func = lambda pid=portfolio_id: self._optimization_service.optimize_model_portfolio(
                pid, self._price_lookup_func
            )

        self._worker = _OptimizationWorker(func, self)
        self._worker.finished.connect(self._on_optimization_finished)
        self._worker.error.connect(self._on_optimization_error)
        self._worker.start()

    def _on_optimization_finished(self, result: OptimizationResult):
        self._set_loading(False)
        self._display_result(result)

    def _on_optimization_error(self, error_msg: str):
        self._set_loading(False)
        Toast.error(self, error_msg)

    def _set_loading(self, loading: bool):
        self.btn_optimize.setEnabled(not loading)
        self.btn_optimize.setText("⏳ Hesaplanıyor..." if loading else "🚀 Optimize Et")
        self.progress_bar.setVisible(loading)

    # ------------------------------------------------------------------
    # Sonuç Gösterimi
    # ------------------------------------------------------------------

    def _display_result(self, result: OptimizationResult):
        self.lbl_empty.setVisible(False)
        self.metrics_frame.setVisible(True)
        self.lbl_suggestions.setVisible(True)
        self.suggestions_table.setVisible(True)

        curr = result.current_metrics
        opt  = result.optimized_metrics

        self.card_return.update(
            current=f"%{curr.expected_return * 100:.2f}",
            optimal=f"%{opt.expected_return * 100:.2f}",
            delta=(opt.expected_return - curr.expected_return) * 100,
            positive_is_good=True,
        )
        self.card_risk.update(
            current=f"%{curr.volatility * 100:.2f}",
            optimal=f"%{opt.volatility * 100:.2f}",
            delta=(curr.volatility - opt.volatility) * 100,
            positive_is_good=True,
        )
        self.card_sharpe.update(
            current=f"{curr.sharpe_ratio:.3f}",
            optimal=f"{opt.sharpe_ratio:.3f}",
            delta=opt.sharpe_ratio - curr.sharpe_ratio,
            positive_is_good=True,
        )

        self.suggestions_table.populate(result.suggestions)
