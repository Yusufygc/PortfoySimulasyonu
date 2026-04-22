from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar, QTextEdit
from PyQt5.QtCore import Qt

class XAICard(QWidget):
    """Model özelliklerini (Explainable AI) gösteren kart"""
    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "aiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)

        title = QLabel("🔍 MODEL AÇIKLAMASI")
        title.setProperty("cssClass", "cardLabel")
        layout.addWidget(title)

        self.features_layout = QVBoxLayout()
        layout.addLayout(self.features_layout)
        
        # Ayraç
        line = QWidget()
        line.setFixedHeight(1)
        line.setProperty("cssClass", "horizontalDivider")
        layout.addWidget(line)

        self.txt_explanation = QTextEdit()
        self.txt_explanation.setReadOnly(True)
        self.txt_explanation.setProperty("cssClass", "aiTextEdit")
        self.txt_explanation.setFixedHeight(80)
        layout.addWidget(self.txt_explanation)

    def update_data(self, features: dict[str, float], text: str):
        # Önceki özellikleri temizle
        while self.features_layout.count():
            child = self.features_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        for name, value in features.items():
            row = QHBoxLayout()
            lbl = QLabel(name)
            lbl.setFixedWidth(60)
            lbl.setProperty("cssClass", "dateLabelMuted")
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(int(value * 100))
            bar.setTextVisible(True)
            bar.setProperty("cssClass", "aiProgressBlue")
            row.addWidget(lbl)
            row.addWidget(bar)
            
            wrapper = QWidget()
            wrapper.setLayout(row)
            wrapper.setProperty("cssClass", "borderlessFrame")
            row.setContentsMargins(0,0,0,0)
            self.features_layout.addWidget(wrapper)

        self.txt_explanation.setText(text)

    def reset(self):
        while self.features_layout.count():
            child = self.features_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.txt_explanation.clear()
