# src/application/events/event_bus.py

from PyQt5.QtCore import QObject, pyqtSignal
from typing import Dict
from decimal import Decimal

class GlobalEventBus(QObject):
    """
    Sistemin Publish/Subscribe (Pub/Sub) mimarisinin merkezi yönetimi.
    Worker (Arka plan) thread'lerinde gerçekleşen verileri, 
    Main(GUI) thread'i kitlemeden anında Reaktif bileşenlere dağıtır.
    """
    
    # 1) Fiyat Güncellemesi Bittiğinde Yayınlanır: dict[stock_id: int, new_price: Decimal]
    prices_updated = pyqtSignal(object)
    
    # 2) Portföy verisinde (Ekle/Sil, Nakit vb) temel değişiklik olduğunda yayınlanır.
    portfolio_changed = pyqtSignal()
    
    # İleride eklenebilecek hücre spesifik sinyaller:
    # stock_added = pyqtSignal(int)
    # stock_removed = pyqtSignal(int)
