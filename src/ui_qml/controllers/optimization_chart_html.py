"""Optimizasyon sayfası grafik HTML üreticileri (Chart.js): verimli sınır ve ağırlık karşılaştırması.

Saf fonksiyonlardır; sayı ve liste girdilerinden QtWebEngine'de gösterilecek tam HTML döndürür.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_JS_DIR = Path(__file__).resolve().parent.parent / "assets" / "js"
_CHART_JS: str = ""
_CDN_TAG = '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'

_FRONTIER_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{script_tag}
<style>
  body {{ margin: 0; padding: 12px; background: #131722; color: #9db2ce; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; overflow: hidden; }}
  #chart-container {{ width: 100%; height: calc(100vh - 24px); position: relative; }}
</style>
</head>
<body>
<div id="chart-container">
  <canvas id="frontierCanvas"></canvas>
</div>
<script>
const mcData = {mc_json};
const frontierData = {frontier_json};

const ctx = document.getElementById('frontierCanvas').getContext('2d');
new Chart(ctx, {{
  type: 'scatter',
  data: {{
    datasets: [
      {{
        label: 'Monte Carlo (1.000 Nokta)',
        data: mcData,
        backgroundColor: 'rgba(41, 98, 255, 0.25)',
        borderColor: 'transparent',
        pointRadius: 2,
        pointHoverRadius: 4,
        order: 5
      }},
      {{
        label: 'Verimli Sınır',
        data: frontierData,
        type: 'line',
        borderColor: '#00e676',
        backgroundColor: 'transparent',
        borderWidth: 3,
        pointRadius: 0,
        tension: 0.35,
        fill: false,
        order: 2
      }},
      {{
        label: 'Maksimum Sharpe',
        data: [{{ x: {opt_x}, y: {opt_y} }}],
        backgroundColor: '#00e676',
        borderColor: '#ffffff',
        borderWidth: 2,
        pointRadius: 9,
        pointHoverRadius: 13,
        pointStyle: 'circle',
        order: 1
      }},
      {{
        label: 'Minimum Risk',
        data: [{{ x: {min_vol_x}, y: {min_vol_y} }}],
        backgroundColor: '#00b0ff',
        borderColor: '#ffffff',
        borderWidth: 2,
        pointRadius: 8,
        pointHoverRadius: 12,
        pointStyle: 'triangle',
        order: 1
      }},
      {{
        label: 'Mevcut Portföy',
        data: [{{ x: {curr_x}, y: {curr_y} }}],
        backgroundColor: '#ff9800',
        borderColor: '#ffffff',
        borderWidth: 2,
        pointRadius: 9,
        pointHoverRadius: 13,
        pointStyle: 'rectRot',
        order: 1
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    layout: {{
      padding: {{ left: 16, right: 20, top: 10, bottom: 10 }}
    }},
    interaction: {{
      mode: 'nearest',
      intersect: true
    }},
    plugins: {{
      legend: {{
        position: 'top',
        align: 'center',
        labels: {{
          color: '#9db2ce',
          font: {{ family: 'Segoe UI', size: 11 }},
          usePointStyle: true,
          boxWidth: 7,
          padding: 12
        }}
      }},
      tooltip: {{
        backgroundColor: '#1e222d',
        titleColor: '#ffffff',
        bodyColor: '#9db2ce',
        borderColor: '#2a2e39',
        borderWidth: 1,
        padding: 10,
        callbacks: {{
          label: function(context) {{
            const p = context.raw;
            function fmtPct(val) {{
              if (val === null || val === undefined || isNaN(val)) return '%0,00';
              const num = Number(val);
              const str = Math.abs(num).toFixed(2).replace('.', ',');
              if (num < 0) return '-%' + str;
              return '%' + str;
            }}
            let str = context.dataset.label + ': ';
            str += 'Risk: ' + fmtPct(p.x) + ' | Getiri: ' + fmtPct(p.y);
            if (p.sharpe !== undefined) {{
              str += ' | Sharpe: ' + Number(p.sharpe).toFixed(2).replace('.', ',');
            }}
            return str;
          }}
        }}
      }}
    }},
    scales: {{
      x: {{
        title: {{
          display: true,
          text: 'Yıllık Volatilite (Oynaklık / Risk %)',
          color: '#9db2ce',
          font: {{ size: 12, weight: 'bold' }}
        }},
        grid: {{ color: '#1e222d' }},
        ticks: {{ color: '#9db2ce' }}
      }},
      y: {{
        title: {{
          display: true,
          text: 'Beklenen Yıllık Getiri (%)',
          color: '#9db2ce',
          font: {{ size: 12, weight: 'bold' }}
        }},
        grid: {{ color: '#1e222d' }},
        ticks: {{ color: '#9db2ce' }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""

_WEIGHTS_TEMPLATE = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
{script_tag}
<style>
  body {{ margin: 0; padding: 12px; background: #131722; color: #9db2ce; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; overflow: hidden; }}
  #weights-container {{ width: 100%; height: calc(100vh - 24px); position: relative; }}
</style>
</head>
<body>
<div id="weights-container">
  <canvas id="weightsCanvas"></canvas>
</div>
<script>
const ctx = document.getElementById('weightsCanvas').getContext('2d');
new Chart(ctx, {{
  type: 'bar',
  data: {{
    labels: {labels_json},
    datasets: [
      {{
        label: 'Mevcut Ağırlık',
        data: {curr_json},
        backgroundColor: '#ff9800',
        borderRadius: 4,
        barPercentage: 0.75,
        categoryPercentage: 0.65
      }},
      {{
        label: 'Önerilen Optimal Ağırlık',
        data: {opt_json},
        backgroundColor: '#00e676',
        borderRadius: 4,
        barPercentage: 0.75,
        categoryPercentage: 0.65
      }}
    ]
  }},
  options: {{
    responsive: true,
    maintainAspectRatio: false,
    layout: {{
      padding: {{ left: 16, right: 20, top: 10, bottom: 10 }}
    }},
    plugins: {{
      legend: {{
        position: 'top',
        align: 'center',
        labels: {{
          color: '#9db2ce',
          font: {{ family: 'Segoe UI', size: 11 }},
          usePointStyle: true,
          boxWidth: 8,
          padding: 12
        }}
      }},
      tooltip: {{
        backgroundColor: '#1e222d',
        titleColor: '#ffffff',
        bodyColor: '#9db2ce',
        borderColor: '#2a2e39',
        borderWidth: 1,
        padding: 10,
        callbacks: {{
          label: function(context) {{
            const v = Number(context.raw);
            const str = v.toFixed(2).replace('.', ',');
            return context.dataset.label + ': %' + str;
          }}
        }}
      }}
    }},
    scales: {{
      x: {{
        grid: {{ color: '#1e222d' }},
        ticks: {{ color: '#9db2ce' }}
      }},
      y: {{
        title: {{
          display: true,
          text: 'Portföy Ağırlığı (%)',
          color: '#9db2ce',
          font: {{ size: 12, weight: 'bold' }}
        }},
        grid: {{ color: '#1e222d' }},
        ticks: {{ color: '#9db2ce' }}
      }}
    }}
  }}
}});
</script>
</body>
</html>"""


