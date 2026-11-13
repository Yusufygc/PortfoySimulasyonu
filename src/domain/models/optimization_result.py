# src/domain/models/optimization_result.py

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class OptimizationMetrics:
    """
    Portföy optimizasyonu metriklerini temsil eder.
    Beklenen getiri, volatilite ve Sharpe oranı değerlerini tutar.
    """
    expected_return: float      # Yıllıklandırılmış beklenen getiri
    volatility: float           # Yıllıklandırılmış volatilite (risk)
    sharpe_ratio: float         # Sharpe oranı


@dataclass(frozen=True)
class OptimizationSuggestion:
    """
    Tek bir hisse için optimizasyon önerisini temsil eder.
    Mevcut ve optimal ağırlıklar arasındaki farkı ve aksiyon önerisini tutar.
    """
    symbol: str                 # Hisse sembolü (örn: ASELS.IS)
    current_weight: float       # Mevcut ağırlık (%)
    optimal_weight: float       # Önerilen optimal ağırlık (%)
    change: float               # Fark (optimal - mevcut) (%)
    action: str                 # Aksiyon: "EKLE", "AZALT", "TUT"


@dataclass(frozen=True)
class OptimizationResult:
    """
    Portföy optimizasyonu sonucunu temsil eden domain modeli.
    Mevcut ve optimize edilmiş metrikleri ve hisse bazlı önerileri içerir.
    """
    current_metrics: OptimizationMetrics
    optimized_metrics: OptimizationMetrics
    suggestions: List[OptimizationSuggestion]
    # Verimli Sınır (Efficient Frontier) grafiğinin 3. noktası — minimum volatilite portföyü
    # (bkz. plan §7.3 madde 5, AnalyticsView'daki OptimizationView). Opsiyonel/varsayılan None:
    # mevcut çağıranlar (QtWidgets OptimizationPage) bu alanı hiç bilmiyor, geriye dönük kırmaz.
    min_volatility_metrics: Optional[OptimizationMetrics] = None
