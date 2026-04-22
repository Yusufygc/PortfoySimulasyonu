from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar
from PyQt5.QtCore import Qt
from src.ui.pages.ai_page.core.models import Signal

class SignalCard(QWidget):
    """Sinyal (AL/SAT/TUT) gösteren kart"""
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "aiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("🎯 SİNYAL")
        title.setProperty("cssClass", "cardLabel")
        layout.addWidget(title)

        self.lbl_signal = QLabel("-")
        self.lbl_signal.setAlignment(Qt.AlignCenter)
        self.lbl_signal.setProperty("cssClass", "signalLabel")
        self.lbl_signal.setProperty("cssState", "neutral")
        layout.addWidget(self.lbl_signal)

        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("Güç: "))
        self.progress_strength = QProgressBar()
        self.progress_strength.setRange(0, 100)
        self.progress_strength.setValue(0)
        self.progress_strength.setProperty("cssClass", "aiProgressPurple")
        strength_layout.addWidget(self.progress_strength)
        
        layout.addLayout(strength_layout)

    def update_data(self, signal: Signal, strength: float):
        state_map = {
            Signal.BUY: "buy",
            Signal.SELL: "sell",
            Signal.HOLD: "hold"
        }
        state = state_map.get(signal, "neutral")
        
        self.lbl_signal.setText(signal.value)
        self.lbl_signal.setProperty("cssState", state)
        self.lbl_signal.style().unpolish(self.lbl_signal)
        self.lbl_signal.style().polish(self.lbl_signal)
        self.progress_strength.setValue(int(strength * 100))

    def reset(self):
        self.lbl_signal.setText("-")
        self.lbl_signal.setProperty("cssState", "neutral")
        self.lbl_signal.style().unpolish(self.lbl_signal)
        self.lbl_signal.style().polish(self.lbl_signal)
        self.progress_strength.setValue(0)
