from PyQt5.QtWidgets import QStyledItemDelegate
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

class PortfolioRowDelegate(QStyledItemDelegate):
    """
    Tablo satırlarının sol kenarına kar/zarar durumuna göre 
    3px renkli border (indicator) çizen delegate.
    """
    def paint(self, painter, option, index):
        super().paint(painter, option, index)
        
        # Sadece ilk kolonun (0) sol kenarına çiz
        if index.column() == 0:
            model = index.model()
            row = index.row()
            
            # Eğer Proxy model kullanılıyorsa, sourceRow/sourceModel alalım (ileride eklenebilir ihtimaline karşı)
            if hasattr(model, 'mapToSource'):
                source_index = model.mapToSource(index)
                model = model.sourceModel()
                row = source_index.row()
                
            if hasattr(model, 'get_position') and hasattr(model, '_price_map'):
                try:
                    position = model.get_position(row)
                    current_price = model._price_map.get(position.stock_id)
                    
                    # Varsayılan: Nötr gri
                    color = QColor("#555555")
                    
                    if current_price is not None:
                        pl = position.unrealized_pl(current_price)
                        if pl > 0:
                            color = QColor("#00C853")
                        elif pl < 0:
                            color = QColor("#FF1744")
                    
                    painter.save()
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(color)
                    painter.drawRect(option.rect.x(), option.rect.y(), 3, option.rect.height())
                    painter.restore()
                except Exception:
                    pass
