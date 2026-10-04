"""Karşılaştırma Laboratuvarı grafik HTML üreticileri.

Saf fonksiyonlar: veri çerçevesi / metrik listesi alır, QtWebEngine'de gösterilecek tam HTML döndürür.
Denetleyici durumuna (QObject) bağımlı değildir; ayrı test edilebilir.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

logger = logging.getLogger(__name__)

_JS_DIR = Path(__file__).resolve().parent.parent / "assets" / "js"
_LW_CHARTS_JS: str = ""
_CHART_JS: str = ""

PALETTE = [
    "#2962ff", "#089981", "#f23645", "#ff9800",
    "#ab47bc", "#00bcd4", "#ff5722", "#4caf50",
    "#e91e63", "#3f51b5", "#009688", "#ffc107"
]


_SCATTER_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
{script_tag}
<style>body{{margin:12px;background:#131722;color:#9db2ce;overflow:hidden}}#chart-wrap{{width:98vw;height:90vh}}</style>
</head><body><div id="chart-wrap"><canvas id="sChart"></canvas></div>
<script>
new Chart(document.getElementById('sChart'), {{
    type: 'scatter',
    data: {{
        datasets: [{datasets}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ labels: {{ color: '#9db2ce', font: {{ family: 'Segoe UI' }} }} }},
            tooltip: {{
                callbacks: {{
                    label: function(ctx) {{
                        return ctx.dataset.label + ' -> Risk: %' + ctx.raw.x + ' | Getiri: %' + ctx.raw.y;
                    }}
                }}
            }}
        }},
        scales: {{
            x: {{
                title: {{ display: true, text: 'Yıllık Volatilite (Oynaklık / Risk %)', color: '#9db2ce' }},
                grid: {{ color: '#1e222d' }}, ticks: {{ color: '#9db2ce' }}
            }},
            y: {{
                title: {{ display: true, text: 'Toplam Getiri (%)', color: '#9db2ce' }},
                grid: {{ color: '#1e222d' }}, ticks: {{ color: '#9db2ce' }}
            }}
        }}
    }}
}});
</script></body></html>"""

_TREEMAP_TEMPLATE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
        margin: 0;
        background: #131722;
        color: #e0e3eb;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        overflow: hidden;
        width: 100vw;
        height: 100vh;
    }}
    #treemap-container {{
        position: relative;
        width: 100%;
        height: 100%;
        padding: 8px;
    }}
    .treemap-node {{
        position: absolute;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        border: 2px solid #131722;
        border-radius: 6px;
        overflow: hidden;
        cursor: pointer;
        user-select: none;
        box-shadow: inset 0 0 10px rgba(0, 0, 0, 0.25);
        transition: transform 0.12s ease, filter 0.12s ease, border-color 0.12s ease;
    }}
    .treemap-node:hover {{
        transform: scale(0.985);
        filter: brightness(1.2);
        border-color: #38bdf8 !important;
        z-index: 10;
        box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
    }}
    .node-label {{
        font-weight: 700;
        color: #ffffff;
        text-shadow: 0 1px 3px rgba(0,0,0,0.6);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 90%;
    }}
    .node-ret {{
        font-weight: 800;
        text-shadow: 0 1px 3px rgba(0,0,0,0.7);
        white-space: nowrap;
    }}
    .node-sub {{
        font-size: 11px;
        color: rgba(255, 255, 255, 0.8);
        text-shadow: 0 1px 2px rgba(0,0,0,0.6);
        margin-top: 2px;
    }}
    #tooltip {{
        position: absolute;
        display: none;
        pointer-events: none;
        background: #1e222d;
        border: 1px solid #2a2e39;
        border-radius: 8px;
        padding: 10px 14px;
        font-size: 12px;
        color: #d1d4dc;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.6);
        z-index: 100;
        line-height: 1.6;
    }}
    .tt-title {{
        font-size: 13px;
        font-weight: bold;
        color: #fff;
        margin-bottom: 4px;
        border-bottom: 1px solid #2a2e39;
        padding-bottom: 4px;
    }}
