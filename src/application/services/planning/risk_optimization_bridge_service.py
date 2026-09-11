"""
RiskOptimizationBridgeService — Risk Profili ↔ Optimizasyon Köprüsü (bkz. plan §5.3).

Kayıtlı risk anketi sonucunu (`RiskProfileService`) doğrudan Markowitz optimizasyonuna
(`OptimizationService`) bağlar: risk etiketine göre tek-hisse ağırlık üst sınırını
(`OptimizationPolicy.max_single_weight`) belirler ve optimizasyonu bu politikayla,
DI singleton'ın varsayılan politikasını değiştirmeden (per-call `policy` parametresi,
bkz. `optimization_service.py`) çalıştırır.

Not: `OptimizationService` yalnızca portföydeki mevcut hisseler arasında ağırlık dağıtır —
nakit/tahvil/fon gibi ayrı bir varlık sınıfı modellemez. Bu nedenle risk profilinin
"min %X nakit/tahvil" kısıtı burada mekanik bir kısıt DEĞİL, `PROFILE_INFO`'daki
`recommended_allocation["Hisse"]` üzerinden bilgilendirici bir tavan (`equity_ceiling_pct`)
olarak sunulur; tek mekanik olarak uygulanan kısıt tek-hisse ağırlık üst sınırıdır.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional

from src.application.services.planning.optimization_market_data import OptimizationPolicy
from src.application.services.planning.optimization_service import OptimizationService
from src.application.services.planning.risk_profile_service import RiskProfileService
from src.domain.models.optimization_result import OptimizationResult
from src.domain.models.risk_profile import PROFILE_INFO, RiskLabel, RiskProfile

# Plan §5.3: Muhafazakar tek-hisse max %10, Agresif tek-hisse max %35.
# Ara etiketler, mevcut PROFILE_INFO'daki artan max_volatility sıralamasıyla tutarlı ara değerler.
MAX_SINGLE_WEIGHT_BY_LABEL: Dict[str, float] = {
    RiskLabel.COK_MUHAFAZAKAR: 0.08,
    RiskLabel.MUHAFAZAKAR: 0.10,
    RiskLabel.DENGELI: 0.20,
    RiskLabel.BUYUME_ODAKLI: 0.28,
    RiskLabel.AGRESIF: 0.35,
}

_DEFAULT_RISK_LABEL = RiskLabel.DENGELI  # Kayıtlı profil yoksa uygulanan varsayılan.

# Muhafazakar->Agresif sıralı liste — OptimizationView'daki risk profili slider'ının
# adımları (bkz. plan §7.3 madde 5). MAX_SINGLE_WEIGHT_BY_LABEL ile aynı artan sıra.
RISK_LABELS_ORDERED: tuple[str, ...] = (
    RiskLabel.COK_MUHAFAZAKAR,
    RiskLabel.MUHAFAZAKAR,
    RiskLabel.DENGELI,
    RiskLabel.BUYUME_ODAKLI,
    RiskLabel.AGRESIF,
)


def max_single_weight_for_label(risk_label: str) -> float:
    """Risk etiketine göre tek-hisse ağırlık üst sınırını (0-1 arası) döner."""
    return MAX_SINGLE_WEIGHT_BY_LABEL.get(risk_label, OptimizationService.MAX_SINGLE_WEIGHT)


@dataclass(frozen=True)
class RiskAwareOptimizationResult:
    """Risk profiline göre kısıtlanmış optimizasyon sonucu + uygulanan politika bilgisi."""
    result: OptimizationResult
    risk_label: str
    max_single_weight_pct: float
    equity_ceiling_pct: Optional[int]  # recommended_allocation["Hisse"] — bilgi amaçlı, kısıt değil
    used_default_profile: bool  # kayıtlı profil yoktu, DENGELI varsayılanı uygulandı
    is_manual_override: bool = False  # slider ile kayıtlı profili geçici olarak ezen bir etiket verildi


class RiskOptimizationBridgeService:
    """Kayıtlı risk profiline göre tek-hisse ağırlık limiti kısıtlanmış Markowitz optimizasyonu çalıştırır."""

    def __init__(
        self,
        risk_profile_service: RiskProfileService,
        optimization_service: OptimizationService,
    ) -> None:
        self._risk_profile_service = risk_profile_service
        self._optimization_service = optimization_service

    def get_active_risk_profile(self) -> Optional[RiskProfile]:
        return self._risk_profile_service.get_current_profile()

    def optimize_dashboard_portfolio_with_risk_profile(
        self, risk_label_override: Optional[str] = None,
    ) -> RiskAwareOptimizationResult:
        return self._run_with_profile(
            lambda policy: self._optimization_service.optimize_dashboard_portfolio(policy=policy),
            risk_label_override,
        )

    def optimize_model_portfolio_with_risk_profile(
        self,
        portfolio_id: int,
        price_lookup_func=None,
        risk_label_override: Optional[str] = None,
    ) -> RiskAwareOptimizationResult:
        return self._run_with_profile(
            lambda policy: self._optimization_service.optimize_model_portfolio(
                portfolio_id, price_lookup_func, policy=policy,
            ),
            risk_label_override,
        )

    def _run_with_profile(
        self,
        run: Callable[[OptimizationPolicy], OptimizationResult],
        risk_label_override: Optional[str] = None,
    ) -> RiskAwareOptimizationResult:
        # Slider'dan gelen geçici geçersiz kılma (bkz. plan §7.3 madde 5) kayıtlı anket
        # profilini DEĞİŞTİRMEZ/KAYDETMEZ — sadece bu tek çağrı için politika hesaplanır
        # (mevcut `policy` per-call override deseniyle aynı ilke, bkz. modül dosya yorumu).
        if risk_label_override is not None and risk_label_override in MAX_SINGLE_WEIGHT_BY_LABEL:
            return self._run_with_label(run, risk_label_override, used_default_profile=False, is_manual_override=True)

        profile = self.get_active_risk_profile()
        risk_label = profile.risk_label if profile is not None else _DEFAULT_RISK_LABEL
        return self._run_with_label(run, risk_label, used_default_profile=profile is None, is_manual_override=False)

    def _run_with_label(
        self,
        run: Callable[[OptimizationPolicy], OptimizationResult],
        risk_label: str,
        used_default_profile: bool,
        is_manual_override: bool,
    ) -> RiskAwareOptimizationResult:
        max_weight = max_single_weight_for_label(risk_label)
        equity_ceiling = PROFILE_INFO.get(risk_label, {}).get("allocation", {}).get("Hisse")

        base_policy = self._optimization_service.policy
        policy = OptimizationPolicy(
            trading_days_per_year=base_policy.trading_days_per_year,
            risk_free_rate=base_policy.risk_free_rate,
            max_single_weight=max_weight,
        )
        result = run(policy)

        return RiskAwareOptimizationResult(
            result=result,
            risk_label=risk_label,
            max_single_weight_pct=max_weight * 100.0,
            equity_ceiling_pct=equity_ceiling,
            used_default_profile=used_default_profile,
            is_manual_override=is_manual_override,
        )
