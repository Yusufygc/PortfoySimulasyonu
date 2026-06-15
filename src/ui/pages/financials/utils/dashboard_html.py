"""
Finansal dashboard HTML üreticisi — orkestratör.

Grafik fonksiyonları: charts.py
Offline Plotly: ensure_patched_plotly_js() ile yerel JS kullanır (CDN yok).
"""
from __future__ import annotations

from typing import Any

from src.ui.pages.comparison.utils.plotly_html import ensure_patched_plotly_js
from src.ui.pages.financials.utils.charts import (
    _chart_bilanco,
    _chart_degerleme,
    _chart_dupont,
    _chart_isletme_sermaye,
    _chart_kpi_table,
    _chart_piotroski,
    _chart_reel_buyume,
    _chart_satis_favok,
    _chart_sezonsellik,
    _chart_temettu,
    _fig_to_div,
)

# ---------------------------------------------------------------------------
# CSS + JS (tab navigasyonu)
# ---------------------------------------------------------------------------

_CSS = (
    "*, *::before, *::after{box-sizing:border-box;margin:0;padding:0}"
    "body{background:#0f172a;color:#f1f5f9;font-family:Inter,'Segoe UI',sans-serif;padding:12px}"
    ".tab-nav{display:flex;flex-wrap:wrap;gap:3px;border-bottom:2px solid #334155;"
    "padding-bottom:0;margin-bottom:0}"
    ".tab-btn{background:#1e293b;color:#94a3b8;border:1px solid #334155;"
    "border-radius:5px 5px 0 0;border-bottom:none;padding:6px 14px;"
    "cursor:pointer;font-size:.8rem;white-space:nowrap;transition:background .12s}"
    ".tab-btn:hover{background:#2d3f53;color:#f1f5f9}"
    ".tab-btn.active{background:#0f172a;color:#00D4FF;border-color:#334155;"
    "border-bottom:2px solid #0f172a;margin-bottom:-2px}"
    ".tab-pane{display:none;border:1px solid #334155;border-top:none;"
    "border-radius:0 0 8px 8px;background:#0f172a;padding:6px}"
    ".tab-pane.active{display:block}"
)

_JS = r"""
function showTab(id,btn){
  document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  btn.classList.add('active');
  setTimeout(()=>{
    document.getElementById(id).querySelectorAll('.plotly-graph-div').forEach(el=>{
      if(window.Plotly) Plotly.Plots.resize(el);
    });
  },30);
}
"""


def build_dashboard(m: dict[str, Any], n_periods: int = 8) -> str:
    """
    Tek HTML dosyası olarak finansal dashboard üret (10 sekme).
    Plotly JS yerel dosyadan yüklenir (CDN bağımlılığı yok).
    """
    ticker = m.get("ticker", "")

    tabs = [
        ("kpi",      "📊 KPI Özeti",            _chart_kpi_table(m, n_periods)),
        ("satis",    "📈 Satışlar & Marjlar",   _chart_satis_favok(m, n_periods)),
        ("bilanco",  "🏦 Bilanço",              _chart_bilanco(m, n_periods)),
        ("dupont",   "🔍 DuPont",               _chart_dupont(m, n_periods)),
        ("isletme",  "⚙️ İşletme Sermayesi",    _chart_isletme_sermaye(m, n_periods)),
        ("fscore",   "🏅 Piotroski F-Score",    _chart_piotroski(m, n_periods)),
        ("sezon",    "📅 Sezonsellik",           _chart_sezonsellik(m, n_periods)),
        ("temettu",  "💰 Temettü",              _chart_temettu(m, n_periods)),
        ("reel",     "📉 Reel Büyüme",          _chart_reel_buyume(m, n_periods)),
        ("deger",    "💹 Değerleme",            _chart_degerleme(m, n_periods)),
    ]

    nav = "".join(
        f"<button class='tab-btn{' active' if i == 0 else ''}' "
        f"onclick=\"showTab('{tid}',this)\">{lbl}</button>"
        for i, (tid, lbl, _) in enumerate(tabs)
    )
    panes = "".join(
        f"<div id='{tid}' class='tab-pane{' active' if i == 0 else ''}'>"
        + _fig_to_div(fig)
        + "</div>"
        for i, (tid, _, fig) in enumerate(tabs)
    )

    js_path     = ensure_patched_plotly_js()
    js_file_url = js_path.replace("\\", "/")
    if not js_file_url.startswith("file://"):
        js_file_url = "file:///" + js_file_url

    return (
        "<!DOCTYPE html>\n<html lang='tr'>\n<head>\n"
        "<meta charset='utf-8'>\n"
        f"<title>{ticker} — Finansal Dashboard</title>\n"
        f"<script src='{js_file_url}'></script>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n<body>\n"
        f"<nav class='tab-nav'>{nav}</nav>\n"
        + panes
        + f"\n<script>\n{_JS}\n</script>\n"
        "</body>\n</html>"
    )
