# src/domain/models/risk_profile.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional


class RiskLabel:
    """Risk profili etiket sabitleri."""

    COK_MUHAFAZAKAR = "COK_MUHAFAZAKAR"
    MUHAFAZAKAR = "MUHAFAZAKAR"
    DENGELI = "DENGELI"
    BUYUME_ODAKLI = "BUYUME_ODAKLI"
    AGRESIF = "AGRESIF"


class Horizon:
    """Yatirim vadesi sabitleri."""

    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class Reaction:
    """Kayip tepkisi sabitleri."""

    SELL = "sell"
    HOLD = "hold"
    BUY_MORE = "buy_more"


PROFILE_INFO = {
    RiskLabel.COK_MUHAFAZAKAR: {
        "description": "Sermaye koruma ve likidite onceliklidir. Dalgalanmasi dusuk, kademeli yatirim yaklasimi uygundur.",
        "max_volatility": 1.0,
        "allocation": {"Nakit": 25, "Tahvil/Bono": 45, "Fon": 20, "Hisse": 10, "Alternatif": 0},
    },
    RiskLabel.MUHAFAZAKAR: {
        "description": "Sinirli dalgalanma kabul edilir; ana hedef varligi korurken olculu getiri aramaktir.",
        "max_volatility": 1.5,
        "allocation": {"Nakit": 15, "Tahvil/Bono": 40, "Fon": 25, "Hisse": 20, "Alternatif": 0},
    },
    RiskLabel.DENGELI: {
        "description": "Getiri ve risk dengesi on plandadir. Cesitlendirilmis, orta vadeli portfoy yapisi uygundur.",
        "max_volatility": 2.5,
        "allocation": {"Nakit": 10, "Tahvil/Bono": 25, "Fon": 30, "Hisse": 30, "Alternatif": 5},
    },
    RiskLabel.BUYUME_ODAKLI: {
        "description": "Uzun vadeli buyume icin yuksek oynaklik tolere edilebilir; hisse ve fon agirligi artabilir.",
        "max_volatility": 3.5,
        "allocation": {"Nakit": 5, "Tahvil/Bono": 15, "Fon": 30, "Hisse": 45, "Alternatif": 5},
    },
    RiskLabel.AGRESIF: {
        "description": "Yuksek getiri hedefiyle belirgin fiyat dalgalanmalari kabul edilir; disiplinli risk limiti kritik hale gelir.",
        "max_volatility": 5.0,
        "allocation": {"Nakit": 5, "Tahvil/Bono": 5, "Fon": 25, "Hisse": 55, "Alternatif": 10},
    },
}

VALID_HORIZONS = {Horizon.SHORT, Horizon.MEDIUM, Horizon.LONG}
VALID_REACTIONS = {Reaction.SELL, Reaction.HOLD, Reaction.BUY_MORE}


@dataclass
class RiskProfile:
    """Yatirimci risk profilini ve profesyonel anket sonucunu temsil eder."""

    id: Optional[int]

    age: int
    horizon: str
    reaction: str

    risk_score: int = 0
    risk_label: str = RiskLabel.DENGELI

    questionnaire_version: str = "legacy"
    answers: Dict[str, str] = field(default_factory=dict)
    dimension_scores: Dict[str, int] = field(default_factory=dict)
    recommended_allocation: Dict[str, int] = field(default_factory=dict)
    suitability_notes: List[str] = field(default_factory=list)

    created_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        if self.age < 0:
            raise ValueError("Age cannot be negative")

        if self.horizon not in VALID_HORIZONS:
            raise ValueError(f"Unknown investment horizon: {self.horizon}")

        if self.reaction not in VALID_REACTIONS:
            raise ValueError(f"Unknown loss reaction: {self.reaction}")

        if self.risk_score < 0:
            raise ValueError("Risk score cannot be negative")

        if self.risk_label not in PROFILE_INFO:
            raise ValueError(f"Unknown risk label: {self.risk_label}")

        if not self.recommended_allocation:
            self.recommended_allocation = dict(PROFILE_INFO[self.risk_label]["allocation"])

    @property
    def description(self) -> str:
        info = PROFILE_INFO.get(self.risk_label, {})
        return info.get("description", "Bilinmeyen profil.")

    @property
    def max_volatility(self) -> float:
        info = PROFILE_INFO.get(self.risk_label, {})
        return info.get("max_volatility", 2.5)

    @property
    def horizon_display(self) -> str:
        mapping = {
            Horizon.SHORT: "Kisa Vade (< 1 Ay)",
            Horizon.MEDIUM: "Orta Vade (1-12 Ay)",
            Horizon.LONG: "Uzun Vade (> 1 Yil)",
        }
        return mapping.get(self.horizon, self.horizon)

    @property
    def reaction_display(self) -> str:
        mapping = {
            Reaction.SELL: "Satarim (Korumaci)",
            Reaction.HOLD: "Beklerim (Sabirli)",
            Reaction.BUY_MORE: "Daha Cok Alirim (Cesur)",
        }
        return mapping.get(self.reaction, self.reaction)
