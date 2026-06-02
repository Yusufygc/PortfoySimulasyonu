# -*- coding: utf-8 -*-
"""
AI Model arayüzü ve adaptörleri.

- AIModelInterface: abstract temel sınıf.
- FastAPIAdapter: AI_Core FastAPI servisinden gerçek analiz verisini çeker.
- MockAdapter: API erişilemez olduğunda demo veriler üretir.
"""

from __future__ import annotations

import logging
import random
from abc import ABC, abstractmethod
from typing import Any, Dict

from src.ui.pages.ai_page.core.models import (
    AnalysisResult,
    DEFAULT_INVESTMENT_DISCLAIMER,
    ForecastPoint,
    ModelOutlook,
    XaiFactorItem,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Abstract arayüz
# ─────────────────────────────────────────────────────────────────────────────

class AIModelInterface(ABC):
    @abstractmethod
    def analyze(self, ticker: str) -> AnalysisResult:
        """Senkron çağrı. UI Worker içinde çalıştırılacak."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Model/process erişilebilir mi? UI banner için."""
        pass


# ─────────────────────────────────────────────────────────────────────────────
# FastAPI Adapter
# ─────────────────────────────────────────────────────────────────────────────

# Güven etiketi → sayısal değer eşleme
_CONFIDENCE_MAP = {"low": 0.25, "medium": 0.60, "high": 0.85}


def _parse_xai_factor(raw: Dict[str, Any], default_direction: str) -> XaiFactorItem:
    """API XAI faktörünü UI modeline geriye uyumlu biçimde taşır."""
    contribution = raw.get("contribution")
    try:
        contribution = None if contribution is None else float(contribution)
    except (TypeError, ValueError):
        contribution = None

    return XaiFactorItem(
        feature_name=raw.get("feature_name", ""),
        human_label=raw.get("human_label", ""),
        importance=abs(float(raw.get("importance", 0) or 0)),
        direction=raw.get("direction", default_direction),
        feature_group=raw.get("feature_group"),
        reason=raw.get("reason"),
        method=raw.get("method"),
        contribution=contribution,
        approximate=raw.get("approximate"),
    )


def _xai_factor_summary(item: XaiFactorItem) -> str:
    name = item.human_label or item.feature_name
    group = f" [{item.feature_group}]" if item.feature_group else ""
    reason = f" — {item.reason}" if item.reason else ""
    return f"{name}{group}{reason}"


def _outlook_from_trend_label(trend_label: str | None) -> ModelOutlook:
    trend_norm = str(trend_label or "").strip().lower()
    if trend_norm == "up":
        return ModelOutlook.UP
    if trend_norm == "down":
        return ModelOutlook.DOWN
    return ModelOutlook.NEUTRAL


def _parse_api_response(data: Dict[str, Any]) -> AnalysisResult:
    """FastAPI /analysis/{symbol} JSON yanıtını AnalysisResult'a dönüştürür."""

    # ── Blokları çıkar ───────────────────────────────────────────────────
    data_block = data.get("data", {})
    model_block = data.get("model", {})
    forecast_block = data.get("forecast", {})
    perf_block = data.get("performance", {})
    conf_block = data.get("confidence", {})
    xai_block = data.get("xai", {})

    # ── Güven ────────────────────────────────────────────────────────────
    conf_label = conf_block.get("label", "low")
    conf_numeric = _CONFIDENCE_MAP.get(conf_label, 0.25)

    # ── Forecast noktaları ───────────────────────────────────────────────
    raw_points = forecast_block.get("points", [])
    forecast_points = [
        ForecastPoint(
            target_date=str(p.get("target_date", "")),
            horizon_index=int(p.get("horizon_index", 0)),
            bounded_predicted_close=p.get("bounded_predicted_close"),
            predicted_return=p.get("predicted_return"),
        )
        for p in raw_points
    ]

    # ── Tahmini fiyat (son noktanın bounded_predicted_close'u) ───────────
    predicted_price = None
    if forecast_points:
        predicted_price = forecast_points[-1].bounded_predicted_close

    # ── Yön beklentisi (emir dili değil, analitik görünüm) ─
    trend_label = forecast_block.get("trend_label")
    trend_norm = str(trend_label or "").strip().lower()
    outlook = _outlook_from_trend_label(trend_label)
    outlook_strength = min(abs(forecast_block.get("weekly_expected_return", 0) or 0) * 10, 1.0)

    # ── XAI ──────────────────────────────────────────────────────────────
    xai_pos = [
        _parse_xai_factor(f, "positive")
        for f in xai_block.get("top_positive_reasons", [])
    ]
    xai_neg = [
        _parse_xai_factor(f, "negative")
        for f in xai_block.get("top_negative_reasons", [])
    ]

    # Eski uyumluluk: xai_features dict (feature_name → importance)
    xai_features: Dict[str, float] = {}
    for item in xai_pos + xai_neg:
        label = item.human_label or item.feature_name
        xai_features[label] = item.importance

    # XAI metin özeti oluştur
    xai_text = ""
    if xai_pos or xai_neg:
        parts = []
        if xai_pos:
            top = xai_pos[0]
            parts.append(f"Fiyatı yukarı çeken en önemli faktör: {_xai_factor_summary(top)}")
        if xai_neg:
            top = xai_neg[0]
            parts.append(f"Aşağı yönlü baskı yapan faktör: {_xai_factor_summary(top)}")
        xai_text = ". ".join(parts) + "."

    return AnalysisResult(
        ticker=data.get("symbol", ""),
        analysis_status=data.get("analysis_status", "error"),
        predicted_price=predicted_price,
        confidence=conf_numeric,
        confidence_label=conf_label,
        confidence_reasons=conf_block.get("reasons", []),
        confidence_warnings=conf_block.get("warnings", []),
        outlook=outlook,
        outlook_strength=outlook_strength,
        last_close=data_block.get("last_close"),
        last_observed_date=data_block.get("last_observed_date"),
        data_freshness=data_block.get("data_freshness", "unknown"),
        staleness_days=data_block.get("staleness_days", 0),
        model_name=model_block.get("model_name", ""),
        model_family=model_block.get("model_family", ""),
        validation_mode=model_block.get("validation_mode"),
        trained_at=model_block.get("trained_at"),
        eligibility_status=model_block.get("eligibility_status", "eligible"),
        trend_label=trend_norm or trend_label,
        horizon_days=forecast_block.get("horizon_days"),
        weekly_expected_return=forecast_block.get("weekly_expected_return"),
        forecast_points=forecast_points,
        rmse=perf_block.get("rmse"),
        mae=perf_block.get("mae"),
        directional_accuracy=perf_block.get("directional_accuracy"),
        hit_rate=perf_block.get("hit_rate"),
        composite_score=perf_block.get("composite_score"),
        sharpe=perf_block.get("sharpe"),
        stability_score=perf_block.get("stability_score"),
        xai_available=xai_block.get("available", False),
        xai_method=xai_block.get("method", ""),
        xai_features=xai_features,
        xai_positive_reasons=xai_pos,
        xai_negative_reasons=xai_neg,
        xai_text=xai_text,
        xai_caveat=xai_block.get("caveat", ""),
        xai_model_family_caveat=xai_block.get("model_family_caveat", ""),
        disclaimer=data.get("disclaimer") or DEFAULT_INVESTMENT_DISCLAIMER,
        raw_output=data,
        generated_at=data.get("generated_at", ""),
    )


class FastAPIAdapter(AIModelInterface):
    """
    AI_Core FastAPI servisinden gerçek model analiz verisini çeker.
    analyze() metodu UI Worker içinde çağrılır — UI donmaz.
    """

    def __init__(self, client) -> None:
        from src.ui.pages.ai_page.core.api_client import AICoreFastAPIClient
        self._client: AICoreFastAPIClient = client

    def analyze(self, ticker: str) -> AnalysisResult:
        raw = self._client.get_analysis(ticker)
        return _parse_api_response(raw)

    def is_available(self) -> bool:
        return self._client.health_check()


# ─────────────────────────────────────────────────────────────────────────────
# Mock Adapter (fallback / demo)
# ─────────────────────────────────────────────────────────────────────────────

class MockAdapter(AIModelInterface):
    """
    Gerçek model hazır olana kadar veya API erişilemezken kullanılacak.
    Gerçekçi rastgele veri üretir.
    is_available() → False döner → UI'da sarı uyarı gösterir.
    """
    def analyze(self, ticker: str) -> AnalysisResult:
        price = random.uniform(10.0, 500.0)
        conf_label = random.choice(["low", "medium", "high"])
        conf = _CONFIDENCE_MAP[conf_label]
        trend_label = random.choice(["up", "down", "neutral"])
        outlook = _outlook_from_trend_label(trend_label)
        strength = random.uniform(0.4, 0.9)

        return AnalysisResult(
            ticker=ticker,
            analysis_status="ok",
            predicted_price=round(price, 2),
            confidence=round(conf, 2),
            confidence_label=conf_label,
            confidence_reasons=["Demo: Gerçek model bağlı değil"],
            outlook=outlook,
            outlook_strength=round(strength, 2),
            last_close=round(price * random.uniform(0.95, 1.05), 2),
            data_freshness="fresh",
            model_name="MockModel",
            model_family="demo",
            trend_label=trend_label,
            horizon_days=5,
            weekly_expected_return=round(random.uniform(-0.05, 0.08), 4),
            rmse=round(random.uniform(0.5, 3.0), 2),
            mae=round(random.uniform(0.3, 2.0), 2),
            directional_accuracy=round(random.uniform(45, 70), 1),
            composite_score=round(random.uniform(30, 80), 1),
            sharpe=round(random.uniform(-0.5, 1.5), 2),
            xai_available=True,
            xai_method="Demo SHAP",
            xai_features={
                "RSI": round(random.uniform(0.1, 0.9), 2),
                "MACD": round(random.uniform(0.1, 0.9), 2),
                "Hacim": round(random.uniform(0.1, 0.9), 2),
            },
            xai_positive_reasons=[
                XaiFactorItem("RSI_14", "RSI (14 gün)", round(random.uniform(0.1, 0.5), 3), "positive"),
            ],
            xai_negative_reasons=[
                XaiFactorItem("vol_20d", "Volatilite (20 gün)", round(random.uniform(0.1, 0.3), 3), "negative"),
            ],
            xai_text="Demo: Bu hisse için teknik göstergeler karışık bir tablo çiziyor.",
            xai_caveat="Demo verisi — gerçek model bağlandığında güncellenecek.",
            disclaimer="Bu çıktı demo amaçlıdır, yatırım tavsiyesi değildir.",
        )

    def is_available(self) -> bool:
        return False
