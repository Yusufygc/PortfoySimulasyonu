# src/ui/widgets/cards/info_card.py
"""
InfoCard — Evrensel Bilgi Kartı Widget'ı

Başlık + tek değer gösteren, state (positive/negative/neutral)
bazlı renk değişimi destekleyen yeniden kullanılabilir kart.

Kullanım:
    card = InfoCard("💵 Toplam Gelir", "₺ 0")
    card.set_value("₺ 12.500,00")
    card.set_value_state("positive")  # cssState ile QSS renk yönetimi
"""
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt, QSize
from src.ui.core.icon_manager import IconManager


class InfoCard(QFrame):
    """
    Tek bir metrik değeri (başlık + değer) gösteren kart bileşeni.

    Desteklenen cssState değerleri: 'positive', 'negative', 'neutral'
    """

    def __init__(self, title: str = "", value: str = "—", icon_name: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "infoCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(5)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        
        self._lbl_icon = QLabel()
        title_row.addWidget(self._lbl_icon)

        self._lbl_title = QLabel(title)
        self._lbl_title.setProperty("cssClass", "infoCardTitle")
        title_row.addWidget(self._lbl_title)
        title_row.addStretch()

        self._lbl_value = QLabel(value)
        self._lbl_value.setProperty("cssClass", "infoCardValue")

        layout.addLayout(title_row)
        layout.addWidget(self._lbl_value)
        
        if icon_name:
            self.set_icon(icon_name)
        else:
            self._lbl_icon.hide()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_icon(self, icon_name: str, color: str = "@COLOR_TEXT_SECONDARY") -> None:
        """Kart ikonunu günceller."""
        if not icon_name:
            self._lbl_icon.hide()
            return
        pix = IconManager.get_icon(icon_name, color=color, size=QSize(18, 18)).pixmap(18, 18)
        self._lbl_icon.setPixmap(pix)
        self._lbl_icon.show()

    def set_title(self, text: str) -> None:
        """Kart başlığını günceller."""
        self._lbl_title.setText(text)

    def set_value(self, text: str) -> None:
        """Kart değerini günceller."""
        self._lbl_value.setText(text)

    def set_value_state(self, state: str) -> None:
        """
        Değer etiketinin cssState property'sini günceller.
        QSS'de [cssState="positive"] / [cssState="negative"] seçicileri
        renk değişimini yönetir — inline setStyleSheet gerekmez.

        Args:
            state: 'positive' | 'negative' | 'neutral'
        """
        self._lbl_value.setProperty("cssState", state)
        self._lbl_value.style().unpolish(self._lbl_value)
        self._lbl_value.style().polish(self._lbl_value)

    def get_value_label(self) -> QLabel:
        """Ham QLabel referansını döner (geriye dönük uyumluluk için)."""
        return self._lbl_value
