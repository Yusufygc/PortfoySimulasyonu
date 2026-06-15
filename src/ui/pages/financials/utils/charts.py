"""
Finansal dashboard grafik fonksiyonları.

Tüm _chart_* builder'lar ve paylaşılan yardımcılar burada.
dashboard_html.py yalnız orkestratör olarak build_dashboard'u içerir.
"""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ---------------------------------------------------------------------------
# Renk paleti ve düzen sabitleri (koyu tema)
# ---------------------------------------------------------------------------

_C = {
    "blue":   "#00D4FF",
    "green":  "#22c55e",
    "red":    "#ef4444",
    "orange": "#f97316",
    "purple": "#a855f7",
    "teal":   "#14b8a6",
    "gray":   "#64748b",
    "text":   "#f1f5f9",
    "grid":   "#334155",
    "bg":     "#0f172a",
    "panel":  "#1e293b",
}

_LAYOUT_BASE = {
    "paper_bgcolor": _C["bg"],
    "plot_bgcolor":  _C["panel"],
    "font":  {"color": _C["text"], "family": "Inter, Segoe UI, sans-serif", "size": 12},
    "xaxis": {"gridcolor": _C["grid"], "linecolor": _C["grid"]},
    "yaxis": {"gridcolor": _C["grid"], "linecolor": _C["grid"]},
}
_MARGIN = {"t": 60, "b": 50, "l": 70, "r": 30}


def _layout(height: int = 520, **overrides) -> dict:
    return {**_LAYOUT_BASE, "margin": _MARGIN, "height": height, **overrides}


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


def _fig_to_div(fig: go.Figure) -> str:
    return fig.to_html(
        full_html=False, include_plotlyjs=False,
        config={"responsive": True, "displayModeBar": True},
    )


# ---------------------------------------------------------------------------
# Sekme: KPI Özet Tablosu
# ---------------------------------------------------------------------------

