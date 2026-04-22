from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar
from PyQt5.QtCore import Qt
from src.ui.pages.ai_page.core.models import Signal

class SignalCard(QWidget):
    """Sinyal (AL/SAT/TUT) gösteren kart"""
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setStyleSheet("""
            QWidget { background-color: #1e293b; border-radius: 8px; }
            QLabel { color: #f8fafc; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("🎯 SİNYAL")
        title.setStyleSheet("font-size: 14px; font-weight: bold; color: #94a3b8;")
        layout.addWidget(title)

        self.lbl_signal = QLabel("-")
        self.lbl_signal.setAlignment(Qt.AlignCenter)
        self.lbl_signal.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                padding: 15px;
                border-radius: 8px;
                background-color: #334155;
                color: #94a3b8;
            }
        """)
        layout.addWidget(self.lbl_signal)

        strength_layout = QHBoxLayout()
        strength_layout.addWidget(QLabel("Güç: "))
        self.progress_strength = QProgressBar()
        self.progress_strength.setRange(0, 100)
        self.progress_strength.setValue(0)
        self.progress_strength.setStyleSheet("""
            QProgressBar { border: 1px solid #334155; border-radius: 4px; text-align: center; color: white; }
            QProgressBar::chunk { background-color: #a855f7; border-radius: 4px; }
        """)
        strength_layout.addWidget(self.progress_strength)
        
        layout.addLayout(strength_layout)

    def update_data(self, signal: Signal, strength: float):
        colors = {
            Signal.BUY: ("#00C853", "white"),
            Signal.SELL: ("#D50000", "white"),
            Signal.HOLD: ("#FFD600", "black")
        }
        bg_color, fg_color = colors.get(signal, ("#334155", "#94a3b8"))
        
        self.lbl_signal.setText(signal.value)
        self.lbl_signal.setStyleSheet(f"""
            QLabel {{
                font-size: 24px;
                font-weight: bold;
                padding: 15px;
                border-radius: 8px;
                background-color: {bg_color};
                color: {fg_color};
            }}
        """)
        self.progress_strength.setValue(int(strength * 100))

    def reset(self):
        self.lbl_signal.setText("-")
        self.lbl_signal.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                padding: 15px;
                border-radius: 8px;
                background-color: #334155;
                color: #94a3b8;
            }
        """)
        self.progress_strength.setValue(0)
