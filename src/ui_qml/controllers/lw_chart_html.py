"""TradingView Lightweight Charts ile çok serili çizgi grafik HTML'i üretir (WebEngineView'a `loadHtml` ile verilir)."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Sequence, Tuple

logger = logging.getLogger(__name__)

_JS_FILE = Path(__file__).resolve().parent.parent / "assets" / "js" / "lightweight-charts.standalone.production.js"
_CDN_TAG = '<script src="https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js"></script>'
_script_tag_cache: str = ""

# (başlık, renk, [(tarih_iso, değer), ...])
SeriesSpec = Tuple[str, str, Sequence[Tuple[str, float]]]


def _script_tag() -> str:
    global _script_tag_cache
    if not _script_tag_cache:
        try:
            _script_tag_cache = f"<script>{_JS_FILE.read_text(encoding='utf-8')}</script>"
        except OSError as exc:
            logger.warning("lightweight-charts script okunamadı, CDN kullanılacak: %s", exc)
            _script_tag_cache = _CDN_TAG
    return _script_tag_cache


def line_chart_html(series_specs: List[SeriesSpec]) -> str:
    """Her seri için bir çizgi; başlıklar sağ fiyat eksenindeki etiketlerde görünür. Seri yoksa boş metin döner."""
    specs = [
        {"title": title, "color": color, "data": [{"time": day, "value": round(value, 2)} for day, value in points]}
        for title, color, points in series_specs if points
    ]
    if not specs:
        return ""
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ margin: 0; background: #131722; overflow: hidden; }}
#c {{ width: 100vw; height: 100vh; }}
</style>
{_script_tag()}
</head><body><div id="c"></div>
<script>
var chart = LightweightCharts.createChart(document.getElementById('c'), {{
    width: window.innerWidth || 800, height: window.innerHeight || 450,
    layout: {{ background: {{ color: '#131722' }}, textColor: '#9db2ce' }},
    grid: {{ vertLines: {{ color: '#1e222d' }}, horzLines: {{ color: '#1e222d' }} }},
    rightPriceScale: {{ borderColor: '#2a2e39', scaleMargins: {{ top: 0.1, bottom: 0.1 }} }},
    timeScale: {{ borderColor: '#2a2e39', timeVisible: false }},
    crosshair: {{ mode: 0 }}
}});
var specs = {json.dumps(specs)};
specs.forEach(function(spec) {{
    var line = chart.addSeries(LightweightCharts.LineSeries, {{
        color: spec.color, lineWidth: 2, title: spec.title,
        priceFormat: {{ type: 'price', precision: 2, minMove: 0.01 }}
    }});
    line.setData(spec.data);
}});
chart.timeScale().fitContent();
window.addEventListener('resize', function() {{
    chart.applyOptions({{ width: window.innerWidth, height: window.innerHeight }});
}});
</script></body></html>"""
