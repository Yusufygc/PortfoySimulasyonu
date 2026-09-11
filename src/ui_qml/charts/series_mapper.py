"""
Seri → piksel koordinat eşlemesi — saf, Qt'siz (bkz. plan §7.4 d0 POC).

`LineChartItem` (QQuickPaintedItem) bu modülü kullanarak değer serisini çizim
alanına eşler. Zoom/pan/crosshair gibi etkileşimler görsel regresyon testi
GEREKTİRMEZ — plan §7.4'te belirtildiği gibi burada test edilen şey nokta/
koordinat eşlemesinin doğruluğudur, ekrana gerçekten çizilen pikseller değil.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple


def map_series_to_points(
    values: Sequence[float],
    width: float,
    height: float,
    padding: float = 8.0,
    value_bounds: Optional[Tuple[float, float]] = None,
) -> List[Tuple[float, float]]:
    """
    Değer serisini (x, y) piksel koordinat listesine çevirir.

    x: soldan sağa eşit aralıklarla dağıtılır (ilk nokta padding'de, son nokta width-padding'de).
    y: ekran koordinatı yukarı doğru küçüldüğünden ters çevrilir — en yüksek değer en küçük y'ye
    (grafiğin üstüne) eşlenir. Sabit seri (value_range=0) tam ortaya düz bir çizgi olarak eşlenir.

    `value_bounds` verilirse (min, max) bu aralık kullanılır — serinin kendi min/max'ı DEĞİL.
    İki seriyi (örn. MACD hattı + sinyal hattı) aynı y-ölçeğinde çizmek için kullanılır:
    çağıran taraf ortak min/max'ı hesaplayıp her iki `map_series_to_points()` çağrısına aynı
    `value_bounds`'u geçer — aksi halde her seri kendi aralığına göre bağımsız normalize olur
    ve ikisi arasındaki gerçek büyüklük farkı (örn. kesişim noktaları) görsel olarak bozulur.

    Boş seri veya sıfır/negatif width/height için boş liste döner (çağıran taraf çizimi atlar).
    """
    if not values or width <= 0 or height <= 0:
        return []

    plot_width = max(width - 2 * padding, 0.0)
    plot_height = max(height - 2 * padding, 0.0)
    count = len(values)
    min_value, max_value = value_bounds if value_bounds is not None else (min(values), max(values))
    value_range = max_value - min_value

    points: List[Tuple[float, float]] = []
    for index, value in enumerate(values):
        x = padding + (plot_width * index / (count - 1) if count > 1 else plot_width / 2.0)
        if value_range == 0:
            y = padding + plot_height / 2.0
        else:
            normalized = (value - min_value) / value_range
            y = padding + (1.0 - normalized) * plot_height
        points.append((x, y))
    return points
