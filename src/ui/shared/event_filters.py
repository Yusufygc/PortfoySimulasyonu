# src/ui/shared/event_filters.py
from PyQt5.QtCore import QObject, QEvent
from PyQt5.QtWidgets import QComboBox, QDateTimeEdit, QTabBar, QTabWidget

class GlobalWheelEventFilter(QObject):
    """
    Uygulama genelinde QComboBox, QDateTimeEdit ve QTabBar/QTabWidget bileşenlerinde
    mouse tekerleği (scroll) ile değer veya sekme değiştirilmesini engelleyen olay filtresi.
    """
    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.Wheel:
            if isinstance(obj, (QComboBox, QDateTimeEdit, QTabBar, QTabWidget)):
                # Olayı kabul edip yutuyoruz, böylece bileşenin kendi wheelEvent metodu çalışmıyor.
                event.accept()
                return True
        return super().eventFilter(obj, event)
