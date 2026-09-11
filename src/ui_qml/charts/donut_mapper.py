"""
Donut/pasta dilim açı hesaplama — saf, Qt'siz (bkz. plan §7.3 Dashboard varlık dağılımı).

Not: `pandas-ta`/harici grafik lib yasağı §9.2/§9.3 kararının doğal uzantısı olarak
donut da §7.4 v1 kapsamına (line/bar/scatter/candlestick) eklenen 5. tip — aynı
`QQuickPaintedItem` + saf-mapper mimarisiyle, ek bağımlılık gerektirmeden.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple


def compute_donut_segments(weights: Sequence[float]) -> List[Tuple[float, float]]:
    """
    Ağırlık listesini (start_angle, span_angle) derece çiftlerine çevirir — ilk dilim
    12 yönünden başlar, saat yönünde ilerler. Toplam 360°'ye normalize edilir.

    Negatif ağırlıklar 0'a kırpılır (kısa pozisyon donut'ta dilim almaz).
    Toplam ağırlık <= 0 ise boş liste döner (çağıran taraf çizimi atlar).
    """
    positive_weights = [max(0.0, w) for w in weights]
    total = sum(positive_weights)
    if total <= 0:
        return []

    segments: List[Tuple[float, float]] = []
    start = 0.0
    for weight in positive_weights:
        span = (weight / total) * 360.0
        segments.append((start, span))
        start += span
    return segments
