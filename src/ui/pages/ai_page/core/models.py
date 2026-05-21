from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal
from enum import Enum


class Signal(Enum):
    BUY  = "AL"
    SELL = "SAT"
    HOLD = "TUT"


class MessageRole(Enum):
    USER   = "user"
    AI     = "ai"
    SYSTEM = "system"


@dataclass
class ForecastPoint:
    """Tek bir tahmin noktası (gün bazlı)."""
    target_date: str
    horizon_index: int
    bounded_predicted_close: float | None = None
    predicted_return: float | None = None


@dataclass
class XaiFactorItem:
    """XAI'dan gelen tek bir özellik/faktör."""
    feature_name: str
    human_label: str
    importance: float
    direction: str          # "positive" veya "negative"


@dataclass
class AnalysisResult:
    """
    FastAPI /analysis/{symbol} endpoint'inden dönen zengin analiz payload'u.

    Eski MockAdapter uyumluluğu korunur; eklenen alanların tümü
    varsayılan değerlere sahiptir.
    """
    ticker: str

    # ── Analiz durumu ────────────────────────────────────────────────────
    analysis_status: str = "ok"                     # ok, stale_data, no_model, no_forecast, low_confidence, xai_unavailable, error

    # ── Tahmin ───────────────────────────────────────────────────────────
    predicted_price: float | None = None            # forecast.points[-1].bounded_predicted_close
    confidence: float = 0.0                         # 0.0 – 1.0 (label'dan türetilir)
    confidence_label: str = "low"                   # "low", "medium", "high"
    confidence_reasons: list[str] = field(default_factory=list)
    confidence_warnings: list[str] = field(default_factory=list)

    # ── Sinyal (şimdilik trend_label'dan doğrudan; türetim sonraya) ────
    signal: Signal = Signal.HOLD
    signal_strength: float = 0.0                    # 0.0 – 1.0

    # ── Veri bilgisi ─────────────────────────────────────────────────────
    last_close: float | None = None
    last_observed_date: str | None = None
    data_freshness: str = "unknown"                 # "fresh", "stale_data", "unknown"
    staleness_days: int = 0

    # ── Model bilgisi ────────────────────────────────────────────────────
    model_name: str = ""
    model_family: str = ""
    validation_mode: str | None = None
    trained_at: str | None = None
    eligibility_status: str = "eligible"

    # ── Forecast ─────────────────────────────────────────────────────────
    trend_label: str | None = None                  # "up", "down", "neutral"
    horizon_days: int | None = None
    weekly_expected_return: float | None = None
    forecast_points: list[ForecastPoint] = field(default_factory=list)

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
    timestamp: datetime = field(default_factory=datetime.now)
