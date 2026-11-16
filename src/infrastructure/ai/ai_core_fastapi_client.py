# -*- coding: utf-8 -*-
"""AI_Core (ts_forecasting_lab) FastAPI servisi ile haberleşen HTTP istemcisi
ve bu istemciyi `IAIAnalysisProvider` portuna bağlayan adapter.

Kullanıcıya gösterilecek hata metinleri burada sade tutulur; UI katmanı
gerekirse bunları L10N ile zenginleştirebilir. Bu modül UI'a bağımlı değildir.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Dict, List, Optional

import requests

from src.domain.models.ai_analysis import (
    AnalysisResult,
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


def _parse_float(block: dict, key: str) -> Optional[float]:
    val = block.get(key)
    try:
        return None if val is None else float(val)
    except (TypeError, ValueError):
        return None


def _parse_int_safe(val) -> Optional[int]:
    try:
        return None if val is None else int(val)
    except (TypeError, ValueError):
        return None


def _parse_peer(block: Optional[Dict[str, Any]]) -> Optional[PeerInfo]:
    """API `peer` bloğunu PeerInfo'ya taşır. Blok yok/boş ise None."""
    if not block:
        return None
    xai_pos = [_parse_xai_factor(f, "positive") for f in block.get("xai_top_positive", [])]
    xai_neg = [_parse_xai_factor(f, "negative") for f in block.get("xai_top_negative", [])]
    return PeerInfo(
        available=bool(block.get("available", False)),
        as_of_date=block.get("as_of_date"),
        peer_score=_parse_float(block, "peer_score"),
        peer_percentile=_parse_float(block, "peer_percentile"),
        peer_label=block.get("peer_label"),
        universe_size=_parse_int_safe(block.get("universe_size")),
        segment_liq=block.get("segment_liq"),
        segment_vol=block.get("segment_vol"),
        segment_sector=block.get("segment_sector"),
        segment_icir=_parse_float(block, "segment_icir"),
        confidence_label=block.get("confidence_label"),
        confidence_reasons=list(block.get("confidence_reasons") or []),
        confidence_warnings=list(block.get("confidence_warnings") or []),
        trend_label=block.get("trend_label"),
        trend_prob_up=_parse_float(block, "trend_prob_up"),
        trend_expected_return=_parse_float(block, "trend_expected_return"),
        kolb_price_p50=_parse_float(block, "kolb_price_p50"),
        kolb_price_low=_parse_float(block, "kolb_price_low"),
        kolb_price_high=_parse_float(block, "kolb_price_high"),
        kolb_horizon_days=_parse_int_safe(block.get("kolb_horizon_days")),
        kolb_band_level=_parse_float(block, "kolb_band_level"),
        risk_sigma_5d=_parse_float(block, "risk_sigma_5d"),
        risk_level=block.get("risk_level"),
        risk_method=block.get("risk_method"),
        ic_mean=_parse_float(block, "ic_mean"),
        icir_overall=_parse_float(block, "icir_overall"),
        pct_ic_positive=_parse_float(block, "pct_ic_positive"),
        risk_validation=dict(block.get("risk_validation") or {}),
        xai_available=bool(block.get("xai_available", False)),
        xai_method=block.get("xai_method") or "",
        xai_caveat=block.get("xai_caveat") or "",
        xai_top_positive=xai_pos,
        xai_top_negative=xai_neg,
    )


_OUTLOOK_BY_TREND = {
    "yukarı": ModelOutlook.UP,
    "up": ModelOutlook.UP,
    "aşağı": ModelOutlook.DOWN,
    "down": ModelOutlook.DOWN,
}


def _xai_text(xai_pos: List[XaiFactorItem], xai_neg: List[XaiFactorItem]) -> str:
    parts = []
    if xai_pos:
        parts.append(f"Akranlara göre sırayı yukarı iten en önemli faktör: {_xai_factor_summary(xai_pos[0])}")
    if xai_neg:
        parts.append(f"Sırayı aşağı çeken faktör: {_xai_factor_summary(xai_neg[0])}")
    return ". ".join(parts) + "." if parts else ""


def _parse_api_response(data: Dict[str, Any]) -> AnalysisResult:
    """FastAPI /analysis/{symbol} v2 yanıtını AnalysisResult'a dönüştürür.

    API v2'de hisse bazlı model/forecast/performance/xai blokları yoktur:
    yön ve göreli sinyal Kol-B `peer` bloğundan, fiyat bandı havuz risk
    modelinden (`peer.kolb_price_*`) gelir.
    """
    data_block = data.get("data") or {}
    conf_block = data.get("confidence") or {}
    run_block = data.get("serving_run") or {}
    conf_label = conf_block.get("label", "low")
    peer = _parse_peer(data.get("peer"))

    trend_label = peer.trend_label if peer else None
    expected_log_ret = peer.trend_expected_return if peer else None
    weekly_return = None if expected_log_ret is None else math.expm1(expected_log_ret)
    xai_pos = peer.xai_top_positive if peer else []
    xai_neg = peer.xai_top_negative if peer else []

    return AnalysisResult(
        ticker=data.get("symbol", ""),
        analysis_status=data.get("analysis_status", "error"),
        confidence=_CONFIDENCE_MAP.get(conf_label, 0.25),
        confidence_label=conf_label,
        confidence_reasons=conf_block.get("reasons", []),
        confidence_warnings=conf_block.get("warnings", []),
        last_close=data_block.get("last_close"),
        last_observed_date=data_block.get("last_observed_date"),
        data_freshness=data_block.get("data_freshness", "unknown"),
        staleness_days=data_block.get("staleness_days", 0),
        model_name=run_block.get("model_name") or "",
        model_family="pooled",
        trained_at=run_block.get("as_of_date"),
        disclaimer=data.get("disclaimer") or "",
        raw_output=data,
        generated_at=data.get("generated_at", ""),
        peer=peer,
        predicted_price=peer.kolb_price_p50 if peer else None,
        predicted_price_low=peer.kolb_price_low if peer else None,
        predicted_price_high=peer.kolb_price_high if peer else None,
        interval_method=(peer.risk_method or None) if peer else None,
        horizon_days=peer.kolb_horizon_days if peer else None,
        weekly_expected_return=weekly_return,
        outlook=_OUTLOOK_BY_TREND.get(str(trend_label or "").strip().lower(), ModelOutlook.NEUTRAL),
        outlook_strength=min(abs(weekly_return or 0.0) * 10, 1.0),
        trend_label=trend_label,
        xai_available=bool(peer and peer.xai_available),
        xai_method=peer.xai_method if peer else "",
        xai_caveat=peer.xai_caveat if peer else "",
        xai_features={(i.human_label or i.feature_name): i.importance for i in xai_pos + xai_neg},
        xai_positive_reasons=xai_pos,
        xai_negative_reasons=xai_neg,
        xai_text=_xai_text(xai_pos, xai_neg),
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
