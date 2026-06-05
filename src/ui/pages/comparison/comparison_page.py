# src/ui/pages/comparison/comparison_page.py
"""Karşılaştırma Laboratuvarı sayfası — orkestrasyon ve yaşam döngüsü."""
from __future__ import annotations
from src.ui.shared.locale_tr import L10N

import logging
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget
from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView

from src.ui.pages.base_page import BasePage
from src.ui.pages.comparison.widgets.ribbon_bar import ComparisonRibbonBar

# Re-export: Test dosyası bu isimleri doğrudan buradan import ediyor
from src.ui.pages.comparison.widgets.chart_panels import (  # noqa: F401
    WheelRedirectFilter,
    ChartPlaceholder,
    ChartInfoCard,
    ChartPanel,
)
from src.ui.pages.comparison.widgets.ui_builder import ComparisonUIBuilder
from src.ui.pages.comparison.utils.ai_helper import AICommentaryHelper
from src.ui.pages.comparison.utils.chart_view_manager import ChartViewManager
from src.ui.pages.comparison.utils.comparison_data_manager import ComparisonDataManager
from src.ui.pages.comparison.utils.chart_renderer import ChartRenderer

logger = logging.getLogger(__name__)


class ComparisonPage(BasePage):
    """
    Karşılaştırma Laboratuvarı ana sayfası.

    Yalnızca orkestrasyon ve yaşam döngüsü:
      - UI builder çağrısı
      - Helper sınıflar arası sinyal bağlantısı
      - on_page_enter / on_page_leave / closeEvent
    """

    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = L10N.KARSILASTIRMA_LABORATUVARI
        self.analysis_service = container.analysis_service

        # Paylaşılan durum
        self._request_seq = 0
        self._temp_files: list[str] = []
        self.chart_overrides: dict[str, str | None] = {}
        self.last_global_df = None
        self.code_to_label: dict[str, str] = {}

        # Helper'lar
        self.ai_helper = AICommentaryHelper(self)
        self._ui_builder = ComparisonUIBuilder(self)
        self._view_manager = ChartViewManager(self)
        self._data_manager = ComparisonDataManager(self, self.analysis_service)
        self._renderer = ChartRenderer(self)

        self._init_ui()
        self._data_manager.load_initial_options()

    # ------------------------------------------------------------------
    # UI Kurulumu
    # ------------------------------------------------------------------

    def _init_ui(self) -> None:
        layout = self.main_layout
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        # Başlık + açıklama
        from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        lbl_title = QLabel(L10N.KARSILASTIRMA_LABORATUVARI)
        lbl_title.setProperty("cssClass", "pageTitle")
        title_col.addWidget(lbl_title)
        lbl_desc = QLabel(
            L10N.VARLIKLARI_BENCHMARKLARI_VE_PORTFOYLERI_RASYO +
            L10N.DRAWDOWN_VE_RISKGETIRI_BAZINDA_KIYASLAYIN
        )
        lbl_desc.setProperty("cssClass", "pageDescription")
        title_col.addWidget(lbl_desc)
        header.addLayout(title_col)
        layout.addLayout(header)

        # Ribbon bar
        self.ribbon_bar = ComparisonRibbonBar()
        self.ribbon_bar.filter_changed.connect(self._request_refresh)
        layout.addWidget(self.ribbon_bar)

        # Uyarı paneli
        self._ui_builder.build_warning_panel(layout)

        # Scroll area
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 10, 0, 0)
        scroll_layout.setSpacing(20)

        self._ui_builder.build_all_chart_panels(scroll_layout)
        self.ribbon_bar.combo_mode.currentTextChanged.connect(self._update_main_info_card)
        self._update_main_info_card(self.ribbon_bar.selected_mode())
        scroll_layout.addWidget(self.ai_helper.build_panel())

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setWidget(scroll_content)
        layout.addWidget(self.scroll_area, 1)

        # Wheel filtresi
        self.wheel_redirect_filter = WheelRedirectFilter(self.scroll_area)
        
        # Scroll olayını dinle ve görünürlüğe göre lazy yükleme yap
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_bar.valueChanged.connect(lambda: self._view_manager.check_viewport_visibility())
        
        # İlk görünürlük kontrolünü biraz gecikmeli yap (UI layout oturduktan sonra)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._view_manager.check_viewport_visibility())

    # ------------------------------------------------------------------
    # WebEngine view properties (lazy)
    # ------------------------------------------------------------------

    @property
    def main_chart_view(self) -> SilentWebEngineView:
        return self._view_manager.get_or_create_view("main")

    @property
    def drawdown_chart_view(self) -> SilentWebEngineView:
        return self._view_manager.get_or_create_view("drawdown")

    @property
    def periodic_chart_view(self) -> SilentWebEngineView:
        return self._view_manager.get_or_create_view("periodic")

    @property
    def scatter_chart_view(self) -> SilentWebEngineView:
        return self._view_manager.get_or_create_view("scatter")

    @property
    def treemap_chart_view(self) -> SilentWebEngineView:
        return self._view_manager.get_or_create_view("treemap")

    # ------------------------------------------------------------------
    # Yönlendirici metodlar (public API)
    # ------------------------------------------------------------------

    def on_page_enter(self) -> None:
        self._data_manager.on_page_enter()

    def _request_refresh(self) -> None:
        self._data_manager.request_refresh()

    def _update_main_info_card(self, mode: str) -> None:
        """Grafik modu değiştiğinde ana grafik bilgi kartını günceller."""
        if not hasattr(self, "main_info_card"):
            return
        if mode == L10N.RASYO_MODU:
            self.main_info_card.update_content(
                L10N.ANA_PERFORMANS_KIYASLAMA_GRAFIGI,
                L10N.ANA_PERFORMANS_RASYO_NEDIR,
                L10N.ANA_PERFORMANS_RASYO_YORUM,
                "ratio",
            )
            return
        self.main_info_card.update_content(
            L10N.ANA_PERFORMANS_KIYASLAMA_GRAFIGI,
            L10N.ANA_PERFORMANS_NORMAL_NEDIR,
            L10N.ANA_PERFORMANS_NORMAL_YORUM,
            "normal",
        )

    def handle_chart_portfolio_selected(
        self, chart_key: str, portfolio_code: str | None
    ) -> None:
        self._data_manager.handle_chart_portfolio_selected(chart_key, portfolio_code)

    def _check_date_warnings(self) -> list[str]:
        """Test uyumluluğu için proxy."""
        return self._data_manager.check_date_warnings()

    def _update_table_height(self) -> None:
        """Test uyumluluğu için proxy."""
        self._renderer._update_table_height()

    def _generate_ai_commentary(self) -> None:
        self.ai_helper.generate_commentary()

    # ------------------------------------------------------------------
    # Sayfa yaşam döngüsü
    # ------------------------------------------------------------------

    def on_page_leave(self) -> None:
        import os
        if hasattr(self, "_view_temp_files"):
            for path in list(self._view_temp_files.values()):
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except OSError:
                    pass
            self._view_temp_files.clear()
        for path in list(self._temp_files):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        self._temp_files.clear()
        self.ai_helper.cleanup()

    def closeEvent(self, event) -> None:
        self.on_page_leave()
        super().closeEvent(event)
