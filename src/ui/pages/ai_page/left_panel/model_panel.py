import logging

from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from PyQt5.QtCore import QThreadPool, pyqtSignal, Qt

from src.application.services.ai.ai_analysis_service import AiAnalysisService
from src.domain.models.ai_analysis import AnalysisResult
from src.ui.pages.ai_page.labels import DEFAULT_INVESTMENT_DISCLAIMER
from src.ui.shared.locale_tr import L10N
from .ticker_input_bar import TickerInputBar
from .status_banner import StatusBanner
from .prediction_card import PredictionCard
from .signal_card import SignalCard
from .xai_card import XAICard
from .performance_card import PerformanceCard
from .send_to_chat_button import SendToChatButton
from src.ui.worker import Worker

logger = logging.getLogger(__name__)


class ModelPanel(QWidget):
    """Sol Panel (Model Analiz Paneli) Ana Kapsayıcısı"""
    send_to_chat_requested = pyqtSignal(AnalysisResult)
    connection_dropped = pyqtSignal()  # FastAPIAdapter aktifken analiz hatası → re-probe için

    def __init__(self, analysis_service: AiAnalysisService):
        super().__init__()
        self._service = analysis_service
        self._threadpool = QThreadPool.globalInstance()
        self._analysis_request_id = 0
        self.worker = None
        self._init_ui()

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

        # 1. Bağlantı durumu banner'ı (set_connection_checking ile görünür olur)
        self.status_banner = StatusBanner()
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

    # ── Async bağlantı kontrol API'si (AIPage.on_page_enter Worker'ı tarafından kullanılır) ──

    def set_connection_checking(self) -> None:
        """UI thread'de: bağlanılıyor durumunu gösterir, analiz butonunu devre dışı bırakır."""
        self.status_banner.show_connecting()
        self.input_bar.btn_analyze.setEnabled(False)

    def probe_connection(self) -> bool:
        """WORKER THREAD'de çalışır — yalnızca ağ I/O, UI'a DOKUNMAZ."""
        return self._service.probe()

    def apply_connection_result(self, ok: bool) -> None:
        """MAIN THREAD (Qt sinyal üzerinden): banner günceller."""
        self.input_bar.btn_analyze.setEnabled(True)
        if ok:
            self.status_banner.show_api_connected()
            logger.info("AI_Core FastAPI bağlantısı başarılı (async probe)")
        else:
            self.status_banner.show_mock_mode()
            logger.warning("AI_Core erişilemedi (async probe), demo sağlayıcı kullanılıyor")

    def _start_analysis(self, ticker: str):
        self._analysis_request_id += 1
        request_id = self._analysis_request_id
        self.input_bar.btn_analyze.setEnabled(False)
        self.prediction_card.reset()
        self.signal_card.reset()
        self.performance_card.reset()
        self.xai_card.reset()
        self.btn_send_chat.reset()
        self._set_disclaimer(DEFAULT_INVESTMENT_DISCLAIMER)

        # Analiz durumu banner'ını sıfırla
        if self._service.live_available:
            self.status_banner.show_api_connected()

        self.worker = Worker(self._service.analyze, ticker)
        self.worker.signals.result.connect(lambda result, rid=request_id: self._on_worker_result(rid, result))
        self.worker.signals.error.connect(lambda err, rid=request_id: self._on_worker_error(rid, err))
        self.worker.signals.finished.connect(lambda rid=request_id: self._on_worker_finished(rid))
        self._threadpool.start(self.worker)

    def _on_worker_result(self, request_id: int, result: AnalysisResult):
        if request_id == self._analysis_request_id:
            self._on_result_ready(result)

    def _on_worker_error(self, request_id: int, err_tuple):
        if request_id == self._analysis_request_id:
            logger.error("Analiz worker hatası: %s", err_tuple[1])
            self._on_error(str(err_tuple[1]))

    def _on_worker_finished(self, request_id: int):
        if request_id == self._analysis_request_id:
            self.input_bar.btn_analyze.setEnabled(True)

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
        self.status_banner.show_error(L10N.ANALIZ_HATASI_TMPL.format(exc=err))
        if self._service.live_available:
            self._service.mark_unavailable()
            self.connection_dropped.emit()

    def _set_disclaimer(self, disclaimer: str | None):
        self.lbl_disclaimer.setText(disclaimer or DEFAULT_INVESTMENT_DISCLAIMER)
        self.lbl_disclaimer.setVisible(True)
