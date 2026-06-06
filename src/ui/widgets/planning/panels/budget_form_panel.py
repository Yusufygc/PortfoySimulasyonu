from src.ui.shared.locale_tr import L10N
# src/ui/widgets/planning/panels/budget_form_panel.py
"""
BudgetFormPanel — Dinamik Bütçe Formu Panel Widget'ı

Gelir ve gider kalemlerini dinamik olarak ekleyip silebilen,
anlık özet hesaplayan 3-kolonlu bütçe form paneli.

Kullanım:
    panel = BudgetFormPanel()
    panel.load(budget)           # mevcut ayın verilerini doldurur
    panel.reset()                # tüm kalemleri ve hedefi sıfırlar
    budget = panel.get_budget(month)  # Budget domain nesnesi döner
"""
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QScrollArea, QWidget, QSizePolicy,
)
from PyQt5.QtCore import Qt, QLocale, pyqtSignal

from src.domain.models.budget import Budget, BudgetItem, BudgetPinnedItem
from src.ui.widgets.shared import AnimatedButton, InfoCard, InstantDoubleSpinBox
from src.ui.widgets.shared.controls.icon_label import IconLabel
from src.ui.widgets.planning.panels.budget_item_row import BudgetItemRow



class BudgetFormPanel(QFrame):
    """3-kolonlu dinamik bütçe formu: Gelirler | Giderler | Özet."""

    pin_toggle_requested = pyqtSignal(str, str, float, bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "panelFrame")

        self._income_rows: list[BudgetItemRow] = []
        self._expense_rows: list[BudgetItemRow] = []
        self._pinned_item_keys: set[tuple[str, str]] = set()

        self._init_ui()

    def _init_ui(self) -> None:
        main = QHBoxLayout(self)
        main.setContentsMargins(16, 14, 16, 14)
        main.setSpacing(0)

        income_col, self._income_layout = self._build_item_column(
            title=L10N.GELIRLER,
            icon="banknote",
            icon_color="@COLOR_SUCCESS",
            header_css="successHeader",
            btn_css="successButton",
            btn_icon="plus",
            btn_icon_color="@COLOR_TEXT_WHITE",
            on_add=lambda: self._add_row("", 0.0, "income"),
        )

        expense_col, self._expense_layout = self._build_item_column(
            title=L10N.GIDERLER,
            icon="shopping-cart",
            icon_color="@COLOR_DANGER",
            header_css="dangerHeader",
            btn_css="dangerButton",
            btn_icon="plus",
            btn_icon_color="@COLOR_TEXT_WHITE",
            on_add=lambda: self._add_row("", 0.0, "expense"),
        )

        summary_col = self._build_summary_col()

        main.addWidget(income_col, stretch=2)
        main.addWidget(self._make_vsep())
        main.addWidget(expense_col, stretch=2)
        main.addWidget(self._make_vsep())
        main.addWidget(summary_col, stretch=1)

    def _build_item_column(
        self,
        title: str,
        icon: str,
        icon_color: str,
        header_css: str,
        btn_css: str,
        btn_icon: str,
        btn_icon_color: str,
        on_add,
    ) -> tuple:
        col = QFrame()
        col.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        vbox = QVBoxLayout(col)
        vbox.setContentsMargins(10, 8, 10, 8)
        vbox.setSpacing(8)

        # Başlık satırı
        header = QHBoxLayout()
        header.setSpacing(6)
        icon_lbl = IconLabel(icon, color=icon_color, size=18)
        lbl = QLabel(title)
        lbl.setProperty("cssClass", header_css)

        btn_add = AnimatedButton()
        btn_add.setIconName(btn_icon, color=btn_icon_color, size=16)
        btn_add.setFixedSize(32, 32)
        btn_add.setToolTip(L10N.EKLE)
        btn_add.setProperty("cssClass", btn_css)
        btn_add.clicked.connect(on_add)

        header.addWidget(icon_lbl)
        header.addWidget(lbl)
        header.addStretch()
        header.addWidget(btn_add)
        vbox.addLayout(header)

        # Kaydırılabilir kalem listesi
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 2, 0, 2)
        scroll_layout.setSpacing(4)
        scroll_layout.setAlignment(Qt.AlignTop)

        scroll.setWidget(scroll_widget)
        vbox.addWidget(scroll)

        return col, scroll_layout

    def _build_summary_col(self) -> QFrame:
        col = QFrame()
        col.setMinimumWidth(200)
        col.setMaximumWidth(260)
        vbox = QVBoxLayout(col)
        vbox.setContentsMargins(12, 12, 8, 12)
        vbox.setAlignment(Qt.AlignTop)
        vbox.setSpacing(8)

        lbl_target = QLabel(L10N.AYLIK_TASARRUF_HEDEFI)
        lbl_target.setProperty("cssClass", "inputLabel")

        self.spin_target = InstantDoubleSpinBox()
        self.spin_target.setRange(0, 10_000_000)
        self.spin_target.setDecimals(2)
        self.spin_target.setLocale(QLocale(QLocale.Turkish, QLocale.Turkey))
        self.spin_target.setGroupSeparatorShown(True)
        self.spin_target.setSuffix("TL")
        self.spin_target.setMinimumHeight(32)
        self.spin_target.setSpecialValueText(" ")
        self.spin_target.lineEdit().setPlaceholderText(L10N.K_000_TL)
        self.spin_target.setProperty("cssClass", "customDoubleSpinBox")
        self.spin_target.valueChanged.connect(self._refresh_summary)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setProperty("cssClass", "horizontalSeparator")

        self.card_income  = InfoCard(L10N.TOPLAM_GELIR,  "₺ 0,00", icon_name="trending-up")
        self.card_expense = InfoCard(L10N.TOPLAM_GIDER,  "₺ 0,00", icon_name="trending-down")
        self.card_net     = InfoCard(L10N.NET_KALAN,     "₺ 0,00", icon_name="banknote")
        self.card_goal    = InfoCard(L10N.HEDEF_DURUMU,  "—",       icon_name="target")
        self.card_goal.set_value_min_lines(2)

        self.card_income.set_value_state("positive")
        self.card_expense.set_value_state("negative")

        vbox.addWidget(lbl_target)
        vbox.addWidget(self.spin_target)
        vbox.addWidget(sep)
        vbox.addWidget(self.card_income)
        vbox.addWidget(self.card_expense)
        vbox.addWidget(self.card_net)
        vbox.addWidget(self.card_goal)
        vbox.addStretch()

        return col

    def _make_vsep(self) -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.VLine)
        sep.setProperty("cssClass", "verticalSeparator")
        return sep

    def set_pinned_items(self, pinned_items: list[BudgetPinnedItem]) -> None:
        """Pinli kalem listesini alır ve mevcut satır ikonlarını günceller."""
        self._pinned_item_keys = {
            self._pin_key(item.item_type, item.name)
            for item in pinned_items
        }
        for row in self._income_rows:
            row.set_pinned(self._is_pinned("income", row.get_name()))
        for row in self._expense_rows:
            row.set_pinned(self._is_pinned("expense", row.get_name()))

    def load(self, budget: Budget) -> None:
        """Kaydedilmiş bütçenin kalemlerini forma yükler."""
        self._clear_rows(self._income_rows, self._income_layout)
        self._clear_rows(self._expense_rows, self._expense_layout)
        self.spin_target.setValue(float(budget.savings_target))
        for item in budget.items:
            self._add_row(item.name, float(item.amount), item.item_type, emit=False)
        self._refresh_summary()

    def reset(self) -> None:
        """Tüm kalemleri ve hedefi sıfırlar."""
        self._clear_rows(self._income_rows, self._income_layout)
        self._clear_rows(self._expense_rows, self._expense_layout)
        self.spin_target.setValue(0.0)
        self._refresh_summary()

    def get_budget(self, month: str) -> Budget:
        """Mevcut form durumundan Budget domain nesnesi üretir."""
        items: list[BudgetItem] = []
        for row in self._income_rows:
            items.append(BudgetItem(
                id=None,
                budget_id=None,
                item_type="income",
                name=row.get_name() or "Gelir",
                amount=row.get_amount(),
            ))
        for row in self._expense_rows:
            items.append(BudgetItem(
                id=None,
                budget_id=None,
                item_type="expense",
                name=row.get_name() or "Gider",
                amount=row.get_amount(),
            ))
        return Budget(
            id=None,
            month=month,
            savings_target=self.spin_target.value(),
            items=items,
        )

    def _refresh_summary(self) -> None:
        income  = sum(r.get_amount() for r in self._income_rows)
        expense = sum(r.get_amount() for r in self._expense_rows)
        net     = income - expense
        target  = self.spin_target.value()

        self.card_income.set_value(f"₺ {income:,.2f}")
        self.card_expense.set_value(f"₺ {expense:,.2f}")
        self.card_net.set_value(f"₺ {net:,.2f}")
        self.card_net.set_value_state("positive" if net >= 0 else "negative")

        if target <= 0:
            self.card_goal.set_value(L10N.HEDEF_BELIRLENMEDI)
            self.card_goal.set_value_state("neutral")
        elif net >= target:
            self.card_goal.set_value(L10N.HEDEFE_ULASILIYOR)
            self.card_goal.set_value_state("positive")
        elif net >= 0:
            self.card_goal.set_value(L10N.HEDEFIN_ALTINDA)
            self.card_goal.set_value_state("negative")
        else:
            self.card_goal.set_value(L10N.ACIK_VAR)
            self.card_goal.set_value_state("negative")

    def _add_row(self, name: str, amount: float, item_type: str, emit: bool = True) -> BudgetItemRow:
        row = BudgetItemRow(name, amount, pinned=self._is_pinned(item_type, name))
        row.changed.connect(lambda: self._on_row_changed(row, item_type))
        row.delete_requested.connect(self._on_delete_row)
        row.pin_toggled.connect(lambda pinned: self._on_pin_toggled(row, item_type, pinned))

        if item_type == "income":
            self._income_rows.append(row)
            self._income_layout.addWidget(row)
        else:
            self._expense_rows.append(row)
            self._expense_layout.addWidget(row)

        if emit:
            self._refresh_summary()
            row.name_edit.setFocus()
        return row

    def _on_row_changed(self, row: BudgetItemRow, item_type: str) -> None:
        row.set_pinned(self._is_pinned(item_type, row.get_name()))
        self._refresh_summary()

    def _on_pin_toggled(self, row: BudgetItemRow, item_type: str, pinned: bool) -> None:
        name = row.get_name()
        if not name:
            name = "Gelir" if item_type == "income" else "Gider"
            row.set_name(name)
        self.pin_toggle_requested.emit(item_type, name, row.get_amount(), pinned)

    def _on_delete_row(self, row: BudgetItemRow) -> None:
        if row in self._income_rows:
            self._income_rows.remove(row)
            self._income_layout.removeWidget(row)
        elif row in self._expense_rows:
            self._expense_rows.remove(row)
            self._expense_layout.removeWidget(row)
        row.deleteLater()
        self._refresh_summary()

    def _clear_rows(self, rows: list, layout: QVBoxLayout) -> None:
        for row in rows:
            layout.removeWidget(row)
            row.deleteLater()
        rows.clear()

    def _is_pinned(self, item_type: str, name: str) -> bool:
        return self._pin_key(item_type, name) in self._pinned_item_keys

    @staticmethod
    def _pin_key(item_type: str, name: str) -> tuple[str, str]:
        return item_type, name.strip().casefold()
