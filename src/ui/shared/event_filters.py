# src/ui/shared/event_filters.py
from src.qt_compat.qtcore import QObject, QEvent
from src.qt_compat.qtwidgets import QComboBox, QDateTimeEdit, QTabBar, QTabWidget

class GlobalWheelEventFilter(QObject):
    """
    Uygulama genelinde QComboBox, QDateTimeEdit ve QTabBar/QTabWidget bileşenlerinde
    mouse tekerleği (scroll) ile değer veya sekme değiştirilmesini engelleyen olay filtresi.
    """
    def eventFilter(self, obj, event) -> bool:
        try:
            if event.type() == QEvent.Wheel:
                if isinstance(obj, (QComboBox, QDateTimeEdit, QTabBar)):
                    # Olayı kabul edip yutuyoruz, böylece bileşenin kendi wheelEvent metodu çalışmıyor.
                    event.accept()
                    return True
        except RuntimeError:
            return False
        return False
