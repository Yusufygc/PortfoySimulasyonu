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
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt


class InfoCard(QFrame):
    """
    Tek bir metrik değeri (başlık + değer) gösteren kart bileşeni.

    Desteklenen cssState değerleri: 'positive', 'negative', 'neutral'
    """

    def __init__(self, title: str = "", value: str = "—", parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "infoCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(5)

        self._lbl_title = QLabel(title)
        self._lbl_title.setProperty("cssClass", "infoCardTitle")

        self._lbl_value = QLabel(value)
        self._lbl_value.setProperty("cssClass", "infoCardValue")

        layout.addWidget(self._lbl_title)
        layout.addWidget(self._lbl_value)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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
