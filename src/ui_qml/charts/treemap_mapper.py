"""
Squarified treemap geometri hesaplama — saf, Qt'siz (bkz. plan §7.4, AnalyticsView
§7.3 madde 6 "Treemap Getiri Katkı Haritası"). Bruls/Huizing/van Wijk (1999)
algoritması: dikdörtgenleri mümkün olduğunca kareye yakın en/boy oranıyla
diziyor — çok uzun/ince dikdörtgenler yerine okunabilir alan blokları üretir.

`candlestick_mapper.py`/`bar_mapper.py` ile aynı desen: piksel geometrisi
burada, çizim `TreemapChartItem`'da.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence, Tuple


@dataclass(frozen=True)
class TreemapRect:
    """Bir treemap hücresinin piksel geometrisi. `value` alan (weight) değil,
    hücrenin RENGİ/etiketi için kullanılan ham metriktir (örn. getiri %)."""
    label: str
    x: float
    y: float
    width: float
    height: float
    value: float


def compute_treemap_rects(
    items: Sequence[Tuple[str, float, float]],
    width: float,
    height: float,
    padding: float = 8.0,
) -> List[TreemapRect]:
    """
    `items`: (label, weight, value) üçlüleri. `weight` hücrenin ALANINI belirler
    (0'dan büyük olmalı, aksi halde eleman atlanır); `value` sadece taşınır (renk
    için, örn. toplam getiri %). Ağırlıklar büyükten küçüğe sıralanıp squarified
    algoritmasıyla dikdörtgenlere dönüştürülür.

    Boş/tümü sıfır-altı ağırlıklı liste veya sıfır/negatif width/height için
    boş liste döner.
    """
    positive_items = [(label, weight, value) for label, weight, value in items if weight > 0]
    if not positive_items or width <= 0 or height <= 0:
        return []

    plot_width = max(width - 2 * padding, 0.0)
    plot_height = max(height - 2 * padding, 0.0)
    if plot_width <= 0 or plot_height <= 0:
        return []

    ordered = sorted(positive_items, key=lambda item: item[1], reverse=True)
    total_weight = sum(weight for _, weight, _ in ordered)
    scale = (plot_width * plot_height) / total_weight
    scaled = [(label, weight * scale, value) for label, weight, value in ordered]

    return _squarify(scaled, padding, padding, plot_width, plot_height)


def _worst_aspect_ratio(row_areas: List[float], side_length: float) -> float:
    if not row_areas or side_length <= 0:
        return float("inf")
    row_sum = sum(row_areas)
    if row_sum <= 0:
        return float("inf")
    row_max = max(row_areas)
    row_min = min(row_areas)
    side_sq = side_length * side_length
    return max(
        (side_sq * row_max) / (row_sum * row_sum),
        (row_sum * row_sum) / (side_sq * row_min),
    )


def _layout_row(
    row: List[Tuple[str, float, float]], x: float, y: float, w: float, h: float,
) -> Tuple[List[TreemapRect], float, float, float, float]:
    row_area = sum(area for _, area, _ in row)
    if w >= h:
        # Kalan alan geniş: satır dikey bir şerit olarak yerleşir (genişlik=row_area/h).
        row_width = row_area / h if h > 0 else 0.0
        cursor = y
        rects: List[TreemapRect] = []
        for label, area, value in row:
            rect_height = area / row_width if row_width > 0 else 0.0
            rects.append(TreemapRect(label, x, cursor, row_width, rect_height, value))
            cursor += rect_height
        return rects, x + row_width, y, max(w - row_width, 0.0), h
    else:
        # Kalan alan dar/yüksek: satır yatay bir şerit olarak yerleşir (yükseklik=row_area/w).
        row_height = row_area / w if w > 0 else 0.0
        cursor = x
        rects = []
        for label, area, value in row:
            rect_width = area / row_height if row_height > 0 else 0.0
            rects.append(TreemapRect(label, cursor, y, rect_width, row_height, value))
            cursor += rect_width
        return rects, x, y + row_height, w, max(h - row_height, 0.0)


def _squarify(
    items: List[Tuple[str, float, float]], x: float, y: float, w: float, h: float,
) -> List[TreemapRect]:
    result: List[TreemapRect] = []
    remaining = list(items)
    while remaining:
        side = min(w, h)
        row = [remaining[0]]
        rest = remaining[1:]
        while rest:
            candidate_row = row + [rest[0]]
            candidate_ratio = _worst_aspect_ratio([area for _, area, _ in candidate_row], side)
            current_ratio = _worst_aspect_ratio([area for _, area, _ in row], side)
            if candidate_ratio <= current_ratio:
                row = candidate_row
                rest = rest[1:]
            else:
                break
        rects, x, y, w, h = _layout_row(row, x, y, w, h)
        result.extend(rects)
        remaining = rest
    return result
