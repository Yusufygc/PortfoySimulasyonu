from __future__ import annotations

from PyQt5.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.application.services.analysis import AllocationRiskDTO
from src.ui.widgets.cards import InfoCard

from .analysis_chart_engine import AnalysisChartEngine


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

        charts_row = QHBoxLayout()
        charts_row.setSpacing(15)
        self.cost_chart = AnalysisChartEngine(show_toolbar=False)
        self.value_chart = AnalysisChartEngine(show_toolbar=False)
        charts_row.addWidget(self.cost_chart, 1)
        charts_row.addWidget(self.value_chart, 1)
        layout.addLayout(charts_row)

    def set_error(self, message: str) -> None:
        self.warning_banner.setText(message)
        self.warning_banner.show()
        self.cost_chart.draw_empty_chart(message)
        self.value_chart.draw_empty_chart(message)

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

        cost_breakdown = [(item.label, item.cost_value) for item in dto.items if item.cost_value > 0]
        current_breakdown = [(item.label, item.current_value) for item in dto.items if item.current_value > 0]
        self.cost_chart.draw_portfolio_pie("Maliyet Bazlı Dağılım", cost_breakdown)
        self.value_chart.draw_portfolio_pie("Güncel Değer Dağılımı", current_breakdown)
