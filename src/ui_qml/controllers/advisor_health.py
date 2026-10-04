"""Portföy Sağlık Skoru (0-100) ve XAI risk faktörleri: eşik tabloları ve hesap.

Saf fonksiyonlardır; yalnızca `get_allocation_and_risk` aracının çıktı sözlüğünü kullanır.
"""
from __future__ import annotations

from typing import Any, Dict, List, Sequence, Tuple

_FACTOR_MAX = 25
_GOOD_SCORE = 18

# (üst sınır, puan, durum); sınırı aşan değerler son satırdaki varsayılana düşer.
_DIVERSITY_BANDS = ((40.0, 25, "Yüksek Çeşitlilik"), (60.0, 20, "Dengeli Dağılım"), (80.0, 12, "Orta Yoğunlaşma"))
_DIVERSITY_DEFAULT = (6, "Yüksek Yoğunlaşma Riski")
_VOLATILITY_BANDS = ((22.0, 25, "Düşük Volatilite"), (32.0, 20, "Piyasa Ortalaması"), (42.0, 14, "Yüksek Dalgalanma"))
_VOLATILITY_DEFAULT = (8, "Aşırı Riskli")
_DRAWDOWN_BANDS = ((15.0, 25, "Mükemmel Koruma"), (25.0, 20, "Normal Geri Çekilme"), (35.0, 14, "Yüksek Kayıp Riski"))
_DRAWDOWN_DEFAULT = (8, "Kritik Düşüş Seviyesi")
# (alt sınır, puan, durum); sınırın altındaki değerler son satırdaki varsayılana düşer.
_SHARPE_BANDS = ((1.5, 25, "Mükemmel Getiri/Risk"), (1.0, 20, "İyi Performans"), (0.5, 14, "Kabul Edilebilir"))
_SHARPE_DEFAULT = (8, "Düşük Getiri Verimi")

_LABEL_BANDS = ((80, "Çok Güçlü"), (65, "Dengeli"), (50, "Orta Risk"))
_LABEL_DEFAULT = "Yüksek Risk"


def _score_at_most(value: float, bands: Sequence[Tuple[float, int, str]], default: Tuple[int, str]) -> Tuple[int, str]:
    for limit, score, status in bands:
        if value <= limit:
            return score, status
    return default


def _score_at_least(value: float, bands: Sequence[Tuple[float, int, str]], default: Tuple[int, str]) -> Tuple[int, str]:
    for limit, score, status in bands:
        if value >= limit:
            return score, status
    return default


def _factor(title: str, value: str, scored: Tuple[int, str]) -> Dict[str, Any]:
    score, status = scored
    return {"title": title, "value": value, "score": score, "maxScore": _FACTOR_MAX, "status": status, "isGood": score >= _GOOD_SCORE}


def _overall_label(score: int) -> str:
    for limit, label in _LABEL_BANDS:
        if score >= limit:
            return label
    return _LABEL_DEFAULT


def compute_health(risk_data: Dict[str, Any]) -> Tuple[int, str, List[Dict[str, Any]]]:
    """`(genel puan, etiket, faktör listesi)`; eksik veriler için ılımlı varsayılanlar kullanılır."""
    top3_w = float(risk_data.get("top_three_weight_pct") or 50.0)
    volatility = float(risk_data.get("volatility_pct") or 30.0)
    sharpe = risk_data.get("sharpe_ratio")
    sharpe_val = float(sharpe) if sharpe is not None else 0.8
    max_dd = abs(float(risk_data.get("max_drawdown_pct") or 20.0))

    diversity = _score_at_most(top3_w, _DIVERSITY_BANDS, _DIVERSITY_DEFAULT)
    vol = _score_at_most(volatility, _VOLATILITY_BANDS, _VOLATILITY_DEFAULT)
    shp = _score_at_least(sharpe_val, _SHARPE_BANDS, _SHARPE_DEFAULT)
    dd = _score_at_most(max_dd, _DRAWDOWN_BANDS, _DRAWDOWN_DEFAULT)

    total = max(0, min(100, diversity[0] + vol[0] + shp[0] + dd[0]))
    factors = [
        _factor("Varlık Çeşitliliği", f"%{top3_w:.1f} (İlk 3)", diversity),
        _factor("Volatilite & Risk", f"%{volatility:.1f}", vol),
        _factor("Sharpe Rasyosu", f"{sharpe_val:.2f}", shp),
        _factor("Maksimum Düşüş", f"-%{max_dd:.1f}", dd),
    ]
    return total, _overall_label(total), factors


def default_health() -> Tuple[int, str, List[Dict[str, Any]]]:
    """Analitik veri alınamadığında gösterilen sabit sağlık özeti."""
    return 70, "Dengeli", [
        {"title": "Varlık Çeşitliliği", "value": "%55.0", "score": 18, "maxScore": 25, "status": "Dengeli Dağılım", "isGood": True},
        {"title": "Volatilite & Risk", "value": "%28.4", "score": 19, "maxScore": 25, "status": "Piyasa Ortalaması", "isGood": True},
        {"title": "Sharpe Rasyosu", "value": "1.12", "score": 18, "maxScore": 25, "status": "İyi Performans", "isGood": True},
        {"title": "Maksimum Düşüş", "value": "-%18.5", "score": 15, "maxScore": 25, "status": "Normal Seviye", "isGood": True},
    ]