_KPI_DEFS = [
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


def _kpi_cell(val: float | None, yoy: float | None, scale: float, kind: str) -> tuple[str, str]:
    if val is None:
        return "—", "#334155"
    if kind == "abs":
        s = f"{val / scale:,.1f}"
        if yoy is not None:
            s += f"\n{'▲' if yoy > 0 else '▼'}{abs(yoy):.1f}%"
        color = "#1a3a2a" if (yoy or 0) > 0 else "#3a1a1a" if (yoy or 0) < 0 else "#1e293b"
        return s, color
    if kind == "pct":
        return f"{val:.1f}%", "#1e293b"
    if kind == "days":
        return f"{val:.0f}g", "#1e293b"
    return f"{val:.2f}x", "#1e293b"


def _chart_kpi_table(m: dict, n: int) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    if not pds:
        return _empty_fig("Veri bulunamadı")

    yoy_data = m.get("_delta", {}).get("yoy", {})
    labels = [k[0] for k in _KPI_DEFS]
    cell_vals:   list[list[str]] = []
    cell_colors: list[list[str]] = []

    for _, key, scale, kind in _KPI_DEFS:
        row_v, row_c = [], []
        for p in pds:
            val = m.get(key, {}).get(p)
            yoy = yoy_data.get(key, {}).get(p)
            v_str, v_clr = _kpi_cell(val, yoy, scale, kind)
            row_v.append(v_str)
            row_c.append(v_clr)
        cell_vals.append(row_v)
        cell_colors.append(row_c)

    n_p = len(pds)
    col_vals   = [[cell_vals[mi][pi]   for mi in range(len(labels))] for pi in range(n_p)]
    col_colors = [[cell_colors[mi][pi] for mi in range(len(labels))] for pi in range(n_p)]
    currency = m.get("currency", "TRY")

    fig = go.Figure(go.Table(
        header=dict(
            values=["<b>Metrik</b>"] + [f"<b>{p}</b>" for p in pds],
            fill_color=_C["bg"], font=dict(color=_C["text"], size=11),
            align="left", height=30,
        ),
        cells=dict(
            values=[labels, *col_vals],
            fill_color=[_C["bg"]] + col_colors,
            font=dict(color=_C["text"], size=11),
            align=["left"] + ["right"] * n_p, height=36,
        ),
    ))
    usd_note = " ⚠ USD verisi yaklaşık — isyatirim.com.tr kaynaklı" if currency != "TRY" else ""
    fig.update_layout(**{
        **_layout(height=480, margin={"t": 60, "b": 10, "l": 10, "r": 10}),
        "title": f"{m.get('ticker', '')} — KPI Özeti ({currency}){usd_note}",
    })
    return fig


# ---------------------------------------------------------------------------
# Sekme: Satışlar & Marjlar
# ---------------------------------------------------------------------------

def _chart_satis_favok(m: dict, n: int) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    if not pds:
        return _empty_fig("Satış verisi bulunamadı")

    mn   = 1e6
    sats = _series(m, "satis",          pds, mn)
    fav  = _series(m, "favok_marji",    pds)
    bmt  = _series(m, "brut_kar_marji", pds)

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
    usd_note = " ⚠ USD verisi yaklaşık — isyatirim.com.tr kaynaklı" if currency != "TRY" else ""
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Satışlar & Karlılık Marjları ({currency}){usd_note}",
        legend={"bgcolor": "rgba(0,0,0,0)", "x": 0.01, "y": 0.99},
    ))
    fig.update_yaxes(title_text=f"Satışlar (mn {currency})", secondary_y=False, gridcolor=_C["grid"])
    fig.update_yaxes(title_text="Marj %", secondary_y=True, gridcolor=_C["grid"], ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# Sekme: Bilanço Yapısı
# ---------------------------------------------------------------------------

def _chart_bilanco(m: dict, n: int) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    if not pds:
        return _empty_fig("Bilanço verisi bulunamadı")

    mn  = 1e6
    don = _series(m, "donen_varlik",      pds, mn)
    kvy = _series(m, "kisa_vadeli_yukuml", pds, mn)
    ozk = _series(m, "ozkaynak",          pds, mn)

    fig = make_subplots(rows=1, cols=2, subplot_titles=("Aktif Yapısı (Dönen)", "Pasif Yapısı"))
    fig.add_trace(go.Bar(
        x=pds, y=don, name="Dönen Varlık", marker_color=_C["blue"], opacity=0.9,
    ), row=1, col=1)
    fig.add_trace(go.Bar(
        x=pds, y=kvy, name="K.V. Yükümlülük", marker_color=_C["red"], opacity=0.85,
    ), row=1, col=2)
    fig.add_trace(go.Bar(
        x=pds, y=ozk, name="Özkaynak", marker_color=_C["green"], opacity=0.85,
    ), row=1, col=2)

    currency = m.get("currency", "TRY")
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Bilanço Yapısı ({currency})",
        barmode="stack", legend={"bgcolor": "rgba(0,0,0,0)"},
    ))
    for col in [1, 2]:
        fig.update_yaxes(gridcolor=_C["grid"], linecolor=_C["grid"],
                         title_text=f"mn {currency}", row=1, col=col)
    return fig


# ---------------------------------------------------------------------------
# Sekme: DuPont Ayrıştırma
# ---------------------------------------------------------------------------

def _chart_dupont(m: dict, n: int) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    nkm = _series(m, "dupont_net_kar_marji", pds)
    vd  = _series(m, "dupont_varlik_devir",  pds)
    fk  = _series(m, "dupont_fin_kaldirac",  pds)
    roe = _series(m, "dupont_roe",           pds)

    if all(v is None for v in roe):
        return _empty_fig("DuPont verisi hesaplanamadı\n(TTM için en az 5 ardışık çeyrek gerekli).")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=pds, y=nkm, name="Net Kar Marjı % (TTM)", marker_color=_C["blue"], opacity=0.8,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=pds, y=vd, name="Varlık Devir Hızı (x)",
        line={"color": _C["teal"], "width": 2}, mode="lines+markers", marker={"size": 5},
    ), secondary_y=True)
    fig.add_trace(go.Scatter(
        x=pds, y=fk, name="Finansal Kaldıraç (x)",
        line={"color": _C["orange"], "width": 2, "dash": "dot"}, mode="lines+markers", marker={"size": 5},
    ), secondary_y=True)
    fig.add_trace(go.Scatter(
        x=pds, y=roe, name="ROE % (DuPont TTM)",
        line={"color": _C["purple"], "width": 3}, mode="lines+markers", marker={"size": 7},
    ), secondary_y=False)

    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — DuPont Ayrıştırma (TTM) | ROE = Marj × Devir × Kaldıraç",
        legend={"bgcolor": "rgba(0,0,0,0)", "x": 0.01, "y": 0.99},
    ))
    fig.update_yaxes(title_text="Marj / ROE (%)", secondary_y=False, gridcolor=_C["grid"], ticksuffix="%")
    fig.update_yaxes(title_text="Oran (x)", secondary_y=True, gridcolor=_C["grid"], ticksuffix="x")
    return fig


