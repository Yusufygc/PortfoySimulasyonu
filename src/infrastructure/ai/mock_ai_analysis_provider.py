# -*- coding: utf-8 -*-
"""Gerçek model/servis erişilemezken kullanılan demo analiz sağlayıcısı.

`is_available()` daima False döner; böylece UI demo (sarı) uyarısını gösterir.
Bu modül UI'a bağımlı değildir; demo metinleri sade tutulur.
"""

from __future__ import annotations

import random

from src.domain.models.ai_analysis import AnalysisResult, ModelOutlook, XaiFactorItem
from src.domain.ports.services.i_ai_analysis_provider import IAIAnalysisProvider

_CONFIDENCE_MAP = {"low": 0.25, "medium": 0.60, "high": 0.85}
_OUTLOOK_BY_TREND = {"up": ModelOutlook.UP, "down": ModelOutlook.DOWN, "neutral": ModelOutlook.NEUTRAL}


class MockAIAnalysisProvider(IAIAnalysisProvider):
    """Gerçekçi rastgele veri üreten demo sağlayıcı."""

    def analyze(self, ticker: str) -> AnalysisResult:
        price = random.uniform(10.0, 500.0)
        conf_label = random.choice(["low", "medium", "high"])
        conf = _CONFIDENCE_MAP[conf_label]
        trend_label = random.choice(["up", "down", "neutral"])
        outlook = _OUTLOOK_BY_TREND[trend_label]
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
