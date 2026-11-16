"""AI_Core API v2 yanıtı: yön Kol-B peer bloğundan, bant havuz risk modelinden gelir."""
from __future__ import annotations

import math

from src.domain.models.ai_analysis import ModelOutlook
from src.infrastructure.ai.ai_core_fastapi_client import _parse_api_response

_V2 = {
    "api_version": "2",
    "symbol": "AKBNK",
    "analysis_status": "stale_data",
    "generated_at": "2026-11-16T03:00:00+03:00",
    "data": {"last_observed_date": "2026-09-16", "last_close": 65.0, "data_freshness": "stale_data", "staleness_days": 42},
    "confidence": {"label": "medium", "reasons": ["r"], "warnings": ["w"]},
    "serving_run": {"run_id": 7, "model_name": "GlobalPooledModel", "as_of_date": "2026-09-16"},
    "disclaimer": "yatırım tavsiyesi değildir",
    "peer": {
        "available": True,
        "peer_label": "inline",
        "trend_label": "yukarı",
        "trend_prob_up": 0.56,
        "trend_expected_return": 0.01,
        "kolb_price_p50": 65.6,
        "kolb_price_low": 59.5,
        "kolb_price_high": 72.4,
        "kolb_horizon_days": 5,
        "kolb_band_level": 0.8,
        "risk_sigma_5d": 0.09,
        "risk_level": "orta",
        "risk_method": "har_x_ridge",
        "xai_available": True,
        "xai_top_positive": [{"feature_name": "NATR_14", "human_label": "Oynaklık", "importance": 0.3}],
    },
}


def test_v2_maps_peer_and_risk_into_result():
    r = _parse_api_response(_V2)

    assert r.ticker == "AKBNK" and r.analysis_status == "stale_data"
    assert r.confidence_label == "medium" and r.confidence == 0.60
    assert r.model_name == "GlobalPooledModel" and r.trained_at == "2026-09-16"
    assert (r.predicted_price, r.predicted_price_low, r.predicted_price_high) == (65.6, 59.5, 72.4)
    assert r.interval_method == "har_x_ridge" and r.horizon_days == 5
    assert r.outlook is ModelOutlook.UP and r.trend_label == "yukarı"
    assert math.isclose(r.weekly_expected_return, math.expm1(0.01))
    assert r.peer.risk_level == "orta" and r.peer.risk_sigma_5d == 0.09
    assert r.xai_available and r.xai_positive_reasons[0].feature_name == "NATR_14"
    assert "Oynaklık" in r.xai_text


def test_v2_without_peer_block_is_neutral_and_empty():
    r = _parse_api_response({"symbol": "ZZZZ", "analysis_status": "no_data", "confidence": {"label": "low"}})

    assert r.analysis_status == "no_data" and r.peer is None
    assert r.predicted_price is None and r.outlook is ModelOutlook.NEUTRAL
    assert r.xai_features == {} and r.xai_text == ""
