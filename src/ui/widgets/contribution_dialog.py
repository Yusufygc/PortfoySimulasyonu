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
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #e2e8f0; font-weight: bold; font-size: 14px; }
            QDoubleSpinBox {
                background-color: #1e293b; color: #f1f5f9;
                border: 1px solid #334155; border-radius: 8px;
                padding: 10px; font-size: 16px; min-height: 30px;
            }
            QDoubleSpinBox:focus { border: 1px solid #3b82f6; }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        lbl = QLabel("Eklenecek Tutar:")
        layout.addWidget(lbl)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(0.01, 100_000_000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setValue(1000)
        layout.addWidget(self.spin_amount)

        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background-color: #475569; color: white; padding: 8px 20px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Ekle")
        btn_save.setStyleSheet("background-color: #3b82f6; color: white; padding: 8px 30px; border-radius: 6px; font-weight: bold;")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_amount(self) -> float:
        return self.spin_amount.value()
