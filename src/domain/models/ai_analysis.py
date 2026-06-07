"""AI analiz ve sohbet alanına ait saf domain modelleri.

Bu modül hiçbir dış bağımlılık (PyQt, requests, SDK, L10N) içermez.
Kullanıcıya gösterilecek Türkçe etiketler UI katmanında
(`src/ui/pages/ai_page/labels.py`) üretilir; burada yalnızca anlamsal
(semantic) değerler tutulur.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ModelOutlook(Enum):
    """Model yön beklentisi — emir dili değil, analitik görünüm.

    Değerler anlamsaldır; kullanıcıya dönük Türkçe etiket için
    `src/ui/pages/ai_page/labels.py::outlook_label` kullanılır.
    """

    UP = "up"
    DOWN = "down"
    NEUTRAL = "neutral"


class MessageRole(Enum):
    USER = "user"
    AI = "ai"
    SYSTEM = "system"


@dataclass
class ForecastPoint:
    """Tek bir tahmin noktası (gün bazlı)."""

    target_date: str
    horizon_index: int
    bounded_predicted_close: float | None = None
    predicted_return: float | None = None
    # Olasılıksal aralık (B2 residual / C conformal). Yoksa None (geriye uyumlu).
    p10_close: float | None = None
    p50_close: float | None = None
    p90_close: float | None = None
    predicted_return_p10: float | None = None
    predicted_return_p50: float | None = None
    predicted_return_p90: float | None = None
    interval_method: str | None = None  # quantile_model | residual_b2 | conformal


@dataclass
class XaiFactorItem:
    """XAI'dan gelen tek bir özellik/faktör."""

    feature_name: str
    human_label: str
    importance: float
    direction: str  # "positive" veya "negative"
    feature_group: str | None = None
    reason: str | None = None
    method: str | None = None
    contribution: float | None = None
    approximate: bool | None = None


@dataclass
class PeerInfo:
    """Kol-B (pooled global model) cross-sectional akran çıktısı.

    Kaynak: AI_Core `/analysis/{symbol}` yanıtının `peer` bloğu (nightly batch →
    PeerStore). Mutlak forecast'tan ayrı, akran-göreli (cross-sectional) bakış.
    Tüm alanlar opsiyonel — peer yoksa `available=False`.
    """

    available: bool = False
    as_of_date: str | None = None
    peer_score: float | None = None       # -1..1 merkezli cross-sectional sıra
    peer_percentile: float | None = None  # 0..100
    peer_label: str | None = None         # outperform | inline | underperform | unknown
    universe_size: int | None = None
    segment_liq: str | None = None
    segment_vol: str | None = None
    segment_sector: str | None = None
    segment_icir: float | None = None
    confidence_label: str | None = None   # low | medium | high
    confidence_reasons: list[str] = field(default_factory=list)
    confidence_warnings: list[str] = field(default_factory=list)
    # Kalibre akran-rank → mutlak trend eğilimi (olasılıksal)
    trend_label: str | None = None             # yukarı | yatay | aşağı | belirsiz
    trend_prob_up: float | None = None         # P(h-gün getiri > 0)
    trend_expected_return: float | None = None  # ort. h-gün log-getiri
    # Kol-B pooled fiyat bandı
    kolb_price_p50: float | None = None
    kolb_price_low: float | None = None
    kolb_price_high: float | None = None
    kolb_horizon_days: int | None = None
    kolb_band_level: float | None = None
    # Kol-B XAI — pooled modelin per-symbol sıra sürücüleri (SHAP)
    xai_available: bool = False
    xai_method: str = ""
    xai_caveat: str = ""
    xai_top_positive: list["XaiFactorItem"] = field(default_factory=list)
    xai_top_negative: list["XaiFactorItem"] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """FastAPI /analysis/{symbol} endpoint'inden dönen zengin analiz payload'u.

    Eklenen alanların tümü varsayılan değerlere sahiptir; eski demo/mock
    uyumluluğu korunur. `disclaimer` varsayılanı boştur — kullanıcıya dönük
    varsayılan metin UI katmanında doldurulur.
    """

    ticker: str

    # ── Analiz durumu ────────────────────────────────────────────────────
    analysis_status: str = "ok"  # ok, stale_data, no_model, no_forecast, low_confidence, xai_unavailable, error

    # ── Tahmin ───────────────────────────────────────────────────────────
    predicted_price: float | None = None
    confidence: float = 0.0  # 0.0 – 1.0
    confidence_label: str = "low"  # "low", "medium", "high"
    confidence_reasons: list[str] = field(default_factory=list)
    confidence_warnings: list[str] = field(default_factory=list)

    # ── Yön beklentisi ───────────────────────────────────────────────────
    outlook: ModelOutlook = ModelOutlook.NEUTRAL
    outlook_strength: float = 0.0  # 0.0 – 1.0

    # ── Veri bilgisi ─────────────────────────────────────────────────────
    last_close: float | None = None
    last_observed_date: str | None = None
    data_freshness: str = "unknown"  # "fresh", "stale_data", "unknown"
    staleness_days: int = 0

    # ── Model bilgisi ────────────────────────────────────────────────────
    model_name: str = ""
    model_family: str = ""
    validation_mode: str | None = None
    trained_at: str | None = None
    eligibility_status: str = "eligible"

    # ── Forecast ─────────────────────────────────────────────────────────
    trend_label: str | None = None  # "up", "down", "neutral"
    horizon_days: int | None = None
    weekly_expected_return: float | None = None
    forecast_points: list[ForecastPoint] = field(default_factory=list)

    # ── Olasılıksal tahmin aralığı (horizon sonu p10/p90) ────────────────
    predicted_price_low: float | None = None   # son nokta p10_close
    predicted_price_high: float | None = None  # son nokta p90_close
    interval_method: str | None = None         # quantile_model | residual_b2 | conformal

    # ── Performans ───────────────────────────────────────────────────────
    rmse: float | None = None
    mae: float | None = None
    directional_accuracy: float | None = None
    hit_rate: float | None = None
    composite_score: float | None = None
    sharpe: float | None = None
    stability_score: float | None = None

    # ── XAI ──────────────────────────────────────────────────────────────
    xai_available: bool = False
    xai_method: str = ""
    xai_features: dict[str, float] = field(default_factory=dict)
    xai_positive_reasons: list[XaiFactorItem] = field(default_factory=list)
    xai_negative_reasons: list[XaiFactorItem] = field(default_factory=list)
    xai_text: str = ""
    xai_caveat: str = ""
    xai_model_family_caveat: str = ""

    # ── Kol-B akran (cross-sectional) ────────────────────────────────────
    peer: "PeerInfo | None" = None

    # ── Uyarı ────────────────────────────────────────────────────────────
    disclaimer: str = ""

    # ── Ham veri & zaman damgası ─────────────────────────────────────────
    raw_output: dict = field(default_factory=dict)
    generated_at: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ChatMessage:
    role: MessageRole
    content: str
    display_content: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ChatSession:
    id: str
    title: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
