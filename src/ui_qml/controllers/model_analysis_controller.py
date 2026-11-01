"""
ModelAnalysisController — Hisse bazlı yapay zeka model analizi (QML, Yapay Zeka sayfası > "Hisse Modeli" modu).

Eski arayüzdeki `ModelPanel`in karşılığıdır: AI_Core (FastAPI) modelinin tahmin, yön beklentisi, performans,
açıklanabilirlik (XAI) ve akran (peer) çıktılarını gösterir. AI_Core erişilemezse servis demo sağlayıcıya düşer;
bu durumda sonuçlar GERÇEK DEĞİLDİR ve arayüzde belirgin şekilde "demo" olarak işaretlenir.
Analiz ve bağlantı yoklaması arka plan thread'inde çalışır.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.domain.models.ai_analysis import AnalysisResult, ModelOutlook, PeerInfo, XaiFactorItem
from src.domain.ticker import clean_ticker
from src.ui_qml.messages import msg

logger = logging.getLogger(__name__)

DISCLAIMER = (
    msg("model_analysis.bu_cikti_kisisel_yatirim_tavsiyesi_degildir")
)
_OUTLOOK_LABELS = {
    ModelOutlook.UP: (msg("model_analysis.yukselis_egilimi"), "up"),
    ModelOutlook.DOWN: (msg("model_analysis.dusus_egilimi"), "down"),
    ModelOutlook.NEUTRAL: (msg("model_analysis.yatay_notr_gorunum"), "neutral"),
}
_CONFIDENCE_LABELS = {"low": msg("model_analysis.dusuk"), "medium": "Orta", "high": msg("model_analysis.yuksek")}
_TREND_LABELS = {"up": msg("model_analysis.yukselis_trendi"), "down": msg("model_analysis.dusus_trendi"), "neutral": "Yatay seyir", "flat": "Yatay seyir"}
_PEER_LABELS = {"outperform": msg("model_analysis.akranlarina_gore_guclu"), "inline": msg("model_analysis.akranlariyla_paralel"),
                "underperform": msg("model_analysis.akranlarina_gore_zayif"), "unknown": "Belirsiz"}
# analysis_status -> (metin, durum)
_STATUS_TEXTS = {
    "ok": (msg("model_analysis.analiz_basarili_veriler_guncel"), "success"),
    "stale_data": (msg("model_analysis.dikkat_piyasa_verisi_eski_tahminler_guncel"), "warning"),
    "no_model": (msg("model_analysis.bu_hisse_icin_kayitli_model_bulunamadi"), "error"),
    "no_forecast": (msg("model_analysis.model_mevcut_ama_tahmin_uretilmemis"), "warning"),
    "low_confidence": (msg("model_analysis.sonuc_mevcut_ancak_guven_duzeyi_dusuk"), "warning"),
    "xai_unavailable": (msg("model_analysis.tahmin_mevcut_ama_aciklanabilirlik_xai_veris"), "warning"),
    "error": (msg("model_analysis.beklenmeyen_bir_hata_olustu"), "error"),
}
_BLOCKING_STATUSES = {"no_model", "no_forecast", "error"}


def _num(value: Optional[float], decimals: int = 2) -> str:
    if value is None:
        return "-"
    text = f"{value:,.{decimals}f}"
    return text.replace(",", "X").replace(".", ",").replace("X", ".")


def _price(value: Optional[float]) -> str:
    return "-" if value is None else f"{_num(value)} ₺"


def _pct(value: Optional[float], decimals: int = 2, signed: bool = False) -> str:
    if value is None:
        return "-"
    text = f"{value:+.{decimals}f}" if signed else f"{value:.{decimals}f}"
    return "%" + text.replace(".", ",")


def _factor(item: XaiFactorItem) -> Dict[str, Any]:
    return {
        "label": item.human_label or item.feature_name,
        "importanceText": _num(item.importance, 3),
        "reason": item.reason or "",
    }


def _peer(peer: Optional[PeerInfo]) -> Dict[str, Any]:
    if peer is None or not peer.available:
        return {"available": False}
    band = ""
    if peer.kolb_price_low is not None and peer.kolb_price_high is not None:
        band = f"{_price(peer.kolb_price_low)} - {_price(peer.kolb_price_high)}"
    return {
        "available": True,
        "asOf": peer.as_of_date or "-",
        "percentileText": "-" if peer.peer_percentile is None else _pct(peer.peer_percentile, 0),
        "labelText": _PEER_LABELS.get((peer.peer_label or "unknown").lower(), peer.peer_label or "-"),
        "universeText": "-" if peer.universe_size is None else f"{peer.universe_size} hisse",
        "trendText": peer.trend_label or "-",
        "probUpText": "-" if peer.trend_prob_up is None else _pct(peer.trend_prob_up * 100, 0),
        "bandText": band or "-",
        "confidenceText": _CONFIDENCE_LABELS.get((peer.confidence_label or "").lower(), peer.confidence_label or "-"),
        "warnings": list(peer.confidence_warnings),
    }


def analysis_to_dict(result: AnalysisResult) -> Dict[str, Any]:
    """Domain sonucunu QML'in doğrudan gösterebileceği biçimli sözlüğe çevirir."""
    outlook_text, outlook_state = _OUTLOOK_LABELS.get(result.outlook, _OUTLOOK_LABELS[ModelOutlook.NEUTRAL])
    change_pct: Optional[float] = None
    if result.predicted_price is not None and result.last_close:
        change_pct = (result.predicted_price - result.last_close) / result.last_close * 100.0
    interval = ""
    if result.predicted_price_low is not None and result.predicted_price_high is not None:
        interval = f"{_price(result.predicted_price_low)} - {_price(result.predicted_price_high)}"
    trend = _TREND_LABELS.get((result.trend_label or "").lower(), result.trend_label or "")
    performance = [
        (msg("model_analysis.bilesik_skor"), _num(result.composite_score, 1)),
        (msg("model_analysis.yon_dogrulugu"), "-" if result.directional_accuracy is None else _pct(result.directional_accuracy, 1)),
        (msg("model_analysis.isabet_orani"), "-" if result.hit_rate is None else _pct(result.hit_rate, 1)),
        ("Sharpe", _num(result.sharpe, 2)),
        ("RMSE", _num(result.rmse, 2)),
        ("MAE", _num(result.mae, 2)),
        (msg("model_analysis.kararlilik"), _num(result.stability_score, 2)),
    ]
    return {
        "ticker": result.ticker,
        "modelName": result.model_name or "-",
        "modelFamily": result.model_family or "-",
        "trainedAt": result.trained_at or "-",
        "lastCloseText": _price(result.last_close),
        "predictedText": _price(result.predicted_price),
        "changeText": _pct(change_pct, 2, signed=True),
        "changeIsUp": change_pct is not None and change_pct >= 0,
        "hasChange": change_pct is not None,
        "intervalText": interval or "-",
        "horizonText": "-" if result.horizon_days is None else msg("model_analysis.gun", horizon_days=result.horizon_days),
        "weeklyReturnText": "-" if result.weekly_expected_return is None else _pct(result.weekly_expected_return * 100, 2, True),
        "confidenceText": _CONFIDENCE_LABELS.get(result.confidence_label, result.confidence_label),
        "confidencePct": int(round(max(0.0, min(1.0, result.confidence)) * 100)),
        "confidenceReasons": list(result.confidence_reasons),
        "confidenceWarnings": list(result.confidence_warnings),
        "outlookText": outlook_text,
        "outlookState": outlook_state,
        "outlookStrengthPct": int(round(max(0.0, min(1.0, result.outlook_strength)) * 100)),
        "trendText": trend,
        "freshnessText": (
            f"Son veri: {result.last_observed_date or '-'}"
            + (msg("model_analysis.islem_gunu_geride", staleness_days=result.staleness_days) if result.staleness_days else "")
        ),
        "performance": [{"label": label, "valueText": value} for label, value in performance],
        "xaiAvailable": result.xai_available,
        "xaiMethod": result.xai_method or "",
        "xaiPositive": [_factor(i) for i in result.xai_positive_reasons],
        "xaiNegative": [_factor(i) for i in result.xai_negative_reasons],
        "xaiText": result.xai_text or "",
        "xaiCaveat": result.xai_caveat or result.xai_model_family_caveat or "",
        "peer": _peer(result.peer),
        "forecastPoints": [
            {
                "date": point.target_date,
                "closeText": _price(point.bounded_predicted_close if point.bounded_predicted_close is not None else point.p50_close),
                "returnText": "-" if point.predicted_return is None else _pct(point.predicted_return * 100, 2, True),
                "rangeText": (
                    f"{_price(point.p10_close)} - {_price(point.p90_close)}"
                    if point.p10_close is not None and point.p90_close is not None else "-"
                ),
            }
            for point in result.forecast_points
        ],
        "disclaimer": result.disclaimer or DISCLAIMER,
    }


