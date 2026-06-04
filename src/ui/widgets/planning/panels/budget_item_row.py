from __future__ import annotations

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QDoubleSpinBox, QFrame, QHBoxLayout, QLineEdit

from src.ui.widgets.shared import AnimatedButton


class BudgetItemRow(QFrame):
    """Single income or expense row with edit, pin and delete actions."""

    changed = pyqtSignal()
    delete_requested = pyqtSignal(object)
    pin_toggled = pyqtSignal(bool)

    def __init__(self, name: str = "", amount: float = 0.0, pinned: bool = False, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "budgetItemRow")

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        layout.setSpacing(6)

        self.name_edit = QLineEdit(name)
        self.name_edit.setPlaceholderText("Kalem adi...")
        self.name_edit.setMinimumWidth(110)
        self.name_edit.setMinimumHeight(30)
        self.name_edit.textChanged.connect(self.changed)

        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 10_000_000)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSuffix(" TL")
        self.amount_spin.setValue(amount)
        self.amount_spin.setMinimumWidth(120)
        self.amount_spin.setMaximumWidth(180)
        self.amount_spin.setMinimumHeight(30)
        self.amount_spin.setProperty("cssClass", "customDoubleSpinBox")
        self.amount_spin.valueChanged.connect(self.changed)

        self.btn_pin = AnimatedButton()
        self.btn_pin.setCheckable(True)
        self.btn_pin.setFixedSize(28, 28)
        self.btn_pin.clicked.connect(self._on_pin_clicked)

        btn_edit = AnimatedButton()
        btn_edit.setIconName("pencil", color="@COLOR_TEXT_SECONDARY", size=13)
        btn_edit.setFixedSize(28, 28)
        btn_edit.setProperty("cssClass", "iconButton")
        btn_edit.clicked.connect(lambda: self.name_edit.setFocus())

        btn_delete = AnimatedButton()
        btn_delete.setIconName("trash-2", color="@COLOR_DANGER", size=13)
        btn_delete.setFixedSize(28, 28)
        btn_delete.setProperty("cssClass", "dangerIconButton")
        btn_delete.clicked.connect(lambda: self.delete_requested.emit(self))

        layout.addWidget(self.name_edit, stretch=1)
        layout.addWidget(self.amount_spin)
        layout.addWidget(self.btn_pin)
        layout.addWidget(btn_edit)
        layout.addWidget(btn_delete)

        self.set_pinned(pinned)

    def get_name(self) -> str:
        return self.name_edit.text().strip()

    def set_name(self, name: str) -> None:
        self.name_edit.setText(name)

    def get_amount(self) -> float:
        return self.amount_spin.value()

    def set_pinned(self, pinned: bool) -> None:
        self.btn_pin.blockSignals(True)
        self.btn_pin.setChecked(pinned)
        self.btn_pin.blockSignals(False)
        self.btn_pin.setProperty("cssClass", "pinIconButtonActive" if pinned else "pinIconButton")
        self.btn_pin.setIconName(
            "bookmark",
            color="@COLOR_PRIMARY" if pinned else "@COLOR_TEXT_SECONDARY",
            size=13,
        )
        self.btn_pin.setToolTip("Pini kaldir" if pinned else "Pinle")
        self.btn_pin.style().unpolish(self.btn_pin)
        self.btn_pin.style().polish(self.btn_pin)

    def _on_pin_clicked(self) -> None:
        self.pin_toggled.emit(self.btn_pin.isChecked())
