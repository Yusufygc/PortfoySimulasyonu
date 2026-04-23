# src/ui/widgets/panels/budget_form_panel.py
"""
BudgetFormPanel — Bütçe Formu Panel Widget'ı

Aylık gelir ve gider giriş spinbox'larını içeren form paneli.
Veriye erişim için public property'ler sunar; kayıt/analiz
mantığı üst bileşende (PlanningPage) kalır.

Kullanım:
    panel = BudgetFormPanel()
    panel.load(budget)          # mevcut ayın verilerini doldurur
    panel.reset()               # tüm alanları sıfırlar
    data = panel.get_values()   # dict döner
"""
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox
)
from src.ui.core.icon_manager import IconManager
from PyQt5.QtCore import QSize


class BudgetFormPanel(QFrame):
    """Aylık gelir/gider veri giriş formu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "panelFrame")
        self._init_ui()

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 15, 20, 15)
        outer.setSpacing(12)

        # Gelirler
        lbl_income = QLabel("Gelirler")
        lbl_income.setProperty("cssClass", "successHeader")
        
        income_header = QHBoxLayout()
        income_header.setSpacing(10)
        img_income = QLabel()
        img_income.setPixmap(IconManager.get_icon("banknote", color="@COLOR_SUCCESS", size=QSize(22, 22)).pixmap(22, 22))
        income_header.addWidget(img_income)
        income_header.addWidget(lbl_income)
        income_header.addStretch()
        outer.addLayout(income_header)

        income_row = QHBoxLayout()
        income_row.setSpacing(20)
        self.spin_salary     = self._make_spin()
        self.spin_additional = self._make_spin()
        income_row.addLayout(self._labeled("Maaş", self.spin_salary, "wallet"))
        income_row.addLayout(self._labeled("Ek Gelir", self.spin_additional, "plus"))
        outer.addLayout(income_row)

        # Giderler
        lbl_expense = QLabel("Giderler")
        lbl_expense.setProperty("cssClass", "dangerHeader")
        
        expense_header = QHBoxLayout()
        expense_header.setSpacing(10)
        img_expense = QLabel()
        img_expense.setPixmap(IconManager.get_icon("shopping-cart", color="@COLOR_DANGER", size=QSize(22, 22)).pixmap(22, 22))
        expense_header.addWidget(img_expense)
        expense_header.addWidget(lbl_expense)
        expense_header.addStretch()
        outer.addLayout(expense_header)

        expense_row1 = QHBoxLayout()
        expense_row1.setSpacing(20)
        self.spin_rent      = self._make_spin()
        self.spin_bills     = self._make_spin()
        self.spin_food      = self._make_spin()
        expense_row1.addLayout(self._labeled("Kira", self.spin_rent, "home"))
        expense_row1.addLayout(self._labeled("Fatura", self.spin_bills, "file-text"))
        expense_row1.addLayout(self._labeled("Market", self.spin_food, "shopping-cart"))
        outer.addLayout(expense_row1)

        expense_row2 = QHBoxLayout()
        expense_row2.setSpacing(20)
        self.spin_transport = self._make_spin()
        self.spin_luxury    = self._make_spin()
        self.spin_target    = self._make_spin()
        expense_row2.addLayout(self._labeled("Ulaşım", self.spin_transport, "car"))
        expense_row2.addLayout(self._labeled("Lüks", self.spin_luxury, "star"))
        expense_row2.addLayout(self._labeled("Bütçe Hedefi", self.spin_target, "target"))
        outer.addLayout(expense_row2)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, budget) -> None:
        """Kaydedilmiş bir bütçe nesnesinin değerlerini formdaki alanlara yazar."""
        self.spin_salary.setValue(budget.income_salary)
        self.spin_additional.setValue(budget.income_additional)
        self.spin_rent.setValue(budget.expense_rent)
        self.spin_bills.setValue(budget.expense_bills)
        self.spin_food.setValue(budget.expense_food)
        self.spin_transport.setValue(budget.expense_transport)
        self.spin_luxury.setValue(budget.expense_luxury)
        self.spin_target.setValue(budget.savings_target)

    def reset(self) -> None:
        """Tüm alanları sıfırlar."""
        for spin in self._all_spins():
            spin.setValue(0.0)

    def get_values(self) -> dict:
        """Form değerlerini dict olarak döner."""
        return {
            "income_salary":     self.spin_salary.value(),
            "income_additional": self.spin_additional.value(),
            "expense_rent":      self.spin_rent.value(),
            "expense_bills":     self.spin_bills.value(),
            "expense_food":      self.spin_food.value(),
            "expense_transport": self.spin_transport.value(),
            "expense_luxury":    self.spin_luxury.value(),
            "savings_target":    self.spin_target.value(),
        }

    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------

    def _make_spin(self) -> QDoubleSpinBox:
        spin = QDoubleSpinBox()
        spin.setRange(0, 10_000_000)
        spin.setDecimals(2)
        spin.setSuffix(" TL")
        spin.setMinimumHeight(36)
        spin.setMinimumWidth(140)
        spin.setProperty("cssClass", "customDoubleSpinBox")
        return spin

    @staticmethod
    def _labeled(text: str, spin: QDoubleSpinBox, icon_name: str = "") -> QVBoxLayout:
        layout = QVBoxLayout()
        layout.setSpacing(6)
        
        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(6)
        if icon_name:
            img = QLabel()
            img.setPixmap(IconManager.get_icon(icon_name, color="@COLOR_TEXT_SECONDARY", size=QSize(16, 16)).pixmap(16, 16))
            lbl_row.addWidget(img)
            
        lbl = QLabel(text)
        lbl.setProperty("cssClass", "inputLabel")
        lbl_row.addWidget(lbl)
        lbl_row.addStretch()
        
        layout.addLayout(lbl_row)
        layout.addWidget(spin)
        return layout

    def _all_spins(self):
        return [
            self.spin_salary, self.spin_additional,
            self.spin_rent, self.spin_bills, self.spin_food,
            self.spin_transport, self.spin_luxury, self.spin_target,
        ]
