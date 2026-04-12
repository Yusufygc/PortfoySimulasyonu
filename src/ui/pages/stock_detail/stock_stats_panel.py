# src/ui/pages/stock_detail/stock_stats_panel.py

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
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
        self.card_total_val, self.lbl_total_val = CardFactory.create_stat_card("TOPLAM DEĞER", "₺ 0.00", icon="💰", is_hero=True)
        self.card_pl, self.lbl_pl = CardFactory.create_stat_card("KAR / ZARAR", "₺ 0.00", is_colored=True, icon="📈")
        self.card_avg_cost, self.lbl_avg_cost = CardFactory.create_stat_card("ORT. MALİYET", "₺ 0.00", icon="🏷️")
        self.card_total_qty, self.lbl_total_qty = CardFactory.create_stat_card("TOPLAM LOT", "0", icon="📦")
        
        layout.addWidget(self.card_total_val, 2) # Hero daha geniş
        layout.addWidget(self.card_pl, 1)
        layout.addWidget(self.card_avg_cost)
        layout.addWidget(self.card_total_qty)

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
            self.lbl_pl.setStyleSheet(f"color: {'#10b981' if pl >= 0 else '#ef4444'}; font-size: 20px; font-weight: bold;")
        else:
            self.clear_stats()
            
    def clear_stats(self):
        self.lbl_avg_cost.setText("₺ 0.00")
        self.lbl_total_qty.setText("0")
        self.lbl_total_val.setText("₺ 0.00")
        self.lbl_pl.setText("₺ 0.00")
