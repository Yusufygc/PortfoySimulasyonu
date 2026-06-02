from __future__ import annotations

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget


from src.application.services.analysis import AllocationRiskDTO
from src.ui.widgets.shared import InfoCard

from PyQt5.QtWebEngineWidgets import QWebEngineView
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

        cards_row = QHBoxLayout()
        cards_row.setSpacing(15)
        self.card_top_three = InfoCard("İlk 3 Pozisyon", "—", icon_name="layers")
        self.card_volatility = InfoCard("Volatilite", "—", icon_name="line-chart")
        self.card_drawdown = InfoCard("Maks. Drawdown", "—", icon_name="trending-down")
        self.card_concentration = InfoCard("Konsantrasyon", "—", icon_name="shield-check")
        for card in [self.card_top_three, self.card_volatility, self.card_drawdown, self.card_concentration]:
            cards_row.addWidget(card, 1)
        layout.addLayout(cards_row)

        cards_row2 = QHBoxLayout()
        cards_row2.setSpacing(15)
        self.card_sharpe = InfoCard("Sharpe Oranı", "—", icon_name="bar-chart-2")
        self.card_sharpe.setToolTip("Alınan 1 birim riske karşılık ne kadar ekstra getiri sağlandığını gösterir (>1 iyidir).")
        self.card_beta = InfoCard("Beta (BIST100)", "—", icon_name="target")
        self.card_beta.setToolTip("Portföyün BIST100'e karşı duyarlılığı (1 = endeksle aynı).")
        self.card_alpha = InfoCard("Alpha", "—", icon_name="star")
        self.card_alpha.setToolTip("Endeks getirisinden bağımsız olarak yaratılan ekstra değer.")
        for card in [self.card_sharpe, self.card_beta, self.card_alpha]:
            cards_row2.addWidget(card, 1)
        # Empty space to balance 4 cards vs 3 cards row
        cards_row2.addStretch(1)
        layout.addLayout(cards_row2)

        charts_row = QHBoxLayout()
        charts_row.setSpacing(15)
        self.cost_chart = QWebEngineView()
        self.value_chart = QWebEngineView()
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
            self.warning_banner.setText(" | ".join(dto.warnings))
            self.warning_banner.show()
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

        if cost_breakdown:
            fig1 = build_pie_chart("Maliyet Bazlı Dağılım", cost_breakdown)
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
            fig2 = build_pie_chart("Güncel Değer Dağılımı", current_breakdown)
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
