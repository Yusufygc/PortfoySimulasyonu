# src/ui/pages/watchlist_page.py

from __future__ import annotations

from typing import Optional, Dict, Any

from PyQt5.QtWidgets import (
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
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
    QSplitter,
)
from PyQt5.QtCore import Qt

from .base_page import BasePage
from src.domain.models.watchlist import Watchlist


class WatchlistPage(BasePage):
    """
    Takip Listeleri sayfası.
    Watchlist CRUD ve hisse yönetimi.
    """

    def __init__(self, watchlist_service, parent=None):
        super().__init__(parent)
        self.page_title = "Takip Listeleri"
        self.watchlist_service = watchlist_service
        self.current_watchlist_id: Optional[int] = None
        
        self._init_ui()

    def _init_ui(self):
        # Başlık
        header_layout = QHBoxLayout()
        lbl_title = QLabel("📋 Takip Listeleri")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: bold; color: #f1f5f9;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        self.main_layout.addLayout(header_layout)

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

        lbl_lists = QLabel("Listelerim")
        lbl_lists.setStyleSheet("font-size: 14px; font-weight: bold; color: #94a3b8;")
        left_layout.addWidget(lbl_lists)

        self.list_widget = QListWidget()
        self.list_widget.setAlternatingRowColors(True)
        self.list_widget.itemClicked.connect(self._on_list_selected)
        left_layout.addWidget(self.list_widget)

        # Butonlar
        btn_layout = QHBoxLayout()
        
        self.btn_new = QPushButton("➕ Yeni")
        self.btn_new.setCursor(Qt.PointingHandCursor)
        self.btn_new.clicked.connect(self._on_new_list)
        
        self.btn_edit = QPushButton("✏️ Düzenle")
        self.btn_edit.setCursor(Qt.PointingHandCursor)
        self.btn_edit.clicked.connect(self._on_edit_list)
        self.btn_edit.setEnabled(False)
        
        self.btn_delete = QPushButton("🗑️ Sil")
        self.btn_delete.setCursor(Qt.PointingHandCursor)
        self.btn_delete.clicked.connect(self._on_delete_list)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setStyleSheet("color: #ef4444;")

        btn_layout.addWidget(self.btn_new)
        btn_layout.addWidget(self.btn_edit)
        btn_layout.addWidget(self.btn_delete)
        left_layout.addLayout(btn_layout)

        # Sağ Panel: İçerik
        right_panel = QFrame()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(15)

        self.lbl_list_name = QLabel("Bir liste seçin")
        self.lbl_list_name.setStyleSheet("font-size: 18px; font-weight: bold; color: #f1f5f9;")
        right_layout.addWidget(self.lbl_list_name)

        self.lbl_list_desc = QLabel("")
        self.lbl_list_desc.setStyleSheet("color: #94a3b8;")
        self.lbl_list_desc.setWordWrap(True)
        right_layout.addWidget(self.lbl_list_desc)

        # Hisse tablosu
        self.stock_table = QTableWidget()
        self.stock_table.setColumnCount(3)
        self.stock_table.setHorizontalHeaderLabels(["Hisse Adı", "Not", ""])
        self.stock_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.stock_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.stock_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.stock_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.stock_table.setAlternatingRowColors(True)
        self.stock_table.verticalHeader().setVisible(False)
        right_layout.addWidget(self.stock_table)

        # Hisse ekleme
        stock_btn_layout = QHBoxLayout()
        stock_btn_layout.addStretch()
        
        self.btn_add_stock = QPushButton("➕ Hisse Ekle")
        self.btn_add_stock.setCursor(Qt.PointingHandCursor)
        self.btn_add_stock.clicked.connect(self._on_add_stock)
        self.btn_add_stock.setEnabled(False)
        self.btn_add_stock.setObjectName("primaryButton")
        
        stock_btn_layout.addWidget(self.btn_add_stock)
        right_layout.addLayout(stock_btn_layout)

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
            item = QListWidgetItem(f"{wl.name} ({count})")
            item.setData(Qt.UserRole, wl)
            self.list_widget.addItem(item)

    def _on_list_selected(self, item: QListWidgetItem):
        watchlist: Watchlist = item.data(Qt.UserRole)
        self.current_watchlist_id = watchlist.id
        
        self.lbl_list_name.setText(watchlist.name)
        self.lbl_list_desc.setText(watchlist.description or "")
        
        self.btn_edit.setEnabled(True)
        self.btn_delete.setEnabled(True)
        self.btn_add_stock.setEnabled(True)

        self._load_stocks()

    def _load_stocks(self):
        self.stock_table.setRowCount(0)
        
        if self.current_watchlist_id is None:
            return

        stocks = self.watchlist_service.get_watchlist_stocks(self.current_watchlist_id)
        
        for i, stock_data in enumerate(stocks):
            self.stock_table.insertRow(i)
            
            # Ticker kolonu kalktı, veriyi Hisse Adı kolonuna gömüyoruz
            name_text = stock_data["name"] or stock_data["ticker"]
            name_item = QTableWidgetItem(name_text)
            name_item.setData(Qt.UserRole, stock_data) # Veriyi burada saklıyoruz
            self.stock_table.setItem(i, 0, name_item)
            
            notes = stock_data["item"].notes or ""
            notes_item = QTableWidgetItem(notes)
            self.stock_table.setItem(i, 1, notes_item)
            
            btn_remove = QPushButton("🗑️")
            btn_remove.setCursor(Qt.PointingHandCursor)
            btn_remove.setFixedWidth(40)
            btn_remove.clicked.connect(
                lambda checked, sid=stock_data["stock"].id: self._on_remove_stock(sid)
            )
            self.stock_table.setCellWidget(i, 2, btn_remove)

    def _on_new_list(self):
        name, ok = QInputDialog.getText(self, "Yeni Liste", "Liste adı:", QLineEdit.Normal, "")
        if not ok or not name.strip():
            return

        desc, ok2 = QInputDialog.getText(self, "Yeni Liste", "Açıklama (opsiyonel):", QLineEdit.Normal, "")

        try:
            self.watchlist_service.create_watchlist(name.strip(), desc.strip() if ok2 else None)
            self._load_watchlists()
            QMessageBox.information(self, "Başarılı", f"'{name}' listesi oluşturuldu.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Liste oluşturulamadı: {e}")

    def _on_edit_list(self):
        if self.current_watchlist_id is None:
            return

        current_item = self.list_widget.currentItem()
        if not current_item:
            return

        watchlist: Watchlist = current_item.data(Qt.UserRole)

        name, ok = QInputDialog.getText(self, "Liste Düzenle", "Liste adı:", QLineEdit.Normal, watchlist.name)
        if not ok or not name.strip():
            return

        desc, ok2 = QInputDialog.getText(self, "Liste Düzenle", "Açıklama:", QLineEdit.Normal, watchlist.description or "")

        try:
            self.watchlist_service.update_watchlist(
                self.current_watchlist_id, name.strip(), desc.strip() if ok2 else None
            )
            self._load_watchlists()
            self.lbl_list_name.setText(name.strip())
            QMessageBox.information(self, "Başarılı", "Liste güncellendi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Liste güncellenemedi: {e}")

    def _on_delete_list(self):
        if self.current_watchlist_id is None:
            return

        reply = QMessageBox.question(
            self, "Liste Sil", "Bu listeyi silmek istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.watchlist_service.delete_watchlist(self.current_watchlist_id)
            self.current_watchlist_id = None
            self._load_watchlists()
            self._clear_right_panel()
            QMessageBox.information(self, "Başarılı", "Liste silindi.")
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Liste silinemedi: {e}")

    def _clear_right_panel(self):
        self.lbl_list_name.setText("Bir liste seçin")
        self.lbl_list_desc.setText("")
        self.stock_table.setRowCount(0)
        self.btn_edit.setEnabled(False)
        self.btn_delete.setEnabled(False)
        self.btn_add_stock.setEnabled(False)

    def _on_add_stock(self):
        if self.current_watchlist_id is None:
            return

        ticker, ok = QInputDialog.getText(
            self, "Hisse Ekle", "Hisse ticker'ı (örn: ASELS):", QLineEdit.Normal, ""
        )
        if not ok or not ticker.strip():
            return

        notes, ok2 = QInputDialog.getText(self, "Hisse Ekle", "Not (opsiyonel):", QLineEdit.Normal, "")

        try:
            self.watchlist_service.add_stock_by_ticker(
                self.current_watchlist_id, ticker.strip(), notes.strip() if ok2 else None
            )
            self._load_stocks()
            self._load_watchlists()
            QMessageBox.information(self, "Başarılı", f"'{ticker.upper()}' listeye eklendi.")
        except ValueError as e:
            QMessageBox.warning(self, "Uyarı", str(e))
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hisse eklenemedi: {e}")

    def _on_remove_stock(self, stock_id: int):
        if self.current_watchlist_id is None:
            return

        reply = QMessageBox.question(
            self, "Hisse Çıkar", "Bu hisseyi listeden çıkarmak istediğinizden emin misiniz?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.watchlist_service.remove_stock_from_watchlist(self.current_watchlist_id, stock_id)
            self._load_stocks()
            self._load_watchlists()
        except Exception as e:
            QMessageBox.critical(self, "Hata", f"Hisse çıkarılamadı: {e}")
