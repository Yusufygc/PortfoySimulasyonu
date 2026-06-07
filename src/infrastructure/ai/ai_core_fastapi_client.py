# -*- coding: utf-8 -*-
"""AI_Core (ts_forecasting_lab) FastAPI servisi ile haberleşen HTTP istemcisi
ve bu istemciyi `IAIAnalysisProvider` portuna bağlayan adapter.

Kullanıcıya gösterilecek hata metinleri burada sade tutulur; UI katmanı
gerekirse bunları L10N ile zenginleştirebilir. Bu modül UI'a bağımlı değildir.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import requests

from src.domain.models.ai_analysis import (
    AnalysisResult,
    ForecastPoint,
    ModelOutlook,
    PeerInfo,
    XaiFactorItem,
)
from src.domain.ports.services.i_ai_analysis_provider import IAIAnalysisProvider

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://localhost:8000"
_DEFAULT_TIMEOUT = 15  # saniye

# Güven etiketi → sayısal değer eşleme
_CONFIDENCE_MAP = {"low": 0.25, "medium": 0.60, "high": 0.85}


class APIConnectionError(Exception):
    """FastAPI sunucusuna bağlanılamadığında fırlatılır."""


class APIResponseError(Exception):
    """Sunucu başarısız HTTP durum kodu döndürdüğünde fırlatılır."""

    def __init__(self, status_code: int, detail: str = ""):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"HTTP {status_code}: {detail}")


# ─────────────────────────────────────────────────────────────────────────────
# HTTP istemci
# ─────────────────────────────────────────────────────────────────────────────


class AICoreFastAPIClient:
    """ts_forecasting_lab FastAPI servisiyle haberleşen HTTP istemcisi."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: int = _DEFAULT_TIMEOUT,
        log_connection_errors: bool = True,
    ) -> None:
        raw_url = base_url or _DEFAULT_BASE_URL
        self.base_url = raw_url.rstrip("/")
        self.timeout = timeout
        self._log_connection_errors = log_connection_errors
        self._session = requests.Session()

    def health_check(self) -> bool:
        """GET /health — servis erişilebilir mi?

        Bağlantı/sunucu hatalarında False döner; istisnayı yutarak UI
        tarafında fallback mekanizmasına izin verir.
        """
        try:
            resp = self._get("/health")
            return resp.get("status") in ("ok", "degraded")
        except Exception:
            logger.debug("AI_Core health check başarısız")
            return False

    def get_analysis(self, symbol: str) -> Dict[str, Any]:
        """GET /analysis/{symbol} — tam analiz payload'unu döner."""
        return self._get(f"/analysis/{symbol.upper()}")

    def get_symbols(self) -> List[str]:
        """GET /symbols — kayıtlı hisse kodlarını döner."""
        data = self._get("/symbols")
        return data.get("symbols", [])

    def get_best_model(self, symbol: str) -> Dict[str, Any]:
        """GET /best-model/{symbol} — en iyi model bilgisini döner."""
        return self._get(f"/best-model/{symbol.upper()}")

    def get_leaderboard(self, top_n: int = 20) -> Dict[str, Any]:
        """GET /leaderboard — hisseler arası lider tablosu."""
        return self._get("/leaderboard", params={"top_n": top_n})

    def _get(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """GET isteği gönderir; hata yönetimini merkezleştirir."""
        url = f"{self.base_url}{path}"
        try:
            resp = self._session.get(url, params=params, timeout=self.timeout)
        except requests.ConnectionError as exc:
            if self._log_connection_errors:
                logger.warning("AI_Core connection failed: url=%s", url, exc_info=True)
            else:
                logger.debug("AI_Core connection failed: url=%s", url)
            raise APIConnectionError(
                f"AI_Core sunucusuna bağlanılamadı ({url}). "
                "Sunucunun çalıştığından emin olun."
            ) from exc
        except requests.Timeout as exc:
            if self._log_connection_errors:
                logger.warning("AI_Core request timed out: url=%s timeout=%s", url, self.timeout, exc_info=True)
            else:
                logger.debug("AI_Core request timed out: url=%s timeout=%s", url, self.timeout)
            raise APIConnectionError(
                f"AI_Core isteği zaman aşımına uğradı ({self.timeout}s): {url}"
            ) from exc

        if resp.status_code >= 400:
            detail = ""
            try:
                body = resp.json()
                detail = body.get("detail", str(body))
            except Exception:
                detail = resp.text[:200]
            logger.error("AI_Core response error: url=%s status_code=%s detail=%s", url, resp.status_code, detail)
            raise APIResponseError(resp.status_code, detail)

        try:
            return resp.json()
        except ValueError as exc:
            logger.error("AI_Core returned invalid JSON: url=%s", url, exc_info=True)
            raise APIResponseError(resp.status_code, "Geçersiz JSON yanıtı") from exc


# ─────────────────────────────────────────────────────────────────────────────
# Payload → domain dönüşümü
# ─────────────────────────────────────────────────────────────────────────────


def _parse_xai_factor(raw: Dict[str, Any], default_direction: str) -> XaiFactorItem:
    """API XAI faktörünü domain modeline geriye uyumlu biçimde taşır."""
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


def _parse_peer(block: Optional[Dict[str, Any]]) -> Optional[PeerInfo]:
    """API `peer` bloğunu PeerInfo'ya taşır. Blok yok/boş ise None."""
    if not block:
        return None

    def _f(key: str) -> Optional[float]:
        val = block.get(key)
        try:
            return None if val is None else float(val)
        except (TypeError, ValueError):
            return None

    xai_pos = [_parse_xai_factor(f, "positive") for f in block.get("xai_top_positive", [])]
    xai_neg = [_parse_xai_factor(f, "negative") for f in block.get("xai_top_negative", [])]
    universe = block.get("universe_size")
    try:
        universe = None if universe is None else int(universe)
    except (TypeError, ValueError):
        universe = None
    horizon = block.get("kolb_horizon_days")
    try:
        horizon = None if horizon is None else int(horizon)
    except (TypeError, ValueError):
        horizon = None
    return PeerInfo(
        available=bool(block.get("available", False)),
        as_of_date=block.get("as_of_date"),
        peer_score=_f("peer_score"),
        peer_percentile=_f("peer_percentile"),
        peer_label=block.get("peer_label"),
        universe_size=universe,
        segment_liq=block.get("segment_liq"),
        segment_vol=block.get("segment_vol"),
        segment_sector=block.get("segment_sector"),
        segment_icir=_f("segment_icir"),
        confidence_label=block.get("confidence_label"),
        confidence_reasons=list(block.get("confidence_reasons", []) or []),
        confidence_warnings=list(block.get("confidence_warnings", []) or []),
        trend_label=block.get("trend_label"),
        trend_prob_up=_f("trend_prob_up"),
        trend_expected_return=_f("trend_expected_return"),
        kolb_price_p50=_f("kolb_price_p50"),
        kolb_price_low=_f("kolb_price_low"),
        kolb_price_high=_f("kolb_price_high"),
        kolb_horizon_days=horizon,
        kolb_band_level=_f("kolb_band_level"),
        xai_available=bool(block.get("xai_available", False)),
        xai_method=block.get("xai_method", "") or "",
        xai_caveat=block.get("xai_caveat", "") or "",
        xai_top_positive=xai_pos,
        xai_top_negative=xai_neg,
    )


def _outlook_from_trend_label(trend_label: str | None) -> ModelOutlook:
    trend_norm = str(trend_label or "").strip().lower()
    if trend_norm == "up":
        return ModelOutlook.UP
    if trend_norm == "down":
        return ModelOutlook.DOWN
    return ModelOutlook.NEUTRAL


def _parse_api_response(data: Dict[str, Any]) -> AnalysisResult:
    """FastAPI /analysis/{symbol} JSON yanıtını AnalysisResult'a dönüştürür."""
    data_block = data.get("data", {})
    model_block = data.get("model", {})
    forecast_block = data.get("forecast", {})
    perf_block = data.get("performance", {})
    conf_block = data.get("confidence", {})
    xai_block = data.get("xai", {})

    conf_label = conf_block.get("label", "low")
    conf_numeric = _CONFIDENCE_MAP.get(conf_label, 0.25)

    peer_info = _parse_peer(data.get("peer"))

    raw_points = forecast_block.get("points", [])
    forecast_points = [
        ForecastPoint(
            target_date=str(p.get("target_date", "")),
            horizon_index=int(p.get("horizon_index", 0)),
            bounded_predicted_close=p.get("bounded_predicted_close"),
            predicted_return=p.get("predicted_return"),
            p10_close=p.get("p10_close"),
            p50_close=p.get("p50_close"),
            p90_close=p.get("p90_close"),
            predicted_return_p10=p.get("predicted_return_p10"),
            predicted_return_p50=p.get("predicted_return_p50"),
            predicted_return_p90=p.get("predicted_return_p90"),
            interval_method=p.get("interval_method"),
        )
        for p in raw_points
    ]

    predicted_price = None
    predicted_price_low = None
    predicted_price_high = None
    interval_method = None
    if forecast_points:
        last_point = forecast_points[-1]
        predicted_price = last_point.bounded_predicted_close
        predicted_price_low = last_point.p10_close
        predicted_price_high = last_point.p90_close
        interval_method = last_point.interval_method

    trend_label = forecast_block.get("trend_label")
    trend_norm = str(trend_label or "").strip().lower()
    outlook = _outlook_from_trend_label(trend_label)
    outlook_strength = min(abs(forecast_block.get("weekly_expected_return", 0) or 0) * 10, 1.0)

    xai_pos = [
        _parse_xai_factor(f, "positive")
        for f in xai_block.get("top_positive_reasons", [])
    ]
    xai_neg = [
        _parse_xai_factor(f, "negative")
        for f in xai_block.get("top_negative_reasons", [])
    ]

    xai_features: Dict[str, float] = {}
    for item in xai_pos + xai_neg:
        label = item.human_label or item.feature_name
        xai_features[label] = item.importance

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
        predicted_price_low=predicted_price_low,
        predicted_price_high=predicted_price_high,
        interval_method=interval_method,
        peer=peer_info,
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
        disclaimer=data.get("disclaimer") or "",
        raw_output=data,
        generated_at=data.get("generated_at", ""),
    )


# ─────────────────────────────────────────────────────────────────────────────
# Provider adapter
# ─────────────────────────────────────────────────────────────────────────────


class FastAPIAnalysisProvider(IAIAnalysisProvider):
    """AI_Core FastAPI servisinden gerçek model analiz verisini çeker."""

    def __init__(self, client: AICoreFastAPIClient) -> None:
        self._client = client

    def analyze(self, ticker: str) -> AnalysisResult:
        raw = self._client.get_analysis(ticker)
        return _parse_api_response(raw)

    def is_available(self) -> bool:
        return self._client.health_check()
