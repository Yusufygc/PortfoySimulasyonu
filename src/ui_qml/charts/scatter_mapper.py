"""
Risk/getiri saçılım (scatter) grafiği geometri hesaplama — saf, Qt'siz (bkz.
plan §7.4 v1 kapsamı, AnalyticsView §7.3 madde 5 "Risk / Getiri Dağılımı").
`series_mapper.py` ile aynı desen: piksel geometrisi burada, çizim
`ScatterChartItem`'da.
"""
from __future__ import annotations

from typing import List, Sequence, Tuple


def compute_scatter_points(
    x_values: Sequence[float],
    y_values: Sequence[float],
    width: float,
    height: float,
    padding: float = 12.0,
) -> List[Tuple[float, float]]:
    """
    Paralel x/y değer listelerini (x, y) piksel koordinat listesine çevirir.

    x ekseni soldan sağa (küçük değer sola), y ekseni ekran koordinatı gereği
    ters çevrilir (küçük değer alta, büyük değer üste). Tek nokta veya sabit
    aralık (range=0) o eksende ortaya yerleştirilir.

    `x_values`/`y_values` uzunlukları eşit olmalıdır; boş liste veya
    sıfır/negatif width/height için boş liste döner.
    """
    if not x_values or not y_values or len(x_values) != len(y_values):
        return []
    if width <= 0 or height <= 0:
        return []

    plot_width = max(width - 2 * padding, 0.0)
    plot_height = max(height - 2 * padding, 0.0)

    min_x, max_x = min(x_values), max(x_values)
    min_y, max_y = min(y_values), max(y_values)
    x_range = max_x - min_x
    y_range = max_y - min_y

    points: List[Tuple[float, float]] = []
    for x_value, y_value in zip(x_values, y_values):
        if x_range == 0:
            x = padding + plot_width / 2.0
        else:
            x = padding + ((x_value - min_x) / x_range) * plot_width
        if y_range == 0:
            y = padding + plot_height / 2.0
        else:
            y = padding + (1.0 - (y_value - min_y) / y_range) * plot_height
        points.append((x, y))
    return points
