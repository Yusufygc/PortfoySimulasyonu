from src.ui.shared.locale_tr import L10N
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
            L10N.TOPLAM_DEGER,
            "₺ 0.00",
            icon_name="wallet",
            icon_color="@COLOR_PRIMARY",
            is_hero=True,
        )
        self.card_pl, self.lbl_pl = CardFactory.create_stat_card(
            L10N.KR_ZARAR,
            "₺ 0.00",
            is_colored=True,
            icon_name="line-chart",
            icon_color="@COLOR_TEXT_SECONDARY",
        )
        self.card_avg_cost, self.lbl_avg_cost = CardFactory.create_stat_card(
            L10N.ORT_MALIYET_1,
            "₺ 0.00",
            icon_name="tag",
            icon_color="@COLOR_WARNING",
        )
        self.card_total_qty, self.lbl_total_qty = CardFactory.create_stat_card(
            L10N.TOPLAM_LOT,
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

    def update_model_stats(
        self,
        model_portfolio_service,
        portfolio_id: int | None,
        stock_id: int | None,
        current_price: Decimal | None,
        price_map: dict[int, Decimal] | None = None,
    ) -> None:
        if not portfolio_id or not stock_id:
            self.clear_stats()
            return

        effective_price_map = dict(price_map or {})
        if current_price is not None:
            effective_price_map[stock_id] = current_price

        positions = model_portfolio_service.get_positions_with_details(portfolio_id, effective_price_map)
        position = next((pos for pos in positions if pos.get("stock_id") == stock_id), None)
        if not position:
            self.clear_stats()
            return

        avg_cost = position.get("avg_cost") or Decimal("0")
        total_qty = position.get("quantity") or 0
        total_cost = position.get("total_cost") or Decimal("0")
        current_val = position.get("current_value")
        if current_val is None and current_price is not None:
            current_val = current_price * Decimal(total_qty)
        current_val = current_val or Decimal("0")
        pl = current_val - total_cost

        self.lbl_avg_cost.setText(f"₺ {avg_cost:,.2f}")
        self.lbl_total_qty.setText(f"{total_qty}")
        self.lbl_total_val.setText(f"₺ {current_val:,.2f}")
        prefix = "▲" if pl >= 0 else "▼"
        self.lbl_pl.setText(f"{prefix} ₺ {abs(pl):,.2f}")
        self._set_pl_state("positive" if pl >= 0 else "negative")
            
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
