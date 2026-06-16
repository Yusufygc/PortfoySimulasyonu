"""
peer_viz.py — Peer Karşılaştırma Dashboard

Birden fazla hisse için metrikler yan yana karşılaştırılır.

Kullanım:
    python run.py FROTO TOASO OTKAR --peer --open
    # → data/peer_FROTO_TOASO_OTKAR.html

Import:
    from peer_viz import build_peer_dashboard
    html = build_peer_dashboard([m_froto, m_toaso, m_otkar])
"""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Renk paleti: viz_prototype.py ile aynı koyu tema
_C = {
    "blue":     "#00D4FF",
    "green":    "#22c55e",
    "red":      "#ef4444",
    "orange":   "#f97316",
    "purple":   "#a855f7",
    "teal":     "#14b8a6",
    "yellow":   "#eab308",
    "pink":     "#ec4899",
    "gray":     "#64748b",
    "light_bg": "#1e293b",
    "text":     "#f1f5f9",
    "grid":     "#334155",
}

# Birden fazla hisse için farklı renkler
_TICKER_COLORS = [
    _C["blue"], _C["green"], _C["orange"], _C["purple"],
    _C["teal"], _C["yellow"], _C["pink"], _C["red"],
]

_LAYOUT_DEFAULTS = {
    "paper_bgcolor": "#0f172a",
    "plot_bgcolor":  "#1e293b",
    "font":          {"color": _C["text"], "family": "Inter, Segoe UI, sans-serif", "size": 12},
    "xaxis":         {"gridcolor": _C["grid"], "linecolor": _C["grid"]},
    "yaxis":         {"gridcolor": _C["grid"], "linecolor": _C["grid"]},
}
_MARGIN = {"t": 60, "b": 40, "l": 60, "r": 20}


def _layout(**overrides) -> dict:
    return {**_LAYOUT_DEFAULTS, "margin": _MARGIN, **overrides}


def _periods_display(periods: list[str], n: int) -> list[str]:
    return list(reversed(periods[:n]))


def _get_series(m: dict, key: str, periods: list[str], scale: float = 1.0) -> list[float | None]:
    bucket = m.get(key, {})
    return [(v / scale if v is not None else None) for v in (bucket.get(p) for p in periods)]


# ---------------------------------------------------------------------------
# Metrik kataloğu — peer karşılaştırmada gösterilecek metrikler
# ---------------------------------------------------------------------------

PEER_METRICS: list[dict[str, Any]] = [
    # label, key, scale, unit, higher_is_better
    {"label": "Satışlar (mn TRY)",     "key": "satis",            "scale": 1e6,  "unit": "mn",  "hib": True},
    {"label": "FAVÖK (mn TRY)",        "key": "favok",            "scale": 1e6,  "unit": "mn",  "hib": True},
    {"label": "Net Kar (mn TRY)",      "key": "net_kar",          "scale": 1e6,  "unit": "mn",  "hib": True},
    {"label": "FAVÖK Marjı %",         "key": "favok_marji",      "scale": 1,    "unit": "%",   "hib": True},
    {"label": "Net Kar Marjı %",       "key": "net_kar_marji",    "scale": 1,    "unit": "%",   "hib": True},
    {"label": "Brüt Marj %",          "key": "brut_kar_marji",   "scale": 1,    "unit": "%",   "hib": True},
    {"label": "ROE %",                 "key": "roe",              "scale": 1,    "unit": "%",   "hib": True},
    {"label": "ROA %",                 "key": "roa",              "scale": 1,    "unit": "%",   "hib": True},
    {"label": "Net Borç/FAVÖK",        "key": "net_borc_favok",   "scale": 1,    "unit": "x",   "hib": False},
    {"label": "Cari Oran",             "key": "cari_oran",        "scale": 1,    "unit": "x",   "hib": True},
    {"label": "DSO (gün)",             "key": "dso",              "scale": 1,    "unit": "g",   "hib": False},
    {"label": "DIO (gün)",             "key": "dio",              "scale": 1,    "unit": "g",   "hib": False},
    {"label": "DPO (gün)",             "key": "dpo",              "scale": 1,    "unit": "g",   "hib": True},
    {"label": "CCC (gün)",             "key": "ccc",              "scale": 1,    "unit": "g",   "hib": False},
    {"label": "FCF (mn TRY)",          "key": "fcf",              "scale": 1e6,  "unit": "mn",  "hib": True},
    {"label": "İhracat Oranı %",       "key": "ihracat_orani",    "scale": 1,    "unit": "%",   "hib": None},
    {"label": "Piotroski F-Score",     "key": "piotroski",        "scale": 1,    "unit": "/9",  "hib": True},
    {"label": "Bedelsiz Potansiyel x", "key": "bedelsiz_potansiyel_x", "scale": 1, "unit": "x", "hib": True},
    {"label": "DuPont ROE % (TTM)",    "key": "dupont_roe",       "scale": 1,    "unit": "%",   "hib": True},
]

