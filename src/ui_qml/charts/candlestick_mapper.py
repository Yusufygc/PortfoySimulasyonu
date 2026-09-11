"""
OHLC mum çubuğu geometri hesaplama — saf, Qt'siz (bkz. plan §7.4 v1 kapsamı,
Stock360View §7.3 Sekme 1). `LineChartItem`/`series_mapper.py` ile aynı desen:
piksel geometrisi burada hesaplanır, çizim `CandlestickChartItem`'da.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence


@dataclass(frozen=True)
class OhlcBar:
    open: float
    high: float
    low: float
    close: float


@dataclass(frozen=True)
class CandlestickBarGeometry:
    """Bir mum çubuğunun piksel geometrisi. Fitil (wick) ince çizgi, gövde (body) dikdörtgen."""
    x_center: float
    bar_width: float
    wick_top_y: float
    wick_bottom_y: float
    body_top_y: float
    body_bottom_y: float
    is_bullish: bool  # close >= open


def compute_candlestick_bars(
    bars: Sequence[OhlcBar],
    width: float,
    height: float,
    padding: float = 8.0,
    body_width_ratio: float = 0.6,
) -> List[CandlestickBarGeometry]:
    """
    OHLC bar listesini piksel geometrisine çevirir.

    y-ölçeği TÜM barların low/high'ından ortak hesaplanır (her bar kendi başına
    normalize edilmez) — aksi halde barlar birbirine göre karşılaştırılamaz olur.
    x ekseni eşit genişlikte "slot"lara bölünür, her bar kendi slot'unun ortasına
    yerleştirilir; gövde genişliği slot genişliğinin `body_width_ratio` kadarıdır.

    Boş liste veya sıfır/negatif width/height için boş liste döner.
    """
    if not bars or width <= 0 or height <= 0:
        return []

    plot_width = max(width - 2 * padding, 0.0)
    plot_height = max(height - 2 * padding, 0.0)
    count = len(bars)
    slot_width = plot_width / count
    bar_width = slot_width * body_width_ratio

    min_low = min(bar.low for bar in bars)
    max_high = max(bar.high for bar in bars)
    value_range = max_high - min_low

    def y_for(value: float) -> float:
        if value_range == 0:
            return padding + plot_height / 2.0
        normalized = (value - min_low) / value_range
        return padding + (1.0 - normalized) * plot_height

    geometries: List[CandlestickBarGeometry] = []
    for index, bar in enumerate(bars):
        x_center = padding + slot_width * (index + 0.5)
        geometries.append(
            CandlestickBarGeometry(
                x_center=x_center,
                bar_width=bar_width,
                wick_top_y=y_for(bar.high),
                wick_bottom_y=y_for(bar.low),
                body_top_y=y_for(max(bar.open, bar.close)),
                body_bottom_y=y_for(min(bar.open, bar.close)),
                is_bullish=bar.close >= bar.open,
            )
        )
    return geometries