# ---------------------------------------------------------------------------
# Sekme: İşletme Sermayesi (DSO / DIO / DPO / CCC)
# ---------------------------------------------------------------------------

def _chart_isletme_sermaye(m: dict, n: int) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    dso = _series(m, "dso", pds)
    dio = _series(m, "dio", pds)
    dpo = _series(m, "dpo", pds)
    ccc = _series(m, "ccc", pds)

    if all(v is None for v in dso):
        return _empty_fig(
            "İşletme sermayesi verisi yok\n"
            "(bankalar için ticari alacak/borç/stok mevcut değildir)."
        )

    dpo_neg = [(-v if v is not None else None) for v in dpo]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=pds, y=dso, name="DSO — Alacak Tahsilat (gün)", marker_color=_C["blue"], opacity=0.8,
    ))
    fig.add_trace(go.Bar(
        x=pds, y=dio, name="DIO — Stok Tutma (gün)", marker_color=_C["teal"], opacity=0.8,
    ))
    fig.add_trace(go.Bar(
        x=pds, y=dpo_neg, name="DPO — Borç Ödeme (gün) [−]", marker_color=_C["red"], opacity=0.7,
    ))
    fig.add_trace(go.Scatter(
        x=pds, y=ccc, name="CCC — Nakit Dönüşüm Döngüsü",
        line={"color": _C["orange"], "width": 3}, mode="lines+markers", marker={"size": 7},
    ))
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — İşletme Sermayesi Döngüsü (Gün)",
        barmode="relative", yaxis_title="Gün", legend={"bgcolor": "rgba(0,0,0,0)"},
    ))
    return fig


# ---------------------------------------------------------------------------
# Sekme: Piotroski F-Score
# ---------------------------------------------------------------------------

_PIOTROSKI_CRIT_LABELS = [
    "F1: Net Kar > 0", "F2: İşletme CF > 0", "F3: ROA Arttı",
    "F4: CF > Net Kar", "F5: UV Borç/Varlık ↓", "F6: Cari Oran ↑",
    "F7: Hisse Artmadı", "F8: Brüt Marj ↑", "F9: Varlık Devir ↑",
]
_PIOTROSKI_CRIT_KEYS = [
    "f1_net_kar_pozitif", "f2_isletme_cf_pozitif", "f3_roa_artan",
    "f4_cf_kar_ustu", "f5_uv_borc_azalan", "f6_cari_oran_artan",
    "f7_hisse_artmadi", "f8_brut_marj_artan", "f9_varlik_devir_artan",
]


def _piotroski_table_trace(detail: dict, p0: str) -> go.Table:
    crit_vals   = [detail.get(k) for k in _PIOTROSKI_CRIT_KEYS]
    crit_strs   = ["✓" if v == 1 else ("✗" if v == 0 else "—") for v in crit_vals]
    crit_colors = [(_C["green"] if v == 1 else (_C["red"] if v == 0 else _C["gray"])) for v in crit_vals]
    row_colors  = ["#1a3a2a" if v == 1 else ("#3a1a1a" if v == 0 else "#1e293b") for v in crit_vals]
    return go.Table(
        header=dict(
            values=["<b>Kriter</b>", f"<b>{p0}</b>"],
            fill_color="#0f172a", font=dict(color=_C["text"], size=10),
            align="left", height=26,
        ),
        cells=dict(
            values=[_PIOTROSKI_CRIT_LABELS, crit_strs],
            fill_color=["#0a1628", row_colors],
            font=dict(color=[_C["text"], crit_colors], size=10),
            align="left", height=28,
        ),
    )


