import logging
import os

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt5.QtCore import QThread, pyqtSignal, Qt

from src.ui.pages.ai_page.core.models import AnalysisResult, DEFAULT_INVESTMENT_DISCLAIMER
from src.ui.pages.ai_page.core.model_interface import (
    AIModelInterface,
    FastAPIAdapter,
    MockAdapter,
)
from src.ui.pages.ai_page.core.api_client import AICoreFastAPIClient
from .ticker_input_bar import TickerInputBar
from .status_banner import StatusBanner
from .prediction_card import PredictionCard
from .signal_card import SignalCard
from .xai_card import XAICard
from .performance_card import PerformanceCard
from .send_to_chat_button import SendToChatButton

logger = logging.getLogger(__name__)


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
            result = self.adapter.analyze(self.ticker)
            self.result_ready.emit(result)
        except Exception as e:
            logger.exception("Analiz worker hatası")
            self.error_occurred.emit(str(e))


class ModelPanel(QWidget):
    """Sol Panel (Model Analiz Paneli) Ana Kapsayıcısı"""
    send_to_chat_requested = pyqtSignal(AnalysisResult)

    def __init__(self):
        super().__init__()
        self._setup_adapter()
        self._init_ui()

    def _setup_adapter(self):
        """API erişilebilirliğine göre adapter seçer."""
        base_url = os.getenv("AI_CORE_API_URL", "http://localhost:8000")
        self._client = AICoreFastAPIClient(base_url=base_url)

        try:
            if self._client.health_check():
                self.adapter = FastAPIAdapter(self._client)
                self._api_connected = True
                logger.info("AI_Core FastAPI bağlantısı başarılı (%s)", base_url)
            else:
                self.adapter = MockAdapter()
                self._api_connected = False
                logger.warning("AI_Core erişilemedi, MockAdapter kullanılıyor")
        except Exception:
            self.adapter = MockAdapter()
            self._api_connected = False
            logger.warning("AI_Core bağlantı hatası, MockAdapter kullanılıyor", exc_info=True)

    def _init_ui(self):
        # Ana layout — scroll destekli
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 12, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setProperty("cssClass", "borderlessScrollArea")

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # 1. Bağlantı durumu banner'ı
        self.status_banner = StatusBanner()
        if self._api_connected:
            self.status_banner.show_api_connected()
        else:
            self.status_banner.show_mock_mode()
        layout.addWidget(self.status_banner)

        # 2. Input
        self.input_bar = TickerInputBar()
        self.input_bar.analyze_requested.connect(self._start_analysis)
        layout.addWidget(self.input_bar)

        # 3. Kartlar
        self.prediction_card = PredictionCard()
        self.signal_card = SignalCard()
        self.performance_card = PerformanceCard()
        self.xai_card = XAICard()

        layout.addWidget(self.prediction_card)
        layout.addWidget(self.signal_card)
        layout.addWidget(self.performance_card)
        layout.addWidget(self.xai_card)

        # 4. Yatırım tavsiyesi uyarısı
        self.lbl_disclaimer = QLabel(DEFAULT_INVESTMENT_DISCLAIMER)
        self.lbl_disclaimer.setProperty("cssClass", "disclaimerText")
        self.lbl_disclaimer.setWordWrap(True)
        layout.addWidget(self.lbl_disclaimer)

        # 5. Gönder butonu
        self.btn_send_chat = SendToChatButton()
        self.btn_send_chat.send_requested.connect(self.send_to_chat_requested.emit)
        layout.addWidget(self.btn_send_chat)

        layout.addStretch()

        scroll.setWidget(content)
        outer_layout.addWidget(scroll)

    def _start_analysis(self, ticker: str):
        self.input_bar.btn_analyze.setEnabled(False)
        self.prediction_card.reset()
        self.signal_card.reset()
        self.performance_card.reset()
        self.xai_card.reset()
        self.btn_send_chat.reset()
        self._set_disclaimer(DEFAULT_INVESTMENT_DISCLAIMER)

        # Analiz durumu banner'ını sıfırla
        if self._api_connected:
            self.status_banner.show_api_connected()

        self.worker = AnalysisWorker(self.adapter, ticker)
        self.worker.result_ready.connect(self._on_result_ready)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.finished.connect(lambda: self.input_bar.btn_analyze.setEnabled(True))
        self.worker.start()

    def _on_result_ready(self, result: AnalysisResult):
        self._set_disclaimer(result.disclaimer)

        # Analiz durumu kontrol et
        if result.analysis_status not in ("ok", "low_confidence", "xai_unavailable"):
            self.status_banner.show_analysis_status(
                result.analysis_status,
                result.staleness_days,
            )
            # no_model ve no_forecast durumlarında kartları güncelleme
            if result.analysis_status in ("no_model", "no_forecast", "error"):
                return
        elif result.analysis_status != "ok":
            self.status_banner.show_analysis_status(
                result.analysis_status,
                result.staleness_days,
            )

        # Kartları güncelle
        self.prediction_card.update_data(
            ticker=result.ticker,
            predicted_price=result.predicted_price,
            confidence=result.confidence,
            confidence_label=result.confidence_label,
            model_name=result.model_name,
            last_close=result.last_close,
            trend_label=result.trend_label,
            horizon_days=result.horizon_days,
            weekly_expected_return=result.weekly_expected_return,
        )

        self.signal_card.update_data(
            outlook=result.outlook,
            strength=result.outlook_strength,
            trend_label=result.trend_label,
            confidence_warnings=result.confidence_warnings,
        )

        self.performance_card.update_data(
            composite_score=result.composite_score,
            directional_accuracy=result.directional_accuracy,
            hit_rate=result.hit_rate,
            sharpe=result.sharpe,
            rmse=result.rmse,
            mae=result.mae,
            stability_score=result.stability_score,
            last_close=result.last_close,
        )

        self.xai_card.update_data(
            features=result.xai_features,
            text=result.xai_text,
            xai_available=result.xai_available,
            xai_method=result.xai_method,
            positive_reasons=result.xai_positive_reasons,
            negative_reasons=result.xai_negative_reasons,
            xai_caveat=result.xai_caveat,
        )

        self.btn_send_chat.set_result(result)

    def _on_error(self, err: str):
        self._set_disclaimer(DEFAULT_INVESTMENT_DISCLAIMER)
        self.status_banner.show_error(f"Analiz hatası: {err}")

    def _set_disclaimer(self, disclaimer: str | None):
        self.lbl_disclaimer.setText(disclaimer or DEFAULT_INVESTMENT_DISCLAIMER)
        self.lbl_disclaimer.setVisible(True)
