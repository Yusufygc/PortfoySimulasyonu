# src/ui/pages/base_page.py

from __future__ import annotations

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import pyqtSignal, Qt


class BasePage(QWidget):
    """
    Tüm sayfalar için temel sınıf.
    Ortak özellikler ve signal'ler burada tanımlanır.
    """
    
    # Navigasyon signal'leri
    navigate_to = pyqtSignal(str)  # Sayfa adı ile navigasyon
    navigate_back = pyqtSignal()   # Geri dön
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.page_title = "Sayfa"
        self._setup_base_layout()
    
    def _setup_base_layout(self):
        """Temel layout'u oluşturur."""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(25, 25, 25, 25)
        self.main_layout.setSpacing(20)
    
    def get_title(self) -> str:
        """Sayfa başlığını döner."""
        return self.page_title
    
    def on_page_enter(self):
        """Sayfa aktif olduğunda çağrılır. Alt sınıflar override edebilir."""
        pass
    
    def on_page_leave(self):
        """Sayfadan çıkıldığında çağrılır. Alt sınıflar override edebilir."""
        pass
    
    def refresh_data(self):
        """Sayfa verilerini yeniler. Alt sınıflar override etmeli."""
        pass