# label → meta
_METRIC_MAP = {d["label"]: d for d in PEER_METRICS}


def _all_periods(metrics_list: list[dict], n: int) -> list[str]:
    """Tüm metrics dictleri için ortak dönem listesi (kesişim, yeniden eskiye)."""
    if not metrics_list:
        return []
    sets = [set(m.get("periods", [])[:n]) for m in metrics_list]
    common = sets[0]
    for s in sets[1:]:
        common = common & s
    # Sıralama: ilk metrics'in orijinal sırasına göre
    ref_order = metrics_list[0].get("periods", [])
    sorted_common = [p for p in ref_order if p in common][:n]
    return list(reversed(sorted_common))  # eski→yeni


def _overlay_chart(
    metrics_list: list[dict],
    meta: dict,
    periods: list[str],
) -> go.Figure:
    """Seçilen metrik için çoklu hisse overlay çizgi/çubuk grafiği."""
    key   = meta["key"]
    scale = meta["scale"]
    unit  = meta["unit"]
    label = meta["label"]

    fig = go.Figure()
    for i, m in enumerate(metrics_list):
        ticker = m.get("ticker", f"Hisse{i+1}")
        color  = _TICKER_COLORS[i % len(_TICKER_COLORS)]
        pds    = [p for p in periods if p in m.get("periods", [])]
        vals   = _get_series(m, key, pds, scale)

        fig.add_trace(go.Scatter(
            x=pds, y=vals,
            name=ticker,
            line={"color": color, "width": 2.5},
            mode="lines+markers",
            marker={"size": 6},
        ))

    fig.update_layout(**_layout(
        title=f"Peer Karşılaştırma — {label}",
        yaxis_title=label,
        yaxis_ticksuffix=unit if unit in ("%", "x") else "",
        legend={"bgcolor": "rgba(0,0,0,0)"},
    ))
    return fig


def _ranking_table(
    metrics_list: list[dict],
    period: str,
) -> go.Figure:
    """Son dönem için tüm metriklerde sıralama tablosu."""
    tickers = [m.get("ticker", f"H{i}") for i, m in enumerate(metrics_list)]
    n_t     = len(tickers)

    row_labels: list[str] = []
    col_vals:   list[list[str]] = [[] for _ in range(n_t)]

    for meta in PEER_METRICS:
        key    = meta["key"]
        scale  = meta["scale"]
        unit   = meta["unit"]
        label  = meta["label"]
        hib    = meta["hib"]  # higher is better

        vals_raw = [m.get(key, {}).get(period) for m in metrics_list]
        if all(v is None for v in vals_raw):
            continue

        row_labels.append(label)

        # Sıralama için rank hesapla
        valid = [(v / scale, i) for i, v in enumerate(vals_raw) if v is not None]
        if hib is True:
            ranked = sorted(valid, key=lambda x: -x[0])
        elif hib is False:
            ranked = sorted(valid, key=lambda x:  x[0])
        else:
            ranked = valid  # sıralama yok

        rank_map = {idx: rank for rank, (_, idx) in enumerate(ranked)}

        for i, v in enumerate(vals_raw):
            if v is None:
                col_vals[i].append("—")
            else:
                scaled = v / scale
                if unit == "%":
                    col_vals[i].append(f"{scaled:.1f}%")
                elif unit == "x":
                    col_vals[i].append(f"{scaled:.2f}x")
                elif unit == "mn":
                    col_vals[i].append(f"{scaled:,.0f}")
                elif unit == "g":
                    col_vals[i].append(f"{scaled:.0f}g")
                else:
                    col_vals[i].append(f"{scaled:.2f}")

    if not row_labels:
        fig = go.Figure()
        fig.add_annotation(text="Ortak veri bulunamadı", x=0.5, y=0.5,
                           xref="paper", yref="paper", showarrow=False)
        return fig

    header_vals = ["<b>Metrik</b>"] + [f"<b>{t}</b>" for t in tickers]
    cell_vals   = [row_labels] + col_vals

    fig = go.Figure(go.Table(
        header=dict(
            values=header_vals,
            fill_color="#0f172a",
            font=dict(color=_C["text"], size=11),
            align="left", height=30,
        ),
        cells=dict(
            values=cell_vals,
            fill_color=["#0a1628"] + ["#1e293b"] * n_t,
            font=dict(color=_C["text"], size=11),
            align=["left"] + ["right"] * n_t,
            height=28,
        ),
    ))

    fig.update_layout(
        paper_bgcolor="#0f172a",
        font={"color": _C["text"], "family": "Inter, Segoe UI, sans-serif", "size": 12},
        margin={"t": 50, "b": 10, "l": 10, "r": 10},
        title=f"Son Dönem Karşılaştırma ({period})",
    )
    return fig