</style>
</head><body>
<div id="treemap-container"></div>
<div id="tooltip"></div>

<script>
const rawData = {items_json};
const isHoldings = {is_holdings_js};
const portfolioName = {portfolio_name_js};
const container = document.getElementById('treemap-container');
const tooltip = document.getElementById('tooltip');

function getColor(ret) {{
    if (ret >= 15) return 'linear-gradient(135deg, #059669, #047857)';
    if (ret >= 8)  return 'linear-gradient(135deg, #10b981, #059669)';
    if (ret >= 3)  return 'linear-gradient(135deg, #0d9488, #0f766e)';
    if (ret > 0)   return 'linear-gradient(135deg, #134e4a, #064e3b)';
    if (ret === 0) return 'linear-gradient(135deg, #374151, #1f2937)';
    if (ret > -3)  return 'linear-gradient(135deg, #4c0519, #701a75)';
    if (ret > -8)  return 'linear-gradient(135deg, #881337, #9f1239)';
    if (ret > -15) return 'linear-gradient(135deg, #be123c, #e11d48)';
    return 'linear-gradient(135deg, #e11d48, #f43f5e)';
}}

function computeTreemap(data, width, height) {{
    if (!data || data.length === 0) return [];
    const totalVal = data.reduce((s, d) => s + d.value, 0);
    if (totalVal <= 0) return [];

    let rects = [];
    let items = data.map(d => ({{ ...d, area: (d.value / totalVal) * width * height }}));
    items.sort((a, b) => b.area - a.area);

    function worst(row, w) {{
        let s = row.reduce((acc, c) => acc + c.area, 0);
        if (s === 0) return Infinity;
        let maxA = Math.max(...row.map(c => c.area));
        let minA = Math.min(...row.map(c => c.area));
        let w2 = w * w;
        let s2 = s * s;
        return Math.max((w2 * maxA) / s2, s2 / (w2 * minA));
    }}

    function layoutRow(row, x, y, w, h, isVertical) {{
        let s = row.reduce((acc, c) => acc + c.area, 0);
        let rowWidth = s / (isVertical ? h : w);
        let offset = 0;
        for (let item of row) {{
            let itemLen = item.area / rowWidth;
            if (isVertical) {{
                rects.push({{ item, x: x, y: y + offset, w: rowWidth, h: itemLen }});
            }} else {{
                rects.push({{ item, x: x + offset, y: y, w: itemLen, h: rowWidth }});
            }}
            offset += itemLen;
        }}
        return rowWidth;
    }}

    function squarifyHelper(children, row, x, y, w, h) {{
        if (children.length === 0) {{
            if (row.length > 0) {{
                let isVertical = w < h;
                layoutRow(row, x, y, w, h, isVertical);
            }}
            return;
        }}
        let isVertical = w < h;
        let side = isVertical ? w : h;
        let c = children[0];
        let newRow = [...row, c];

        if (row.length === 0 || worst(row, side) >= worst(newRow, side)) {{
            squarifyHelper(children.slice(1), newRow, x, y, w, h);
        }} else {{
            let rowSize = layoutRow(row, x, y, w, h, isVertical);
            if (isVertical) {{
                squarifyHelper(children, [], x + rowSize, y, w - rowSize, h);
            }} else {{
                squarifyHelper(children, [], x, y + rowSize, w, h - rowSize);
            }}
        }}
    }}

    squarifyHelper(items, [], 0, 0, width, height);
    return rects;
}}

