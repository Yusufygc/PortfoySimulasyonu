from src.ui.shared.locale_tr import L10N
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


DEFAULT_INVESTMENT_DISCLAIMER = (
    L10N.BU_CIKTI_KISISEL_YATIRIM_TAVSIYESI +
    L10N.MODEL_GECMIS_VERILERDEN_URETILMIS_ANALITIK +
    L10N.NIHAI_KARAR_KULLANICIYA_AITTIR
)


class ModelOutlook(Enum):
    UP = L10N.YUKSELIS_EGILIMI
    DOWN = L10N.DUSUS_EGILIMI
    NEUTRAL = "Yatay/Nötr görünüm"


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
    feature_group: str | None = None
    reason: str | None = None
    method: str | None = None
    contribution: float | None = None
    approximate: bool | None = None


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

    # ── Yön beklentisi (trend_label'dan türetilen kullanıcı-facing görünüm) ──
    outlook: ModelOutlook = ModelOutlook.NEUTRAL
    outlook_strength: float = 0.0                   # 0.0 – 1.0

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
    display_content: str | None = None
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ChatSession:
    id: str
    title: str
    messages: list[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
