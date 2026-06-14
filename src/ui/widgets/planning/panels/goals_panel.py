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
from src.qt_compat.qtwidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QHeaderView, QFrame, QSizePolicy
)
from src.qt_compat.qtcore import Qt, Signal, QSize
from src.qt_compat.qtgui import QColor
from src.ui.widgets.shared import AnimatedButton, Toast
from src.ui.core.icon_manager import IconManager


_PRIORITY_ORDER = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}


def _build_goals_btn_row(add_cb, analyze_cb):
    btn_row = QHBoxLayout()
    btn_add = AnimatedButton(L10N.YENI_HEDEF_1)
    btn_add.setIconName("plus", color="@COLOR_TEXT_WHITE")
    btn_add.setMinimumHeight(38)
    btn_add.setProperty("cssClass", "primaryButton")
    btn_add.clicked.connect(add_cb)
    btn_row.addWidget(btn_add)
    btn_row.addStretch()
    btn_analyze = AnimatedButton(L10N.FIZIBILITE_ANALIZI)
    btn_analyze.setIconName("trending-up", color="@COLOR_TEXT_WHITE")
    btn_analyze.setMinimumHeight(38)
    btn_analyze.setProperty("cssClass", "purpleButton")
    btn_analyze.clicked.connect(analyze_cb)
    btn_row.addWidget(btn_analyze)
    return btn_row, btn_add, btn_analyze


def _build_feasibility_frame():
    frame = QFrame()
    frame.setProperty("cssClass", "panelFrameBordered")
    feas_row = QHBoxLayout(frame)
    feas_row.setContentsMargins(18, 12, 18, 12)
    lbl_power = QLabel(L10N.AYLIK_TASARRUF_GUCU)
    lbl_power.setProperty("cssClass", "feasibilityText")
    lbl_need = QLabel(L10N.TOPLAM_AYLIK_IHTIYAC)
    lbl_need.setProperty("cssClass", "feasibilityText")
    lbl_status = QLabel("")
    lbl_status.setProperty("cssClass", "feasibilityStatus")
    feas_row.addWidget(lbl_power)
    feas_row.addWidget(lbl_need)
    feas_row.addStretch()
    feas_row.addWidget(lbl_status)
    return frame, lbl_power, lbl_need, lbl_status


def _build_goals_table(columns: list) -> QTableWidget:
    from src.ui.widgets.shared.wrapped_header_view import WrappedHeaderView
    table = QTableWidget()
    table.setColumnCount(len(columns))
    table.setHorizontalHeader(WrappedHeaderView(Qt.Horizontal, table))
    table.setHorizontalHeaderLabels(columns)
    for col in range(len(columns)):
        table.horizontalHeaderItem(col).setTextAlignment(Qt.AlignCenter)
    hh = table.horizontalHeader()
    hh.setMinimumSectionSize(85)
    for col in range(len(columns)):
        if col == 7:
            hh.setSectionResizeMode(col, QHeaderView.Fixed)
            table.setColumnWidth(col, 120)
        else:
            hh.setSectionResizeMode(col, QHeaderView.Stretch)
    hh.setStretchLastSection(False)
    table.setSelectionBehavior(QTableWidget.SelectRows)
    table.setAlternatingRowColors(True)
    table.setShowGrid(True)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(48)
    table.setEditTriggers(QTableWidget.NoEditTriggers)
    table.setProperty("cssClass", "goalsTable")
    return table


class GoalsPanel(QWidget):
    """Hedef takip sekmesinin tüm görsel yapısını kapsayan panel."""

    add_requested        = Signal()
    contribute_requested = Signal(int, str)   # goal_id, goal_name
    delete_requested     = Signal(int, str)   # goal_id, goal_name
    analyze_requested    = Signal()
    edit_requested       = Signal(int)        # goal_id

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
        btn_row, self._btn_add, self._btn_analyze = _build_goals_btn_row(
            self.add_requested, self.analyze_requested
        )
        layout.addLayout(btn_row)
        (self._feasibility_frame, self._lbl_power,
         self._lbl_need, self._lbl_status) = _build_feasibility_frame()
        self._feasibility_frame.setVisible(False)
        layout.addWidget(self._feasibility_frame)
        self._table = _build_goals_table(self._COLUMNS)
        layout.addWidget(self._table)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, goals: list) -> None:
        """Hedef listesini tabloya yazar."""
        self._table.setRowCount(0)
        sorted_goals = sorted(
            enumerate(goals),
            key=lambda item: (
                _PRIORITY_ORDER.get(getattr(item[1], "priority", "MEDIUM"), 1),
                item[1].months_remaining(),
                item[0],
            ),
        )
        for i, (_, goal) in enumerate(sorted_goals):
            self._table.insertRow(i)
            self._set_readonly(i, 0, goal.name, user_data=goal.id)
            self._set_readonly(i, 1, f"₺ {goal.target_amount:,.2f}", Qt.AlignCenter)
            self._set_readonly(i, 2, f"₺ {goal.current_amount:,.2f}", Qt.AlignCenter)
            self._set_row_months_cell(i, goal)
            self._set_readonly(i, 4, f"₺ {goal.required_monthly_contribution():,.2f}", Qt.AlignCenter)
            self._set_row_progress_cell(i, goal)
            self._set_row_status_cell(i, goal)
            self._set_row_actions(i, goal)

    def _set_row_months_cell(self, row: int, goal) -> None:
        months = goal.months_remaining()
        m_item = QTableWidgetItem(f"{months}")
        m_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        m_item.setTextAlignment(Qt.AlignCenter)
        if months == 0:
            m_item.setForeground(QColor("#ef4444"))
        self._table.setItem(row, 3, m_item)

    def _set_row_progress_cell(self, row: int, goal) -> None:
        pct = goal.progress_ratio * 100
        p_item = QTableWidgetItem(f"%{pct:.1f}")
        p_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        p_item.setTextAlignment(Qt.AlignCenter)
        if pct >= 100:
            p_item.setForeground(QColor("#10b981"))
        elif pct >= 50:
            p_item.setForeground(QColor("#ca8a04"))
        self._table.setItem(row, 5, p_item)

    def _set_row_status_cell(self, row: int, goal) -> None:
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
        self._table.setItem(row, 6, s_item)

    def _set_row_actions(self, row: int, goal) -> None:
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
        is_completed = goal.status == "COMPLETED"
        btn_contrib.setEnabled(not is_completed)
        btn_delete = QPushButton()
        btn_delete.setProperty("cssClass", "tableActionButtonDelete")
        btn_delete.setMinimumSize(26, 26)
        btn_delete.setMaximumSize(26, 26)
        btn_delete.setCursor(Qt.PointingHandCursor)
        btn_delete.setIcon(IconManager.get_icon("trash-2", color="@COLOR_TEXT_WHITE"))
        btn_delete.setIconSize(QSize(16, 16))
        btn_delete.setToolTip(L10N.HEDEFI_SIL)
        g_id, g_name = goal.id, goal.name
        btn_edit.clicked.connect(lambda _, gid=g_id: self.edit_requested.emit(gid))
        if not is_completed:
            btn_contrib.clicked.connect(lambda _, gid=g_id, gname=g_name: self.contribute_requested.emit(gid, gname))
        btn_delete.clicked.connect(lambda _, gid=g_id, gname=g_name: self.delete_requested.emit(gid, gname))
        action_layout.addWidget(btn_edit)
        action_layout.addWidget(btn_contrib)
        action_layout.addWidget(btn_delete)
        self._table.setCellWidget(row, 7, action_widget)

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
