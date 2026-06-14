from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from src.qt_compat.qtcore import QTimer
from src.qt_compat.qtwidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from src.application.services.analysis import AnalysisOverviewDTO
from src.ui.widgets.shared import InfoCard, MetricCard


def _fmt_pct(value: float | None) -> str:
    return "—" if value is None else f"%{value:+.2f}"


def _set_card_state(card: InfoCard, value: float | None) -> None:
    if value is None:
        card.set_value_state("neutral")
    elif value >= 0:
        card.set_value_state("positive")
    else:
        card.set_value_state("negative")


def _resolve_currency_symbol(mode: str) -> str:
    if mode == "REAL":
        return L10N.REEL
    return "$" if mode == "USD" else "₺"


def _fmt_position_label(label: str, weight_pct: float | None) -> str:
    if weight_pct is None:
        return label
    return f"{label} (%{weight_pct:.1f})"


def _or_zero(v) -> float:
    return v or 0.0


class AnalysisOverviewSection(QWidget):
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

        self.card_total = InfoCard(L10N.TOPLAM_PORTFOY_DEGERI, "₺ 0", icon_name="wallet")
        self.card_return = InfoCard(L10N.DONEM_GETIRISI, "—", icon_name="trending-up")
        self.card_gap = InfoCard(L10N.BENCHMARK_FARKI, "—", icon_name="scale")
        self.card_position = InfoCard(L10N.EN_BUYUK_POZISYON, "—", icon_name="layers")
        self.card_drawdown = InfoCard(L10N.MAKS_DRAWDOWN, "—", icon_name="trending-down")

        overview_cards = [self.card_total, self.card_return, self.card_gap, self.card_position, self.card_drawdown]
        for idx, card in enumerate(overview_cards):
            cards_grid.addWidget(card, idx // 3, idx % 3)
        for column in range(3):
            cards_grid.setColumnStretch(column, 1)
        layout.addLayout(cards_grid)

        detail_row = QHBoxLayout()
        detail_row.setSpacing(15)

        self.metric_best = MetricCard(L10N.EN_IYI_KATKI, icon_name="star")
        self.metric_worst = MetricCard(L10N.EN_ZAYIF_KATKI, icon_name="alert-triangle")
        detail_row.addWidget(self.metric_best, 1)
        detail_row.addWidget(self.metric_worst, 1)
        layout.addLayout(detail_row)

        insight_frame = QFrame()
        insight_frame.setProperty("cssClass", "panelFramePadded")
        insight_layout = QVBoxLayout(insight_frame)
        insight_layout.setContentsMargins(15, 15, 15, 15)
        insight_layout.setSpacing(10)

        lbl_title = QLabel(L10N.ONE_CIKAN_ICGORULER)
        lbl_title.setProperty("cssClass", "tableTitle")
        insight_layout.addWidget(lbl_title)

        self.lbl_insights = QLabel(L10N.ANALIZ_BEKLENIYOR)
        self.lbl_insights.setWordWrap(True)
        self.lbl_insights.setProperty("cssClass", "pageDescription")
        insight_layout.addWidget(self.lbl_insights)
        layout.addWidget(insight_frame)
        layout.addStretch()

    def set_error(self, message: str) -> None:
        self.warning_banner.setText(message)
        self.warning_banner.show()
        self.lbl_insights.setText(message)

    def _update_warning_banner(self, warnings: list) -> None:
        new_warnings = [w for w in warnings if w not in getattr(self, '_shown_warnings', set())]
        if new_warnings:
            self.warning_banner.setText(" | ".join(new_warnings))
            self.warning_banner.show()
            if not hasattr(self, '_shown_warnings'):
                self._shown_warnings = set()
            self._shown_warnings.update(new_warnings)
            QTimer.singleShot(10000, self.warning_banner.hide)

    def set_data(self, dto: AnalysisOverviewDTO) -> None:
        if dto.warnings:
            self._update_warning_banner(dto.warnings)
        else:
            self.warning_banner.hide()

        currency_symbol = _resolve_currency_symbol(dto.currency_mode)
        self.card_total.set_value(f"{currency_symbol} {float(dto.total_value):,.2f}")
        self.card_return.set_value(_fmt_pct(dto.period_return_pct))
        self.card_gap.set_title(f"{dto.benchmark_label} Farkı")
        self.card_gap.set_value(_fmt_pct(dto.benchmark_gap_pct))
        self.card_position.set_value(_fmt_position_label(dto.largest_position_label, dto.largest_position_weight_pct))
        self.card_drawdown.set_value(_fmt_pct(dto.max_drawdown_pct))

        _set_card_state(self.card_return, dto.period_return_pct)
        _set_card_state(self.card_gap, dto.benchmark_gap_pct)
        _set_card_state(self.card_drawdown, dto.max_drawdown_pct)

        self.metric_best.update(
            current="Portföy",
            optimal=dto.best_contributor_label,
            delta=_or_zero(dto.best_contributor_pct),
            positive_is_good=True,
        )
        if dto.worst_contributor_label == "-":
            self.metric_worst.hide()
        else:
            self.metric_worst.show()
            self.metric_worst.update(
                current="Portföy",
                optimal=dto.worst_contributor_label,
                delta=_or_zero(dto.worst_contributor_pct),
                positive_is_good=True,
            )
        self.lbl_insights.setText("\n".join(dto.insights))
