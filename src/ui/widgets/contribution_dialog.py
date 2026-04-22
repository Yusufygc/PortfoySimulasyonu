from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QDoubleSpinBox,
    QPushButton
)

class ContributionDialog(QDialog):
    """Hedefe katkı ekleme diyaloğu."""

    def __init__(self, goal_name: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"💵 Katkı Ekle — {goal_name}")
        self.setFixedSize(350, 180)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "dialogContainer")

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        lbl = QLabel("Eklenecek Tutar:")
        lbl.setProperty("cssClass", "dialogHeaderTitle")
        layout.addWidget(lbl)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0.01, 100_000_000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setValue(1000)
        self.spin_amount.setProperty("cssClass", "tradeInputNormal")
        layout.addWidget(self.spin_amount)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setProperty("cssClass", "secondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Ekle")
        btn_save.setProperty("cssClass", "primaryButton")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_amount(self) -> float:
        return self.spin_amount.value()
