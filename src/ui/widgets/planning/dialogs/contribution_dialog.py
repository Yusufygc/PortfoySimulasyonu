from src.ui.shared.locale_tr import L10N
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton
)
from src.ui.widgets.shared import InstantDoubleSpinBox
from PyQt5.QtCore import Qt

from src.ui.widgets.dialog_behavior import configure_dialog_behavior

class ContributionDialog(QDialog):
    """Hedefe katkı ekleme diyaloğu."""

    def __init__(self, goal_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Katkı Ekle — {goal_name}")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setFixedSize(350, 180)
        self.setModal(True)
        self._init_ui()
        configure_dialog_behavior(self, self.btn_save, self.accept)

    def _init_ui(self):
        self.setProperty("cssClass", "dialogContainer")

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        lbl = QLabel(L10N.EKLENECEK_TUTAR)
        lbl.setProperty("cssClass", "dialogHeaderTitle")
        layout.addWidget(lbl)

        self.spin_amount = InstantDoubleSpinBox()
        self.spin_amount.setRange(0.01, 100_000_000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setGroupSeparatorShown(True)
        self.spin_amount.setValue(1000)
        self.spin_amount.setProperty("cssClass", "tradeInputNormal")
        layout.addWidget(self.spin_amount)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton(L10N.CANCEL)
        btn_cancel.setProperty("cssClass", "secondaryButton")
        btn_cancel.clicked.connect(self.reject)
        self.btn_save = QPushButton(L10N.EKLE)
        self.btn_save.setProperty("cssClass", "primaryButton")
        self.btn_save.clicked.connect(self.accept)
        self.btn_save.setDefault(True)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

    def get_amount(self) -> float:
        return self.spin_amount.value()
