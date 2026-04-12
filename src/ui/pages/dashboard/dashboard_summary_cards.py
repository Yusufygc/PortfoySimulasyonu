# src/ui/pages/dashboard/dashboard_summary_cards.py

from PyQt5.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from decimal import Decimal

class DashboardSummaryCards(QWidget):
    """Dashboard özet metrik kartları (Toplam Değer, Maliyet, Sermaye, Getiriler)."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(20)

        self.card_total, self.lbl_total_value, self.lbl_total_context = self._create_card("TOPLAM PORTFÖY DEĞERİ", "₺ 0.00", "#3b82f6")
        self.card_cost, self.lbl_total_cost, _ = self._create_card("TOPLAM MALİYET", "₺ 0.00", "#8b5cf6")
        self.card_capital, self.lbl_capital, _ = self._create_card("NAKİT SERMAYE", "₺ 0.00", "#10b981")
        
        self.card_returns, self.lbl_weekly_return, self.lbl_monthly_return = self._create_returns_card()

        layout.addWidget(self.card_total, 1)
        layout.addWidget(self.card_cost, 1)
        layout.addWidget(self.card_capital, 1)
        layout.addWidget(self.card_returns, 1)

    def _create_card(self, title, initial_value, accent_color="#3b82f6"):
        card = QFrame()
        card.setObjectName("infoCard")
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet(f"""
            QFrame#infoCard {{
                background-color: #1e293b;
                border-radius: 12px;
                border-left: 4px solid {accent_color};
            }}
        """)
        
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 15, 20, 15)
        
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        
        lbl_value = QLabel(initial_value)
        lbl_value.setStyleSheet("color: #f1f5f9; font-size: 18px; font-weight: bold;")
        
        lay.addWidget(lbl_title)
        lay.addWidget(lbl_value)
        
        lbl_context = QLabel("")
        lbl_context.setStyleSheet("color: #64748b; font-size: 11px; margin-top: 2px;")
        lay.addWidget(lbl_context)
        
        return card, lbl_value, lbl_context

    def _create_returns_card(self):
        card = QFrame()
        card.setObjectName("infoCard")
        card.setFrameShape(QFrame.StyledPanel)
        card.setStyleSheet("""
            QFrame#infoCard {
                background-color: #1e293b;
                border-radius: 12px;
                border-left: 4px solid #f59e0b;
            }
        """)
        
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 15, 20, 15)
        
        lbl_title = QLabel("DÖNEMSEL GETİRİLER")
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold;")
        lay.addWidget(lbl_title)
        
        returns_lay = QVBoxLayout()
        returns_lay.setSpacing(5)
        
        weekly_lay = QHBoxLayout()
        lbl_wk_title = QLabel("Haftalık:")
        lbl_wk_title.setStyleSheet("color: #94a3b8; font-size: 13px;")
        lbl_wk_value = QLabel("-")
        lbl_wk_value.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")
        weekly_lay.addWidget(lbl_wk_title)
        weekly_lay.addWidget(lbl_wk_value)
        weekly_lay.addStretch()
        
        monthly_lay = QHBoxLayout()
        lbl_mo_title = QLabel("Aylık:")
        lbl_mo_title.setStyleSheet("color: #94a3b8; font-size: 13px;")
        lbl_mo_value = QLabel("-")
        lbl_mo_value.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")
        monthly_lay.addWidget(lbl_mo_title)
        monthly_lay.addWidget(lbl_mo_value)
        monthly_lay.addStretch()
        
        returns_lay.addLayout(weekly_lay)
        returns_lay.addLayout(monthly_lay)
        lay.addLayout(returns_lay)
        
        return card, lbl_wk_value, lbl_mo_value

    def update_base_metrics(self, total_value: Decimal, total_cost: Decimal, capital: Decimal, profit_loss: Decimal):
        self.lbl_total_value.setText(f"₺ {total_value:,.2f}")
        self.lbl_total_cost.setText(f"₺ {total_cost:,.2f}")
        self.lbl_capital.setText(f"₺ {capital:,.2f}")

        roi = 0
        cost_basis = total_value - profit_loss
        if cost_basis != 0:
            roi = (profit_loss / cost_basis) * 100
            
        prefix = "▲" if profit_loss >= 0 else "▼"
        sign = "+" if profit_loss >= 0 else ""
        color = "#10b981" if profit_loss >= 0 else "#ef4444"
        
        self.lbl_total_context.setText(f"{prefix} ₺ {abs(profit_loss):,.2f} ({sign}{roi:.1f}% All Time)")
        self.lbl_total_context.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 500;")

    def update_returns(self, weekly_pct: float, monthly_pct: float):
        if weekly_pct is not None:
            color = "#10b981" if weekly_pct >= 0 else "#ef4444"
            self.lbl_weekly_return.setText(f"%{weekly_pct:+.2f}")
            self.lbl_weekly_return.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        else:
            self.lbl_weekly_return.setText("-")
            self.lbl_weekly_return.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")

        if monthly_pct is not None:
            color = "#10b981" if monthly_pct >= 0 else "#ef4444"
            self.lbl_monthly_return.setText(f"%{monthly_pct:+.2f}")
            self.lbl_monthly_return.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        else:
            self.lbl_monthly_return.setText("-")
            self.lbl_monthly_return.setStyleSheet("color: #f1f5f9; font-size: 14px; font-weight: bold;")
