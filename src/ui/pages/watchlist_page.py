# src/ui/pages/watchlist_page.py

from __future__ import annotations
from src.ui.shared.locale_tr import L10N

from typing import Optional

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFrame,
    QInputDialog,
    QStackedWidget,
    QWidget,
)
from PyQt5.QtCore import Qt, QSize
from src.ui.formatters import display_ticker
from src.ui.widgets.shared.controls.icon_label import IconLabel

from .base_page import BasePage
from src.domain.models.watchlist import Watchlist
from src.ui.widgets.shared import ActionListItem, AnimatedButton, Toast
from src.ui.widgets.watchlist.dialogs import AddStockToWatchlistDialog, EditStockInWatchlistDialog
from src.ui.widgets.watchlist.dialogs.watchlist_dialog import WatchlistDialog


class WatchlistPage(BasePage):
    """
    Takip Listeleri sayfası.
    Watchlist CRUD ve hisse yönetimi.
    """

    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = L10N.TAKIP_LISTELERI
        self.watchlist_service = container.watchlist_service
        self.current_watchlist_id: Optional[int] = None
        
        self._init_ui()

    def _init_ui(self):
        # Başlık
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        icon_lbl = IconLabel("clipboard-list", color="@COLOR_ACCENT", size=28)
        header_layout.addWidget(icon_lbl)
        
        lbl_title = QLabel(L10N.TAKIP_LISTELERI)
        lbl_title.setProperty("cssClass", "pageTitle")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)

        lbl_desc = QLabel(L10N.HISSE_SENETLERINI_LISTELER_HALINDE_ORGANIZE)
        lbl_desc.setWordWrap(True)
        lbl_desc.setProperty("cssClass", "pageDescription")
        self.main_layout.addWidget(lbl_desc)

        # Ana içerik - Yatay bölünmüş
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # Sol Panel: Liste
        left_panel = QFrame()
        left_panel.setObjectName("leftPanel")
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(15, 15, 15, 15)
        left_layout.setSpacing(10)

        lbl_row = QHBoxLayout()
        lbl_row.setSpacing(8)
        img = IconLabel("bookmark", color="@COLOR_TEXT_BRIGHT", size=18)
        lbl_row.addWidget(img)
        
        lbl_lists = QLabel(L10N.LISTELERIM)
        lbl_lists.setProperty("cssClass", "tableTitle")
        lbl_row.addWidget(lbl_lists)
        lbl_row.addStretch()

        self.btn_new = AnimatedButton(L10N.YENI)
        self.btn_new.setIconName("plus", color="@COLOR_TEXT_WHITE")
        self.btn_new.setProperty("cssClass", "watchlistNewButton")
        self.btn_new.clicked.connect(self._on_new_list)
        lbl_row.addWidget(self.btn_new)

        self._left_header_layout = lbl_row
        left_layout.addLayout(lbl_row)

        self.list_widget = QListWidget()
        self.list_widget.setProperty("cssClass", "watchlistList")
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.setDragDropMode(QListWidget.InternalMove)
        self.list_widget.model().rowsMoved.connect(self._on_list_reordered)
        self.list_widget.itemClicked.connect(self._on_list_selected)
        left_layout.addWidget(self.list_widget)

        self.btn_edit = AnimatedButton(L10N.DUZENLE)
        self.btn_edit.setIconName("pencil", color="@COLOR_TEXT_PRIMARY")
        self.btn_edit.setProperty("cssClass", "secondaryButton")
        self.btn_edit.setEnabled(False)

        self.btn_delete = AnimatedButton(L10N.SIL)
        self.btn_delete.setIconName("trash-2", color="@COLOR_DANGER")
        self.btn_delete.setEnabled(False)
        self.btn_delete.setProperty("cssClass", "dangerOutlineButton")
        self.btn_edit.hide()
        self.btn_delete.hide()

        # Sağ Panel: İçerik
        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(15)

        detail_header_layout = QHBoxLayout()
        detail_header_layout.setSpacing(12)

        self.lbl_list_name = QLabel(L10N.BIR_LISTE_SECIN)
        self.lbl_list_name.setProperty("cssClass", "panelTitleLarge")
        detail_header_layout.addWidget(self.lbl_list_name, 1)

        self.btn_add_stock = AnimatedButton(L10N.HISSE_EKLE)
        self.btn_add_stock.setIconName("plus", color="@COLOR_TEXT_WHITE")
        self.btn_add_stock.clicked.connect(self._on_add_stock)
        self.btn_add_stock.setEnabled(False)
        self.btn_add_stock.setProperty("cssClass", "primaryButton")
        detail_header_layout.addWidget(self.btn_add_stock, 0, Qt.AlignRight | Qt.AlignVCenter)

        self._detail_header_layout = detail_header_layout
        right_layout.addLayout(detail_header_layout)

        self.lbl_list_desc = QLabel("")
        self.lbl_list_desc.setProperty("cssClass", "panelDescription")
        self.lbl_list_desc.setWordWrap(True)
        right_layout.addWidget(self.lbl_list_desc)

        # Hisse tablosu
        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(3)
        self.stock_table.setHorizontalHeaderLabels([L10N.HISSE_ADI, "Not", ""])
        self.stock_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.stock_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.stock_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Fixed)
        self.stock_table.setColumnWidth(2, 100)
        self.stock_table.setSelectionMode(QTableWidget.NoSelection)
        self.stock_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stock_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.stock_table.setAlternatingRowColors(True)
        self.stock_table.setShowGrid(False)
        self.stock_table.setFocusPolicy(Qt.NoFocus)
        self.stock_table.setWordWrap(True)
        self.stock_table.setProperty("cssClass", "watchlistTable")
        self.stock_table.horizontalHeader().setHighlightSections(False)
        self.stock_table.verticalHeader().setDefaultSectionSize(42)
        self.stock_table.verticalHeader().setVisible(False)

        self.empty_state = self._create_empty_state()
        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.stock_table)
        self.content_stack.addWidget(self.empty_state)
        right_layout.addWidget(self.content_stack, 1)

        content_layout.addWidget(left_panel)
        content_layout.addWidget(right_panel, 1)
        self.main_layout.addLayout(content_layout)

    def on_page_enter(self):
        self.refresh_data()

    def refresh_data(self):
        self._load_watchlists()

    def _load_watchlists(self):
        self.list_widget.clear()
        watchlists = self.watchlist_service.get_all_watchlists()

        for wl in watchlists:
            count = self.watchlist_service.get_watchlist_item_count(wl.id)
            label = wl.name
            secondary = f"({count} hisse)"
            item = QListWidgetItem()
            item.setData(Qt.UserRole, wl)
            item.setSizeHint(QSize(0, 44))
            self.list_widget.addItem(item)
            row = ActionListItem(label, secondary_text=secondary, draggable=True)
            row.selected.connect(lambda wl=wl, item=item: self._select_watchlist_item(item, wl))
            row.edit_requested.connect(lambda wl=wl, item=item: self._run_watchlist_action(item, wl, self._on_edit_list))
            row.delete_requested.connect(lambda wl=wl, item=item: self._run_watchlist_action(item, wl, self._on_delete_list))
            self.list_widget.setItemWidget(item, row)

    def _on_list_selected(self, item: QListWidgetItem):
        watchlist: Watchlist = item.data(Qt.UserRole)
        self._select_watchlist_item(item, watchlist)

    def _on_list_reordered(self, parent, start, end, destination, row):
        ordered_ids = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            wl: Watchlist = item.data(Qt.UserRole)
            ordered_ids.append(wl.id)
            
        try:
            self.watchlist_service.reorder_watchlists(ordered_ids)
        except Exception as e:
            Toast.error(self, L10N.SIRALAMA_GUNCELLENEMEDI_TMPL.format(exc=e))

    def _select_watchlist_item(self, item: QListWidgetItem, watchlist: Watchlist) -> None:
        self.list_widget.setCurrentItem(item)
        self.current_watchlist_id = watchlist.id
        
        self.lbl_list_name.setText(watchlist.name)
        self.lbl_list_desc.setText(watchlist.description or "")
        
        self.btn_edit.setEnabled(True)
        self.btn_delete.setEnabled(True)
        self.btn_add_stock.setEnabled(True)
        self.btn_empty_add_stock.setEnabled(True)

        self._load_stocks()

    def _run_watchlist_action(self, item: QListWidgetItem, watchlist: Watchlist, action) -> None:
        self._select_watchlist_item(item, watchlist)
        action()

    def _load_stocks(self):
        self.stock_table.setRowCount(0)
        
        if self.current_watchlist_id is None:
            self.content_stack.setCurrentWidget(self.stock_table)
            return

        stocks = self.watchlist_service.get_watchlist_stocks(self.current_watchlist_id)
        self.content_stack.setCurrentWidget(self.empty_state if not stocks else self.stock_table)
        
        for i, stock_data in enumerate(stocks):
            self.stock_table.insertRow(i)
            
            # Ticker kolonu kalktı, veriyi Hisse Adı kolonuna gömüyoruz
            name_text = display_ticker(stock_data["name"] or stock_data["ticker"])
            name_item = self._readonly_table_item(name_text, align_center=True)
            name_item.setData(Qt.UserRole, stock_data) # Veriyi burada saklıyoruz
            self.stock_table.setItem(i, 0, name_item)
            
            notes = stock_data["item"].notes or ""
            notes_item = self._readonly_table_item(notes)
            self.stock_table.setItem(i, 1, notes_item)
            
            # Eylem butonları için layout
            actions_widget = QWidget()
            actions_widget.setProperty("cssClass", "tableActionContainer")
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 0, 4, 0)
            actions_layout.setSpacing(6)
            
            btn_edit = AnimatedButton("")
            btn_edit.setIconName("pencil", color="@COLOR_TEXT_PRIMARY")
            btn_edit.setFixedWidth(32)
            btn_edit.setProperty("cssClass", "textButton")
            btn_edit.clicked.connect(
                lambda checked, sd=stock_data: self._on_edit_stock(sd)
            )
            
            btn_remove = AnimatedButton("")
            btn_remove.setIconName("trash-2", color="@COLOR_DANGER")
            btn_remove.setFixedWidth(32)
            btn_remove.setProperty("cssClass", "dangerTextButton")
            btn_remove.clicked.connect(
                lambda checked, sid=stock_data["stock"].id: self._on_remove_stock(sid)
            )
            
            actions_layout.addWidget(btn_edit)
            actions_layout.addWidget(btn_remove)
            actions_layout.setAlignment(Qt.AlignCenter)
            self.stock_table.setCellWidget(i, 2, actions_widget)

        self.stock_table.resizeRowsToContents()

    def _create_empty_state(self) -> QWidget:
        empty = QFrame()
        empty.setProperty("cssClass", "watchlistEmptyState")
        layout = QVBoxLayout(empty)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(14)
        layout.addStretch()

        icon = IconLabel("plus", color="@COLOR_TEXT_MUTED", size=28)
        layout.addWidget(icon, 0, Qt.AlignCenter)

        label = QLabel(L10N.BU_LISTEDE_HENUZ_HISSE_YOK)
        label.setProperty("cssClass", "watchlistEmptyTitle")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        btn_empty_add = AnimatedButton(L10N.HISSE_EKLE)
        btn_empty_add.setIconName("plus", color="@COLOR_TEXT_WHITE")
        btn_empty_add.setProperty("cssClass", "primaryButton")
        btn_empty_add.clicked.connect(self._on_add_stock)
        self.btn_empty_add_stock = btn_empty_add
        layout.addWidget(btn_empty_add, 0, Qt.AlignCenter)

        layout.addStretch()
        return empty

    @staticmethod
    def _readonly_table_item(text: str, align_center: bool = False) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setFlags(Qt.ItemIsEnabled)
        if align_center:
            item.setTextAlignment(Qt.AlignCenter)
        return item

    def _on_new_list(self):
        result = WatchlistDialog.get_watchlist_data(self, L10N.YENI_LISTE)
        if not result:
            return
            
        name, desc = result

        try:
            self.watchlist_service.create_watchlist(name, desc if desc else None)
            self._load_watchlists()
            Toast.success(self, L10N.LISTE_OLUSTURULDU_TMPL.format(name=name))
        except Exception as e:
            Toast.error(self, L10N.LISTE_OLUSTURULAMADI_TMPL.format(exc=e))

    def _on_edit_list(self):
        if self.current_watchlist_id is None:
            return

        current_item = self.list_widget.currentItem()
        if not current_item:
            return

        watchlist: Watchlist = current_item.data(Qt.UserRole)

        result = WatchlistDialog.get_watchlist_data(self, L10N.LISTE_DUZENLE, watchlist.name, watchlist.description or "")
        if not result:
            return
            
        name, desc = result

        try:
            self.watchlist_service.update_watchlist(
                self.current_watchlist_id, name, desc if desc else None
            )
            self._load_watchlists()
            self.lbl_list_name.setText(name.strip())
            Toast.success(self, L10N.LISTE_GUNCELLENDI)
        except Exception as e:
            Toast.error(self, L10N.LISTE_GUNCELLENEMEDI_TMPL.format(exc=e))

    def _on_delete_list(self):
        if self.current_watchlist_id is None:
            return

        reply = QMessageBox.question(
            self, L10N.LISTE_SIL, L10N.BU_LISTEYI_SILMEK_ISTEDIGINIZDEN_EMIN,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.watchlist_service.delete_watchlist(self.current_watchlist_id)
            self.current_watchlist_id = None
            self._load_watchlists()
            self._clear_right_panel()
            Toast.success(self, L10N.LISTE_SILINDI)
        except Exception as e:
            Toast.error(self, L10N.LISTE_SILINEMEDI_TMPL.format(exc=e))

    def _clear_right_panel(self):
        self.lbl_list_name.setText(L10N.BIR_LISTE_SECIN)
        self.lbl_list_desc.setText("")
        self.stock_table.setRowCount(0)
        self.content_stack.setCurrentWidget(self.stock_table)
        self.btn_edit.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_add_stock.setEnabled(False)
        self.btn_empty_add_stock.setEnabled(False)

    def _on_add_stock(self):
        if self.current_watchlist_id is None:
            return

        result = AddStockToWatchlistDialog.get_stock_input(self)
        if result is None:
            return
        ticker, notes = result

        try:
            self.watchlist_service.add_stock_by_ticker(
                self.current_watchlist_id, ticker, notes
            )
            self._load_stocks()
            self._load_watchlists()
            Toast.success(self, L10N.HISSE_EKLENDI_TMPL.format(ticker=display_ticker(ticker.upper())))
        except ValueError as e:
            Toast.warning(self, str(e))
        except Exception as e:
            Toast.error(self, L10N.HISSE_EKLENEMEDI_TMPL.format(exc=e))

    def _on_edit_stock(self, stock_data: dict):
        if self.current_watchlist_id is None:
            return

        ticker = stock_data["ticker"]
        current_notes = stock_data["item"].notes or ""

        ok, new_notes = EditStockInWatchlistDialog.get_notes_input(
            ticker=display_ticker(ticker),
            current_notes=current_notes,
            parent=self
        )
        if not ok:
            return

        try:
            self.watchlist_service.update_watchlist_item_notes(
                self.current_watchlist_id,
                stock_data["stock"].id,
                new_notes
            )
            self._load_stocks()
            Toast.success(self, L10N.HISSE_NOTU_GUNCELLENDI)
        except Exception as e:
            Toast.error(self, L10N.HISSE_GUNCELLENEMEDI_TMPL.format(exc=e))

    def _on_remove_stock(self, stock_id: int):
        if self.current_watchlist_id is None:
            return

        reply = QMessageBox.question(
            self, L10N.HISSE_CIKAR, L10N.BU_HISSEYI_LISTEDEN_CIKARMAK_ISTEDIGINIZDEN,
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.watchlist_service.remove_stock_from_watchlist(self.current_watchlist_id, stock_id)
            self._load_stocks()
            self._load_watchlists()
        except Exception as e:
            QMessageBox.critical(self, L10N.ERROR, L10N.HISSE_CIKARILAMADI_TMPL.format(exc=e))
