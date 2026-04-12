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
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #e2e8f0; font-weight: bold; font-size: 14px; }
            QLineEdit, QDoubleSpinBox, QDateEdit, QComboBox {
                background-color: #1e293b; color: #f1f5f9;
                border: 1px solid #334155; border-radius: 8px;
                padding: 8px; font-size: 14px; min-height: 25px;
            }
            QLineEdit:focus, QDoubleSpinBox:focus, QDateEdit:focus {
                border: 1px solid #3b82f6;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 25, 25, 25)

        form = QFormLayout()
        form.setSpacing(12)

        self.txt_name = QLineEdit()
        self.txt_name.setPlaceholderText("Örn: Araba, Ev, Tatil...")
        form.addRow("Hedef Adı:", self.txt_name)

        self.spin_amount = QDoubleSpinBox()
        self.spin_amount.setRange(1, 100_000_000)
        self.spin_amount.setDecimals(2)
        self.spin_amount.setSuffix(" TL")
        self.spin_amount.setValue(50000)
        form.addRow("Hedef Tutar:", self.spin_amount)

        self.date_deadline = QDateEdit()
        self.date_deadline.setDate(QDate.currentDate().addMonths(12))
        self.date_deadline.setCalendarPopup(True)
        form.addRow("Hedef Tarih:", self.date_deadline)

        self.combo_priority = QComboBox()
        self.combo_priority.addItems(["LOW", "MEDIUM", "HIGH"])
        self.combo_priority.setCurrentIndex(1)
        form.addRow("Öncelik:", self.combo_priority)

        layout.addLayout(form)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet("background-color: #475569; color: white; padding: 8px 20px; border-radius: 6px;")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Ekle")
        btn_save.setStyleSheet("background-color: #10b981; color: white; padding: 8px 30px; border-radius: 6px; font-weight: bold;")
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
