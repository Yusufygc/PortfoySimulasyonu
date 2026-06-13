from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from src.qt_compat.qtwidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget, QGridLayout
from src.qt_compat.qtcore import QTimer, QUrl, Qt

import tempfile

from src.application.services.analysis import AllocationRiskDTO
from src.ui.widgets.shared import InfoCard

from .chart_builder import build_pie_chart, patch_plotly_html


def _fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"%{value:+.2f}"


class AnalysisRiskSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cost_chart = None
        self.value_chart = None
        self._charts_initialized = False
        self._latest_dto: AllocationRiskDTO | None = None
        self._pending_error: str | None = None
        self._cost_temp_file = None
        self._val_temp_file = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        self.warning_banner = QLabel("")
        self.warning_banner.setProperty("cssClass", "warningBanner")
        self.warning_banner.setWordWrap(True)
        self.warning_banner.hide()
        layout.addWidget(self.warning_banner)

        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(15)
        cards_grid.setVerticalSpacing(15)

        self.card_top_three = InfoCard(L10N.ILK_3_POZISYON, "—", icon_name="layers")
        self.card_volatility = InfoCard(L10N.FIYAT_DALGALANMASI_RISK, "—", icon_name="line-chart")
        self.card_drawdown = InfoCard(L10N.MAKSIMUM_DUSUS_KAYIP, "—", icon_name="trending-down")
        self.card_concentration = InfoCard(L10N.CESITLENDIRME_DAGILIMI, "—", icon_name="shield-check")

        self.card_sharpe = InfoCard(L10N.RISK_BASINA_GETIRI_SHARPE, "—", icon_name="activity")
        self.card_sharpe.setToolTip(L10N.ALINAN_1_BIRIM_RISKE_KARSILIK)
        self.card_beta = InfoCard(L10N.BIST100E_TEPKISI_BETA, "—", icon_name="crosshair")
        self.card_beta.setToolTip(L10N.PORTFOYUN_BIST100E_KARSI_DUYARLILIGI_1)
        self.card_alpha = InfoCard(L10N.EKSTRA_BASARI_ALPHA, "—", icon_name="star")
        self.card_alpha.setToolTip(L10N.ENDEKS_GETIRISINDEN_BAGIMSIZ_OLARAK_YARATILAN)

        cards_grid.addWidget(self.card_top_three, 0, 0)
        cards_grid.addWidget(self.card_volatility, 0, 1)
        cards_grid.addWidget(self.card_drawdown, 0, 2)
        cards_grid.addWidget(self.card_concentration, 0, 3)

        cards_grid.addWidget(self.card_sharpe, 1, 0)
        cards_grid.addWidget(self.card_beta, 1, 1)
        cards_grid.addWidget(self.card_alpha, 1, 2)

        for col in range(4):
            cards_grid.setColumnStretch(col, 1)

        layout.addLayout(cards_grid)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(15)
        self.cost_chart_container = self._build_chart_placeholder(L10N.MALIYET_BAZLI_DAGILIM)
        self.value_chart_container = self._build_chart_placeholder(L10N.GUNCEL_DEGER_DAGILIMI)
        charts_row.addWidget(self.cost_chart_container, 1)
        charts_row.addWidget(self.value_chart_container, 1)
        layout.addLayout(charts_row)

    def _build_chart_placeholder(self, title: str) -> QWidget:
        container = QWidget()
        container.setMinimumHeight(400)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        placeholder = QLabel(title)
        placeholder.setProperty("cssClass", "mutedText")
        placeholder.setMinimumHeight(400)
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignCenter)
        layout.addWidget(placeholder)
        return container

    def activate_charts(self) -> None:
        self._ensure_chart_views()
        if self._pending_error:
            self._set_chart_error(self._pending_error)
        elif self._latest_dto is not None:
            self._render_charts(self._latest_dto)

    def _ensure_chart_views(self) -> None:
        if self._charts_initialized:
            return

        from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView

        self.cost_chart = SilentWebEngineView()
        self.value_chart = SilentWebEngineView()
        self.cost_chart.setMinimumHeight(400)
        self.value_chart.setMinimumHeight(400)
        self._replace_chart_placeholder(self.cost_chart_container, self.cost_chart)
        self._replace_chart_placeholder(self.value_chart_container, self.value_chart)
        self._charts_initialized = True

    def _replace_chart_placeholder(self, container: QWidget, chart: QWidget) -> None:
        layout = container.layout()
        item = layout.takeAt(0)
        if item is not None and item.widget() is not None:
            item.widget().deleteLater()
        layout.addWidget(chart)

    def set_error(self, message: str) -> None:
        self._pending_error = message
        self.warning_banner.setText(message)
        self.warning_banner.show()
        if self._charts_initialized:
            self._set_chart_error(message)

    def set_data(self, dto: AllocationRiskDTO) -> None:
        self._latest_dto = dto
        self._pending_error = None
        if dto.warnings:
            new_warnings = [w for w in dto.warnings if w not in getattr(self, '_shown_warnings', set())]
            if new_warnings:
                self.warning_banner.setText(" | ".join(new_warnings))
                self.warning_banner.show()
                if not hasattr(self, '_shown_warnings'):
                    self._shown_warnings = set()
                self._shown_warnings.update(new_warnings)
                QTimer.singleShot(10000, self.warning_banner.hide)
        else:
            self.warning_banner.hide()

        self.card_top_three.set_value(_fmt_pct(dto.top_three_weight_pct))
        self.card_volatility.set_value(_fmt_pct(dto.volatility_pct))
        self.card_drawdown.set_value(_fmt_pct(dto.max_drawdown_pct))
        self.card_concentration.set_value(dto.concentration_label)
        self.card_sharpe.set_value(f"{dto.sharpe_ratio:.2f}" if dto.sharpe_ratio is not None else "—")
        self.card_beta.set_value(f"{dto.beta:.2f}" if dto.beta is not None else "—")
        self.card_alpha.set_value(_fmt_pct(dto.alpha) if dto.alpha is not None else "—")

        if self._charts_initialized:
            self._render_charts(dto)

    def _set_chart_error(self, message: str) -> None:
        self.cost_chart.setHtml(f"<div style='color:white; text-align:center; padding-top:150px;'>{message}</div>")
        self.value_chart.setHtml(f"<div style='color:white; text-align:center; padding-top:150px;'>{message}</div>")

    def _render_charts(self, dto: AllocationRiskDTO) -> None:
        cost_breakdown = [(item.label, float(item.cost_value)) for item in dto.items if item.cost_value > 0]
        current_breakdown = [(item.label, float(item.current_value)) for item in dto.items if item.current_value > 0]

        from src.ui.styles.tokens import DEFAULT_THEME
        text_color = DEFAULT_THEME.get("COLOR_TEXT_PRIMARY", "#f1f5f9")

        if cost_breakdown:
            fig1 = build_pie_chart(L10N.MALIYET_BAZLI_DAGILIM, cost_breakdown, text_color=text_color)
            html1 = fig1.to_html(include_plotlyjs=True)
            html1 = patch_plotly_html(html1)
            if not hasattr(self, "_cost_temp_file") or self._cost_temp_file is None:
                f = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
                self._cost_temp_file = f.name
                f.close()
            with open(self._cost_temp_file, "w", encoding="utf-8") as f:
                f.write(html1)
            self.cost_chart.load(QUrl.fromLocalFile(self._cost_temp_file))
        else:
            self.cost_chart.setHtml("<div style='color:white; text-align:center; padding-top:150px;'>Maliyet verisi yok</div>")

        if current_breakdown:
            fig2 = build_pie_chart(L10N.GUNCEL_DEGER_DAGILIMI, current_breakdown, text_color=text_color)
            html2 = fig2.to_html(include_plotlyjs=True)
            html2 = patch_plotly_html(html2)
            if not hasattr(self, "_val_temp_file") or self._val_temp_file is None:
                f = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
                self._val_temp_file = f.name
                f.close()
            with open(self._val_temp_file, "w", encoding="utf-8") as f:
                f.write(html2)
            self.value_chart.load(QUrl.fromLocalFile(self._val_temp_file))
        else:
            self.value_chart.setHtml("<div style='color:white; text-align:center; padding-top:150px;'>Değer verisi yok</div>")
