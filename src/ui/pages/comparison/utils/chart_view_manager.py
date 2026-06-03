"""
utils/chart_view_manager.py
---------------------------
QWebEngineView nesnelerinin tembel (lazy) oluşturulmasını ve
scroll wheel filtrelerinin kurulumunu yönetir.

ComparisonPage tarafından Facade deseninde kullanılır.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PyQt5.QtWidgets import QWidget
from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView

if TYPE_CHECKING:
    from src.ui.pages.comparison.comparison_page import ComparisonPage

logger = logging.getLogger(__name__)

# Grafik adları → layout/placeholder attribute isimleri için sabit liste
_CHART_NAMES = ("main", "drawdown", "periodic", "scatter", "treemap")


class ChartViewManager:
    """
    ComparisonPage içindeki beş QWebEngineView'u tembel başlatır ve
    WheelRedirectFilter'ı her view'a kurar.

    Attributes:
        page: Sahibi olan ComparisonPage nesnesi.
    """

    def __init__(self, page: ComparisonPage) -> None:
        self.page = page

    # ------------------------------------------------------------------
    # Wheel filter kurulumu
    # ------------------------------------------------------------------

    def install_filters_on_children(self, view: SilentWebEngineView) -> None:
        """View ve tüm alt widget'larına wheel filtresi kurar."""
        if not hasattr(self.page, "wheel_redirect_filter"):
            return
        filt = self.page.wheel_redirect_filter
        view.installEventFilter(filt)
        proxy = view.focusProxy()
        if proxy:
            proxy.installEventFilter(filt)
        for child in view.findChildren(QWidget):
            child.installEventFilter(filt)

    # ------------------------------------------------------------------
    # Lazy init
    # ------------------------------------------------------------------

    def lazy_init_view_safe(self, name: str) -> None:
        """sip.isdeleted kontrolüyle güvenli tembel başlatma."""
        import sip
        try:
            if sip.isdeleted(self.page):
                return
        except Exception:
            return
        self.get_or_create_view(name)

    def get_or_create_view(self, name: str) -> SilentWebEngineView:
        """
        İsimlendirilmiş bir QWebEngineView döner; yoksa oluşturur ve
        sayfanın ilgili layout'una ekler.
        """
        attr_name = f"_{name}_chart_view"
        view = getattr(self.page, attr_name, None)
        if view is not None:
            return view

        view = SilentWebEngineView()
        view.setMinimumHeight(600)

        # Wheel filtresi bağla
        if hasattr(self.page, "wheel_redirect_filter"):
            view.loadFinished.connect(
                lambda ok, v=view: self.install_filters_on_children(v)
            )
            self.install_filters_on_children(view)

        # Placeholder'ı kaldır, view'u layout'a ekle
        layout_attr = f"{name}_chart_layout"
        layout = getattr(self.page, layout_attr, None)
        if layout:
            placeholder_attr = f"{name}_chart_placeholder"
            placeholder = getattr(self.page, placeholder_attr, None)
            if placeholder:
                layout.removeWidget(placeholder)
                placeholder.deleteLater()
                setattr(self.page, placeholder_attr, None)
            layout.addWidget(view)

        setattr(self.page, attr_name, view)
        return view

    # ------------------------------------------------------------------
    # Tüm view'ları kademeli (staggered) başlat
    # ------------------------------------------------------------------

    def schedule_staggered_init(self) -> None:
        """
        Uygulama başlangıcında UI donmalarını önlemek için
        her view'u 150 ms aralıkla başlatır.
        """
        from PyQt5.QtCore import QTimer
        delays = {"main": 150, "drawdown": 300, "periodic": 450,
                  "scatter": 600, "treemap": 750}
        for name, delay in delays.items():
            QTimer.singleShot(
                delay,
                lambda n=name: self.lazy_init_view_safe(n)
            )
