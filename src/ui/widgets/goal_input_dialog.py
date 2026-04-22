from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
    QDateEdit,
    QComboBox,
    QPushButton
)
from PyQt5.QtCore import QDate

class GoalInputDialog(QDialog):
    """Yeni hedef ekleme diyaloğu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🎯 Yeni Hedef")
        self.setFixedSize(420, 300)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "dialogContainer")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 25, 25, 25)

        form = QFormLayout()
        form.setSpacing(12)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Örn: Araba, Ev, Tatil...")
        self.txt_name.setProperty("cssClass", "tradeInputNormal")
        lbl_name = QLabel("Hedef Adı:")
        lbl_name.setProperty("cssClass", "formLabel")
        form.addRow(lbl_name, self.txt_name)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(1, 100_000_000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setValue(50000)
        self.spin_amount.setProperty("cssClass", "tradeInputNormal")
        lbl_amount = QLabel("Hedef Tutar:")
        lbl_amount.setProperty("cssClass", "formLabel")
        form.addRow(lbl_amount, self.spin_amount)

        self.date_deadline = QDateEdit()
        self.date_deadline.setDate(QDate.currentDate().addMonths(12))
        self.date_deadline.setCalendarPopup(True)
        self.date_deadline.setProperty("cssClass", "tradeInputNormal")
        lbl_date = QLabel("Hedef Tarih:")
        lbl_date.setProperty("cssClass", "formLabel")
        form.addRow(lbl_date, self.date_deadline)

        self.combo_priority = QComboBox()
        self.combo_priority.addItems(["LOW", "MEDIUM", "HIGH"])
        self.combo_priority.setCurrentIndex(1)
        self.combo_priority.setProperty("cssClass", "tradeInputNormal")
        lbl_prio = QLabel("Öncelik:")
        lbl_prio.setProperty("cssClass", "formLabel")
        form.addRow(lbl_prio, self.combo_priority)

        layout.addLayout(form)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setProperty("cssClass", "secondaryButton")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Ekle")
        btn_save.setProperty("cssClass", "tradeConfirmBuyBtn")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)
        layout.addLayout(btn_layout)

    def get_result(self):
        name = self.txt_name.text().strip()
        if not name:
            return None
        return {
            "name": name,
            "target_amount": self.spin_amount.value(),
            "deadline": self.date_deadline.date().toPyDate(),
            "priority": self.combo_priority.currentText(),
        }
