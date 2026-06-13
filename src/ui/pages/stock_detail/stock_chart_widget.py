# src/ui/pages/stock_detail/stock_chart_widget.py

from __future__ import annotations
from src.ui.shared.locale_tr import L10N

import bisect
import logging
from datetime import date, datetime, time, timedelta

import pyqtgraph as pg
from src.qt_compat.qtcore import Qt, QPointF, QThreadPool
from src.qt_compat.qtwidgets import QFrame, QSizePolicy, QVBoxLayout

from src.ui.formatters import display_ticker
from src.ui.worker import Worker

logger = logging.getLogger(__name__)

BG_BASE = "#0f172a"
BORDER = "#334155"
TEXT_PRIMARY = "#f1f5f9"
TEXT_SECONDARY = "#94a3b8"
LINE_BLUE = "#3b82f6"
LINE_CURRENT = "#10b981"
LINE_AVG_COST = "#f59e0b"
CROSSHAIR_COLOR = "#64748b"


def _format_date_tr(dt: datetime, with_year: bool = False) -> str:
    """Türkçe ay kısaltmasıyla tarih formatı: '15 Oca' veya '15 Oca 2026'."""
    month = L10N.AYLAR_KISA[dt.month - 1]
    if with_year:
        return f"{dt.day:02d} {month} {dt.year}"
    return f"{dt.day:02d} {month}"


def _format_tr_currency(value: float) -> str:
    """TR locale para formatı: ``₺ 1.234,56``."""
    text = f"{value:,.2f}"  # "1,234.56"
    int_part, dec_part = text.split(".")
    int_part = int_part.replace(",", ".")
    return f"₺ {int_part},{dec_part}"


class DateAxisItem(pg.AxisItem):
    """Tarih ekseni — Türkçe ay kısaltmalarıyla tick yazar."""

    def tickStrings(self, values, scale, spacing):  # noqa: N802 - pyqtgraph API
        labels = []
        for value in values:
            try:
                labels.append(_format_date_tr(datetime.fromtimestamp(value)))
            except (OSError, OverflowError, ValueError):
                labels.append("")
        return labels


class CurrencyAxisItem(pg.AxisItem):
    """Sol eksen — değerleri ``₺ 1.234,56`` biçiminde gösterir."""

    def tickStrings(self, values, scale, spacing):  # noqa: N802 - pyqtgraph API
        labels = []
        for value in values:
            try:
                labels.append(_format_tr_currency(float(value)))
            except (TypeError, ValueError):
                labels.append("")
        return labels