def _chart_piotroski(m: dict, n: int) -> go.Figure:
    pds        = _periods_display(m["periods"], n)
    score_vals = _series(m, "piotroski", pds)

    if all(v is None for v in score_vals):
        return _empty_fig(
            "Piotroski F-Score için yeterli YoY karşılaştırma verisi yok\n"
            "(en az 2 yıl veri gereklidir)."
        )

    p0     = m["periods"][0]
    detail = m.get("_piotroski_detail", {}).get(p0, {})
    fig    = make_subplots(
        rows=1, cols=2, column_widths=[0.52, 0.48],
        specs=[[{"type": "xy"}, {"type": "table"}]],
        subplot_titles=("F-Score Trend (0–9)", f"Kriter Kırılımı ({p0})"),
    )

    bar_colors = [
        (_C["green"] if (v or 0) >= 7 else _C["orange"] if (v or 0) >= 5 else _C["red"])
        for v in score_vals
    ]
    fig.add_trace(go.Bar(
        x=pds, y=score_vals, name="Piotroski Skoru",
        marker_color=bar_colors, opacity=0.85,
        text=[str(int(v)) if v is not None else "" for v in score_vals],
        textposition="outside",
    ), row=1, col=1)
    fig.add_trace(_piotroski_table_trace(detail, p0), row=1, col=2)

    score0    = m.get("piotroski", {}).get(p0)
    score_str = f"{int(score0)}/9" if score0 is not None else "—"
    fig.update_layout(**_layout(
        height=460,
        title=f"{m.get('ticker', '')} — Piotroski F-Score | Son dönem: {score_str}",
        showlegend=False,
    ))
    fig.update_yaxes(range=[0, 10], title_text="F-Score", row=1, col=1, gridcolor=_C["grid"])
    return fig


# ---------------------------------------------------------------------------
# Sekme: Sezonsellik
# ---------------------------------------------------------------------------

def _chart_sezonsellik(m: dict, n: int) -> go.Figure:
    pds         = _periods_display(m["periods"], n)
    mn          = 1e6
    ceyrek_data = m.get("satis_ceyrek", {})

    year_data: dict[str, dict[int, float | None]] = {}
    for p in pds:
        y, mth = p.split("/")
        q = {3: 1, 6: 2, 9: 3, 12: 4}.get(int(mth), 0)
        if q == 0:
            continue
        year_data.setdefault(y, {})[q] = (ceyrek_data.get(p) / mn if ceyrek_data.get(p) is not None else None)

    if not year_data:
        return _empty_fig("Diskret çeyrek verisi hesaplanamadı\n(yetersiz geçmiş veri).")

    years     = sorted(year_data.keys())
    colors_q  = [_C["blue"], _C["teal"], _C["orange"], _C["purple"]]
    currency  = m.get("currency", "TRY")
    fig       = go.Figure()
    for qi, ql in enumerate(["Q1", "Q2", "Q3", "Q4"], 1):
        vals = [year_data.get(y, {}).get(qi) for y in years]
        fig.add_trace(go.Bar(x=years, y=vals, name=ql, marker_color=colors_q[qi - 1], opacity=0.85))

    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Sezonsellik (Diskret Çeyrek Satış, mn {currency})",
        barmode="group", yaxis_title=f"Satış (mn {currency})", legend={"bgcolor": "rgba(0,0,0,0)"},
    ))
    return fig


# ---------------------------------------------------------------------------
# Sekme: Temettü Analizi
# ---------------------------------------------------------------------------

