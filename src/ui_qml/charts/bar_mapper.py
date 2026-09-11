"""
Dönemsel getiri bar grafiği geometri hesaplama — saf, Qt'siz (bkz. plan §7.4 v1
kapsamı, AnalyticsView §7.3 madde 4 "Dönemsel Getiri Karşılaştırma Grafiği").
`candlestick_mapper.py` ile aynı desen: piksel geometrisi burada, çizim
`BarChartItem`'da.

Candlestick'ten fark: tek değerli barlar (OHLC değil) ve sıfır çizgisi (baseline)
HER ZAMAN ölçek içinde tutulur — aksi halde tüm değerler aynı işaretliyken (örn.
hepsi pozitif) negatif/pozitif ayrımı görsel olarak kaybolur.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class BarGeometry:
    """Bir barın piksel geometrisi. `bar_top_y <= bar_bottom_y` her zaman doğrudur."""
    x_center: float
    bar_width: float
    bar_top_y: float
    bar_bottom_y: float
    is_positive: bool  # value >= 0


def compute_bar_geometry(
    values: Sequence[float],
    width: float,
    height: float,
    padding: float = 8.0,
    bar_width_ratio: float = 0.6,
) -> List[BarGeometry]:
    """
    Değer listesini piksel bar geometrisine çevirir. Sıfır çizgisi ölçeğe dahil
    edilir (`min(0, min(values))`..`max(0, max(values))`) — böylece pozitif ve
    negatif barlar aynı taban çizgisinden büyür.

    Boş liste veya sıfır/negatif width/height için boş liste döner.
    """
    if not values or width <= 0 or height <= 0:
        return []

    plot_width = max(width - 2 * padding, 0.0)
    plot_height = max(height - 2 * padding, 0.0)
    count = len(values)
    slot_width = plot_width / count
    bar_width = slot_width * bar_width_ratio

    min_value = min(0.0, min(values))
    max_value = max(0.0, max(values))
    value_range = max_value - min_value

    def y_for(value: float) -> float:
        if value_range == 0:
            return padding + plot_height / 2.0
        normalized = (value - min_value) / value_range
        return padding + (1.0 - normalized) * plot_height

    zero_y = y_for(0.0)

    geometries: List[BarGeometry] = []
    for index, value in enumerate(values):
        x_center = padding + slot_width * (index + 0.5)
        value_y = y_for(value)
        geometries.append(
            BarGeometry(
                x_center=x_center,
                bar_width=bar_width,
                bar_top_y=min(value_y, zero_y),
                bar_bottom_y=max(value_y, zero_y),
                is_positive=value >= 0,
            )
        )
    return geometries
