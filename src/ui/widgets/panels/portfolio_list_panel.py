# src/ui/widgets/panels/portfolio_list_panel.py
"""
PortfolioListPanel — Sol Panel Widget'ı (Model Portföy Sayfası)

Portföy listesini, CRUD butonlarını içeren sol kenar bileşeni.
Seçim ve aksiyon sinyallerini üst bileşene iletir.

Kullanım:
    panel = PortfolioListPanel()
    panel.portfolio_selected.connect(self._on_selected)
    panel.new_requested.connect(self._on_new)
    panel.edit_requested.connect(self._on_edit)
    panel.delete_requested.connect(self._on_delete)
    panel.refresh(portfolios, trade_count_func)
"""
from PyQt5.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout,
    QListWidget, QListWidgetItem, QPushButton, QLabel
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtWidgets import QSizePolicy
from src.ui.widgets.animated_button import AnimatedButton
from src.ui.core.icon_manager import IconManager


class PortfolioListPanel(QFrame):
    """Model portföy listesini ve CRUD butonlarını içeren sol panel."""

    portfolio_selected = pyqtSignal(object)   # ModelPortfolio
    new_requested      = pyqtSignal()
    edit_requested     = pyqtSignal()
    delete_requested   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        # Sabit genişlik yerine min/max ile responsive
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
        lbl.setStyleSheet("font-size: 16px; color: #FFFFFF; font-weight: bold; border: none;") # Brighter and larger as requested
        lbl_row.addWidget(lbl)
        lbl_row.addStretch()
        layout.addLayout(lbl_row)

        self._list = QListWidget()
        self._list.setAlternatingRowColors(True)
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        # CRUD butonları
        btn_row = QHBoxLayout()

        self._btn_new = AnimatedButton(" Yeni")
        self._btn_new.setIconName("plus", color="@COLOR_TEXT_PRIMARY")
        self._btn_new.setProperty("cssClass", "secondaryButton")
        self._btn_new.clicked.connect(self.new_requested)

        self._btn_edit = AnimatedButton(" Düzenle")
        self._btn_edit.setIconName("pencil", color="@COLOR_TEXT_PRIMARY")
        self._btn_edit.setProperty("cssClass", "secondaryButton")
        self._btn_edit.setEnabled(False)
        self._btn_edit.clicked.connect(self.edit_requested)

        self._btn_delete = AnimatedButton(" Sil")
        self._btn_delete.setIconName("trash-2", color="@COLOR_DANGER")
        self._btn_delete.setEnabled(False)
        self._btn_delete.setProperty("cssClass", "dangerOutlineButton")
        self._btn_delete.clicked.connect(self.delete_requested)

        btn_row.addWidget(self._btn_new)
        btn_row.addWidget(self._btn_edit)
        btn_row.addWidget(self._btn_delete)
        layout.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def refresh(self, portfolios: list, trade_count_func=None) -> None:
        """
        Portföy listesini yeniler.

        Args:
            portfolios: ModelPortfolio listesi
            trade_count_func: portfolio_id -> int; opsiyonel
        """
        self._list.clear()
        for pf in portfolios:
            count = trade_count_func(pf.id) if trade_count_func else ""
            label = f"{pf.name} ({count} işlem)" if count != "" else pf.name
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, pf)
            self._list.addItem(item)

    def set_selection_enabled(self, enabled: bool) -> None:
        """Düzenle/Sil butonlarını etkinleştirir veya devre dışı bırakır."""
        self._btn_edit.setEnabled(enabled)
        self._btn_delete.setEnabled(enabled)

    def current_portfolio(self):
        """Seçili portföyü döner, yoksa None."""
        item = self._list.currentItem()
        return item.data(Qt.UserRole) if item else None

    # ------------------------------------------------------------------
    # İç Bağlantılar
    # ------------------------------------------------------------------

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        portfolio = item.data(Qt.UserRole)
        self.set_selection_enabled(True)
        self.portfolio_selected.emit(portfolio)