class StockChartWidget(QFrame):
    """Hisse fiyat grafiğini çizen bağımsız bileşen."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "chartWidget")
        self.setMinimumHeight(320)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._price_series_provider = None
        self._chart_points: list[tuple[float, float]] = []
        self._init_ui()

    def set_price_series_provider(self, provider) -> None:
        """DB serisi boşken kullanılacak fiyat serisi sağlayıcısını enjekte eder.

        UI doğrudan piyasaya (yfinance) gitmez; sağlayıcı container'daki
        market client'tan gelir: ``(ticker, start, end) -> dict[date, Decimal]``.
        """
        self._price_series_provider = provider

    def _init_ui(self):
        pg.setConfigOptions(antialias=True, background=BG_BASE, foreground=TEXT_SECONDARY)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plot_widget = pg.PlotWidget(axisItems={
            "bottom": DateAxisItem(orientation="bottom"),
            "left": CurrencyAxisItem(orientation="left"),
        })
        self.plot_widget.setBackground(BG_BASE)
        self.plot_widget.setMinimumHeight(320)
        self.plot_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self.plot_widget)
        self._reference_legend = None

        self._configure_plot_item()
        self._install_crosshair()
        self.draw_empty_chart(L10N.GRAFIK_VERISI_BEKLENIYOR)

    def _configure_plot_item(self) -> None:
        plot_item = self.plot_widget.getPlotItem()
        plot_item.showGrid(x=True, y=True, alpha=0.14)
        plot_item.setMenuEnabled(False)
        plot_item.hideButtons()
        plot_item.setLabel("bottom", L10N.TARIH, color=TEXT_SECONDARY)
        plot_item.setLabel("left", "", color=TEXT_SECONDARY)
        plot_item.setContentsMargins(8, 8, 12, 8)
        for axis_name in ("left", "bottom"):
            axis = plot_item.getAxis(axis_name)
            axis.setPen(pg.mkPen(BORDER))
            axis.setTextPen(pg.mkPen(TEXT_SECONDARY))
            axis.setStyle(tickTextOffset=8)
            if hasattr(axis, "enableAutoSIPrefix"):
                axis.enableAutoSIPrefix(False)

    def _install_crosshair(self) -> None:
        """Mouse-over crosshair (vLine/hLine) + tarih·fiyat tooltip etiketi."""
        plot_item = self.plot_widget.getPlotItem()
        pen = pg.mkPen(CROSSHAIR_COLOR, width=1, style=Qt.DashLine)

        self._cursor_vline = pg.InfiniteLine(angle=90, movable=False, pen=pen)
        self._cursor_hline = pg.InfiniteLine(angle=0, movable=False, pen=pen)
        self._cursor_vline.setVisible(False)
        self._cursor_hline.setVisible(False)
        plot_item.addItem(self._cursor_vline, ignoreBounds=True)
        plot_item.addItem(self._cursor_hline, ignoreBounds=True)

        self._cursor_label = pg.TextItem(
            text="",
            color=TEXT_PRIMARY,
            anchor=(0, 1),
            fill=pg.mkBrush(15, 23, 42, 230),
            border=pg.mkPen(BORDER),
        )
        self._cursor_label.setVisible(False)
        plot_item.addItem(self._cursor_label, ignoreBounds=True)

        scene = self.plot_widget.scene()
        self._mouse_proxy = pg.SignalProxy(
            scene.sigMouseMoved, rateLimit=60, slot=self._on_mouse_moved
        )

    def draw_empty_chart(self, message: str) -> None:
        self.plot_widget.clear()
        self._chart_points = []
        self._clear_reference_legend()
        self._configure_plot_item()
        self._install_crosshair()  # plot_widget.clear() crosshair item'larını da temizler
        self.plot_widget.getPlotItem().setTitle(message, color=TEXT_SECONDARY, size="13px")
        self.plot_widget.enableAutoRange()

    def draw_chart(
        self,
        current_ticker: str,
        current_stock_id,
        current_price,
        portfolio_service,
        price_repo=None,
        average_cost=None,
    ):
        if not current_ticker:
            self.draw_empty_chart(L10N.GRAFIK_VERISI_BEKLENIYOR)
            return

        self.draw_empty_chart(L10N.VERI_YUKLENIYOR)

        def _fetch():
            end_date = date.today()
            start_date = end_date - timedelta(days=180)

            points = self._db_series_to_points(price_repo, current_stock_id, start_date, end_date)
            if not points and self._price_series_provider is not None:
                yf_ticker = current_ticker if "." in current_ticker else f"{current_ticker}.IS"
                try:
                    series = self._price_series_provider(yf_ticker, start_date, end_date)
                except Exception as exc:
                    logger.warning("Piyasa fiyat serisi okunamadı: %s", exc)
                    series = None
                points = self._provider_series_to_points(series)

            avg_cost = (
                float(average_cost)
                if average_cost is not None
                else self._average_cost(current_stock_id, portfolio_service)
            )
            return points, avg_cost

        worker = Worker(_fetch)
        worker.signals.result.connect(
            lambda result: self._render_chart(result[0], result[1], current_price, current_ticker)
        )
        worker.signals.error.connect(lambda _err: self.draw_empty_chart(L10N.GRAFIK_YUKLENEMEDI))
        QThreadPool.globalInstance().start(worker)

    def _render_chart(
        self,
        points: list,
        avg_cost,
        current_price,
        current_ticker: str,
    ) -> None:
        try:
            if not points:
                self.draw_empty_chart(L10N.VERI_BULUNAMADI)
                return

            self.plot_widget.clear()
            self._clear_reference_legend()
            self._configure_plot_item()
            self._install_crosshair()
            plot_item = self.plot_widget.getPlotItem()
            plot_item.setTitle(
                L10N.FIYAT_GECMISI_TMPL.format(ticker=display_ticker(current_ticker)),
                color=TEXT_PRIMARY,
                size="15pt",
            )

            # Crosshair snap için noktaları sakla (x'e göre sıralı varsay)
            self._chart_points = sorted(points, key=lambda p: p[0])

            x_values = [point[0] for point in self._chart_points]
            y_values = [point[1] for point in self._chart_points]

            curve = self.plot_widget.plot(
                x_values,
                y_values,
                pen=pg.mkPen(LINE_BLUE, width=3),
                symbol=None,
                name=L10N.FIYAT,
            )
            baseline = min(y_values)
            baseline_curve = pg.PlotDataItem(x_values, [baseline] * len(x_values), pen=pg.mkPen(None))
            fill = pg.FillBetweenItem(curve, baseline_curve, brush=pg.mkBrush(59, 130, 246, 34))
            self.plot_widget.addItem(baseline_curve)
            self.plot_widget.addItem(fill)

            ymin = min(y_values)
            ymax = max(y_values)
            padding = (ymax - ymin) * 0.12 if ymax > ymin else max(ymax * 0.1, 1.0)
            self.plot_widget.setYRange(max(0, ymin - padding), ymax + padding, padding=0)

            if avg_cost is not None:
                self._add_reference_line(avg_cost, L10N.ORT_MALIYET, LINE_AVG_COST, Qt.DashLine)

            if current_price:
                self._add_reference_line(
                    float(current_price),
                    L10N.GUNCEL_DEGER_TMPL.format(value=f"{float(current_price):.2f}"),
                    LINE_CURRENT,
                    Qt.SolidLine,
                )

            self.plot_widget.enableAutoRange(axis=pg.ViewBox.XAxis)
        except Exception as exc:
            logger.error("Grafik render hatası: %s", exc)
            self.draw_empty_chart(L10N.GRAFIK_YUKLENEMEDI)

    def _on_mouse_moved(self, event) -> None:
        """Crosshair'ı en yakın gerçek noktaya snap eder ve tooltip günceller."""
        if not self._chart_points:
            self._set_crosshair_visible(False)
            return
        pos = event[0] if isinstance(event, tuple) else event
        plot_item = self.plot_widget.getPlotItem()
        view_box = plot_item.vb
        if not plot_item.sceneBoundingRect().contains(pos):
            self._set_crosshair_visible(False)
            return
        scene_point = view_box.mapSceneToView(pos)
        snap_x, snap_y = self._nearest_point(scene_point.x())
        self._cursor_vline.setPos(snap_x)
        self._cursor_hline.setPos(snap_y)
        self._set_crosshair_visible(True)
        try:
            dt = datetime.fromtimestamp(snap_x)
            date_text = _format_date_tr(dt, with_year=True)
        except (OSError, OverflowError, ValueError):
            date_text = "-"
        price_text = _format_tr_currency(snap_y).replace("₺ ", "")  # tek ₺ tooltip içinde
        self._cursor_label.setText(L10N.GRAFIK_TOOLTIP_TMPL.format(date=date_text, price=price_text))
        # Etiketi her zaman ViewBox'ın üst-orta veya üst-sağ kısmında sabit tut (Plotly 'x unified' benzeri)
        view_range = view_box.viewRange()
        x_min, x_max = view_range[0]
        y_min, y_max = view_range[1]
        
        self._cursor_label.setAnchor((1, 0))  # Sağ-Üst hizalama
        self._cursor_label.setPos(QPointF(x_max, y_max))

    def _set_crosshair_visible(self, visible: bool) -> None:
        for item in (self._cursor_vline, self._cursor_hline, self._cursor_label):
            item.setVisible(visible)

    def _nearest_point(self, x: float) -> tuple[float, float]:
        """``_chart_points`` içinde x'e en yakın (x, y) noktasını döner."""
        xs = [p[0] for p in self._chart_points]
        idx = bisect.bisect_left(xs, x)
        if idx <= 0:
            return self._chart_points[0]
        if idx >= len(xs):
            return self._chart_points[-1]
        before = self._chart_points[idx - 1]
        after = self._chart_points[idx]
        return before if abs(x - before[0]) <= abs(after[0] - x) else after

    def _add_reference_line(self, value: float, label: str, color: str, style: Qt.PenStyle) -> None:
        pen = pg.mkPen(color, width=1.4, style=style)
        line = pg.InfiniteLine(
            pos=value,
            angle=0,
            movable=False,
            pen=pen,
        )
        self.plot_widget.addItem(line)
        self._add_reference_legend_item(label, pen)

    def _add_reference_legend_item(self, label: str, pen) -> None:
        if self._reference_legend is None:
            self._reference_legend = pg.LegendItem(
                offset=(70, 44),  # Y ekseninden (sol kenar) uzaklaştırmak için 14 -> 70 yapıldı
                brush=pg.mkBrush(15, 23, 42, 220),
                pen=pg.mkPen(BORDER),
                labelTextColor=TEXT_PRIMARY,
            )
            self._reference_legend.setParentItem(self.plot_widget.getPlotItem().graphicsItem())
        sample = pg.PlotDataItem([], [], pen=pen)
        self._reference_legend.addItem(sample, label)

    def _clear_reference_legend(self) -> None:
        if self._reference_legend is not None:
            legend = self._reference_legend
            self._reference_legend = None
            scene = legend.scene()
            if scene is not None:
                scene.removeItem(legend)

    @staticmethod
    def _average_cost(current_stock_id, portfolio_service) -> float | None:
        if not current_stock_id or not portfolio_service:
            return None
        portfolio = portfolio_service.get_current_portfolio()
        pos = portfolio.positions.get(current_stock_id)
        if not pos or not pos.average_cost:
            return None
        return float(pos.average_cost)

    @staticmethod
    def _provider_series_to_points(series) -> list[tuple[float, float]]:
        """Market client serisini (``dict[date, Decimal]``) grafik noktalarına çevirir."""
        points: list[tuple[float, float]] = []
        for index_value, raw_value in (series or {}).items():
            try:
                value = float(raw_value)
            except (TypeError, ValueError):
                continue
            if not value:
                continue

            if isinstance(index_value, datetime):
                dt = index_value
            elif isinstance(index_value, date):
                dt = datetime.combine(index_value, time.min)
            else:
                continue
            points.append((dt.timestamp(), value))
        return points

    @staticmethod
    def _db_series_to_points(price_repo, stock_id, start_date: date, end_date: date) -> list[tuple[float, float]]:
        if not price_repo or not stock_id:
            return []
        try:
            series = price_repo.get_price_series(stock_id, start_date, end_date)
        except Exception as exc:
            logger.warning("DB fiyat serisi okunamadı: %s", exc)
            return []

        points: list[tuple[float, float]] = []
        for daily in series or []:
            price_date = getattr(daily, "price_date", None)
            close_price = getattr(daily, "close_price", None)
            if price_date is None or close_price is None:
                continue
            try:
                value = float(close_price)
            except (TypeError, ValueError):
                continue
            points.append((datetime.combine(price_date, time.min).timestamp(), value))
        return points
