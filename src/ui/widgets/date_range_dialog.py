# src/ui/widgets/date_range_dialog.py

from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

from PyQt5.QtCore import QDate, Qt
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLabel,
    QDateEdit,
    QPushButton,
    QMessageBox,
)


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
        title: str = "Tarih Aralığı Seç",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(360)

        today_q = QDate.currentDate()
        self._min_qdate = QDate(min_date.year, min_date.month, min_date.day) if min_date else QDate(2000, 1, 1)
        self._max_qdate = QDate(max_date.year, max_date.month, max_date.day) if max_date else today_q

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        header = QLabel("Excel’e aktarım için tarih aralığını seçin.")
        header.setWordWrap(True)
        main_layout.addWidget(header)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)

        # Başlangıç tarihi
        self.start_edit = QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setMinimumDate(self._min_qdate)
        self.start_edit.setMaximumDate(self._max_qdate)
        self.start_edit.setDate(self._min_qdate if self._min_qdate.isValid() else today_q)

        # Bitiş tarihi
        self.end_edit = QDateEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setMinimumDate(self._min_qdate)
        self.end_edit.setMaximumDate(self._max_qdate)
        self.end_edit.setDate(self._max_qdate if self._max_qdate.isValid() else today_q)

        form.addRow("Başlangıç:", self.start_edit)
        form.addRow("Bitiş:", self.end_edit)

        main_layout.addLayout(form)

        # Butonlar
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.btn_ok = QPushButton("Tamam")
        self.btn_cancel = QPushButton("İptal")

        btn_layout.addWidget(self.btn_ok)
        btn_layout.addWidget(self.btn_cancel)

        main_layout.addLayout(btn_layout)

        # Sinyaller
        self.btn_ok.clicked.connect(self._on_accept_clicked)
        self.btn_cancel.clicked.connect(self.reject)

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
        title: str = "Tarih Aralığı Seç",
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
        ok = dlg.exec_() == QDialog.Accepted
        if not ok:
            return None
        return dlg.get_range()

    # ---- internal ---------------------------------------------------

    def _on_accept_clicked(self) -> None:
        s = self.start_edit.date()
        e = self.end_edit.date()

        if s > e:
            QMessageBox.warning(self, "Geçersiz Aralık", "Başlangıç tarihi bitiş tarihinden büyük olamaz.")
            return

        self.accept()