def advisor_prompt(data: Dict[str, Any]) -> str:
    """Analiz özetini portföy danışmanına soru olarak gönderilecek metne çevirir."""
    return (
        msg("model_analysis.icin_model_analizi_sonucu_tahmin_son", ticker=data["ticker"], predicted=data["predictedText"], last_close=data["lastCloseText"], change=data["changeText"], outlook=data["outlookText"], confidence=data["confidenceText"])
    )


class ModelAnalysisController(QObject):
    """QML context property: modelAnalysisController"""

    resultChanged = Signal()
    busyChanged = Signal()
    bannerChanged = Signal()
    # Sonucu portföy danışmanına gönder (QML sohbet moduna geçer ve mesajı yollar)
    advisorPromptReady = Signal(str, arguments=["prompt"])

    _probeFinished = Signal(bool)
    _analysisFinished = Signal(int, object, str)

    def __init__(self, container=None, parent: QObject | None = None, autoprobe: bool = True) -> None:
        super().__init__(parent)
        self._container = container
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._busy = False
        self._probing = False
        self._live = False
        self._result: Dict[str, Any] = {}
        self._banner_text = ""
        self._banner_state = "neutral"
        self._request_id = 0
        self._probeFinished.connect(self._on_probe_finished)
        self._analysisFinished.connect(self._on_analysis_finished)
        if autoprobe:
            self.probe()

    @property
    def _service(self):
        return getattr(self._container, "ai_analysis_service", None) if self._container else None

    # ------------------------------------------------------------------ properties

    @Property(bool, constant=True)
    def serviceAvailable(self) -> bool:
        return self._service is not None

    @Property(bool, notify=busyChanged)
    def isBusy(self) -> bool:
        return self._busy or self._probing

    @Property(bool, notify=resultChanged)
    def hasResult(self) -> bool:
        return bool(self._result)

    @Property("QVariantMap", notify=resultChanged)
    def result(self) -> Dict[str, Any]:
        return self._result

    @Property(str, notify=bannerChanged)
    def bannerText(self) -> str:
        return self._banner_text

    @Property(str, notify=bannerChanged)
    def bannerState(self) -> str:
        return self._banner_state

    @Property(str, constant=True)
    def disclaimer(self) -> str:
        return DISCLAIMER

    def _set_banner(self, text: str, state: str) -> None:
        self._banner_text, self._banner_state = text, state
        self.bannerChanged.emit()

    # ------------------------------------------------------------------ bağlantı

    @Slot()
    def probe(self) -> None:
        service = self._service
        if service is None or self._probing:
            return
        self._probing = True
        self.busyChanged.emit()
        self._set_banner(msg("model_analysis.yapay_zeka_motoruna_baglaniliyor"), "warning")

        def work() -> None:
            try:
                self._probeFinished.emit(bool(service.probe()))
            except Exception as exc:
                logger.debug("AI_Core yoklaması başarısız: %s", exc)
                self._probeFinished.emit(False)

        self._executor.submit(work)

    def _on_probe_finished(self, live: bool) -> None:
        self._probing = False
        self._live = live
        self.busyChanged.emit()
        if live:
            self._set_banner(msg("model_analysis.ai_core_modeli_bagli"), "success")
        else:
            self._set_banner(msg("model_analysis.model_henuz_bagli_degil_sonuclar_demo"), "warning")

    # ------------------------------------------------------------------ analiz

    @Slot(str)
    def analyze(self, ticker: str) -> None:
        service = self._service
        symbol = clean_ticker(ticker)
        if service is None or not symbol or self._busy:
            return
        self._busy = True
        self._request_id += 1
        request_id = self._request_id
        self.busyChanged.emit()
        self._result = {}
        self.resultChanged.emit()

        def work() -> None:
            try:
                self._analysisFinished.emit(request_id, service.analyze(symbol), "")
            except Exception as exc:
                logger.warning("Model analizi başarısız (%s): %s", symbol, exc)
                self._analysisFinished.emit(request_id, None, str(exc))

        self._executor.submit(work)

    def _on_analysis_finished(self, request_id: int, result: Any, error: str) -> None:
        if request_id != self._request_id:
            return
        self._busy = False
        self.busyChanged.emit()
        if error or result is None:
            self._set_banner(msg("model_analysis.analiz_hatasi", value=error or msg("model_analysis.no_result")), "error")
            # Zaman aşımında canlı bağlantı korunur; diğer hatalarda demo'ya düşülür
            lowered = error.lower()
            service = self._service
            if self._live and service is not None and not any(k in lowered for k in ("zaman aşımı", "timeout", "timed out")):  # metin-muaf: hata metninde aranan anahtar sözcükler
                service.mark_unavailable()
                self._live = False
            return
        text, state = _STATUS_TEXTS.get(result.analysis_status, (f"Bilinmeyen durum: {result.analysis_status}", "warning"))
        if result.analysis_status == "stale_data" and result.staleness_days:
            text += msg("model_analysis.islem_gunu_geride", staleness_days=result.staleness_days)
        if not self._live:
            text = msg("model_analysis.demo_verisi_model_bagli_degil") + text
            state = "warning"
        self._set_banner(text, state)
        if result.analysis_status in _BLOCKING_STATUSES:
            return
        data = analysis_to_dict(result)
        data["isLive"] = self._live
        self._result = data
        self.resultChanged.emit()

    @Slot()
    def sendToAdvisor(self) -> None:
        if self._result:
            self.advisorPromptReady.emit(advisor_prompt(self._result))
