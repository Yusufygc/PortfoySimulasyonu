# src/ui/shared/card_factory.py

from src.qt_compat.qtwidgets import QFrame, QLabel, QVBoxLayout, QHBoxLayout
from typing import NamedTuple, Tuple

from src.ui.widgets.shared.controls.icon_label import IconLabel


class StatCardStyle(NamedTuple):
    is_colored: bool = False
    icon: str = ""
    is_hero: bool = False
    icon_name: "str | None" = None
    icon_color: str = "@COLOR_TEXT_SECONDARY"
    icon_size: int = 16


class CardFactory:
    """Ortak istatistik kartları ve metrik kutularını dondurur."""

    @staticmethod
    def create_stat_card(
        title: str,
        initial_value: str,
        style: StatCardStyle = StatCardStyle(),
    ) -> Tuple[QFrame, QLabel]:
        card = QFrame()
        card.setProperty("cssClass", "statCard")
        card.setProperty("isHero", style.is_hero)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(15, 15, 15, 15)

        header_layout = QHBoxLayout()
        if style.icon_name:
            lbl_icon = IconLabel(style.icon_name, color=style.icon_color, size=style.icon_size)
            lbl_icon.setProperty("cssClass", "statCardIcon")
            header_layout.addWidget(lbl_icon)

        lbl_title = QLabel(f"{style.icon} {title}" if style.icon and not style.icon_name else title)
        lbl_title.setProperty("cssClass", "statCardTitle")
        header_layout.addWidget(lbl_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        lbl_val = QLabel(initial_value)
        lbl_val.setObjectName("valueLabel")
        lbl_val.setProperty("cssClass", "statCardValue")
        lbl_val.setProperty("isHero", style.is_hero)
        lbl_val.setProperty("colored", style.is_colored)

        layout.addWidget(lbl_val)

        return card, lbl_val