function render() {{
    container.innerHTML = '';
    const pad = 12;
    const w = (container.clientWidth || window.innerWidth) - pad;
    const h = (container.clientHeight || window.innerHeight) - pad;
    if (w <= 0 || h <= 0) return;

    if (!rawData || rawData.length === 0) {{
        if (isHoldings) {{
            container.innerHTML = '<div style="display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:#9db2ce; text-align:center; padding:20px;">' +
                '<div style="font-size:16px; font-weight:600; margin-bottom:8px; color:#e0e3eb;">' + portfolioName + ' Pozisyonu Bulunamadı</div>' +
                '<div style="font-size:13px; color:#64748b;">Bu model portföyde seçilen dönem için aktif hisse senedi kaydı bulunmuyor.</div>' +
                '</div>';
        }}
        return;
    }}

    const rects = computeTreemap(rawData, w, h);

    rects.forEach(r => {{
        const node = document.createElement('div');
        node.className = 'treemap-node';
        node.style.left = (r.x + pad/2) + 'px';
        node.style.top = (r.y + pad/2) + 'px';
        node.style.width = Math.max(1, r.w) + 'px';
        node.style.height = Math.max(1, r.h) + 'px';
        node.style.background = getColor(r.item.ret);

        const sign = r.item.ret >= 0 ? '+' : '';
        const titleSize = Math.max(11, Math.min(18, Math.floor(Math.min(r.w, r.h) / 4.8)));
        const retSize = Math.max(10, Math.min(16, Math.floor(Math.min(r.w, r.h) / 5.5)));

        let content = `<div class="node-label" style="font-size: ${{titleSize}}px;">${{r.item.label}}</div>
                       <div class="node-ret" style="font-size: ${{retSize}}px;">${{sign}}${{r.item.ret.toFixed(2)}}%</div>`;

        if (r.h >= 62 && r.w >= 70) {{
            if (isHoldings) {{
                content += `<div class="node-sub">Pay: %${{r.item.weight.toFixed(1)}}</div>`;
            }} else if (r.item.vol > 0) {{
                content += `<div class="node-sub">Vol: %${{r.item.vol.toFixed(1)}}</div>`;
            }}
        }}

        node.innerHTML = content;

        node.addEventListener('mouseenter', (e) => {{
            tooltip.style.display = 'block';
            let ttHtml = `<div class="tt-title">${{r.item.label}} ${{isHoldings ? '(' + portfolioName + ' Pozisyonu)' : ''}}</div>`;
            if (isHoldings) {{
                ttHtml += `
                    <div><b>Portföy Payı:</b> %${{r.item.weight.toFixed(2)}}</div>
                    <div><b>Kâr / Zarar Getirisi:</b> <span style="color:${{r.item.ret >= 0 ? '#10b981' : '#f43f5e'}}; font-weight:bold;">${{sign}}${{r.item.ret.toFixed(2)}}%</span></div>
                    <div><b>Piyasa Değeri:</b> ₺${{Number(r.item.marketValue).toLocaleString('tr-TR', {{minimumFractionDigits: 2}})}}</div>
                    <div><b>Maliyet Tutarı:</b> ₺${{Number(r.item.costValue).toLocaleString('tr-TR', {{minimumFractionDigits: 2}})}}</div>
                `;
            }} else {{
                ttHtml += `
                    <div><b>Toplam Getiri:</b> <span style="color:${{r.item.ret >= 0 ? '#10b981' : '#f43f5e'}}; font-weight:bold;">${{sign}}${{r.item.ret.toFixed(2)}}%</span></div>
                    <div><b>Yıllık Oynaklık (Risk):</b> %${{r.item.vol.toFixed(2)}}</div>
                    <div><b>Göreceli Katkı:</b> ${{r.item.value.toFixed(1)}} Puan</div>
                `;
            }}
            tooltip.innerHTML = ttHtml;
        }});

        node.addEventListener('mousemove', (e) => {{
            const ttW = tooltip.offsetWidth || 190;
            const ttH = tooltip.offsetHeight || 100;
            let left = e.clientX + 14;
            let top = e.clientY + 14;
            if (left + ttW > window.innerWidth) left = e.clientX - ttW - 14;
            if (top + ttH > window.innerHeight) top = e.clientY - ttH - 14;
            tooltip.style.left = left + 'px';
            tooltip.style.top = top + 'px';
        }});

        node.addEventListener('mouseleave', () => {{
            tooltip.style.display = 'none';
        }});

        container.appendChild(node);
    }});
}}

