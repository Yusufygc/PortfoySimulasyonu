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
class AnalysisResult:
    ticker: str
    predicted_price: float | None
    confidence: float           # 0.0 – 1.0
    signal: Signal
    signal_strength: float      # 0.0 – 1.0
    xai_features: dict[str, float]   # {"RSI": 0.34, "MACD": 0.21, ...}
    xai_text: str
    raw_output: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class ChatMessage:
    role: MessageRole
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
