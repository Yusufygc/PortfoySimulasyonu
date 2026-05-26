# src/ui/pages/stock_detail/stock_stats_panel.py

from PyQt5.QtWidgets import QWidget, QHBoxLayout
from decimal import Decimal
from src.ui.shared.card_factory import CardFactory

class StockStatsPanel(QWidget):
    """Hisse istatistiklerini gösteren yan yana kartlar paneli."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(15)
        
        # Hero Metric: Toplam Değer
        self.card_total_val, self.lbl_total_val = CardFactory.create_stat_card(
            "TOPLAM DEĞER",
            "₺ 0.00",
            icon_name="wallet",
            icon_color="@COLOR_PRIMARY",
            is_hero=True,
        )
        self.card_pl, self.lbl_pl = CardFactory.create_stat_card(
            "KAR / ZARAR",
            "₺ 0.00",
            is_colored=True,
            icon_name="line-chart",
            icon_color="@COLOR_TEXT_SECONDARY",
        )
        self.card_avg_cost, self.lbl_avg_cost = CardFactory.create_stat_card(
            "ORT. MALİYET",
            "₺ 0.00",
            icon_name="tag",
            icon_color="@COLOR_WARNING",
        )
        self.card_total_qty, self.lbl_total_qty = CardFactory.create_stat_card(
            "TOPLAM LOT",
            "0",
            icon_name="package",
            icon_color="@COLOR_TEXT_SECONDARY",
        )
        self._set_card_minimums()
        self._set_pl_state("neutral")
        
        layout.addWidget(self.card_total_val, 8) # Hero daha geniş
        layout.addWidget(self.card_pl, 5)
        layout.addWidget(self.card_avg_cost, 4)
        layout.addWidget(self.card_total_qty, 4)

    def update_stats(self, portfolio_service, stock_id: int, current_price: Decimal):
        if not stock_id:
            self.clear_stats()
            return
            
        portfolio = portfolio_service.get_current_portfolio()
        position = portfolio.positions.get(stock_id)
        
        if position:
            avg_cost = position.average_cost or Decimal("0")
            total_qty = position.total_quantity
            total_cost = position.total_cost
            
            current_val = Decimal("0")
            if current_price:
                current_val = current_price * total_qty
            
            pl = current_val - total_cost
            
            self.lbl_avg_cost.setText(f"₺ {avg_cost:,.2f}")
            self.lbl_total_qty.setText(f"{total_qty}")
            self.lbl_total_val.setText(f"₺ {current_val:,.2f}")
            
            prefix = "▲" if pl >= 0 else "▼"
            self.lbl_pl.setText(f"{prefix} ₺ {abs(pl):,.2f}")
            state = "positive" if pl >= 0 else "negative"
            self._set_pl_state(state)
        else:
            self.clear_stats()
            
    def clear_stats(self):
        self.lbl_avg_cost.setText("₺ 0.00")
        self.lbl_total_qty.setText("0")
        self.lbl_total_val.setText("₺ 0.00")
        self.lbl_pl.setText("₺ 0.00")
        self._set_pl_state("neutral")

    def _set_card_minimums(self) -> None:
        self.card_total_val.setMinimumWidth(320)
        self.card_pl.setMinimumWidth(230)
        self.card_avg_cost.setMinimumWidth(140)
        self.card_total_qty.setMinimumWidth(140)

    def _set_pl_state(self, state: str) -> None:
        icon_map = {
            "positive": ("trending-up", "@COLOR_SUCCESS"),
            "negative": ("trending-down", "@COLOR_DANGER"),
            "neutral": ("line-chart", "@COLOR_TEXT_SECONDARY"),
        }
        icon_name, icon_color = icon_map.get(state, icon_map["neutral"])
        self.card_pl.setProperty("cssState", state)
        self.lbl_pl.setProperty("cssState", state)

        icon_label = getattr(self, "_pl_icon_label", None)
        if icon_label is None:
            from src.ui.widgets.shared.controls.icon_label import IconLabel
            for child in self.card_pl.findChildren(IconLabel):
                icon_label = child
                break
            self._pl_icon_label = icon_label
        if icon_label is not None:
            icon_label.set_icon(icon_name, color=icon_color)

        for widget in (self.card_pl, self.lbl_pl):
            widget.style().unpolish(widget)
            widget.style().polish(widget)