window.addEventListener('resize', render);
window.addEventListener('DOMContentLoaded', render);
render();
</script></body></html>"""


def _load_embedded_scripts() -> None:
    global _LW_CHARTS_JS, _CHART_JS
    if not _LW_CHARTS_JS:
        lw_file = _JS_DIR / "lightweight-charts.standalone.production.js"
        if lw_file.exists():
            try:
                _LW_CHARTS_JS = lw_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("lightweight-charts script okunamadı: %s", e)
    if not _CHART_JS:
        chart_file = _JS_DIR / "chart.umd.min.js"
        if chart_file.exists():
            try:
                _CHART_JS = chart_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("chart.umd.min.js script okunamadı: %s", e)


def build_line_chart_html(df: pd.DataFrame, is_ratio: bool = False, is_normal: bool = False, is_normalized: bool = False) -> str:
    datasets_js = []
    for i, col in enumerate(df.columns):
        color = PALETTE[i % len(PALETTE)]
        series = df[col].dropna()
        data_points = []
        for dt_val, val in series.items():
            time_str = dt_val.strftime("%Y-%m-%d") if hasattr(dt_val, "strftime") else str(dt_val)[:10]
            data_points.append(f"{{time:'{time_str}',value:{float(val):.2f}}}")

        datasets_js.append(f"""
                var s{i} = chart.addSeries(LightweightCharts.LineSeries, {{
                    color: '{color}',
                    lineWidth: 2,
                    title: '{col}'
                }});
                s{i}.setData([{','.join(data_points)}]);
            """)

    title_note = "Rasyo (A/B)" if is_ratio else ("Fiyat / Değer" if is_normal else "Normalize Getiri (Baz 100)")
    return _wrap_lw_chart(''.join(datasets_js), title_note)


def build_drawdown_html(dd_df: pd.DataFrame) -> str:
    """Drawdown derinlik eğrileri (negatif yüzdeler)."""
    datasets_js = []
    for i, col in enumerate(dd_df.columns):
        color = PALETTE[i % len(PALETTE)]
        series = dd_df[col].dropna()
        data_points = []
        for dt_val, val in series.items():
            time_str = dt_val.strftime("%Y-%m-%d") if hasattr(dt_val, "strftime") else str(dt_val)[:10]
            data_points.append(f"{{time:'{time_str}',value:{float(val):.2f}}}")

        datasets_js.append(f"""
                var s{i} = chart.addSeries(LightweightCharts.AreaSeries, {{
                    topColor: 'rgba(0, 0, 0, 0)',
                    bottomColor: '{color}22',
                    lineColor: '{color}',
                    lineWidth: 2,
                    title: '{col}'
                }});
                s{i}.setData([{','.join(data_points)}]);
            """)

    return _wrap_lw_chart(''.join(datasets_js), "Maksimum Değer Kaybı (Drawdown %)")


def _wrap_lw_chart(series_code: str, title: str) -> str:
    _load_embedded_scripts()
    script_tag = f"<script>{_LW_CHARTS_JS}</script>" if _LW_CHARTS_JS else '<script src="https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js"></script>'
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>body {{ margin: 0; background: #131722; overflow: hidden; }} #c {{ width: 100vw; height: 100vh; }}</style>
{script_tag}
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
{series_code}
chart.timeScale().fitContent();
window.addEventListener('resize', function() {{
    chart.applyOptions({{ width: window.innerWidth, height: window.innerHeight }});
}});
</script></body></html>"""


