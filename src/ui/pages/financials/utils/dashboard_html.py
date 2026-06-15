"""
finansal dashboard HTML üreticisi — MVP (3 sekme).

Offline Plotly: ensure_patched_plotly_js() ile yerel JS kullanır (CDN yok).
"""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.ui.pages.comparison.utils.plotly_html import ensure_patched_plotly_js

# ---------------------------------------------------------------------------
# Renk paleti ve düzen sabitleri (koyu tema)
# ---------------------------------------------------------------------------

_C = {
    "blue":     "#00D4FF",
    "green":    "#22c55e",
    "red":      "#ef4444",
    "orange":   "#f97316",
    "purple":   "#a855f7",
    "teal":     "#14b8a6",
    "gray":     "#64748b",
    "text":     "#f1f5f9",
    "grid":     "#334155",
    "bg":       "#0f172a",
    "panel":    "#1e293b",
}

_LAYOUT_BASE = {
    "paper_bgcolor": _C["bg"],
    "plot_bgcolor":  _C["panel"],
    "font":          {"color": _C["text"], "family": "Inter, Segoe UI, sans-serif", "size": 12},
    "xaxis":         {"gridcolor": _C["grid"], "linecolor": _C["grid"]},
    "yaxis":         {"gridcolor": _C["grid"], "linecolor": _C["grid"]},
}
_MARGIN = {"t": 60, "b": 40, "l": 60, "r": 20}


def _layout(**overrides) -> dict:
    return {**_LAYOUT_BASE, "margin": _MARGIN, **overrides}


def _periods_display(periods: list[str], n: int) -> list[str]:
    """Son n dönemi al, eski → yeni sırayla."""
    return list(reversed(periods[:n]))


def _series(m: dict, key: str, periods: list[str], scale: float = 1.0) -> list[float | None]:
    bucket = m.get(key, {})
    return [(v / scale if v is not None else None) for v in (bucket.get(p) for p in periods)]


