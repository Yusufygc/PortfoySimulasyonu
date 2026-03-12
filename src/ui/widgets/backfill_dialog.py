# src/ui/widgets/backfill_dialog.py

from __future__ import annotations

from datetime import date
from typing import Optional, Dict

from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QRadioButton,
    QButtonGroup,
    QDateEdit,
    QFrame,
)
from PyQt5.QtCore import Qt, QDate


class BackfillDialog(QDialog):
    """
    Geçmişe yönelik veri yönetimi diyaloğu.
    İki işlem modu:
        1. Veri Çek: yfinance'den tarih aralığı için fiyat verisi indir
        2. Veri Sil: belirli tarih aralığındaki verileri sil
    İki tarih modu:
        1. Tek Gün: sadece bir gün
        2. Tarih Aralığı: başlangıç ve bitiş
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Geçmişe Yönelik Veri Yönetimi")
        self.setFixedSize(480, 380)
        self.setModal(True)
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QDialog { background-color: #0f172a; }
            QLabel { color: #e2e8f0; font-weight: bold; font-size: 13px; }
            QComboBox, QDateEdit {
                background-color: #1e293b; color: #f1f5f9;
                border: 1px solid #334155; border-radius: 8px;
                padding: 8px; font-size: 14px; min-height: 28px;
            }
            QComboBox:hover, QDateEdit:hover { border: 1px solid #3b82f6; }
            QComboBox QAbstractItemView {
                background-color: #1e293b; color: #f1f5f9;
                selection-background-color: #3b82f6;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(25, 25, 25, 25)

        # ---- İşlem Türü ----
        lbl_action = QLabel("🔧 İşlem Türü:")
        layout.addWidget(lbl_action)

        self.combo_action = QComboBox()
        self.combo_action.addItem("📥 Veri Çek (yfinance)", "backfill")
        self.combo_action.addItem("🗑️ Veri Sil", "delete")
        self.combo_action.currentIndexChanged.connect(self._on_action_changed)
        layout.addWidget(self.combo_action)

        # ---- Tarih Modu ----
        lbl_mode = QLabel("📅 Tarih Modu:")
        layout.addWidget(lbl_mode)

        mode_row = QHBoxLayout()
        self.date_mode_group = QButtonGroup(self)

        self.rb_single = QRadioButton("Tek Gün")
        self.rb_single.setChecked(True)
        self.rb_single.setStyleSheet(self._radio_style())
        self.rb_single.setCursor(Qt.PointingHandCursor)

        self.rb_range = QRadioButton("Tarih Aralığı")
        self.rb_range.setStyleSheet(self._radio_style())
        self.rb_range.setCursor(Qt.PointingHandCursor)

        self.date_mode_group.addButton(self.rb_single)
        self.date_mode_group.addButton(self.rb_range)
        self.rb_single.toggled.connect(self._on_mode_changed)

        mode_row.addWidget(self.rb_single)
        mode_row.addWidget(self.rb_range)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # ---- Tarih Seçiciler ----
        dates_frame = QFrame()
        dates_frame.setStyleSheet("QFrame { border: none; }")
        dates_layout = QHBoxLayout(dates_frame)
        dates_layout.setContentsMargins(0, 0, 0, 0)
        dates_layout.setSpacing(15)

        # Başlangıç
        start_col = QVBoxLayout()
        self.lbl_start = QLabel("Tarih:")
        start_col.addWidget(self.lbl_start)
        self.date_start = QDateEdit()
        self.date_start.setDate(QDate.currentDate().addDays(-1))
        self.date_start.setCalendarPopup(True)
        self.date_start.setMaximumDate(QDate.currentDate())
        start_col.addWidget(self.date_start)
        dates_layout.addLayout(start_col)

        # Bitiş
        end_col = QVBoxLayout()
        self.lbl_end = QLabel("Bitiş Tarihi:")
        end_col.addWidget(self.lbl_end)
        self.date_end = QDateEdit()
        self.date_end.setDate(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        self.date_end.setMaximumDate(QDate.currentDate())
        end_col.addWidget(self.date_end)
        dates_layout.addLayout(end_col)

        layout.addWidget(dates_frame)

        # Bitiş alanını başlangıçta gizle (tek gün modu)
        self.lbl_end.setVisible(False)
        self.date_end.setVisible(False)

        # ---- Uyarı mesajı (silme modu) ----
        self.lbl_warning = QLabel("⚠️ Seçilen tarih aralığındaki tüm fiyat verileri silinecek!")
        self.lbl_warning.setStyleSheet(
            "color: #ef4444; font-size: 12px; font-weight: bold; padding: 8px; "
            "background-color: rgba(239,68,68,0.1); border-radius: 6px;"
        )
        self.lbl_warning.setVisible(False)
        layout.addWidget(self.lbl_warning)

        layout.addStretch()

        # ---- Butonlar ----
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("İptal")
        btn_cancel.setStyleSheet(
            "background-color: #475569; color: white; padding: 10px 22px; border-radius: 8px; font-size: 14px;"
        )
        btn_cancel.clicked.connect(self.reject)

        self.btn_execute = QPushButton("📥 Veri Çek")
        self.btn_execute.setStyleSheet(
            "background-color: #3b82f6; color: white; padding: 10px 28px; "
            "border-radius: 8px; font-weight: bold; font-size: 14px;"
        )
        self.btn_execute.clicked.connect(self.accept)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_execute)
        layout.addLayout(btn_layout)

    @staticmethod
    def _radio_style() -> str:
        return """
            QRadioButton {
                color: #f1f5f9; font-size: 13px; spacing: 6px;
            }
            QRadioButton::indicator {
                width: 14px; height: 14px;
                border: 2px solid #64748b; border-radius: 7px;
                background-color: #0f172a;
            }
            QRadioButton::indicator:checked {
                background-color: #3b82f6; border: 2px solid #3b82f6;
            }
        """

    def _on_mode_changed(self, is_single: bool):
        """Tarih modu değiştiğinde bitiş alanını göster/gizle."""
        self.lbl_end.setVisible(not is_single)
        self.date_end.setVisible(not is_single)
        self.lbl_start.setText("Tarih:" if is_single else "Başlangıç Tarihi:")

    def _on_action_changed(self, index: int):
        """İşlem türü değiştiğinde buton ve uyarıyı güncelle."""
        action = self.combo_action.currentData()
        if action == "delete":
            self.btn_execute.setText("🗑️ Veri Sil")
            self.btn_execute.setStyleSheet(
                "background-color: #ef4444; color: white; padding: 10px 28px; "
                "border-radius: 8px; font-weight: bold; font-size: 14px;"
            )
            self.lbl_warning.setVisible(True)
        else:
            self.btn_execute.setText("📥 Veri Çek")
            self.btn_execute.setStyleSheet(
                "background-color: #3b82f6; color: white; padding: 10px 28px; "
                "border-radius: 8px; font-weight: bold; font-size: 14px;"
            )
            self.lbl_warning.setVisible(False)

    def get_result(self) -> Optional[Dict]:
        """
        Diyalog sonucunu döner.
        Returns:
            {"action": "backfill"|"delete", "start_date": date, "end_date": date}
        """
        action = self.combo_action.currentData()
        start = self.date_start.date().toPyDate()

        if self.rb_single.isChecked():
            end = start
        else:
            end = self.date_end.date().toPyDate()

        if start > end:
            return None

        return {
            "action": action,
            "start_date": start,
            "end_date": end,
        }
