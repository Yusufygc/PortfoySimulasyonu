from src.ui.shared.locale_tr import L10N
from src.qt_compat.qtwidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QDateEdit,
    QComboBox,
    QPushButton,
    QMessageBox,
)
from src.ui.widgets.shared import InstantDoubleSpinBox
from src.qt_compat.qtcore import QDate, Qt

from src.ui.widgets.dialog_behavior import configure_dialog_behavior


def _build_goal_form(parent_layout):
    form = QFormLayout()
    form.setSpacing(12)
    txt_name = QLineEdit()
    txt_name.setPlaceholderText(L10N.ORN_ARABA_EV_TATIL)
    txt_name.setProperty("cssClass", "tradeInputNormal")
    lbl_name = QLabel(L10N.HEDEF_ADI)
    lbl_name.setProperty("cssClass", "formLabel")
    form.addRow(lbl_name, txt_name)
    spin_amount = InstantDoubleSpinBox()
    spin_amount.setRange(1, 100_000_000)
    spin_amount.setDecimals(2)
    spin_amount.setSuffix(" TL")
    spin_amount.setGroupSeparatorShown(True)
    spin_amount.setValue(50000)
    spin_amount.setProperty("cssClass", "tradeInputNormal")
    lbl_amount = QLabel(L10N.HEDEF_TUTAR)
    lbl_amount.setProperty("cssClass", "formLabel")
    form.addRow(lbl_amount, spin_amount)
    date_deadline = QDateEdit()
    minimum_deadline = QDate.currentDate()
    date_deadline.setMinimumDate(minimum_deadline)
    date_deadline.setDate(QDate.currentDate().addMonths(12))
    date_deadline.setCalendarPopup(True)
    if date_deadline.calendarWidget():
        date_deadline.calendarWidget().setMinimumDate(minimum_deadline)
    date_deadline.setProperty("cssClass", "tradeInputNormal")
    lbl_date = QLabel(L10N.HEDEF_TARIH)
    lbl_date.setProperty("cssClass", "formLabel")
    form.addRow(lbl_date, date_deadline)
    lbl_error = QLabel()
    lbl_error.setProperty("cssClass", "validationErrorLabel")
    lbl_error.setVisible(False)
    form.addRow("", lbl_error)
    combo_priority = QComboBox()
    combo_priority.addItems(["Düşük", "Orta", "Yüksek"])
    combo_priority.setCurrentIndex(1)
    combo_priority.setProperty("cssClass", "tradeInputNormal")
    lbl_prio = QLabel(L10N.ONCELIK)
    lbl_prio.setProperty("cssClass", "formLabel")
    form.addRow(lbl_prio, combo_priority)
    parent_layout.addLayout(form)
    parent_layout.addStretch()
    return txt_name, spin_amount, date_deadline, lbl_error, combo_priority


def _build_goal_buttons(parent_layout, accept_cb, reject_cb):
    btn_layout = QHBoxLayout()
    btn_layout.addStretch()
    btn_cancel = QPushButton(L10N.CANCEL)
    btn_cancel.setProperty("cssClass", "secondaryButton")
    btn_cancel.clicked.connect(reject_cb)
    btn_save = QPushButton(L10N.EKLE)
    btn_save.setProperty("cssClass", "tradeConfirmBuyBtn")
    btn_save.clicked.connect(accept_cb)
    btn_save.setDefault(True)
    btn_layout.addWidget(btn_cancel)
    btn_layout.addWidget(btn_save)
    parent_layout.addLayout(btn_layout)
    return btn_save


class GoalInputDialog(QDialog):
    """Yeni hedef ekleme diyaloğu."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(L10N.YENI_HEDEF)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self.setFixedSize(420, 320)  # Slightly larger to fit validation error label
        self.setModal(True)
        self._init_ui()
        configure_dialog_behavior(self, self.btn_save)

    def _init_ui(self):
        self.setProperty("cssClass", "dialogContainer")
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(25, 25, 25, 25)
        (self.txt_name, self.spin_amount, self.date_deadline,
         self.lbl_error, self.combo_priority) = _build_goal_form(layout)
        self.btn_save = _build_goal_buttons(layout, self.accept, self.reject)
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
            error_msg = L10N.HEDEF_ADI_BOS_OLAMAZ
        elif date_val <= today:
            is_valid = False
            error_msg = L10N.HEDEF_TARIHI_YARIN_VEYA_SONRA_OLMALI

        self.lbl_error.setText(error_msg)
        self.lbl_error.setVisible(bool(error_msg))
        self.btn_save.setEnabled(True)

    def accept(self):
        name = self.txt_name.text().strip()
        date_val = self.date_deadline.date()
        today = QDate.currentDate()
        if not name:
            QMessageBox.warning(self, L10N.ERROR, L10N.HEDEF_ADI_BOS_OLAMAZ)
            self.txt_name.setFocus()
            return
        if not self.spin_amount.has_valid_input(require_positive=True):
            QMessageBox.warning(self, L10N.ERROR, L10N.GECERLI_BIR_TUTAR_GIRINIZ)
            self.spin_amount.setFocus()
            return
        if date_val <= today:
            QMessageBox.warning(self, L10N.ERROR, L10N.HEDEF_TARIHI_YARIN_VEYA_SONRA_OLMALI)
            self.date_deadline.setFocus()
            return
        super().accept()

    def load_goal(self, goal) -> None:
        self.setWindowTitle(L10N.HEDEFI_DUZENLE)
        self.txt_name.setText(goal.name)
        self.spin_amount.setValue(float(goal.target_amount))
        if goal.deadline:
            self.date_deadline.setDate(goal.deadline)
        priority_map_reverse = {
            "LOW": 0,
            "MEDIUM": 1,
            "HIGH": 2
        }
        self.combo_priority.setCurrentIndex(priority_map_reverse.get(goal.priority, 1))
        self.btn_save.setText(L10N.SAVE)
        self._validate_inputs()

    def get_result(self):
        name = self.txt_name.text().strip()
        if not name:
            return None
        if not self.spin_amount.has_valid_input(require_positive=True):
            return None
        if self.date_deadline.date() <= QDate.currentDate():
            return None
        priority_map = {
            "Düşük": "LOW",
            "Orta": "MEDIUM",
            "Yüksek": "HIGH"
        }
        return {
            "name": name,
            "target_amount": self.spin_amount.input_decimal_value(),
            "deadline": self.date_deadline.date().toPyDate(),
            "priority": priority_map.get(self.combo_priority.currentText(), "MEDIUM"),
        }
