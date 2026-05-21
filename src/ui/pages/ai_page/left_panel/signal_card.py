from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar
from PyQt5.QtCore import Qt
from src.ui.pages.ai_page.core.models import ModelOutlook
from src.ui.core.icon_manager import IconManager


class SignalCard(QWidget):
    """Modelin yön beklentisini emir dili kullanmadan gösteren kart."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "aiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconManager.get_icon("target", color="@COLOR_PRIMARY").pixmap(20, 20))
        title = QLabel("YÖN BEKLENTİSİ")
        title.setProperty("cssClass", "cardLabel")
        header_layout.addWidget(lbl_icon)
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.lbl_signal = QLabel("-")
        self.lbl_signal.setAlignment(Qt.AlignCenter)
        self.lbl_signal.setProperty("cssClass", "outlookLabel")
        self.lbl_signal.setProperty("cssState", "neutral")
        self.lbl_signal.setFixedHeight(54)
        layout.addWidget(self.lbl_signal)

        strength_layout = QHBoxLayout()
        lbl_strength = QLabel("Model beklenti gücü: ")
        lbl_strength.setProperty("cssClass", "aiStrongMetaText")
        strength_layout.addWidget(lbl_strength)
        self.progress_strength = QProgressBar()
        self.progress_strength.setRange(0, 100)
        self.progress_strength.setValue(0)
        self.progress_strength.setProperty("cssClass", "aiProgressPurple")
        strength_layout.addWidget(self.progress_strength)

        layout.addLayout(strength_layout)

        # Trend bilgisi
        self.lbl_trend_info = QLabel("")
        self.lbl_trend_info.setProperty("cssClass", "aiMetaText")
        self.lbl_trend_info.setWordWrap(True)
        layout.addWidget(self.lbl_trend_info)

        # Güven uyarıları
        self.lbl_warnings = QLabel("")
        self.lbl_warnings.setProperty("cssClass", "warningText")
        self.lbl_warnings.setWordWrap(True)
        self.lbl_warnings.setVisible(False)
        layout.addWidget(self.lbl_warnings)

    def update_data(
        self,
        outlook: ModelOutlook,
        strength: float,
        trend_label: str | None = None,
        confidence_warnings: list[str] | None = None,
    ):
        state_map = {
            ModelOutlook.UP: "up",
            ModelOutlook.DOWN: "down",
            ModelOutlook.NEUTRAL: "neutral",
        }
        state = state_map.get(outlook, "neutral")

        self.lbl_signal.setText(outlook.value)
        self.lbl_signal.setProperty("cssState", state)
        self.lbl_signal.style().unpolish(self.lbl_signal)
        self.lbl_signal.style().polish(self.lbl_signal)
        self.progress_strength.setValue(int(strength * 100))

        # Trend bilgisi
        if trend_label:
            tl_lower = trend_label.lower()
            trend_map = {"up": "Yükseliş trendi", "down": "Düşüş trendi", "neutral": "Yatay seyir", "flat": "Yatay seyir"}
            self.lbl_trend_info.setText(f"Trend: {trend_map.get(tl_lower, trend_label)}")

        # Güven uyarıları
        if confidence_warnings:
            warnings_text = "\n".join(f"⚠ {w}" for w in confidence_warnings[:3])
            self.lbl_warnings.setText(warnings_text)
            self.lbl_warnings.setVisible(True)
        else:
            self.lbl_warnings.setVisible(False)

    def reset(self):
        self.lbl_signal.setText("-")
        self.lbl_signal.setProperty("cssState", "neutral")
        self.lbl_signal.style().unpolish(self.lbl_signal)
        self.lbl_signal.style().polish(self.lbl_signal)
        self.progress_strength.setValue(0)
        self.lbl_trend_info.setText("")
        self.lbl_warnings.setText("")
        self.lbl_warnings.setVisible(False)
