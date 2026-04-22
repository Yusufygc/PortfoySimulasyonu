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

        self.card_total, self.lbl_total_value, self.lbl_total_context = self._create_card("TOPLAM PORTFÖY DEĞERİ", "₺ 0.00", "total")
        self.card_cost, self.lbl_total_cost, _ = self._create_card("TOPLAM MALİYET", "₺ 0.00", "cost")
        self.card_capital, self.lbl_capital, _ = self._create_card("NAKİT SERMAYE", "₺ 0.00", "capital")
        
        self.card_returns, self.lbl_weekly_return, self.lbl_monthly_return = self._create_returns_card()

        layout.addWidget(self.card_total, 1)
        layout.addWidget(self.card_cost, 1)
        layout.addWidget(self.card_capital, 1)
        layout.addWidget(self.card_returns, 1)

    def _create_card(self, title, initial_value, card_type="total"):
        card = QFrame()
        card.setProperty("cssClass", "summaryCard")
        card.setProperty("cardType", card_type)
        card.setFrameShape(QFrame.StyledPanel)
        
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 15, 20, 15)
        
        lbl_title = QLabel(title)
        lbl_title.setProperty("cssClass", "summaryCardTitle")
        
        lbl_value = QLabel(initial_value)
        lbl_value.setProperty("cssClass", "summaryCardValue")
        
        lay.addWidget(lbl_title)
        lay.addWidget(lbl_value)
        
        lbl_context = QLabel("")
        lbl_context.setProperty("cssClass", "summaryCardContext")
        lay.addWidget(lbl_context)
        
        return card, lbl_value, lbl_context

    def _create_returns_card(self):
        card = QFrame()
        card.setProperty("cssClass", "summaryCard")
        card.setProperty("cardType", "returns")
        card.setFrameShape(QFrame.StyledPanel)
        
        lay = QVBoxLayout(card)
        lay.setContentsMargins(20, 15, 20, 15)
        
        lbl_title = QLabel("DÖNEMSEL GETİRİLER")
        lbl_title.setProperty("cssClass", "summaryCardTitle")
        lay.addWidget(lbl_title)
        
        returns_lay = QVBoxLayout()
        returns_lay.setSpacing(5)
        
        weekly_lay = QHBoxLayout()
        lbl_wk_title = QLabel("Haftalık:")
        lbl_wk_title.setProperty("cssClass", "summaryCardSubTitle")
        lbl_wk_value = QLabel("-")
        lbl_wk_value.setProperty("cssClass", "summaryCardValueSmall")
        weekly_lay.addWidget(lbl_wk_title)
        weekly_lay.addWidget(lbl_wk_value)
        weekly_lay.addStretch()
        
        monthly_lay = QHBoxLayout()
        lbl_mo_title = QLabel("Aylık:")
        lbl_mo_title.setProperty("cssClass", "summaryCardSubTitle")
        lbl_mo_value = QLabel("-")
        lbl_mo_value.setProperty("cssClass", "summaryCardValueSmall")
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
        state = "positive" if profit_loss >= 0 else "negative"
        
        self.lbl_total_context.setText(f"{prefix} ₺ {abs(profit_loss):,.2f} ({sign}{roi:.1f}% All Time)")
        self.lbl_total_context.setProperty("state", state)
        self.lbl_total_context.style().unpolish(self.lbl_total_context)
        self.lbl_total_context.style().polish(self.lbl_total_context)

    def update_returns(self, weekly_pct: float, monthly_pct: float):
        if weekly_pct is not None:
            state = "positive" if weekly_pct >= 0 else "negative"
            self.lbl_weekly_return.setText(f"%{weekly_pct:+.2f}")
            self.lbl_weekly_return.setProperty("state", state)
        else:
            self.lbl_weekly_return.setText("-")
            self.lbl_weekly_return.setProperty("state", "neutral")
            
        self.lbl_weekly_return.style().unpolish(self.lbl_weekly_return)
        self.lbl_weekly_return.style().polish(self.lbl_weekly_return)

        if monthly_pct is not None:
            state = "positive" if monthly_pct >= 0 else "negative"
            self.lbl_monthly_return.setText(f"%{monthly_pct:+.2f}")
            self.lbl_monthly_return.setProperty("state", state)
        else:
            self.lbl_monthly_return.setText("-")
            self.lbl_monthly_return.setProperty("state", "neutral")
            
        self.lbl_monthly_return.style().unpolish(self.lbl_monthly_return)
        self.lbl_monthly_return.style().polish(self.lbl_monthly_return)