def _chart_temettu(m: dict, n: int) -> go.Figure:
    pds     = _periods_display(m["periods"], n)
    mn      = 1e6
    tem     = _series(m, "temettu_odeme", pds, mn)
    dr      = _series(m, "dagitim_orani", pds)
    nk      = _series(m, "net_kar",       pds, mn)
    tem_abs = [abs(v) if v is not None else None for v in tem]

    if all(v is None for v in tem_abs):
        return _empty_fig("Temettü ödemesi verisi bulunamadı.")

    currency   = m.get("currency", "TRY")
    market_val = m.get("_market_val", {})
    tv         = market_val.get("temettu_verimi") if market_val else None
    tv_str     = f" | Verim: {tv:.2f}%" if tv is not None else ""

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=pds, y=tem_abs, name=f"Temettü Ödemesi (mn {currency})", marker_color=_C["green"], opacity=0.85,
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=pds, y=nk, name=f"Net Kar (mn {currency})", marker_color=_C["blue"], opacity=0.35,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=pds, y=dr, name="Dağıtım Oranı %",
        line={"color": _C["orange"], "width": 2.5}, mode="lines+markers", marker={"size": 6},
    ), secondary_y=True)

    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Temettü Analizi{tv_str}",
        barmode="group", legend={"bgcolor": "rgba(0,0,0,0)"},
    ))
    fig.update_yaxes(title_text=f"mn {currency}", secondary_y=False, gridcolor=_C["grid"])
    fig.update_yaxes(title_text="Dağıtım Oranı %", secondary_y=True, gridcolor=_C["grid"], ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# Sekme: Reel Büyüme (TÜFE-deflate) — _tufe enjekte edilmişse
# ---------------------------------------------------------------------------

def _chart_reel_buyume(m: dict, n: int) -> go.Figure:
    tufe = m.get("_tufe", {})
    if not tufe:
        err = m.get("_tufe_error", "")
        msg = (
            f"TÜFE verisi yüklenemedi.\n{err}"
            if err
            else "TÜFE verisi yok.\nEVDS_API_KEY .env dosyasında tanımlı olmalı."
        )
        return _empty_fig(msg)

    try:
        from src.application.services.analysis.financials.inflation import get_yoy_tufe, real_growth
    except ImportError:
        return _empty_fig("Enflasyon modülü bulunamadı.")

    pds     = _periods_display(m["periods"], n)
    nom_yoy = m.get("_delta", {}).get("yoy", {})
    satis_y = nom_yoy.get("satis", {})
    nk_y    = nom_yoy.get("net_kar", {})

    nom_vals, reel_vals, nk_reel = [], [], []
    for p in pds:
        nom      = satis_y.get(p)
        tufe_yoy = get_yoy_tufe(p, tufe)
        nom_vals.append(nom)
        reel_vals.append(real_growth(nom, tufe_yoy) if (nom is not None and tufe_yoy is not None) else None)
        nk_n = nk_y.get(p)
        nk_reel.append(real_growth(nk_n, tufe_yoy) if (nk_n is not None and tufe_yoy is not None) else None)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=pds, y=nom_vals, name="Nominal Satış YoY %", marker_color=_C["blue"], opacity=0.6))
    fig.add_trace(go.Bar(x=pds, y=reel_vals, name="Reel Satış YoY %", marker_color=_C["teal"], opacity=0.9))
    fig.add_trace(go.Scatter(
        x=pds, y=nk_reel, name="Reel Net Kar YoY %",
        line={"color": _C["orange"], "width": 2}, mode="lines+markers", marker={"size": 5},
    ))
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Reel Büyüme (TÜFE-deflate edilmiş)",
        barmode="group", yaxis_title="YoY % Büyüme", yaxis_ticksuffix="%",
        legend={"bgcolor": "rgba(0,0,0,0)"},
    ))
    return fig


# ---------------------------------------------------------------------------
# Sekme: Değerleme Çarpanları — _market_val enjekte edilmişse
# ---------------------------------------------------------------------------

def _chart_degerleme(m: dict, n: int) -> go.Figure:
    market_val = m.get("_market_val", {})
    if not market_val or market_val.get("error"):
        err = (market_val.get("error") if market_val else None) or ""
        return _empty_fig(f"Piyasa verisi yok{' — ' + err if err else ''}.")

    labels = ["F/K (P/E)", "PD/DD (P/B)", "EV/FAVÖK", "F/S (P/S)"]
    keys   = ["fk", "pddd", "ev_favok", "fs"]
    colors = [_C["blue"], _C["teal"], _C["orange"], _C["purple"]]

    lv = [(l, market_val.get(k), c) for l, k, c in zip(labels, keys, colors) if market_val.get(k) is not None]
    if not lv:
        return _empty_fig("Değerleme çarpanları hesaplanamadı.")

    currency = m.get("currency", "TRY")
    mc       = market_val.get("market_cap")
    mc_str   = f"{mc / 1e9:.1f}B {currency}" if mc else "—"
    period   = market_val.get("period", "")

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[l for l, _, _ in lv], y=[v for _, v, _ in lv],
        marker_color=[c for _, _, c in lv], opacity=0.85,
        text=[f"{v:.1f}x" for _, v, _ in lv], textposition="outside", width=0.45,
    ))
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Değerleme Çarpanları ({period}) | Piyasa Değeri: {mc_str}",
        yaxis_title="Çarpan (x)", yaxis_ticksuffix="x", showlegend=False,
    ))
    return fig


