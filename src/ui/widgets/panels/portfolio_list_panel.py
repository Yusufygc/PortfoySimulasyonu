from __future__ import annotations

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtWidgets import QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QSizePolicy, QVBoxLayout

from src.ui.core.icon_manager import IconManager
from src.ui.widgets.action_list_item import ActionListItem
from src.ui.widgets.animated_button import AnimatedButton


class PortfolioListPanel(QFrame):
    """Left panel for model portfolios."""

    portfolio_selected = pyqtSignal(object)
    new_requested = pyqtSignal()
    edit_requested = pyqtSignal()
    delete_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(220)
        self.setMaximumWidth(340)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(8)
        img = QLabel()
        img.setPixmap(IconManager.get_icon("layers", color="@COLOR_TEXT_BRIGHT", size=QSize(18, 18)).pixmap(18, 18))
        lbl_row.addWidget(img)

        lbl = QLabel("Portföylerim")
        lbl.setStyleSheet("font-size: 16px; color: #FFFFFF; font-weight: bold; border: none;")
        lbl_row.addWidget(lbl)
        lbl_row.addStretch()
        layout.addLayout(lbl_row)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        self._btn_new = AnimatedButton(" Yeni")
        self._btn_new.setIconName("plus", color="@COLOR_TEXT_PRIMARY")
        self._btn_new.setProperty("cssClass", "secondaryButton")
        self._btn_new.clicked.connect(self.new_requested)
        btn_row.addWidget(self._btn_new)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def refresh(self, portfolios: list, trade_count_func=None) -> None:
        self._list.clear()
        for portfolio in portfolios:
            count = trade_count_func(portfolio.id) if trade_count_func else ""
            label = f"{portfolio.name} ({count} işlem)" if count != "" else portfolio.name
            item = QListWidgetItem()
            item.setData(Qt.UserRole, portfolio)
            item.setSizeHint(QSize(0, 36))
            self._list.addItem(item)

            row = ActionListItem(label)
            row.selected.connect(lambda portfolio=portfolio, item=item: self._select_item(item, portfolio))
            row.edit_requested.connect(
                lambda portfolio=portfolio, item=item: self._emit_item_action(item, portfolio, self.edit_requested)
            )
            row.delete_requested.connect(
                lambda portfolio=portfolio, item=item: self._emit_item_action(item, portfolio, self.delete_requested)
            )
            self._list.setItemWidget(item, row)

    def set_selection_enabled(self, enabled: bool) -> None:
        return None

    def current_portfolio(self):
        item = self._list.currentItem()
        return item.data(Qt.UserRole) if item else None

    def select_portfolio_by_id(self, portfolio_id: int):
        for row_index in range(self._list.count()):
            item = self._list.item(row_index)
            portfolio = item.data(Qt.UserRole)
            if portfolio and portfolio.id == portfolio_id:
                self._list.setCurrentItem(item)
                return portfolio
        return None

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        portfolio = item.data(Qt.UserRole)
        self._select_item(item, portfolio)

    def _select_item(self, item: QListWidgetItem, portfolio) -> None:
        self._list.setCurrentItem(item)
        self.portfolio_selected.emit(portfolio)

    def _emit_item_action(self, item: QListWidgetItem, portfolio, signal) -> None:
        self._list.setCurrentItem(item)
        self.portfolio_selected.emit(portfolio)
        signal.emit()
