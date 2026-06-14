# src/ui/widgets/dashboard/dialogs/date_range_dialog.py

from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from datetime import date
from typing import Optional, Tuple

from src.qt_compat.qtcore import QDate, Qt
from src.qt_compat.qtwidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QDateEdit,
    QPushButton,
    QMessageBox,
)

from src.ui.widgets.dialog_behavior import configure_dialog_behavior


def _build_date_range_form(min_qdate, max_qdate, today_q):
    form = QFormLayout()
    form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
    form.setHorizontalSpacing(12)
    form.setVerticalSpacing(10)
    start_edit = QDateEdit()
    start_edit.setCalendarPopup(True)
    start_edit.setMinimumDate(min_qdate)
    start_edit.setMaximumDate(max_qdate)
    start_edit.setDate(min_qdate if min_qdate.isValid() else today_q)
    start_edit.setProperty("cssClass", "tradeInputNormal")
    end_edit = QDateEdit()
    end_edit.setCalendarPopup(True)
    end_edit.setMinimumDate(min_qdate)
    end_edit.setMaximumDate(max_qdate)
    end_edit.setDate(max_qdate if max_qdate.isValid() else today_q)
    end_edit.setProperty("cssClass", "tradeInputNormal")
    lbl_start = QLabel(L10N.BASLANGIC_1)
    lbl_start.setProperty("cssClass", "formLabel")
    form.addRow(lbl_start, start_edit)
    lbl_end = QLabel(L10N.BITIS_1)
    lbl_end.setProperty("cssClass", "formLabel")
    form.addRow(lbl_end, end_edit)
    return form, start_edit, end_edit


def _build_date_range_buttons(accept_cb, reject_cb):
    btn_layout = QHBoxLayout()
    btn_layout.addStretch()
    btn_cancel = QPushButton(L10N.IPTAL)
    btn_cancel.setProperty("cssClass", "secondaryButton")
    btn_ok = QPushButton(L10N.TAMAM)
    btn_ok.setProperty("cssClass", "primaryButton")
    btn_layout.addWidget(btn_cancel)
    btn_layout.addWidget(btn_ok)
    btn_ok.clicked.connect(accept_cb)
    btn_cancel.clicked.connect(reject_cb)
    return btn_layout, btn_ok, btn_cancel


class DateRangeDialog(QDialog):
    """
    Excel export için tarih aralığı seçme penceresi.

    Bilerek SADE TUTULDU:
    - Hafta sonu kısıtlaması yok
    - Gelecek tarih kısıtlaması yok (istersen kolayca eklenebilir)
    - Tek kontrol: başlangıç <= bitiş
    """

    def __init__(
        self,
        parent=None,
        min_date: Optional[date] = None,
        max_date: Optional[date] = None,
        title: str = L10N.TARIH_ARALIGI_SEC,
    ) -> None:
        super().__init__(parent)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.setWindowFlag(Qt.WindowCloseButtonHint, True)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(360)
        self.setProperty("cssClass", "dialogContainer")
        today_q = QDate.currentDate()
        min_qdate = QDate(min_date.year, min_date.month, min_date.day) if min_date else QDate(2000, 1, 1)
        max_qdate = QDate(max_date.year, max_date.month, max_date.day) if max_date else today_q
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)
        header = QLabel(L10N.EXCELE_AKTARIM_ICIN_TARIH_ARALIGINI)
        header.setProperty("cssClass", "dialogSubtitle")
        header.setWordWrap(True)
        main_layout.addWidget(header)
        form, self.start_edit, self.end_edit = _build_date_range_form(min_qdate, max_qdate, today_q)
        main_layout.addLayout(form)
        btn_row, self.btn_ok, self.btn_cancel = _build_date_range_buttons(self._on_accept_clicked, self.reject)
        main_layout.addLayout(btn_row)
        configure_dialog_behavior(self, self.btn_ok, self._on_accept_clicked)

    # ---- public API -------------------------------------------------

    def get_range(self) -> Tuple[date, date]:
        """Dialog kapandıktan sonra seçilen tarihleri Python date olarak döner."""
        s_q = self.start_edit.date()
        e_q = self.end_edit.date()
        start = date(s_q.year(), s_q.month(), s_q.day())
        end = date(e_q.year(), e_q.month(), e_q.day())
        return start, end

    @staticmethod
    def get_date_range(
        parent=None,
        min_date: Optional[date] = None,
        max_date: Optional[date] = None,
        title: str = L10N.TARIH_ARALIGI_SEC,
    ) -> Optional[Tuple[date, date]]:
        """
        Kullanımı kolaylaştırmak için helper:

        result = DateRangeDialog.get_date_range(self)
        if result is None:
            # kullanıcı iptal etti
        else:
            start, end = result
        """
        dlg = DateRangeDialog(parent=parent, min_date=min_date, max_date=max_date, title=title)
        ok = dlg.exec() == QDialog.Accepted
        if not ok:
            return None
        return dlg.get_range()

    # ---- internal ---------------------------------------------------

    def _on_accept_clicked(self) -> None:
        s = self.start_edit.date()
        e = self.end_edit.date()

        if s > e:
            QMessageBox.warning(self, L10N.GECERSIZ_ARALIK, L10N.BASLANGIC_TARIHI_BITIS_TARIHINDEN_BUYUK)
            return

        self.accept()
