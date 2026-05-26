# src/ui/shared/card_factory.py

from PyQt5.QtWidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout
from typing import Tuple

from src.ui.widgets.shared.controls.icon_label import IconLabel

class CardFactory:
    """Ortak istatistik kartları ve metrik kutularını dondurur."""
    
    @staticmethod
    def create_stat_card(
        title: str,
        initial_value: str,
        is_colored: bool = False,
        icon: str = "",
        is_hero: bool = False,
        icon_name: str | None = None,
        icon_color: str = "@COLOR_TEXT_SECONDARY",
        icon_size: int = 16,
    ) -> Tuple[QFrame, QLabel]:
        """
        Görsel bir metrik kartı oluşturur. (örn: Toplam Kar, Sermaye, vb.)
        Güncellenebilmesi için hem çerçeveyi (QFrame) hem de değer etiketini (QLabel) Tuple olarak döner.
        """
        card = QFrame()
        card.setProperty("cssClass", "statCard")
        card.setProperty("isHero", is_hero)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)
        
        header_layout = QHBoxLayout()
        if icon_name:
            lbl_icon = IconLabel(icon_name, color=icon_color, size=icon_size)
            lbl_icon.setProperty("cssClass", "statCardIcon")
            header_layout.addWidget(lbl_icon)

        lbl_title = QLabel(f"{icon} {title}" if icon and not icon_name else title)
        lbl_title.setProperty("cssClass", "statCardTitle")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        lbl_val = QLabel(initial_value)
        lbl_val.setObjectName("valueLabel")
        lbl_val.setProperty("cssClass", "statCardValue")
        lbl_val.setProperty("isHero", is_hero)
        lbl_val.setProperty("colored", is_colored)
            
        layout.addWidget(lbl_val)
        
        return card, lbl_val
