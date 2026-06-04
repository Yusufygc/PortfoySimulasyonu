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
from PyQt5.QtCore import QDate, Qt

from src.ui.widgets.dialog_behavior import configure_dialog_behavior

class GoalInputDialog(QDialog):
    """Yeni hedef ekleme diyaloğu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Yeni Hedef")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setFixedSize(420, 320)  # Slightly larger to fit validation error label
        self.setModal(True)
        self._init_ui()
        configure_dialog_behavior(self, self.btn_save)

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
        self.spin_amount.setGroupSeparatorShown(True)
        self.spin_amount.setValue(50000)
        self.spin_amount.setProperty("cssClass", "tradeInputNormal")
        lbl_amount = QLabel("Hedef Tutar:")
        lbl_amount.setProperty("cssClass", "formLabel")
        form.addRow(lbl_amount, self.spin_amount)

        self.date_deadline = QDateEdit()
        self.date_deadline.setDate(QDate.currentDate().addMonths(12))
        self.date_deadline.setCalendarPopup(True)
        if self.date_deadline.calendarWidget():
            self.date_deadline.calendarWidget().setMinimumDate(QDate.currentDate())
        self.date_deadline.setProperty("cssClass", "tradeInputNormal")
        lbl_date = QLabel("Hedef Tarih:")
        lbl_date.setProperty("cssClass", "formLabel")
        form.addRow(lbl_date, self.date_deadline)

        self.lbl_error = QLabel()
        self.lbl_error.setProperty("cssClass", "validationErrorLabel")
        self.lbl_error.setVisible(False)
        form.addRow("", self.lbl_error)

        self.combo_priority = QComboBox()
        self.combo_priority.addItems(["Düşük", "Orta", "Yüksek"])
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
        self.btn_save = QPushButton("Ekle")
        self.btn_save.setProperty("cssClass", "tradeConfirmBuyBtn")
        self.btn_save.clicked.connect(self.accept)
        self.btn_save.setDefault(True)
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        # Connect validation signals
        self.txt_name.textChanged.connect(self._validate_inputs)
        self.date_deadline.dateChanged.connect(self._validate_inputs)
        self._validate_inputs()

    def _validate_inputs(self):
        name = self.txt_name.text().strip()
        date_val = self.date_deadline.date()
        today = QDate.currentDate()

        is_valid = True
        error_msg = ""

        if not name:
            is_valid = False
        elif date_val < today:
            is_valid = False
            error_msg = "Hedef tarih bugünden önce olamaz!"

        self.lbl_error.setText(error_msg)
        self.lbl_error.setVisible(bool(error_msg))
        self.btn_save.setEnabled(is_valid)

    def accept(self):
        name = self.txt_name.text().strip()
        date_val = self.date_deadline.date()
        today = QDate.currentDate()
        if not name or date_val < today:
            return
        super().accept()

    def get_result(self):
        name = self.txt_name.text().strip()
        if not name:
            return None
        priority_map = {
            "Düşük": "LOW",
            "Orta": "MEDIUM",
            "Yüksek": "HIGH"
        }
        return {
            "name": name,
            "target_amount": self.spin_amount.value(),
            "deadline": self.date_deadline.date().toPyDate(),
            "priority": priority_map.get(self.combo_priority.currentText(), "MEDIUM"),
        }