# ---------------------------------------------------------------------------
# Sekme: Net Borç & Kaldıraç
# ---------------------------------------------------------------------------

def _chart_net_borc(m: dict, n: int) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    mn  = 1e6
    nb  = _series(m, "net_borc",       pds, mn)
    nbf = _series(m, "net_borc_favok", pds)

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=pds, y=nb, name="Net Borç (mn)",
        marker_color=[_C["red"] if (v or 0) > 0 else _C["green"] for v in nb],
        opacity=0.8,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=pds, y=nbf, name="Net Borç / FAVÖK",
        line={"color": _C["orange"], "width": 2.5},
        mode="lines+markers", marker={"size": 6},
    ), secondary_y=True)

    currency = m.get("currency", "TRY")
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Net Borç & Kaldıraç ({currency})",
    ))
    fig.update_yaxes(title_text=f"Net Borç (mn {currency})", secondary_y=False, gridcolor=_C["grid"])
    fig.update_yaxes(title_text="Net Borç / FAVÖK (x)", secondary_y=True, gridcolor=_C["grid"], ticksuffix="x")
    return fig


# ---------------------------------------------------------------------------
# Sekme: Gelir Köprüsü (Waterfall — en son dönem)
# ---------------------------------------------------------------------------

def _chart_waterfall(m: dict, n: int) -> go.Figure:
    p = m["periods"][0] if m["periods"] else None
    if not p:
        return _empty_fig("Dönem verisi bulunamadı.")

    def _v(key: str) -> float:
        return m.get(key, {}).get(p) or 0.0

    mn       = 1e6
    satis    = _v("satis")
    brut_kar = _v("brut_kar")
    faal_kar = _v("faaliyet_kar")
    favok    = _v("favok")
    net_kar  = _v("net_kar")

    labels   = ["Satışlar", "Satışların Maliyeti", "Brüt Kar",
                "Opex & Diğer", "Faaliyet Karı", "Amortisman+", "FAVÖK",
                "Faiz/Vergi/Diğer", "Net Kar"]
    values   = [
        satis / mn,               (brut_kar - satis) / mn,    brut_kar / mn,
        (faal_kar - brut_kar) / mn, faal_kar / mn,
        (favok - faal_kar) / mn,    favok / mn,
        (net_kar - favok) / mn,     net_kar / mn,
    ]
    measures = ["absolute", "relative", "total",
                "relative", "total", "relative", "total", "relative", "total"]
    currency = m.get("currency", "TRY")
    fig = go.Figure(go.Waterfall(
        x=labels, y=values, measure=measures,
        connector={"line": {"color": _C["gray"]}},
        decreasing={"marker": {"color": _C["red"]}},
        increasing={"marker": {"color": _C["green"]}},
        totals={"marker": {"color": _C["blue"]}},
        textposition="outside",
        text=[f"{v:,.0f}" if v else "" for v in values],
    ))
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Gelir Köprüsü ({p}, mn {currency})",
        yaxis_title=f"mn {currency}",
    ))
    return fig


# ---------------------------------------------------------------------------
# Sekme: FCF vs Net Kar (Kazanç Kalitesi)
# ---------------------------------------------------------------------------

