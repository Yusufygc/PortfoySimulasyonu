# src/domain/models/risk_profile.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


class RiskLabel:
    """Risk profili etiket sabitleri."""
    MUHAFAZAKAR = "MUHAFAZAKAR"
    DENGELI = "DENGELİ"
    AGRESIF = "AGRESİF"


class Horizon:
    """Yatırım vadesi sabitleri."""
    SHORT = "short"
    MEDIUM = "medium"
    LONG = "long"


class Reaction:
    """Kayıp tepkisi sabitleri."""
    SELL = "sell"
    HOLD = "hold"
    BUY_MORE = "buy_more"


# Profil açıklamaları ve volatilite limitleri
PROFILE_INFO = {
    RiskLabel.MUHAFAZAKAR: {
        "description": "Düşük risk, sermaye koruma odaklı. Sabit getirili ve temettü hisseleri önerilir.",
        "max_volatility": 1.5,
        "color": "#3b82f6",        # Mavi
        "emoji": "🛡️",
    },
    RiskLabel.DENGELI: {
        "description": "Orta risk, dengeli büyüme odaklı. Çeşitlendirilmiş portföy önerilir.",
        "max_volatility": 2.5,
        "color": "#f59e0b",        # Turuncu
        "emoji": "⚖️",
    },
    RiskLabel.AGRESIF: {
        "description": "Yüksek risk, agresif büyüme odaklı. Volatil hisseler ve spekülatif pozisyonlar uygun.",
        "max_volatility": 5.0,
        "color": "#ef4444",        # Kırmızı
        "emoji": "🚀",
    },
}


@dataclass
class RiskProfile:
    """
    Yatırımcı risk profilini temsil eder.
    Anket sonuçları ve hesaplanan risk skoru/etiketi tutar.
    'risk_profiles' tablosunun domain karşılığı.
    """
    id: Optional[int]

    # Anket yanıtları
    age: int                            # Kullanıcı yaşı
    horizon: str                        # short / medium / long
    reaction: str                       # sell / hold / buy_more

    # Hesaplanan sonuç
    risk_score: int = 0                 # 0-100 arası puan
    risk_label: str = RiskLabel.DENGELI # MUHAFAZAKAR / DENGELİ / AGRESİF

    created_at: Optional[datetime] = None

    # ---------- Hesaplanan Özellikler ---------- #

    @property
    def description(self) -> str:
        """Profil açıklaması."""
        info = PROFILE_INFO.get(self.risk_label, {})
        return info.get("description", "Bilinmeyen profil.")

    @property
    def max_volatility(self) -> float:
        """Profil için önerilen maksimum volatilite."""
        info = PROFILE_INFO.get(self.risk_label, {})
        return info.get("max_volatility", 2.5)

    @property
    def color(self) -> str:
        """Profil renk kodu."""
        info = PROFILE_INFO.get(self.risk_label, {})
        return info.get("color", "#94a3b8")

    @property
    def emoji(self) -> str:
        """Profil emojisi."""
        info = PROFILE_INFO.get(self.risk_label, {})
        return info.get("emoji", "❓")

    @property
    def horizon_display(self) -> str:
        """Vade görüntüleme metni."""
        mapping = {
            Horizon.SHORT: "Kısa Vade (< 1 Ay)",
            Horizon.MEDIUM: "Orta Vade (1-12 Ay)",
            Horizon.LONG: "Uzun Vade (> 1 Yıl)",
        }
        return mapping.get(self.horizon, self.horizon)

    @property
    def reaction_display(self) -> str:
        """Tepki görüntüleme metni."""
        mapping = {
            Reaction.SELL: "Satarım (Korumacı)",
            Reaction.HOLD: "Beklerim (Sabırlı)",
            Reaction.BUY_MORE: "Daha Çok Alırım (Cesur)",
        }
        return mapping.get(self.reaction, self.reaction)
