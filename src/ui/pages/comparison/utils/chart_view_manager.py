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

from src.qt_compat.lifecycle import is_qobject_deleted as _is_qobject_deleted
from src.qt_compat.qtwidgets import QWidget
from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView
from src.ui.shared.locale_tr import L10N

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
        """QObject yaşam döngüsü kontrolüyle güvenli tembel başlatma."""
        if _is_qobject_deleted(self.page) or not self._page_is_active():
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
            if not _is_qobject_deleted(view):
                return view
            setattr(self.page, attr_name, None)

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
        self._apply_empty_state_if_needed(view)
        return view

    # ------------------------------------------------------------------
    # Viewport Visibility Kontrolü
    # ------------------------------------------------------------------

    def _process_chart_name_visibility(self, name, scroll_area, scroll_y, viewport_height, df) -> None:
        existing_view = getattr(self.page, f"_{name}_chart_view", None)
        if existing_view is not None and not _is_qobject_deleted(existing_view):
            return
        container = getattr(self.page, f"{name}_chart_container", None)
        if not container:
            return
        from src.qt_compat.qtcore import QPoint
        scroll_widget = scroll_area.widget()
        if not scroll_widget:
            return
        pos = container.mapTo(scroll_widget, QPoint(0, 0))
        top = pos.y()
        bottom = top + container.height()
        if bottom >= scroll_y - 300 and top <= scroll_y + viewport_height + 300:
            self.get_or_create_view(name)
            if hasattr(self.page, "_renderer"):
                if hasattr(self.page._renderer, "render_single_chart_async"):
                    self.page._renderer.render_single_chart_async(name, df)

    def check_viewport_visibility(self) -> None:
        """
        ScrollArea içerisindeki grafik panellerinin görünürlüğünü kontrol eder.
        Viewport içine giren panellerin QWebEngineView nesnelerini tembel olarak oluşturur
        ve eğer veri hazırsa asenkron render işlemini tetikler.
        """
        if (
            _is_qobject_deleted(self.page)
            or not self._page_is_active()
            or not hasattr(self.page, "scroll_area")
        ):
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
        df = getattr(self.page, "last_global_df", None)
        has_renderable_data = df is not None and not df.empty
        if not has_renderable_data:
            self._update_placeholders_for_empty_state()
            return
        for name in _CHART_NAMES:
            self._process_chart_name_visibility(name, scroll_area, scroll_y, viewport_height, df)

    def _page_is_active(self) -> bool:
        return getattr(self.page, "_comparison_page_active", True) is not False

    def _update_placeholders_for_empty_state(self) -> None:
        message = (
            getattr(self.page, "_comparison_empty_message", None)
            or L10N.LUTFEN_KIYASLANACAK_VARLIKLARI_SECIN
        )
        for name in _CHART_NAMES:
            placeholder = getattr(self.page, f"{name}_chart_placeholder", None)
            if placeholder and not _is_qobject_deleted(placeholder):
                placeholder.label.setText(message)

    def _apply_empty_state_if_needed(self, view: SilentWebEngineView) -> None:
        df = getattr(self.page, "last_global_df", None)
        message = (
            getattr(self.page, "_comparison_empty_message", None)
            or L10N.LUTFEN_KIYASLANACAK_VARLIKLARI_SECIN
        )
        if df is not None and not df.empty:
            return
        from src.ui.pages.comparison.utils.chart_renderer import _EMPTY_HTML
        view.setHtml(_EMPTY_HTML.format(message=message))