def _chart_fcf_vs_netkar(m: dict, n: int) -> go.Figure:
    pds  = _periods_display(m["periods"], n)
    mn   = 1e6
    fcf  = _series(m, "fcf",     pds, mn)
    nkar = _series(m, "net_kar", pds, mn)

    currency = m.get("currency", "TRY")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pds, y=fcf, name="Serbest Nakit Akım",
        fill="tozeroy", line={"color": _C["green"], "width": 2},
        fillcolor="rgba(34,197,94,0.15)",
    ))
    fig.add_trace(go.Scatter(
        x=pds, y=nkar, name="Net Kar",
        line={"color": _C["orange"], "width": 2, "dash": "dash"},
        mode="lines+markers", marker={"size": 5},
    ))
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — FCF vs Net Kar ({currency})",
        yaxis_title=f"mn {currency}",
    ))
    return fig


# ---------------------------------------------------------------------------
# Sekme: Nakit Akış Çubuk Grafiği
# ---------------------------------------------------------------------------

def _chart_nakit_akis(m: dict, n: int) -> go.Figure:
    pds  = _periods_display(m["periods"], n)
    mn   = 1e6
    islt = _series(m, "isletme_cf", pds, mn)
    fcf  = _series(m, "fcf",        pds, mn)
    cpx  = _series(m, "capex",      pds, mn)

    currency = m.get("currency", "TRY")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=pds, y=islt, name="İşletme CF",          marker_color=_C["blue"],  opacity=0.85))
    fig.add_trace(go.Bar(x=pds, y=fcf,  name="Serbest Nakit Akım",  marker_color=_C["green"], opacity=0.85))
    fig.add_trace(go.Bar(x=pds, y=cpx,  name="Capex",               marker_color=_C["red"],   opacity=0.85))
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Nakit Akış ({currency})",
        barmode="group", yaxis_title=f"mn {currency}",
    ))
    return fig


# ---------------------------------------------------------------------------
# Sekme: YoY Isı Haritası
# ---------------------------------------------------------------------------

_HEATMAP_METRICS = [
    ("Satışlar",     "satis"),
    ("FAVÖK",        "favok"),
    ("Net Kar",      "net_kar"),
    ("FCF",          "fcf"),
    ("Net Borç",     "net_borc"),
    ("FAVÖK Marjı",  "favok_marji"),
    ("Net Kar Marj", "net_kar_marji"),
    ("ROE",          "roe"),
]


def _chart_heatmap(m: dict, n: int) -> go.Figure:
    pds  = _periods_display(m["periods"], n)
    yoy  = m.get("_delta", {}).get("yoy", {})
    z_vals: list[list] = []
    annotations: list[dict] = []

    for label, key in _HEATMAP_METRICS:
        row: list = []
        for p in pds:
            v = yoy.get(key, {}).get(p)
            row.append(v)
            annotations.append(dict(
                x=p, y=label, text=(f"{v:+.1f}%" if v is not None else "—"),
                showarrow=False, font=dict(color="white", size=10),
            ))
        z_vals.append(row)

    labels = [k[0] for k in _HEATMAP_METRICS]
    fig = go.Figure(go.Heatmap(
        z=z_vals, x=pds, y=labels,
        colorscale=[[0.0,"#7f1d1d"],[0.35,"#1a3a2a"],[0.5,"#1e293b"],[0.65,"#14532d"],[1.0,"#052e16"]],
        zmid=0, zmin=-50, zmax=50, showscale=True,
        colorbar=dict(title="YoY %", ticksuffix="%"),
    ))
    fig.update_layout(**_layout(
        height=420,
        title=f"{m.get('ticker', '')} — YoY % Değişim Isı Haritası",
        annotations=annotations,
        xaxis=dict(side="top", gridcolor=_C["grid"]),
        yaxis=dict(gridcolor=_C["grid"], autorange="reversed"),
    ))
    return fig


# ---------------------------------------------------------------------------
# Sekme: Bedelsiz Potansiyel (helper + ana fn)
# ---------------------------------------------------------------------------

def _bedelsiz_ef_info(m: dict, p0: str | None) -> tuple[str, str]:
    """(subtitle, ef_color) — enflasyon muhasebesi durumuna göre."""
    bx0 = m.get("bedelsiz_potansiyel_x",  {}).get(p0)
    bp0 = m.get("bedelsiz_potansiyel_pct", {}).get(p0)
    ef0 = m.get("enflasyon_duzeltildi",    {}).get(p0)
    ef_text  = "✓ Enflasyon muhasebesi uygulanmış (TMS 29)" if ef0 else "⚠ Nominal — enflasyon düzeltmesi uygulanmamış"
    ef_color = _C["green"] if ef0 else _C["orange"]
    subtitle = f"{bx0:.2f}x  (~%{bp0:.0f})  |  {ef_text}" if bx0 is not None else ef_text
    return subtitle, ef_color