def build_periodic_html(monthly_df: pd.DataFrame) -> str:
    """Aylık getirileri yan yana gösteren interaktif Chart.js Bar Grafiği."""
    _load_embedded_scripts()
    script_tag = f"<script>{_CHART_JS}</script>" if _CHART_JS else '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
    labels = [d.strftime("%Y-%m") if hasattr(d, "strftime") else str(d)[:7] for d in monthly_df.index]
    datasets = []
    for i, col in enumerate(monthly_df.columns):
        color = PALETTE[i % len(PALETTE)]
        vals = [round(float(v), 2) if not pd.isna(v) else 0 for v in monthly_df[col]]
        datasets.append(f"""{{
                label: '{col}',
                data: {vals},
                backgroundColor: '{color}cc',
                borderColor: '{color}',
                borderWidth: 1
            }}""")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
{script_tag}
<style>body{{margin:12px;background:#131722;color:#9db2ce;overflow:hidden}}#chart-wrap{{width:98vw;height:90vh}}</style>
</head><body><div id="chart-wrap"><canvas id="pChart"></canvas></div>
<script>
new Chart(document.getElementById('pChart'), {{
    type: 'bar',
    data: {{
        labels: {labels},
        datasets: [{','.join(datasets)}]
    }},
    options: {{
        responsive: true,
        maintainAspectRatio: false,
        plugins: {{
            legend: {{ labels: {{ color: '#9db2ce', font: {{ family: 'Segoe UI' }} }} }}
        }},
        scales: {{
            x: {{ grid: {{ color: '#1e222d' }}, ticks: {{ color: '#9db2ce' }} }},
            y: {{ grid: {{ color: '#1e222d' }}, ticks: {{ color: '#9db2ce', callback: v => '%' + v }} }}
        }}
    }}
}});
</script></body></html>"""


def build_scatter_html(metrics: List[Dict[str, Any]]) -> str:
    """Risk / Getiri Saçılım (Scatter Plot) Grafiği."""
    _load_embedded_scripts()
    script_tag = f"<script>{_CHART_JS}</script>" if _CHART_JS else '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'
    datasets = []
    for i, m in enumerate(metrics):
        color = PALETTE[i % len(PALETTE)]
        datasets.append(f"""{{
                label: '{m["label"]}',
                data: [{{ x: {m["volatility"]}, y: {m["totalReturn"]} }}],
                backgroundColor: '{color}',
                borderColor: '#ffffff',
                borderWidth: 2,
                pointRadius: 9,
                pointHoverRadius: 12
            }}""")

    return _SCATTER_TEMPLATE.format(script_tag=script_tag, datasets=','.join(datasets))


def treemap_items_from_metrics(metrics: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Seçilen varlıkların (portföy, BIST100, altın vb.) getiri katkı kutularını üretir."""
    items = []
    for m in metrics:
        ret = float(m.get("totalReturn", 0.0))
        vol = float(m.get("volatility", 0.0))
        label = str(m.get("label", m.get("code", "")))
        weight = max(abs(ret), 1.0)
        items.append({
            "code": str(m.get("code", "")),
            "label": label,
            "ret": round(ret, 2),
            "vol": round(vol, 2),
            "weight": round(weight, 2),
            "value": round(weight, 2),
            "marketValue": 0.0,
            "costValue": 0.0,
        })
    return items


def build_treemap_html(items: List[Dict[str, Any]], is_holdings: bool, portfolio_name: str) -> str:
    """Portföy Getiri Katkı & Büyüklük Haritası (Squarified Treemap).

    is_holdings: Seçilen portföyün hisse ağırlık ve getiri haritası; aksi halde seçilen varlıkların getiri katkı haritası.
    """
    items_json = json.dumps(items)
    is_holdings_js = "true" if is_holdings else "false"
    portfolio_name_js = json.dumps(portfolio_name)

    return _TREEMAP_TEMPLATE.format(
        items_json=items_json, is_holdings_js=is_holdings_js, portfolio_name_js=portfolio_name_js
    )
