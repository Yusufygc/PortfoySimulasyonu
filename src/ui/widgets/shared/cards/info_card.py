# src/ui/widgets/shared/cards/info_card.py
"""
InfoCard — Evrensel Bilgi Kartı Widget'ı

Başlık + tek değer gösteren, state (positive/negative/neutral)
bazlı renk değişimi destekleyen yeniden kullanılabilir kart.

Kullanım:
    card = InfoCard("💵 Toplam Gelir", "₺ 0")
    card.set_value("₺ 12.500,00")
    card.set_value_state("positive")  # cssState ile QSS renk yönetimi
"""
from src.qt_compat.qtwidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from src.qt_compat.qtcore import Qt, QSize
from src.ui.core.icon_manager import IconManager
from src.ui.widgets.shared.feedback.skeleton_widget import SkeletonBlock


class InfoCard(QFrame):
    """
    Tek bir metrik değeri (başlık + değer) gösteren kart bileşeni.

    Desteklenen cssState değerleri: 'positive', 'negative', 'neutral'
    """

    def __init__(self, title: str = "", value: str = "—", icon_name: str = "", parent=None):
        super().__init__(parent)
        self._value_min_lines = 1
        self.setProperty("cssClass", "infoCard")
        self.setMinimumWidth(0)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_row.setSpacing(8)
        
        self._lbl_icon = QLabel()
        title_row.addWidget(self._lbl_icon)

        self._lbl_title = QLabel(title)
        self._lbl_title.setProperty("cssClass", "infoCardTitle")
        self._lbl_title.setWordWrap(True)
        title_row.addWidget(self._lbl_title)
        title_row.addStretch()

        self._lbl_value = QLabel(value)
        self._lbl_value.setProperty("cssClass", "infoCardValue")
        self._lbl_value.setWordWrap(True)

        layout.addLayout(title_row)
        layout.addWidget(self._lbl_value)
        
        self._skeleton_title = SkeletonBlock(width=90, height=12, parent=self)
        self._skeleton_value = SkeletonBlock(width=140, height=20, parent=self)
        self._skeleton_title.hide()
        self._skeleton_value.hide()

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
        self._lbl_value.setProperty("cssClass", "infoCardValue")
        self._lbl_value.style().unpolish(self._lbl_value)
        self._lbl_value.style().polish(self._lbl_value)
        self._refresh_value_min_height()

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
        self._refresh_value_min_height()

    def set_value_min_lines(self, min_lines: int) -> None:
        """
        Dar kartlarda sarilan deger metni icin minimum satir yuksekligi ayarlar.
        Renkler QSS cssState uzerinden kalir; bu metod yalnizca yerlesimi etkiler.
        """
        self._value_min_lines = max(1, min_lines)
        self._lbl_value.setWordWrap(True)
        self._lbl_value.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._lbl_value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self._refresh_value_min_height()

    def set_loading(self, loading: bool) -> None:
        """Yükleme durumunu açar/kapatır. True iken skeleton gösterilir."""
        self._lbl_title.setVisible(not loading)
        self._lbl_value.setVisible(not loading)
        self._lbl_icon.setVisible(not loading)
        if loading:
            self._skeleton_title.start()
            self._skeleton_value.start()
        else:
            self._skeleton_title.stop()
            self._skeleton_value.stop()

    def get_value_label(self) -> QLabel:
        """Ham QLabel referansını döner (geriye dönük uyumluluk için)."""
        return self._lbl_value

    def _refresh_value_min_height(self) -> None:
        if self._value_min_lines <= 1:
            return

        line_height = self._lbl_value.fontMetrics().lineSpacing()
        self._lbl_value.setMinimumHeight(line_height * self._value_min_lines)
        self.updateGeometry()
