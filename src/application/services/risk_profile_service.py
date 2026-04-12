# src/application/services/risk_profile_service.py

from __future__ import annotations

from typing import Optional

from src.domain.models.risk_profile import (
    RiskProfile,
    RiskLabel,
    Horizon,
    Reaction,
    PROFILE_INFO,
)
from src.domain.ports.repositories.i_risk_profile_repo import IRiskProfileRepository


class RiskProfileService:
    """
    Risk Profili iş mantığı servisi.

    Kullanıcı anket yanıtlarından risk skoru hesaplar, profil etiketler
    ve DB'ye kaydeder. YKDS RiskManager mantığı korunmuştur.

    Skor hesaplama:
        - Yaş: <30 → 30 puan, 30-50 → 20, >50 → 10
        - Vade: long → 30, medium → 20, short → 10
        - Tepki: buy_more → 40, hold → 20, sell → 0
        - Toplam max: 100

    Profil etiketleri:
        - <40: MUHAFAZAKAR
        - 40-75: DENGELİ
        - >75: AGRESİF
    """

    def __init__(self, risk_profile_repo: IRiskProfileRepository) -> None:
        self._repo = risk_profile_repo

    def get_current_profile(self) -> Optional[RiskProfile]:
        """En son kaydedilen risk profilini döner."""
        return self._repo.get_latest_profile()

    def calculate_and_save_profile(
        self,
        age: int,
        horizon: str,
        reaction: str,
    ) -> RiskProfile:
        """
        Anket yanıtlarından risk profilini hesaplar ve kaydeder.

        Args:
            age: Kullanıcı yaşı
            horizon: Yatırım vadesi (short / medium / long)
            reaction: %20 düşüşe tepki (sell / hold / buy_more)

        Returns:
            Kaydedilen RiskProfile
        """
        if age <= 0:
            raise ValueError("Yaş pozitif olmalıdır.")

        score = self._calculate_score(age, horizon, reaction)
        label = self._score_to_label(score)

        profile = RiskProfile(
            id=None,
            age=age,
            horizon=horizon,
            reaction=reaction,
            risk_score=score,
            risk_label=label,
        )

        return self._repo.save_profile(profile)

    @staticmethod
    def _calculate_score(age: int, horizon: str, reaction: str) -> int:
        """
        Risk skorunu hesaplar.

        YKDS RiskManager.calculate_risk_profile() mantığı:
            - Yaş faktörü (gençler daha çok risk alabilir)
            - Vade faktörü (uzun vade = daha çok risk toleransı)
            - Kayıp tepkisi (en önemli faktör, %40 ağırlık)
        """
        score = 0

        # 1. Yaş Faktörü
        if age < 30:
            score += 30
        elif age < 50:
            score += 20
        else:
            score += 10

        # 2. Vade Faktörü
        if horizon == Horizon.LONG:
            score += 30
        elif horizon == Horizon.MEDIUM:
            score += 20
        else:
            score += 10

        # 3. Kayıp Tepkisi (En ağırlıklı)
        if reaction == Reaction.BUY_MORE:
            score += 40
        elif reaction == Reaction.HOLD:
            score += 20
        elif reaction == Reaction.SELL:
            score += 0

        return score

    @staticmethod
    def _score_to_label(score: int) -> str:
        """Skordan profil etiketi türetir."""
        if score < 40:
            return RiskLabel.MUHAFAZAKAR
        elif score > 75:
            return RiskLabel.AGRESIF
        else:
            return RiskLabel.DENGELI