# ---------------------------------------------------------------------------
# Ana API
# ---------------------------------------------------------------------------

def build_peer_dashboard(
    metrics_list: list[dict],
    n_periods: int = 8,
) -> str:
    """
    Peer karşılaştırma HTML dashboard üret.

    Args:
        metrics_list: Her hisse için compute_metrics() çıktısı.
        n_periods:    Grafiklerde gösterilecek max dönem.

    Returns:
        HTML string.
    """
    import json as _json

    if not metrics_list:
        return "<html><body>Veri yok</body></html>"

    tickers  = [m.get("ticker", f"H{i}") for i, m in enumerate(metrics_list)]
    title    = " vs ".join(tickers)
    periods  = _all_periods(metrics_list, n_periods)
    p0       = periods[-1] if periods else ""  # en güncel (son eleman = newest)
    # Aslında _all_periods eski→yeni döndürür, newest = son eleman
    all_per0 = metrics_list[0].get("periods", [])
    p0       = all_per0[0] if all_per0 else ""  # newest from first metrics

    # ----- Overlay grafikleri (her PEER_METRICS için bir grafik) -----
    overlay_figs = [
        (meta["label"], _overlay_chart(metrics_list, meta, periods))
        for meta in PEER_METRICS
    ]

    # ----- Sıralama tablosu -----
    ranking_fig = _ranking_table(metrics_list, p0)

    # ----- HTML yapısı -----
    _css = (
        "*, *::before, *::after{box-sizing:border-box;margin:0;padding:0}"
        "body{background:#0f172a;color:#f1f5f9;font-family:Inter,'Segoe UI',sans-serif;padding:16px}"
        "h1{color:#00D4FF;font-size:1.4rem;margin-bottom:4px}"
        ".sub{color:#94a3b8;font-size:.85rem;margin-bottom:12px}"
        ".tab-nav{display:flex;flex-wrap:wrap;gap:3px;border-bottom:2px solid #334155;padding-bottom:0;margin-bottom:0}"
        ".tab-btn{background:#1e293b;color:#94a3b8;border:1px solid #334155;"
            "border-radius:5px 5px 0 0;border-bottom:none;padding:5px 12px;"
            "cursor:pointer;font-size:.75rem;white-space:nowrap;transition:background .12s}"
        ".tab-btn:hover{background:#2d3f53;color:#f1f5f9}"
        ".tab-btn.active{background:#0f172a;color:#00D4FF;border-color:#334155;"
            "border-bottom:2px solid #0f172a;margin-bottom:-2px}"
        ".tab-pane{display:none;border:1px solid #334155;border-top:none;"
            "border-radius:0 0 8px 8px;background:#0f172a;padding:8px}"
        ".tab-pane.active{display:block}"
    )

    _js = r"""
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

    # Nav + pane için tüm sekmeler
    all_tabs = [("ranking", "📊 Sıralama Tablosu", ranking_fig)] + \
               [(f"m_{i}", lbl, fig) for i, (lbl, fig) in enumerate(overlay_figs)]

    nav = "".join(
        f"<button class='tab-btn{' active' if i == 0 else ''}' "
        f"onclick=\"showTab('{tid}',this)\">{lbl}</button>"
        for i, (tid, lbl, _) in enumerate(all_tabs)
    )

    panes = "".join(
        f"<div id='{tid}' class='tab-pane{' active' if i == 0 else ''}'>"
        + fig.to_html(full_html=False, include_plotlyjs=False,
                      config={"responsive": True, "displayModeBar": True})
        + "</div>"
        for i, (tid, _, fig) in enumerate(all_tabs)
    )

    return (
        "<!DOCTYPE html>\n<html lang='tr'>\n<head>\n"
        "<meta charset='utf-8'>\n"
        f"<title>{title} — Peer Karşılaştırma</title>\n"
        "<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>\n"
        f"<style>{_css}</style>\n"
        "</head>\n<body>\n"
        f"<h1>{title} — Peer Karşılaştırma</h1>\n"
        f"<p class='sub'>Kaynak: isyatirim.com.tr | Son güncelleme: {p0}</p>\n"
        f"<nav class='tab-nav'>{nav}</nav>\n"
        + panes +
        f"\n<script>\n{_js}\n</script>\n"
        "</body>\n</html>"
    )