def _empty_fig(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(
        text=msg, x=0.5, y=0.5,
        xref="paper", yref="paper", showarrow=False,
        font={"color": _C["gray"], "size": 14},
    )
    fig.update_layout(**_layout())
    return fig


# ---------------------------------------------------------------------------
# Sekme 1: KPI Özet Tablosu
# ---------------------------------------------------------------------------

def _chart_kpi_table(m: dict, n: int) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    if not pds:
        return _empty_fig("Veri bulunamadı")

    kpi_defs = [
        ("Satışlar (mn)",   "satis",          1e6, "abs"),
        ("FAVÖK (mn)",      "favok",          1e6, "abs"),
        ("Net Kar (mn)",    "net_kar",        1e6, "abs"),
        ("Net Borç (mn)",   "net_borc",       1e6, "abs"),
        ("FCF (mn)",        "fcf",            1e6, "abs"),
        ("Brüt Marj %",     "brut_kar_marji", 1,   "pct"),
        ("FAVÖK Marjı %",   "favok_marji",    1,   "pct"),
        ("Net Kar Marj %",  "net_kar_marji",  1,   "pct"),
        ("Net Borç/FAVÖK",  "net_borc_favok", 1,   "ratio"),
        ("Cari Oran",       "cari_oran",      1,   "ratio"),
        ("ROE %",           "roe",            1,   "pct"),
        ("DSO (gün)",       "dso",            1,   "days"),
        ("CCC (gün)",       "ccc",            1,   "days"),
    ]
    labels = [k[0] for k in kpi_defs]
    yoy_data = m.get("_delta", {}).get("yoy", {})

    cell_vals:   list[list[str]] = []
    cell_colors: list[list[str]] = []

    for _, key, scale, kind in kpi_defs:
        row_v, row_c = [], []
        for p in pds:
            val = m.get(key, {}).get(p)
            yoy = yoy_data.get(key, {}).get(p)
            if val is None:
                row_v.append("—"); row_c.append("#334155")
            elif kind == "abs":
                s = f"{val / scale:,.1f}"
                if yoy is not None:
                    s += f"\n{'▲' if yoy > 0 else '▼'}{abs(yoy):.1f}%"
                row_v.append(s)
                row_c.append("#1a3a2a" if (yoy or 0) > 0 else "#3a1a1a" if (yoy or 0) < 0 else "#1e293b")
            elif kind == "pct":
                row_v.append(f"{val:.1f}%"); row_c.append("#1e293b")
            elif kind == "days":
                row_v.append(f"{val:.0f}g"); row_c.append("#1e293b")
            else:
                row_v.append(f"{val:.2f}x"); row_c.append("#1e293b")
        cell_vals.append(row_v)
        cell_colors.append(row_c)

    n_m = len(labels)
    n_p = len(pds)
    col_vals   = [[cell_vals[mi][pi]   for mi in range(n_m)] for pi in range(n_p)]
    col_colors = [[cell_colors[mi][pi] for mi in range(n_m)] for pi in range(n_p)]

    currency = m.get("currency", "TRY")
    fig = go.Figure(go.Table(
        header=dict(
            values=["<b>Metrik</b>"] + [f"<b>{p}</b>" for p in pds],
            fill_color=_C["bg"],
            font=dict(color=_C["text"], size=11),
            align="left", height=30,
        ),
        cells=dict(
            values=[labels, *col_vals],
            fill_color=[_C["bg"]] + col_colors,
            font=dict(color=_C["text"], size=11),
            align=["left"] + ["right"] * n_p,
            height=36,
        ),
    ))
    fig.update_layout(**{**_layout(margin={"t": 60, "b": 10, "l": 10, "r": 10}),
                         "title": f"{m.get('ticker', '')} — KPI Özeti ({currency})"})
    return fig


# ---------------------------------------------------------------------------
# Sekme 2: Satışlar & Marjlar
# ---------------------------------------------------------------------------

def _chart_satis_favok(m: dict, n: int) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    if not pds:
        return _empty_fig("Satış verisi bulunamadı")

    mn      = 1e6
    sats    = _series(m, "satis",          pds, mn)
    fav     = _series(m, "favok_marji",    pds)
    bmt     = _series(m, "brut_kar_marji", pds)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=pds, y=sats, name="Satışlar (mn)",
        marker_color=_C["blue"], opacity=0.85,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=pds, y=fav, name="FAVÖK Marjı %",
        line={"color": _C["orange"], "width": 2.5},
        mode="lines+markers", marker={"size": 6},
    ), secondary_y=True)
    fig.add_trace(go.Scatter(
        x=pds, y=bmt, name="Brüt Marj %",
        line={"color": _C["green"], "width": 1.5, "dash": "dot"},
        mode="lines+markers", marker={"size": 4},
    ), secondary_y=True)

    currency = m.get("currency", "TRY")
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Satışlar & Karlılık Marjları ({currency})",
        legend={"bgcolor": "rgba(0,0,0,0)", "x": 0.01, "y": 0.99},
    ))
    fig.update_yaxes(title_text=f"Satışlar (mn {currency})", secondary_y=False,
                     gridcolor=_C["grid"])
    fig.update_yaxes(title_text="Marj %", secondary_y=True,
                     gridcolor=_C["grid"], ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# Sekme 3: Bilanço Yapısı
# ---------------------------------------------------------------------------

def _chart_bilanco(m: dict, n: int) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    if not pds:
        return _empty_fig("Bilanço verisi bulunamadı")

    mn   = 1e6
    don  = _series(m, "donen_varlik",      pds, mn)
    kvy  = _series(m, "kisa_vadeli_yukuml", pds, mn)
    ozk  = _series(m, "ozkaynak",          pds, mn)
    nb   = _series(m, "net_borc",          pds, mn)

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Aktif Yapısı (Dönen)", "Pasif Yapısı"),
    )
    fig.add_trace(go.Bar(
        x=pds, y=don, name="Dönen Varlık",
        marker_color=_C["blue"], opacity=0.9,
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=pds, y=kvy, name="K.V. Yükümlülük",
        marker_color=_C["red"], opacity=0.85,
    ), row=1, col=2)
    fig.add_trace(go.Bar(
        x=pds, y=ozk, name="Özkaynak",
        marker_color=_C["green"], opacity=0.85,
    ), row=1, col=2)

    currency = m.get("currency", "TRY")
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Bilanço Yapısı ({currency})",
        barmode="stack",
        legend={"bgcolor": "rgba(0,0,0,0)"},
    ))
    for col in [1, 2]:
        fig.update_yaxes(
            gridcolor=_C["grid"], linecolor=_C["grid"],
            title_text=f"mn {currency}", row=1, col=col,
        )
    return fig


# ---------------------------------------------------------------------------
# HTML üreticisi — tek dosya, tab navigasyonu, yerel Plotly JS
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

_CHART_OPTS = {"responsive": True, "displayModeBar": True}


def _fig_to_div(fig: go.Figure) -> str:
    return fig.to_html(full_html=False, include_plotlyjs=False, config=_CHART_OPTS)


def build_dashboard(m: dict[str, Any], n_periods: int = 8) -> str:
    """
    Tek HTML dosyası olarak finansal dashboard üret (3 sekme).
    Plotly JS yerel dosyadan yüklenir (CDN bağımlılığı yok).
    """
    ticker   = m.get("ticker", "")
    currency = m.get("currency", "TRY")

    tabs = [
        ("kpi",     "📊 KPI Özeti",         _chart_kpi_table(m, n_periods)),
        ("satis",   "📈 Satışlar & Marjlar", _chart_satis_favok(m, n_periods)),
        ("bilanco", "🏦 Bilanço",            _chart_bilanco(m, n_periods)),
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

    # Yerel Plotly JS (temp dosya — uygulama başlangıcında üretilir)
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
        + panes +
        f"\n<script>\n{_JS}\n</script>\n"
        "</body>\n</html>"
    )
