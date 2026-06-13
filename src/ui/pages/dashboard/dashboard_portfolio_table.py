from decimal import Decimal

from src.qt_compat.qtcore import QModelIndex, QPoint, Qt, Signal
from src.qt_compat.qtgui import QAction, QColor
from src.qt_compat.qtwidgets import (
    QHeaderView,
    QMenu,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.ui.shared.locale_tr import L10N
from src.ui.widgets.dashboard import PortfolioRowDelegate
from src.ui.widgets.shared.wrapped_header_view import WrappedHeaderView


class DashboardPortfolioTable(QWidget):
    """Portfolio table plus the summary row below it."""

    MIN_SECTION_WIDTH = 95

    row_double_clicked = Signal(QModelIndex)
    # row, action_type ("BEDELLI" | "BEDELSIZ")
    corporate_action_requested = Signal(int, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.model = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.setSelectionBehavior(QTableView.SelectRows)
        self.table_view.setSelectionMode(QTableView.NoSelection)
        self.table_view.setFocusPolicy(Qt.NoFocus)
        self.table_view.setSortingEnabled(True)
        self.table_view.verticalHeader().setVisible(False)
        self.table_view.verticalHeader().setDefaultSectionSize(44)
        self.table_view.setHorizontalHeader(WrappedHeaderView(Qt.Horizontal, self.table_view))
        self.table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table_view.setShowGrid(False)
        self.table_view.doubleClicked.connect(self.row_double_clicked.emit)
        self.table_view.viewport().setCursor(Qt.PointingHandCursor)

        self.table_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self._on_context_menu_requested)

        self.row_delegate = PortfolioRowDelegate(self.table_view)
        self.table_view.setItemDelegate(self.row_delegate)

        layout.addWidget(self.table_view)

        self.table_summary = QTableWidget(1, 8)
        self.table_summary.horizontalHeader().setVisible(False)
        self.table_summary.verticalHeader().setVisible(False)
        self.table_summary.setFixedHeight(40)
        self.table_summary.setSelectionMode(QTableView.NoSelection)
        self.table_summary.setFocusPolicy(Qt.NoFocus)
        self.table_summary.setEditTriggers(QTableView.NoEditTriggers)
        self.table_summary.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_summary.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.table_summary.setShowGrid(False)
        self.table_summary.setProperty("cssClass", "tableSummary")
        layout.addWidget(self.table_summary)

        self._configure_header_behavior()
        self.table_view.horizontalScrollBar().valueChanged.connect(
            self.table_summary.horizontalScrollBar().setValue
        )

    def _configure_header_behavior(self):
        header = self.table_view.horizontalHeader()
        header.setMinimumSectionSize(self.MIN_SECTION_WIDTH)
        header.setStretchLastSection(False)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.sectionResized.connect(self._on_section_resized)

        summary_header = self.table_summary.horizontalHeader()
        summary_header.setMinimumSectionSize(self.MIN_SECTION_WIDTH)
        summary_header.setStretchLastSection(False)

    def _apply_column_layout(self):
        if self.model is None:
            return

        header = self.table_view.horizontalHeader()
        summary_header = self.table_summary.horizontalHeader()
        for column in range(self.model.columnCount()):
            header.setSectionResizeMode(column, QHeaderView.Stretch)
            summary_header.setSectionResizeMode(column, QHeaderView.Fixed)

        header.resizeSections()
        header.updateGeometry()
        self._sync_summary_column_widths()

    def _sync_summary_column_widths(self):
        header = self.table_view.horizontalHeader()
        for column in range(self.table_summary.columnCount()):
            self.table_summary.setColumnWidth(column, header.sectionSize(column))

    def _on_section_resized(self, logical_index: int, _old_size: int, new_size: int):
        if 0 <= logical_index < self.table_summary.columnCount():
            self.table_summary.setColumnWidth(logical_index, new_size)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._sync_summary_column_widths()

    def _on_context_menu_requested(self, pos: QPoint):
        index = self.table_view.indexAt(pos)
        if not index.isValid():
            return

        row = index.row()
        menu = QMenu(self.table_view)
        menu.setProperty("cssClass", "contextMenu")

        act_bedelsiz = QAction(L10N.BEDELSIZ_SERMAYE_ARTIRIMI, self)
        act_bedelli = QAction(L10N.BEDELLI_SERMAYE_ARTIRIMI_RUCHAN_HAKKI, self)

        act_bedelsiz.triggered.connect(lambda: self.corporate_action_requested.emit(row, "BEDELSIZ"))
        act_bedelli.triggered.connect(lambda: self.corporate_action_requested.emit(row, "BEDELLI"))

        menu.addAction(act_bedelsiz)
        menu.addAction(act_bedelli)
        menu.exec(self.table_view.viewport().mapToGlobal(pos))

    def set_model(self, model):
        self.model = model
        self.table_view.setModel(self.model)
        self._apply_column_layout()

    def update_summary_row(self, total_value: Decimal, profit_loss: Decimal):
        """Refresh the total summary row shown under the main table."""
        for col in range(8):
            item = QTableWidgetItem("")
            item.setFlags(Qt.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignCenter)
            self.table_summary.setItem(0, col, item)

        item_title = QTableWidgetItem(L10N.TOPLAM_SATIRI)
        item_title.setFlags(Qt.ItemIsEnabled)
        item_title.setTextAlignment(Qt.AlignCenter)
        self.table_summary.setItem(0, 0, item_title)

        item_mv = QTableWidgetItem(f"{total_value:,.2f}")
        item_mv.setFlags(Qt.ItemIsEnabled)
        item_mv.setTextAlignment(Qt.AlignCenter)
        self.table_summary.setItem(0, 5, item_mv)

        item_pl = QTableWidgetItem(f"{profit_loss:+,.2f}")
        item_pl.setFlags(Qt.ItemIsEnabled)
        item_pl.setTextAlignment(Qt.AlignCenter)

        if profit_loss > 0:
            item_pl.setForeground(QColor("#22c55e"))
        elif profit_loss < 0:
            item_pl.setForeground(QColor("#ef4444"))
        else:
            item_pl.setForeground(QColor("#f1f5f9"))

        self.table_summary.setItem(0, 7, item_pl)
