from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt5.QtCore import QThread, pyqtSignal, Qt
from src.ui.pages.ai_page.core.models import AnalysisResult
from src.ui.pages.ai_page.core.model_interface import AIModelInterface, MockAdapter
from .ticker_input_bar import TickerInputBar
from .prediction_card import PredictionCard
from .signal_card import SignalCard
from .xai_card import XAICard
from .send_to_chat_button import SendToChatButton

class AnalysisWorker(QThread):
    """Analizi UI donmadan arka planda çalıştıran worker"""
    result_ready = pyqtSignal(AnalysisResult)
    error_occurred = pyqtSignal(str)

    def __init__(self, adapter: AIModelInterface, ticker: str):
        super().__init__()
        self.adapter = adapter
        self.ticker = ticker

    def run(self):
        try:
            # QThread gecikmesi simülasyonu
            import time
            time.sleep(1.0)
            result = self.adapter.analyze(self.ticker)
            self.result_ready.emit(result)
        except Exception as e:
            self.error_occurred.emit(str(e))

class ModelPanel(QWidget):
    """Sol Panel (Model Analiz Paneli) Ana Kapsayıcısı"""
    send_to_chat_requested = pyqtSignal(AnalysisResult)

    def __init__(self):
        super().__init__()
        self.adapter = MockAdapter()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 10, 0) # Sağ boşluk bırak
        layout.setSpacing(15)

        # 1. Uyarı Banner (MockAdapter devredeyse)
        if not self.adapter.is_available():
            self.banner = QLabel("⚠ Model henüz bağlı değil — Demo verileri gösteriliyor")
            self.banner.setAlignment(Qt.AlignCenter)
            self.banner.setStyleSheet("""
                background-color: #ca8a04;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 6px;
            """)
            layout.addWidget(self.banner)

        # 2. Input
        self.input_bar = TickerInputBar()
        self.input_bar.analyze_requested.connect(self._start_analysis)
        layout.addWidget(self.input_bar)

        # 3. Kartlar
        self.prediction_card = PredictionCard()
        self.signal_card = SignalCard()
        self.xai_card = XAICard()
        
        layout.addWidget(self.prediction_card)
        layout.addWidget(self.signal_card)
        layout.addWidget(self.xai_card)

        # 4. Gönder butonu
        self.btn_send_chat = SendToChatButton()
        self.btn_send_chat.send_requested.connect(self.send_to_chat_requested.emit)
        layout.addWidget(self.btn_send_chat)

        layout.addStretch()

    def _start_analysis(self, ticker: str):
        self.input_bar.btn_analyze.setEnabled(False)
        self.prediction_card.reset()
        self.signal_card.reset()
        self.xai_card.reset()
        self.btn_send_chat.reset()

        self.worker = AnalysisWorker(self.adapter, ticker)
        self.worker.result_ready.connect(self._on_result_ready)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished.connect(lambda: self.input_bar.btn_analyze.setEnabled(True))
        self.worker.start()

    def _on_result_ready(self, result: AnalysisResult):
        self.prediction_card.update_data(result.ticker, result.predicted_price, result.confidence)
        self.signal_card.update_data(result.signal, result.signal_strength)
        self.xai_card.update_data(result.xai_features, result.xai_text)
        self.btn_send_chat.set_result(result)

    def _on_error(self, err: str):
        self.xai_card.txt_explanation.setText(f"HATA: {err}")
