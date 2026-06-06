from src.ui.shared.locale_tr import L10N
# src/ui/widgets/planning/panels/goals_panel.py
"""
GoalsPanel — Finansal Hedef Takip Paneli Widget'ı

Hedef tablosu ve fizibilite kartını kapsayan panel.
Aksiyon sinyallerini (add, contribute, delete, analyze) dışarıya iletir.

Kullanım:
    panel = GoalsPanel()
    panel.add_requested.connect(self._on_add_goal)
    panel.contribute_requested.connect(self._on_contribute)
    panel.delete_requested.connect(self._on_delete_goal)
    panel.analyze_requested.connect(self._on_analyze)
    panel.load(goals)
    panel.show_feasibility(result)
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QColor
from src.ui.widgets.shared import AnimatedButton, Toast
from src.ui.core.icon_manager import IconManager


class GoalsPanel(QWidget):
    """Hedef takip sekmesinin tüm görsel yapısını kapsayan panel."""

    add_requested        = pyqtSignal()
    contribute_requested = pyqtSignal(int, str)   # goal_id, goal_name
    delete_requested     = pyqtSignal(int, str)   # goal_id, goal_name
    analyze_requested    = pyqtSignal()
    edit_requested       = pyqtSignal(int)        # goal_id

    _COLUMNS = ["Hedef", L10N.HEDEF_TUTAR_1, "Biriken", L10N.KALAN_AY, L10N.AYLIK_GEREKEN, "İlerleme", "Durum", L10N.ISLEMLER]
    _STATUS_TR = {
        "ACTIVE":    "AKTİF",
        "COMPLETED": "TAMAMLANDI",
        "PAUSED":    "DURAKLATILDI",
        "CANCELLED": "İPTAL",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Buton satırı
        btn_row = QHBoxLayout()

        self._btn_add = AnimatedButton(L10N.YENI_HEDEF_1)
        self._btn_add.setIconName("plus", color="@COLOR_TEXT_WHITE")
        self._btn_add.setMinimumHeight(38)
        self._btn_add.setProperty("cssClass", "primaryButton")
        self._btn_add.clicked.connect(self.add_requested)

        btn_row.addWidget(self._btn_add)
        btn_row.addStretch()

        self._btn_analyze = AnimatedButton(L10N.FIZIBILITE_ANALIZI)
        self._btn_analyze.setIconName("trending-up", color="@COLOR_TEXT_WHITE")
        self._btn_analyze.setMinimumHeight(38)
        self._btn_analyze.setProperty("cssClass", "purpleButton")
        self._btn_analyze.clicked.connect(self.analyze_requested)
        btn_row.addWidget(self._btn_analyze)
        layout.addLayout(btn_row)

        # Fizibilite kartı (başlangıçta gizli)
        self._feasibility_frame = QFrame()
        self._feasibility_frame.setProperty("cssClass", "panelFrameBordered")
        feas_row = QHBoxLayout(self._feasibility_frame)
        feas_row.setContentsMargins(18, 12, 18, 12)
        self._lbl_power  = QLabel(L10N.AYLIK_TASARRUF_GUCU)
        self._lbl_power.setProperty("cssClass", "feasibilityText")
        self._lbl_need   = QLabel(L10N.TOPLAM_AYLIK_IHTIYAC)
        self._lbl_need.setProperty("cssClass", "feasibilityText")
        self._lbl_status = QLabel("")
        self._lbl_status.setProperty("cssClass", "feasibilityStatus")
        feas_row.addWidget(self._lbl_power)
        feas_row.addWidget(self._lbl_need)
        feas_row.addStretch()
        feas_row.addWidget(self._lbl_status)
        self._feasibility_frame.setVisible(False)
        layout.addWidget(self._feasibility_frame)

        # Hedefler tablosu
        from src.ui.widgets.shared.wrapped_header_view import WrappedHeaderView
        self._table = QTableWidget()
        self._table.setColumnCount(len(self._COLUMNS))
        self._table.setHorizontalHeader(WrappedHeaderView(Qt.Horizontal, self._table))
        self._table.setHorizontalHeaderLabels(self._COLUMNS)
        for col in range(len(self._COLUMNS)):
            self._table.horizontalHeaderItem(col).setTextAlignment(Qt.AlignCenter)
        hh = self._table.horizontalHeader()
        hh.setMinimumSectionSize(85)
        for col in range(len(self._COLUMNS)):
            if col == 7:  # İşlemler
                hh.setSectionResizeMode(col, QHeaderView.Fixed)
                self._table.setColumnWidth(col, 120)
            else:
                hh.setSectionResizeMode(col, QHeaderView.Stretch)
        hh.setStretchLastSection(False)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.setShowGrid(True)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(48)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setProperty("cssClass", "goalsTable")
        layout.addWidget(self._table)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, goals: list) -> None:
        """Hedef listesini tabloya yazar."""
        self._table.setRowCount(0)
        for i, goal in enumerate(goals):
            self._table.insertRow(i)
            self._set_readonly(i, 0, goal.name, user_data=goal.id)
            self._set_readonly(i, 1, f"₺ {goal.target_amount:,.2f}", Qt.AlignCenter)
            self._set_readonly(i, 2, f"₺ {goal.current_amount:,.2f}", Qt.AlignCenter)

            months = goal.months_remaining()
            m_item = QTableWidgetItem(f"{months}")
            m_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            m_item.setTextAlignment(Qt.AlignCenter)
            if months == 0:
                m_item.setForeground(QColor("#ef4444"))
            self._table.setItem(i, 3, m_item)

            self._set_readonly(i, 4, f"₺ {goal.required_monthly_contribution():,.2f}", Qt.AlignCenter)

            pct = goal.progress_ratio * 100
            p_item = QTableWidgetItem(f"%{pct:.1f}")
            p_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            p_item.setTextAlignment(Qt.AlignCenter)
            if pct >= 100:
                p_item.setForeground(QColor("#10b981"))
            elif pct >= 50:
                p_item.setForeground(QColor("#ca8a04"))
            self._table.setItem(i, 5, p_item)

            status_tr = self._STATUS_TR.get(goal.status, goal.status)
            s_item = QTableWidgetItem(status_tr)
            s_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            s_item.setTextAlignment(Qt.AlignCenter)
            if goal.status == "COMPLETED":
                s_item.setForeground(QColor("#10b981"))
            elif goal.status == "ACTIVE":
                s_item.setForeground(QColor("#3b82f6"))
            elif goal.status == "PAUSED":
                s_item.setForeground(QColor("#ca8a04"))
            else:
                s_item.setForeground(QColor("#ef4444"))
            self._table.setItem(i, 6, s_item)

            # İşlemler sütunu için butonlar (Düzenle, Katkı Ekle ve Sil)
            action_widget = QWidget()
            action_widget.setProperty("cssClass", "tableActionContainer")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(8, 0, 8, 0)
            action_layout.setSpacing(6)
            action_layout.setAlignment(Qt.AlignCenter)

            btn_edit = QPushButton()
            btn_edit.setProperty("cssClass", "tableActionButtonEdit")
            btn_edit.setMinimumSize(26, 26)
            btn_edit.setMaximumSize(26, 26)
            btn_edit.setCursor(Qt.PointingHandCursor)
            btn_edit.setIcon(IconManager.get_icon("pencil", color="@COLOR_PRIMARY"))
            btn_edit.setIconSize(QSize(16, 16))
            btn_edit.setToolTip(L10N.HEDEFI_DUZENLE)

            btn_contrib = QPushButton()
            btn_contrib.setProperty("cssClass", "tableActionButtonContrib")
            btn_contrib.setMinimumSize(26, 26)
            btn_contrib.setMaximumSize(26, 26)
            btn_contrib.setCursor(Qt.PointingHandCursor)
            btn_contrib.setIcon(IconManager.get_icon("plus", color="@COLOR_PRIMARY"))
            btn_contrib.setIconSize(QSize(16, 16))
            btn_contrib.setToolTip(L10N.KATKI_EKLE_1)

            btn_delete = QPushButton()
            btn_delete.setProperty("cssClass", "tableActionButtonDelete")
            btn_delete.setMinimumSize(26, 26)
            btn_delete.setMaximumSize(26, 26)
            btn_delete.setCursor(Qt.PointingHandCursor)
            btn_delete.setIcon(IconManager.get_icon("trash-2", color="@COLOR_TEXT_WHITE"))
            btn_delete.setIconSize(QSize(16, 16))
            btn_delete.setToolTip(L10N.HEDEFI_SIL)

            # Sinyal bağlantıları (default arguments binding ile güvenli ID aktarımı)
            g_id = goal.id
            g_name = goal.name
            btn_edit.clicked.connect(lambda _, gid=g_id: self.edit_requested.emit(gid))
            btn_contrib.clicked.connect(lambda _, gid=g_id, gname=g_name: self.contribute_requested.emit(gid, gname))
            btn_delete.clicked.connect(lambda _, gid=g_id, gname=g_name: self.delete_requested.emit(gid, gname))

            action_layout.addWidget(btn_edit)
            action_layout.addWidget(btn_contrib)
            action_layout.addWidget(btn_delete)
            self._table.setCellWidget(i, 7, action_widget)

    def show_feasibility(self, result: dict) -> None:
        """Fizibilite analizini gösterir. cssState ile renk yönetimi."""
        self._feasibility_frame.setVisible(True)
        self._lbl_power.setText(L10N.AYLIK_TASARRUF_GUCU_TMPL.format(value=f"{result['monthly_power']:,.2f}"))
        self._lbl_need.setText(L10N.TOPLAM_AYLIK_IHTIYAC_TMPL.format(value=f"{result['total_monthly_need']:,.2f}"))
        status = result["status"]
        self._lbl_status.setText(status)
        state = "positive" if status == "BAŞARILI" else "negative"
        self._lbl_status.setProperty("cssState", state)
        self._lbl_status.style().unpolish(self._lbl_status)
        self._lbl_status.style().polish(self._lbl_status)

    def current_goal(self) -> tuple[int, str] | tuple[None, None]:
        """Seçili satırın (goal_id, goal_name) çiftini döner."""
        row = self._table.currentRow()
        if row < 0:
            return None, None
        item = self._table.item(row, 0)
        return item.data(Qt.UserRole), item.text()

    # ------------------------------------------------------------------
    # İç Sinyal Yönlendirme
    # ------------------------------------------------------------------


    # ------------------------------------------------------------------
    # Yardımcılar
    # ------------------------------------------------------------------

    def _set_readonly(self, row: int, col: int, text: str,
                      align=None, user_data=None) -> None:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        if align is not None:
            item.setTextAlignment(align)
        if user_data is not None:
            item.setData(Qt.UserRole, user_data)
        self._table.setItem(row, col, item)
