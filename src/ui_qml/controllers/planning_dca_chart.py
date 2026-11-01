"""Planlama sayfası DCA simülasyonu portföy değeri grafiği (TradingView Lightweight Charts alan serisi, WebEngine HTML'i)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Dict

from src.ui_qml.controllers.lw_chart_html import _script_tag as script_tag


def build_dca_chart_html(series: Dict[date, Decimal]) -> str:
    if not series:
        return ""

    data_points = []
    for dt_val in sorted(series.keys()):
        val = float(series[dt_val])
        data_points.append(f"{{time:'{dt_val.isoformat()}',value:{val:.2f}}}")

    # metin-muaf: HTML şablonu
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
body {{ margin: 0; background: #131722; overflow: hidden; }}
#c {{ width: 100vw; height: 100vh; }}
</style>
{script_tag()}
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
var areaSeries = chart.addSeries(LightweightCharts.AreaSeries, {{
    topColor: 'rgba(41, 98, 255, 0.45)',
    bottomColor: 'rgba(41, 98, 255, 0.04)',
    lineColor: '#2962ff',
    lineWidth: 2,
    priceFormat: {{
        type: 'price',
        precision: 2,
        minMove: 0.01,
    }},
    title: 'Portföy Değeri (₺)',
}});
areaSeries.setData([{','.join(data_points)}]);
chart.timeScale().fitContent();
window.addEventListener('resize', function() {{
    chart.applyOptions({{ width: window.innerWidth, height: window.innerHeight }});
}});
</script></body></html>"""
