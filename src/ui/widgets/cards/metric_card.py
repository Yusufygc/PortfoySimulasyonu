# src/ui/widgets/cards/metric_card.py
"""
MetricCard — Mevcut vs Optimal Karşılaştırma Kartı

Optimizasyon sayfasında kullanılan, üç değer (mevcut, optimal, delta)
gösteren ve delta yönüne göre renk değiştiren kart bileşeni.

Kullanım:
    card = MetricCard("⭐ Sharpe Oranı")
    card.update(current="1.23", optimal="1.87", delta=0.64, positive_is_good=True)
    card.reset()
"""
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt


class MetricCard(QFrame):
    """
    Mevcut ve optimal değerleri yan yana gösteren metrik karşılaştırma kartı.
    Delta değeri QSS cssState ile renklenir (inline setStyleSheet kullanılmaz).
    """

    def __init__(self, title: str = "", parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "infoCard")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        # Başlık
        self._lbl_title = QLabel(title)
        self._lbl_title.setProperty("cssClass", "infoCardTitle")
        layout.addWidget(self._lbl_title)

        # Mevcut değer satırı
        row_current = QHBoxLayout()
        lbl_curr_label = QLabel("Mevcut:")
        lbl_curr_label.setProperty("cssClass", "infoCardDetail")
        self._lbl_current = QLabel("—")
        self._lbl_current.setProperty("cssClass", "infoCardValueSmall")
        row_current.addWidget(lbl_curr_label)
        row_current.addStretch()
        row_current.addWidget(self._lbl_current)
        layout.addLayout(row_current)

        # Optimal değer satırı
        row_optimal = QHBoxLayout()
        lbl_opt_label = QLabel("Optimal:")
        lbl_opt_label.setProperty("cssClass", "infoCardDetail")
        self._lbl_optimal = QLabel("—")
        self._lbl_optimal.setProperty("cssClass", "infoCardValueMedium")
        row_optimal.addWidget(lbl_opt_label)
        row_optimal.addStretch()
        row_optimal.addWidget(self._lbl_optimal)
        layout.addLayout(row_optimal)

        # Delta satırı
        self._lbl_delta = QLabel("—")
        self._lbl_delta.setProperty("cssClass", "infoCardDelta")
        self._lbl_delta.setAlignment(Qt.AlignRight)
        layout.addWidget(self._lbl_delta)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        current: str,
        optimal: str,
        delta: float,
        positive_is_good: bool = True,
    ) -> None:
        """
        Kartın tüm değerlerini günceller.

        Args:
            current: Mevcut değer metni
            optimal: Optimal değer metni
            delta: Sayısal fark (pozitif = artış)
            positive_is_good: True ise artış yeşil, azalış kırmızı
        """
        self._lbl_current.setText(current)
        self._lbl_optimal.setText(optimal)

        is_positive = delta > 0
        is_good = is_positive if positive_is_good else not is_positive

        arrow = "▲" if is_positive else "▼"
        self._lbl_delta.setText(f"{arrow} {abs(delta):+.2f}")

        # Renk QSS cssState ile yönetilir, inline setStyleSheet değil
        state = "positive" if is_good else "negative"
        self._lbl_delta.setProperty("cssState", state)
        self._lbl_delta.style().unpolish(self._lbl_delta)
        self._lbl_delta.style().polish(self._lbl_delta)

    def reset(self) -> None:
        """Kartı başlangıç değerlerine döndürür."""
        self._lbl_current.setText("—")
        self._lbl_optimal.setText("—")
        self._lbl_delta.setText("—")
        self._lbl_delta.setProperty("cssState", "")
        self._lbl_delta.style().unpolish(self._lbl_delta)
        self._lbl_delta.style().polish(self._lbl_delta)
