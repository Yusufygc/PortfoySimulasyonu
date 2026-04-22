from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar
from PyQt5.QtCore import Qt

class PredictionCard(QWidget):
    """Tahmin sonuçlarını gösteren kart"""
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "aiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("📈 TAHMİN")
        title.setProperty("cssClass", "cardLabel")
        layout.addWidget(title)

        self.lbl_ticker = QLabel("Hisse: -")
        self.lbl_price = QLabel("Fiyat: -")
        self.lbl_price.setProperty("cssClass", "priceValueLargeCyan")

        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Güven: "))
        self.progress_conf = QProgressBar()
        self.progress_conf.setRange(0, 100)
        self.progress_conf.setValue(0)
        self.progress_conf.setTextVisible(True)
        self.progress_conf.setProperty("cssClass", "aiProgressCyan")
        conf_layout.addWidget(self.progress_conf)

        self.lbl_time = QLabel("Zaman: 5 günlük tahmin")
        self.lbl_time.setProperty("cssClass", "dateLabelMuted")

        layout.addWidget(self.lbl_ticker)
        layout.addWidget(self.lbl_price)
        layout.addLayout(conf_layout)
        layout.addWidget(self.lbl_time)

    def update_data(self, ticker: str, price: float, confidence: float):
        self.lbl_ticker.setText(f"Hisse: {ticker}")
        self.lbl_price.setText(f"Fiyat: ₺{price:.2f}")
        self.progress_conf.setValue(int(confidence * 100))

    def reset(self):
        self.lbl_ticker.setText("Hisse: -")
        self.lbl_price.setText("Fiyat: -")
        self.progress_conf.setValue(0)