def _load_embedded_scripts() -> None:
    global _CHART_JS
    if not _CHART_JS:
        chart_file = _JS_DIR / "chart.umd.min.js"
        if chart_file.exists():
            try:
                _CHART_JS = chart_file.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning("chart.umd.min.js script okunamadı: %s", e)


def _script_tag() -> str:
    _load_embedded_scripts()
    return f"<script>{_CHART_JS}</script>" if _CHART_JS else _CDN_TAG


def build_frontier_chart_html(
    mc_points: List[Dict[str, float]],
    frontier_curve: List[Dict[str, float]],
    curr_pt: Dict[str, float],
    opt_pt: Dict[str, float],
    min_vol_pt: Dict[str, float],
) -> str:
    """Verimli Sınır (Efficient Frontier) ve Monte Carlo saçılım grafiği HTML5/Chart.js."""
    return _FRONTIER_TEMPLATE.format(
        script_tag=_script_tag(),
        mc_json=json.dumps(mc_points),
        frontier_json=json.dumps(frontier_curve),
        opt_x=opt_pt["x"], opt_y=opt_pt["y"],
        min_vol_x=min_vol_pt["x"], min_vol_y=min_vol_pt["y"],
        curr_x=curr_pt["x"], curr_y=curr_pt["y"],
    )


def build_weights_chart_html(comparison: List[Dict[str, Any]]) -> str:
    """Mevcut vs Optimize Ağırlık Karşılaştırması Çubuk Grafiği HTML5/Chart.js."""
    return _WEIGHTS_TEMPLATE.format(
        script_tag=_script_tag(),
        labels_json=json.dumps([item["symbol"] for item in comparison]),
        curr_json=json.dumps([item["currentWeight"] for item in comparison]),
        opt_json=json.dumps([item["optimalWeight"] for item in comparison]),
    )