def _chart_bedelsiz(m: dict, n: int) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    bx  = _series(m, "bedelsiz_potansiyel_x", pds)
    ozk = _series(m, "ozkaynak",              pds, 1e9)
    sem = _series(m, "odenmis_sermaye",        pds, 1e9)

    p0               = m["periods"][0] if m["periods"] else None
    subtitle, ef_color = _bedelsiz_ef_info(m, p0)
    currency         = m.get("currency", "TRY")

    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=pds, y=bx, name="Bedelsiz Potansiyel (x)", marker_color=_C["purple"], opacity=0.85,
        text=[f"{v:.1f}x" if v is not None else "" for v in bx], textposition="outside",
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=pds, y=ozk, name=f"Özkaynak (milyar {currency})",
        line={"color": _C["teal"], "width": 2}, mode="lines+markers", marker={"size": 5},
    ), secondary_y=True)
    fig.add_trace(go.Scatter(
        x=pds, y=sem, name=f"Ödenmiş Sermaye (milyar {currency})",
        line={"color": _C["gray"], "width": 1.5, "dash": "dot"}, mode="lines+markers", marker={"size": 4},
    ), secondary_y=True)
    fig.update_layout(**_layout(
        title={"text": (f"{m.get('ticker', '')} — Bedelsiz Potansiyel & Özkaynak ({currency})<br>"
                        f"<sup><span style='color:{ef_color}'>{subtitle}</span></sup>"),
               "font": {"size": 14}},
        legend={"bgcolor": "rgba(0,0,0,0)", "x": 0.01, "y": 0.99},
    ))
    fig.update_yaxes(title_text="Bedelsiz Pot. (x)", secondary_y=False, gridcolor=_C["grid"], ticksuffix="x")
    fig.update_yaxes(title_text=f"Milyar {currency}", secondary_y=True, gridcolor=_C["grid"])
    return fig


# ---------------------------------------------------------------------------
# Sekme: Yurtiçi / Yurtdışı Satış Kırılımı
# ---------------------------------------------------------------------------

def _chart_satis_breakdown(m: dict, n: int) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    mn  = 1e6
    yi  = _series(m, "yurtici_satis",  pds, mn)
    yd  = _series(m, "yurtdisi_satis", pds, mn)
    ihr = _series(m, "ihracat_orani",  pds)

    if all(v is None for v in yi) and all(v is None for v in yd):
        return _empty_fig(
            "Yurtiçi/Yurtdışı satış verisi bulunamadı\n"
            "(bankalar için dipnot verisi mevcut değildir)"
        )

    currency = m.get("currency", "TRY")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    fig.add_trace(go.Bar(
        x=pds, y=yi, name=f"Yurtiçi (mn {currency})", marker_color=_C["blue"], opacity=0.85,
    ), secondary_y=False)
    fig.add_trace(go.Bar(
        x=pds, y=yd, name=f"Yurtdışı / İhracat (mn {currency})", marker_color=_C["teal"], opacity=0.85,
    ), secondary_y=False)
    fig.add_trace(go.Scatter(
        x=pds, y=ihr, name="İhracat Oranı %",
        line={"color": _C["orange"], "width": 2.5}, mode="lines+markers", marker={"size": 6},
    ), secondary_y=True)
    fig.update_layout(**_layout(
        title=f"{m.get('ticker', '')} — Yurtiçi / Yurtdışı Satış Kırılımı ({currency})",
        barmode="stack", legend={"bgcolor": "rgba(0,0,0,0)", "x": 0.01, "y": 0.99},
    ))
    fig.update_yaxes(title_text=f"Satışlar (mn {currency})", secondary_y=False, gridcolor=_C["grid"])
    fig.update_yaxes(title_text="İhracat Oranı %", secondary_y=True, gridcolor=_C["grid"], ticksuffix="%")
    return fig
