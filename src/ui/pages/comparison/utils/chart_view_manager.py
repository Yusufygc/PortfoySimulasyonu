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
    # Viewport Visibility Kontrolü
    # ------------------------------------------------------------------

    def check_viewport_visibility(self) -> None:
        """
        ScrollArea içerisindeki grafik panellerinin görünürlüğünü kontrol eder.
        Viewport içine giren panellerin QWebEngineView nesnelerini tembel olarak oluşturur
        ve eğer veri hazırsa asenkron render işlemini tetikler.
        """
        import sip
        try:
            if sip.isdeleted(self.page) or not hasattr(self.page, "scroll_area"):
                return
        except Exception:
            return

        scroll_area = self.page.scroll_area
        vbar = scroll_area.verticalScrollBar()
        if not vbar:
            return
            
        scroll_y = vbar.value()
        viewport = scroll_area.viewport()
        if not viewport:
            return
            
        viewport_height = viewport.height()

        for name in _CHART_NAMES:
            # Zaten oluşturulmuşsa atla
            if getattr(self.page, f"_{name}_chart_view", None) is not None:
                continue

            container = getattr(self.page, f"{name}_chart_container", None)
            if not container:
                continue

            from PyQt5.QtCore import QPoint
            scroll_widget = scroll_area.widget()
            if not scroll_widget:
                continue
                
            pos = container.mapTo(scroll_widget, QPoint(0, 0))
            top = pos.y()
            bottom = top + container.height()

            # Viewport ile kesişiyorsa (300px tolerans ile) oluştur
            if bottom >= scroll_y - 300 and top <= scroll_y + viewport_height + 300:
                self.get_or_create_view(name)
                # Veri hazırsa render işlemini tetikle
                df = getattr(self.page, "last_global_df", None)
                if df is not None and not df.empty and hasattr(self.page, "_renderer"):
                    if hasattr(self.page._renderer, "render_single_chart_async"):
                        self.page._renderer.render_single_chart_async(name, df)
