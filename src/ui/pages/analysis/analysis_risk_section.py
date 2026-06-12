from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget, QGridLayout
from PyQt5.QtCore import QTimer


from src.application.services.analysis import AllocationRiskDTO
from src.ui.widgets.shared import InfoCard

from src.ui.widgets.shared.controls.silent_web_view import SilentWebEngineView
from .chart_builder import build_pie_chart, patch_plotly_html


def _fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"%{value:+.2f}"


class AnalysisRiskSection(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
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
        self.cost_chart = SilentWebEngineView()
        self.value_chart = SilentWebEngineView()
        self.cost_chart.setMinimumHeight(400)
        self.value_chart.setMinimumHeight(400)
        charts_row.addWidget(self.cost_chart, 1)
        charts_row.addWidget(self.value_chart, 1)
        layout.addLayout(charts_row)

    def set_error(self, message: str) -> None:
        self.warning_banner.setText(message)
        self.warning_banner.show()
        self.cost_chart.setHtml(f"<div style='color:white; text-align:center; padding-top:150px;'>{message}</div>")
        self.value_chart.setHtml(f"<div style='color:white; text-align:center; padding-top:150px;'>{message}</div>")

    def set_data(self, dto: AllocationRiskDTO) -> None:
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

        cost_breakdown = [(item.label, float(item.cost_value)) for item in dto.items if item.cost_value > 0]
        current_breakdown = [(item.label, float(item.current_value)) for item in dto.items if item.current_value > 0]
        
        from PyQt5.QtCore import QUrl
        import tempfile

        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtGui import QPalette
        palette = QApplication.instance().palette()
        is_light = palette.color(QPalette.Window).lightness() > 128
        text_color = "#1e293b" if is_light else "#f1f5f9"

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
