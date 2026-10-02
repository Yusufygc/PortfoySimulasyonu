"""Hisse bazlı yapay zeka model analizi: denetleyici ve QML paneli."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.domain.models.ai_analysis import (
    AnalysisResult,
    ForecastPoint,
    ModelOutlook,
    PeerInfo,
    XaiFactorItem,
)
from src.ui_qml.controllers.model_analysis_controller import (
    ModelAnalysisController,
    advisor_prompt,
    analysis_to_dict,
)

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


def _result(**overrides):
    values = dict(
        ticker="THYAO", predicted_price=330.0, last_close=300.0, confidence=0.6, confidence_label="medium",
        confidence_warnings=["Veri kısıtlı"], outlook=ModelOutlook.UP, outlook_strength=0.7, model_name="LGBM",
        model_family="gbm", trend_label="up", horizon_days=5, weekly_expected_return=0.05,
        predicted_price_low=310.0, predicted_price_high=350.0, rmse=2.5, directional_accuracy=58.2, sharpe=1.1,
        xai_available=True, xai_method="SHAP",
        xai_positive_reasons=[XaiFactorItem("RSI_14", "RSI (14 gün)", 0.4, "positive")],
        xai_negative_reasons=[XaiFactorItem("VOL", "Hacim", 0.2, "negative")],
        peer=PeerInfo(available=True, peer_percentile=82.0, peer_label="outperform", universe_size=300,
                      trend_prob_up=0.64, kolb_price_low=305.0, kolb_price_high=340.0),
        forecast_points=[ForecastPoint("2026-10-06", 1, bounded_predicted_close=305.0, predicted_return=0.016,
                                       p10_close=295.0, p90_close=315.0)],
        last_observed_date="2026-10-02",
    )
    values.update(overrides)
    return AnalysisResult(**values)


class FakeService:
    def __init__(self, live=True, result=None, error=None):
        self.live, self.result, self.error = live, result or _result(), error
        self.analyzed, self.dropped = [], False

    def probe(self):
        return self.live

    def analyze(self, ticker):
        self.analyzed.append(ticker)
        if self.error:
            raise self.error
        return self.result

    def mark_unavailable(self):
        self.dropped = True


def _ctrl(qapp, service):
    ctrl = ModelAnalysisController(container=SimpleNamespace(ai_analysis_service=service), autoprobe=False)
    ctrl._executor = ImmediateExecutor()
    return ctrl


def test_analysis_to_dict_formats_turkish_values():
    data = analysis_to_dict(_result())

    assert data["predictedText"] == "330,00 ₺" and data["changeText"] == "%+10,00" and data["changeIsUp"] is True
    assert data["intervalText"] == "310,00 ₺ - 350,00 ₺" and data["horizonText"] == "5 gün"
    assert data["confidenceText"] == "Orta" and data["confidencePct"] == 60
    assert data["outlookText"] == "Yükseliş eğilimi" and data["outlookState"] == "up" and data["outlookStrengthPct"] == 70
    assert data["peer"]["available"] and data["peer"]["percentileText"] == "%82" and data["peer"]["probUpText"] == "%64"
    assert data["forecastPoints"][0]["rangeText"] == "295,00 ₺ - 315,00 ₺"
    assert data["xaiPositive"][0]["label"] == "RSI (14 gün)" and data["performance"][1]["valueText"] == "%58,2"
    assert "tavsiyesi değildir" in data["disclaimer"]
    assert analysis_to_dict(_result(predicted_price=None, peer=None))["hasChange"] is False


def test_probe_sets_live_state_and_demo_warning(qapp):
    live = _ctrl(qapp, FakeService(live=True))
    live.probe()
    assert live.isLive is True and live.bannerState == "success"

    demo = _ctrl(qapp, FakeService(live=False))
    demo.probe()
    assert demo.isLive is False and "DEMO" in demo.bannerText and demo.bannerState == "warning"


def test_analyze_live_result_and_ticker_normalization(qapp):
    service = FakeService(live=True)
    ctrl = _ctrl(qapp, service)
    ctrl.probe()

    ctrl.analyze("thyao.is")

    assert service.analyzed == ["THYAO"]
    assert ctrl.hasResult and ctrl.isDemoResult is False and ctrl.result["ticker"] == "THYAO"
    assert ctrl.bannerState == "success" and ctrl.isBusy is False


def test_demo_results_are_marked_as_demo(qapp):
    ctrl = _ctrl(qapp, FakeService(live=False))
    ctrl.probe()

    ctrl.analyze("ASELS")

    assert ctrl.isDemoResult is True and ctrl.bannerText.startswith("DEMO verisi")


def test_blocking_status_shows_banner_without_result(qapp):
    ctrl = _ctrl(qapp, FakeService(result=_result(analysis_status="no_model")))
    ctrl.probe()

    ctrl.analyze("ASELS")

    assert ctrl.hasResult is False and ctrl.bannerState == "error" and "model bulunamadı" in ctrl.bannerText


def test_error_drops_to_demo_except_on_timeout(qapp):
    service = FakeService(live=True, error=RuntimeError("bağlantı koptu"))
    ctrl = _ctrl(qapp, service)
    ctrl.probe()
    ctrl.analyze("ASELS")
    assert service.dropped is True and ctrl.isLive is False and ctrl.bannerState == "error"

    slow = FakeService(live=True, error=RuntimeError("istek zaman aşımına uğradı: timeout"))
    ctrl2 = _ctrl(qapp, slow)
    ctrl2.probe()
    ctrl2.analyze("ASELS")
    assert slow.dropped is False and ctrl2.isLive is True


def test_send_to_advisor_emits_summary_prompt(qapp):
    ctrl = _ctrl(qapp, FakeService())
    ctrl.probe()
    prompts = _capture(ctrl.advisorPromptReady)

    ctrl.sendToAdvisor()
    assert prompts == []  # sonuç yokken gönderilmez

    ctrl.analyze("THYAO")
    ctrl.sendToAdvisor()

    assert prompts and "THYAO" in prompts[0][0] and "330,00 ₺" in prompts[0][0]
    assert advisor_prompt(ctrl.result) == prompts[0][0]


def test_controller_without_service_is_inert(qapp):
    ctrl = ModelAnalysisController(container=None, autoprobe=False)

    ctrl.probe()
    ctrl.analyze("THYAO")

    assert ctrl.serviceAvailable is False and ctrl.hasResult is False and ctrl.isBusy is False


def test_model_analysis_panel_renders_result_without_warnings(qapp):
    ctrl = _ctrl(qapp, FakeService())
    ctrl.probe()
    ctrl.analyze("THYAO")
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    engine.rootContext().setContextProperty("modelAnalysisController", ctrl)
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / "components/ModelAnalysisPanel.qml")))
    if not component.isReady():
        pytest.fail("; ".join(e.toString() for e in component.errors()))

    item = component.create()

    assert item is not None and item.property("hasResult") is True
    assert warnings == [], "; ".join(warnings)
