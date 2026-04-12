# src/ui/shared/card_factory.py

from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout
from typing import Tuple

class CardFactory:
    """Ortak istatistik kartları ve metrik kutularını dondurur."""
    
    @staticmethod
    def create_stat_card(title: str, initial_value: str, is_colored: bool = False, icon: str = "", is_hero: bool = False) -> Tuple[QFrame, QLabel]:
        """
        Görsel bir metrik kartı oluşturur. (örn: Toplam Kar, Sermaye, vb.)
        Güncellenebilmesi için hem çerçeveyi (QFrame) hem de değer etiketini (QLabel) Tuple olarak döner.
        """
        card = QFrame()
        bg_color = "#1e293b" if not is_hero else "#0f172a"
        border = "1px solid #334155" if not is_hero else "1px solid #3b82f6"
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color}; 
                border-radius: 12px;
                border: {border};
            }}
            QLabel {{ border: none; }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        header_layout = QHBoxLayout()
        lbl_title = QLabel(f"{icon} {title}")
        lbl_title.setStyleSheet("color: #94a3b8; font-size: 11px; font-weight: bold; text-transform: uppercase;")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        lbl_val = QLabel(initial_value)
        val_size = "20px" if not is_hero else "28px"
        lbl_val.setObjectName("valueLabel")
        if is_colored:
            lbl_val.setStyleSheet(f"color: #f1f5f9; font-size: {val_size}; font-weight: bold;")
        else:
            val_color = "#f1f5f9" if not is_hero else "#3b82f6"
            lbl_val.setStyleSheet(f"color: {val_color}; font-size: {val_size}; font-weight: bold;")
            
        layout.addWidget(lbl_val)
        
        return card, lbl_val
