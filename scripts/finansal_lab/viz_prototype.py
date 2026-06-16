"""
viz_prototype.py — Finansal Görselleştirme Prototipi (Plotly)

Grafik kataloğu:
  1. Bar+Line combo : Satışlar (bar) + FAVÖK Marjı % (line)
  2. Stacked bar    : Aktif = Dönen + Duran / Pasif = KVY + UVY + Özkaynak
  3. Line           : Net Borç ve Net Borç/FAVÖK trend
  4. KPI tablosu    : 6 metrik + YoY % değişim (renk kodlu)
  5. Waterfall      : Gelir Köprüsü (Satış → Brüt Kar → FAVÖK → Net Kar)
  6. FCF vs Net Kar : Kazanç kalitesi (area)
  7. Nakit Akış     : İşletme / Yatırım / Finansman CF (3-renk bar)
  8. Heatmap        : Dönem × Metrik % değişim ısı haritası

Kullanım:
    python viz_prototype.py                        # veri yoksa scrape eder
    python viz_prototype.py FROTO 16               # 16 çeyrek
    python viz_prototype.py FROTO 16 --no-scrape   # sadece mevcut JSON'ı oku

Import:
    from viz_prototype import build_dashboard
    html = build_dashboard(metrics_dict, ticker="FROTO")
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path
from typing import Any

import plotly.graph_objects as go
import plotly.subplots as sp
from plotly.subplots import make_subplots

def _fix_stdout() -> None:
    """Windows cp1254 fix — yalnızca CLI entry-point'te çağır."""
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "") != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "") != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


LAB_DIR = Path(__file__).parent

# Renk paleti (koyu tema uyumlu)
_C = {
    "blue":      "#00D4FF",
    "green":     "#22c55e",
    "red":       "#ef4444",
    "orange":    "#f97316",
    "purple":    "#a855f7",
    "teal":      "#14b8a6",
    "gray":      "#64748b",
    "light_bg":  "#1e293b",
    "text":      "#f1f5f9",
    "grid":      "#334155",
}

_LAYOUT_DEFAULTS = {
    "paper_bgcolor": "#0f172a",
    "plot_bgcolor":  "#1e293b",
    "font":          {"color": _C["text"], "family": "Inter, Segoe UI, sans-serif", "size": 12},
    "xaxis":         {"gridcolor": _C["grid"], "linecolor": _C["grid"]},
    "yaxis":         {"gridcolor": _C["grid"], "linecolor": _C["grid"]},
}

_MARGIN_DEFAULT = {"t": 60, "b": 40, "l": 60, "r": 20}
_MARGIN_TABLE   = {"t": 60, "b": 10, "l": 10, "r": 10}


def _layout(margin: dict | None = None, **overrides) -> dict:
    """_LAYOUT_DEFAULTS + margin + overrides — tekrar eden key yok."""
    return {**_LAYOUT_DEFAULTS, "margin": margin or _MARGIN_DEFAULT, **overrides}


def _periods_display(periods: list[str], n: int) -> list[str]:
    """Son n dönemi al, eski→yeni sırasında döndür."""
    return list(reversed(periods[:n]))


def _series(m: dict, key: str, periods: list[str], scale: float = 1.0) -> list[float | None]:
    bucket = m.get(key, {})
    return [
        (v / scale if v is not None else None)
        for v in (bucket.get(p) for p in periods)
    ]


def _yoy_series(m: dict, key: str, periods: list[str]) -> list[float | None]:
    bucket = m["_delta"]["yoy"].get(key, {})
    return [bucket.get(p) for p in periods]


def _empty_fig(msg: str, height: int = 320) -> go.Figure:
    """Veri yokken placeholder figür."""
    fig = go.Figure()
    fig.add_annotation(
        text=msg.replace("\n", "<br>"),
        x=0.5, y=0.5, xref="paper", yref="paper",
        showarrow=False,
        font={"color": _C["gray"], "size": 14},
        align="center",
    )
    fig.update_layout(**_layout(height=height))
    return fig


# ---------------------------------------------------------------------------
# Grafik 1: Satışlar Bar + FAVÖK Marjı Line
# ---------------------------------------------------------------------------

def chart_satis_favok(m: dict, n: int = 8) -> go.Figure:
    pds  = _periods_display(m["periods"], n)
    mn   = 1e6  # mn birim
    sats = _series(m, "satis",       pds, mn)
    fav  = _series(m, "favok_marji", pds)
    bmt  = _series(m, "brut_kar_marji", pds)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=pds, y=sats,
        name="Satışlar (mn)",
        marker_color=_C["blue"],
        opacity=0.85,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=pds, y=fav,
        name="FAVÖK Marjı %",
        line={"color": _C["orange"], "width": 2.5},
        mode="lines+markers",
        marker={"size": 6},
    ), secondary_y=True)

    fig.add_trace(go.Scatter(
        x=pds, y=bmt,
        name="Brüt Marj %",
        line={"color": _C["green"], "width": 1.5, "dash": "dot"},
        mode="lines+markers",
        marker={"size": 4},
    ), secondary_y=True)

    currency = m.get("currency", "TRY")
    fig.update_layout(**_layout(
        title=f"{m['ticker']} — Satışlar & Karlılık Marjları ({currency})",
        legend={"bgcolor": "rgba(0,0,0,0)", "x": 0.01, "y": 0.99},
        barmode="group",
    ))
    fig.update_yaxes(title_text=f"Satışlar (mn {currency})", secondary_y=False,
                     gridcolor=_C["grid"], linecolor=_C["grid"])
    fig.update_yaxes(title_text="Marj %", secondary_y=True,
                     gridcolor=_C["grid"], linecolor=_C["grid"], ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# Grafik 2: Bilanço Stacked Bar (Aktif + Pasif yan yana)
# ---------------------------------------------------------------------------

def chart_bilanco(m: dict, n: int = 8) -> go.Figure:
    pds = _periods_display(m["periods"], n)
    mn  = 1e6

    secs = m.get("_sections_raw")  # varsa ham bölümler

    donen  = _series(m, "donen_varlik",       pds, mn)
    kvy    = _series(m, "kisa_vadeli_yukuml",  pds, mn)
    ozk    = _series(m, "ozkaynak",            pds, mn)

    # Duran varlık ve uzun vadeli yükümlülük doğrudan metrikte yok — ham bölümden al
    # (varsa), yoksa total - dönen yaklaşımı
    def raw_series(section_key: str, kalem: str, pds_: list) -> list[float | None]:
        if "_raw_sections" in m:
            sec = m["_raw_sections"].get(section_key, {})
            for k, v in sec.items():
                if k.startswith(kalem):
                    return [v.get(p) for p in pds_]
        return [None] * len(pds_)

    currency = m.get("currency", "TRY")

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Aktif Yapısı", "Pasif + Özkaynak Yapısı"),
    )

    # Sol: Aktif (Dönen + Duran)
    # Duran varlık için placeholder (toplam - dönen yaklaşımı)
    fig.add_trace(go.Bar(
        x=pds, y=donen, name="Dönen Varlık",
        marker_color=_C["blue"], opacity=0.9,
    ), row=1, col=1)

    # Sağ: Pasif
    fig.add_trace(go.Bar(
        x=pds, y=kvy, name="Kısa Vadeli Yük.",
        marker_color=_C["red"], opacity=0.85,
    ), row=1, col=2)

    fig.add_trace(go.Bar(
        x=pds, y=ozk, name="Özkaynak",
        marker_color=_C["green"], opacity=0.85,
    ), row=1, col=2)

    fig.update_layout(**_layout(
        title=f"{m['ticker']} — Bilanço Yapısı ({currency})",
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
# Grafik 3: Net Borç Trend
# ---------------------------------------------------------------------------

def chart_net_borc(m: dict, n: int = 8) -> go.Figure:
    pds  = _periods_display(m["periods"], n)
    mn   = 1e6
    nb   = _series(m, "net_borc",      pds, mn)
    nbf  = _series(m, "net_borc_favok",pds)

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
        title=f"{m['ticker']} — Net Borç & Kaldıraç ({currency})",
    ))
    fig.update_yaxes(title_text=f"Net Borç (mn {currency})", secondary_y=False,
                     gridcolor=_C["grid"])
    fig.update_yaxes(title_text="Net Borç / FAVÖK (x)", secondary_y=True,
                     gridcolor=_C["grid"], ticksuffix="x")
    return fig


# ---------------------------------------------------------------------------
# Grafik 4: KPI Tablosu (Tablolu görsel)
# ---------------------------------------------------------------------------

def chart_kpi_table(m: dict, n: int = 8) -> go.Figure:
    pds = _periods_display(m["periods"], n)

    kpi_defs = [
        ("Satışlar (mn)",  "satis",          1e6,  "abs"),
        ("FAVÖK (mn)",     "favok",          1e6,  "abs"),
        ("Net Kar (mn)",   "net_kar",        1e6,  "abs"),
        ("Net Borç (mn)",  "net_borc",       1e6,  "abs"),
        ("FCF (mn)",       "fcf",            1e6,  "abs"),
        ("Brüt Marj %",    "brut_kar_marji", 1,    "pct"),
        ("FAVÖK Marjı %",  "favok_marji",    1,    "pct"),
        ("Net Kar Marj %", "net_kar_marji",  1,    "pct"),
        ("Net Borç/FAVÖK", "net_borc_favok", 1,    "ratio"),
        ("Cari Oran",      "cari_oran",      1,    "ratio"),
        ("ROE %",          "roe",            1,    "pct"),
    ]

    labels = [k[0] for k in kpi_defs]
    cell_vals: list[list[str]] = []
    cell_colors: list[list[str]] = []

    yoy_data = m["_delta"]["yoy"]

    for label, key, scale, kind in kpi_defs:
        row_vals   = []
        row_colors = []
        for p in pds:
            val  = m.get(key, {}).get(p)
            yoy  = yoy_data.get(key, {}).get(p)
            if val is None:
                row_vals.append("—")
                row_colors.append("#334155")
            elif kind == "abs":
                v_str = f"{val/scale:,.1f}"
                if yoy is not None:
                    arr = "▲" if yoy > 0 else "▼"
                    v_str += f"\n{arr}{abs(yoy):.1f}%"
                row_vals.append(v_str)
                c = "#1a3a2a" if (yoy or 0) > 0 else "#3a1a1a" if (yoy or 0) < 0 else "#1e293b"
                row_colors.append(c)
            elif kind == "pct":
                v_str = f"{val:.1f}%"
                if yoy is not None:
                    arr = "▲" if yoy > 0 else "▼"
                    v_str += f"\n{arr}{abs(yoy):.1f}pp"
                row_vals.append(v_str)
                row_colors.append("#1e293b")
            else:
                row_vals.append(f"{val:.2f}x")
                row_colors.append("#1e293b")
        cell_vals.append(row_vals)
        cell_colors.append(row_colors)

    # go.Table sütun-major: her eleman bir sütun.
    # cell_vals[i] = metrik i'nin dönem değerleri → dönem-başına sütuna çevir.
    n_p       = len(pds)
    n_m       = len(labels)
    col_vals   = [[cell_vals[mi][pi]   for mi in range(n_m)] for pi in range(n_p)]
    col_colors = [[cell_colors[mi][pi] for mi in range(n_m)] for pi in range(n_p)]

    fig = go.Figure(go.Table(
        header=dict(
            values=["<b>Metrik</b>"] + [f"<b>{p}</b>" for p in pds],
            fill_color="#0f172a",
            font=dict(color=_C["text"], size=11),
            align="left",
            height=30,
        ),
        cells=dict(
            values=[labels, *col_vals],
            fill_color=["#0f172a"] + col_colors,
            font=dict(color=_C["text"], size=11),
            align=["left"] + ["right"] * n_p,
            height=36,
        ),
    ))

    currency = m.get("currency", "TRY")
    fig.update_layout(**_layout(
        margin=_MARGIN_TABLE,
        title=f"{m['ticker']} — KPI Özeti ({currency}) | Altında: YoY değişim",
    ))
    return fig


# ---------------------------------------------------------------------------
# Grafik 5: Waterfall — Gelir Köprüsü (son dönem)
# ---------------------------------------------------------------------------

def chart_waterfall(m: dict, period: str | None = None) -> go.Figure:
    p = period or (m["periods"][0] if m["periods"] else None)
    if not p:
        return go.Figure()

    def v(key: str) -> float:
        return m.get(key, {}).get(p) or 0.0

    satis     = v("satis")
    brut_kar  = v("brut_kar")
    faal_kar  = v("faaliyet_kar")
    favok     = v("favok")
    net_kar   = v("net_kar")
    mn = 1e6

    # Köprü adımları
    labels = ["Satışlar", "Satışların Maliyeti", "Brüt Kar",
              "Opex & Diğer", "Faaliyet Karı", "Amortisman+", "FAVÖK",
              "Faiz/Vergi/Diğer", "Net Kar"]
    values = [
        satis / mn,
        (brut_kar - satis) / mn,   # negatif
        brut_kar / mn,
        (faal_kar - brut_kar) / mn,
        faal_kar / mn,
        (favok - faal_kar) / mn,
        favok / mn,
        (net_kar - favok) / mn,
        net_kar / mn,
    ]
    measures = [
        "absolute", "relative", "total",
        "relative", "total",
        "relative", "total",
        "relative", "total",
    ]
    colors = [
        _C["blue"],
        _C["red"] if values[1] < 0 else _C["green"],
        _C["teal"],
        _C["red"] if values[3] < 0 else _C["green"],
        _C["teal"],
        _C["green"],
        _C["teal"],
        _C["red"] if values[7] < 0 else _C["green"],
        _C["blue"],
    ]

    currency = m.get("currency", "TRY")
    fig = go.Figure(go.Waterfall(
        x=labels,
        y=values,
        measure=measures,
        connector={"line": {"color": _C["gray"]}},
        decreasing={"marker": {"color": _C["red"]}},
        increasing={"marker": {"color": _C["green"]}},
        totals={"marker": {"color": _C["blue"]}},
        textposition="outside",
        text=[f"{v:,.0f}" if v else "" for v in values],
    ))

    fig.update_layout(**_layout(
        title=f"{m['ticker']} — Gelir Köprüsü ({p}, mn {currency})",
        yaxis_title=f"mn {currency}",
    ))
    return fig


# ---------------------------------------------------------------------------
# Grafik 6: FCF vs Net Kar (Kazanç Kalitesi)
# ---------------------------------------------------------------------------

def chart_fcf_vs_netkar(m: dict, n: int = 8) -> go.Figure:
    pds  = _periods_display(m["periods"], n)
    mn   = 1e6
    fcf  = _series(m, "fcf",     pds, mn)
    nkar = _series(m, "net_kar", pds, mn)

    currency = m.get("currency", "TRY")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pds, y=fcf, name="Serbest Nakit Akım",
        fill="tozeroy",
        line={"color": _C["green"], "width": 2},
        fillcolor="rgba(34,197,94,0.15)",
    ))
    fig.add_trace(go.Scatter(
        x=pds, y=nkar, name="Net Kar",
        line={"color": _C["orange"], "width": 2, "dash": "dash"},
        mode="lines+markers", marker={"size": 5},
    ))
    fig.update_layout(**_layout(
        title=f"{m['ticker']} — FCF vs Net Kar ({currency})",
        yaxis_title=f"mn {currency}",
    ))
    return fig


# ---------------------------------------------------------------------------
# Grafik 7: Nakit Akış Çubuk Grafiği
# ---------------------------------------------------------------------------

def chart_nakit_akis(m: dict, n: int = 8) -> go.Figure:
    pds  = _periods_display(m["periods"], n)
    mn   = 1e6
    islt = _series(m, "isletme_cf", pds, mn)
    fcf  = _series(m, "fcf",        pds, mn)
    cpx  = _series(m, "capex",      pds, mn)

    currency = m.get("currency", "TRY")
    fig = go.Figure()
    fig.add_trace(go.Bar(x=pds, y=islt, name="İşletme CF",
                         marker_color=_C["blue"], opacity=0.85))
    fig.add_trace(go.Bar(x=pds, y=fcf, name="Serbest Nakit Akım",
                         marker_color=_C["green"], opacity=0.85))
    fig.add_trace(go.Bar(x=pds, y=cpx, name="Capex",
                         marker_color=_C["red"], opacity=0.85))

    fig.update_layout(**_layout(
        title=f"{m['ticker']} — Nakit Akış ({currency})",
        barmode="group",
        yaxis_title=f"mn {currency}",
    ))
    return fig


# ---------------------------------------------------------------------------
# Grafik 8: YoY Değişim Heatmap
# ---------------------------------------------------------------------------

def chart_heatmap(m: dict, n: int = 8) -> go.Figure:
    pds = _periods_display(m["periods"], n)

    metrics_to_show = [
        ("Satışlar",     "satis"),
        ("FAVÖK",        "favok"),
        ("Net Kar",      "net_kar"),
        ("FCF",          "fcf"),
        ("Net Borç",     "net_borc"),
        ("FAVÖK Marjı",  "favok_marji"),
        ("Net Kar Marj", "net_kar_marji"),
        ("ROE",          "roe"),
    ]

    yoy = m["_delta"]["yoy"]
    z_vals = []
    annotations = []

    for label, key in metrics_to_show:
        row = []
        for p in pds:
            v = yoy.get(key, {}).get(p)
            row.append(v)
            text = f"{v:+.1f}%" if v is not None else "—"
            annotations.append(dict(
                x=p, y=label, text=text,
                showarrow=False, font=dict(color="white", size=10),
            ))
        z_vals.append(row)

    labels = [k[0] for k in metrics_to_show]

    fig = go.Figure(go.Heatmap(
        z=z_vals, x=pds, y=labels,
        colorscale=[
            [0.0,  "#7f1d1d"],
            [0.35, "#1a3a2a"],
            [0.5,  "#1e293b"],
            [0.65, "#14532d"],
            [1.0,  "#052e16"],
        ],
        zmid=0, zmin=-50, zmax=50,
        showscale=True,
        colorbar=dict(title="YoY %", ticksuffix="%"),
    ))

    fig.update_layout(**_layout(
        title=f"{m['ticker']} — YoY % Değişim Isı Haritası",
        annotations=annotations,
        xaxis=dict(side="top", gridcolor=_C["grid"]),
        yaxis=dict(gridcolor=_C["grid"], autorange="reversed"),
        height=400,
    ))
    return fig


# ---------------------------------------------------------------------------
# Grafik 9: Bedelsiz Potansiyel — Enflasyon Muhasebesi (TMS 29)
# ---------------------------------------------------------------------------

def chart_bedelsiz(m: dict, n: int = 8) -> go.Figure:
    pds = _periods_display(m["periods"], n)

    bx  = _series(m, "bedelsiz_potansiyel_x", pds)
    ozk = _series(m, "ozkaynak",              pds, 1e9)
    sem = _series(m, "odenmis_sermaye",        pds, 1e9)

    p0  = m["periods"][0] if m["periods"] else None
    bx0 = m.get("bedelsiz_potansiyel_x",  {}).get(p0)
    bp0 = m.get("bedelsiz_potansiyel_pct",{}).get(p0)
    ef0 = m.get("enflasyon_duzeltildi",   {}).get(p0)

    if ef0:
        ef_text  = "✓ Enflasyon muhasebesi uygulanmış (TMS 29)"
        ef_color = _C["green"]
    else:
        ef_text  = "⚠ Nominal — enflasyon düzeltmesi uygulanmamış"
        ef_color = _C["orange"]

    subtitle = (f"{bx0:.2f}x  (~%{bp0:.0f})  |  {ef_text}"
                if bx0 is not None else ef_text)

    currency = m.get("currency", "TRY")
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=pds, y=bx,
        name="Bedelsiz Potansiyel (x)",
        marker_color=_C["purple"], opacity=0.85,
        text=[f"{v:.1f}x" if v is not None else "" for v in bx],
        textposition="outside",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=pds, y=ozk,
        name=f"Özkaynak (milyar {currency})",
        line={"color": _C["teal"], "width": 2},
        mode="lines+markers", marker={"size": 5},
    ), secondary_y=True)

    fig.add_trace(go.Scatter(
        x=pds, y=sem,
        name=f"Ödenmiş Sermaye (milyar {currency})",
        line={"color": _C["gray"], "width": 1.5, "dash": "dot"},
        mode="lines+markers", marker={"size": 4},
    ), secondary_y=True)

    fig.update_layout(**_layout(
        title={
            "text": (
                f"{m['ticker']} — Bedelsiz Potansiyel & Özkaynak ({currency})<br>"
                f"<sup><span style='color:{ef_color}'>{subtitle}</span></sup>"
            ),
            "font": {"size": 14},
        },
        legend={"bgcolor": "rgba(0,0,0,0)", "x": 0.01, "y": 0.99},
    ))
    fig.update_yaxes(title_text="Bedelsiz Pot. (x)", secondary_y=False,
                     gridcolor=_C["grid"], ticksuffix="x")
    fig.update_yaxes(title_text=f"Milyar {currency}", secondary_y=True,
                     gridcolor=_C["grid"])
    return fig


# ---------------------------------------------------------------------------
# Grafik 10: Yurtiçi / Yurtdışı Satış Kırılımı
# ---------------------------------------------------------------------------

def chart_satis_breakdown(m: dict, n: int = 8) -> go.Figure:
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
        x=pds, y=yi, name=f"Yurtiçi (mn {currency})",
        marker_color=_C["blue"], opacity=0.85,
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        x=pds, y=yd, name=f"Yurtdışı / İhracat (mn {currency})",
        marker_color=_C["teal"], opacity=0.85,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=pds, y=ihr, name="İhracat Oranı %",
        line={"color": _C["orange"], "width": 2.5},
        mode="lines+markers", marker={"size": 6},
    ), secondary_y=True)

    fig.update_layout(**_layout(
        title=f"{m['ticker']} — Yurtiçi / Yurtdışı Satış Kırılımı ({currency})",
        barmode="stack",
        legend={"bgcolor": "rgba(0,0,0,0)", "x": 0.01, "y": 0.99},
    ))
    fig.update_yaxes(title_text=f"Satışlar (mn {currency})", secondary_y=False,
                     gridcolor=_C["grid"])
    fig.update_yaxes(title_text="İhracat Oranı %", secondary_y=True,
                     gridcolor=_C["grid"], ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# Grafik 11: Reel Büyüme (TÜFE-deflate)
# ---------------------------------------------------------------------------

def chart_reel_buyume(m: dict, n: int = 8) -> go.Figure:
    tufe = m.get("_tufe", {})
    if not tufe:
        return _empty_fig(
            "TÜFE verisi yok.\n"
            "run.py'yi --no-tufe olmadan çalıştırın\n"
            "veya EVDS_API_KEY ortam değişkenini ayarlayın."
        )

    try:
        from tufe_provider import get_yoy_tufe, real_growth as _real
    except ImportError:
        return _empty_fig("tufe_provider modülü bulunamadı.")

    pds     = _periods_display(m["periods"], n)
    nom_yoy = m["_delta"]["yoy"].get("satis",   {})
    nk_yoy  = m["_delta"]["yoy"].get("net_kar", {})

    nom_vals: list[float | None] = []
    reel_vals: list[float | None] = []
    nk_reel:   list[float | None] = []

    for p in pds:
        nom      = nom_yoy.get(p)
        tufe_yoy = get_yoy_tufe(p, tufe)

        nom_vals.append(nom)
        reel_vals.append(
            _real(nom, tufe_yoy)
            if (nom is not None and tufe_yoy is not None) else None
        )
        nk_n = nk_yoy.get(p)
        nk_reel.append(
            _real(nk_n, tufe_yoy)
            if (nk_n is not None and tufe_yoy is not None) else None
        )

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=pds, y=nom_vals, name="Nominal Satış YoY %",
        marker_color=_C["blue"], opacity=0.6,
    ))
    fig.add_trace(go.Bar(
        x=pds, y=reel_vals, name="Reel Satış YoY %",
        marker_color=_C["teal"], opacity=0.9,
    ))
    fig.add_trace(go.Scatter(
        x=pds, y=nk_reel, name="Reel Net Kar YoY %",
        line={"color": _C["orange"], "width": 2},
        mode="lines+markers", marker={"size": 5},
    ))

    fig.update_layout(**_layout(
        title=f"{m['ticker']} — Reel Büyüme (TÜFE-deflate edilmiş)",
        barmode="group",
        yaxis_title="YoY % Büyüme",
        yaxis_ticksuffix="%",
        legend={"bgcolor": "rgba(0,0,0,0)"},
    ))
    return fig


# ---------------------------------------------------------------------------
# Grafik 12: Sezonsellik (Diskret Çeyrek)
# ---------------------------------------------------------------------------

def chart_sezonsellik(m: dict, n: int = 12) -> go.Figure:
    """Yıl × çeyrek diskret satış — sezonsellik paterni."""
    pds = _periods_display(m["periods"], n)
    mn  = 1e6
    ceyrek_data = m.get("satis_ceyrek", {})

    year_data: dict[str, dict[int, float | None]] = {}
    for p in pds:
        y, mth = p.split("/")
        q = {3: 1, 6: 2, 9: 3, 12: 4}.get(int(mth), 0)
        if q == 0:
            continue
        if y not in year_data:
            year_data[y] = {}
        v = ceyrek_data.get(p)
        year_data[y][q] = (v / mn) if v is not None else None

    if not year_data:
        return _empty_fig("Diskret çeyrek verisi hesaplanamadı\n(yetersiz geçmiş veri).")

    colors_q = [_C["blue"], _C["teal"], _C["orange"], _C["purple"]]
    q_labels  = ["Q1", "Q2", "Q3", "Q4"]
    years     = sorted(year_data.keys())

    currency = m.get("currency", "TRY")
    fig = go.Figure()
    for qi, ql in enumerate(q_labels, 1):
        vals = [year_data.get(y, {}).get(qi) for y in years]
        fig.add_trace(go.Bar(
            x=years, y=vals, name=ql,
            marker_color=colors_q[qi - 1], opacity=0.85,
        ))

    fig.update_layout(**_layout(
        title=f"{m['ticker']} — Sezonsellik (Diskret Çeyrek Satış, mn {currency})",
        barmode="group",
        yaxis_title=f"Satış (mn {currency})",
        legend={"bgcolor": "rgba(0,0,0,0)"},
    ))
    return fig


# ---------------------------------------------------------------------------
# Grafik 13: Değerleme Çarpanları (yfinance canlı)
# ---------------------------------------------------------------------------

def chart_degerleme(m: dict, n: int = 8) -> go.Figure:
    """F/K, PD/DD, EV/FAVÖK, F/S. m['_market_val'] yoksa placeholder."""
    market_val = m.get("_market_val", {})
    if not market_val or market_val.get("error"):
        err = (market_val.get("error") if market_val else None) or ""
        return _empty_fig(
            f"Piyasa verisi yok{' — ' + err if err else ''}.\n"
            "run.py'yi --no-market olmadan çalıştırın."
        )

    fk       = market_val.get("fk")
    pddd     = market_val.get("pddd")
    ev_favok = market_val.get("ev_favok")
    fs       = market_val.get("fs")
    mc       = market_val.get("market_cap")
    period   = market_val.get("period", "")

    labels  = ["F/K (P/E)", "PD/DD (P/B)", "EV/FAVÖK", "F/S (P/S)"]
    values  = [fk, pddd, ev_favok, fs]
    colors  = [_C["blue"], _C["teal"], _C["orange"], _C["purple"]]

    lv = [(l, v, c) for l, v, c in zip(labels, values, colors) if v is not None]
    if not lv:
        return _empty_fig("Değerleme çarpanları hesaplanamadı.")

    currency = m.get("currency", "TRY")
    mc_str   = f"{mc / 1e9:.1f}B {currency}" if mc else "—"

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[l for l, _, _ in lv],
        y=[v for _, v, _ in lv],
        marker_color=[c for _, _, c in lv],
        opacity=0.85,
        text=[f"{v:.1f}x" for _, v, _ in lv],
        textposition="outside",
        width=0.45,
    ))

    fig.update_layout(**_layout(
        title=(
            f"{m['ticker']} — Değerleme Çarpanları ({period}) | "
            f"Piyasa Değeri: {mc_str}"
        ),
        yaxis_title="Çarpan (x)",
        yaxis_ticksuffix="x",
        showlegend=False,
    ))
    return fig


# ---------------------------------------------------------------------------
# Grafik 14: DuPont Ayrıştırma
# ---------------------------------------------------------------------------

def chart_dupont(m: dict, n: int = 8) -> go.Figure:
    """ROE = Net Kar Marjı (TTM) × Varlık Devir Hızı × Finansal Kaldıraç."""
    pds = _periods_display(m["periods"], n)

    nkm  = _series(m, "dupont_net_kar_marji", pds)   # %
    vd   = _series(m, "dupont_varlik_devir",  pds)   # ratio
    fk   = _series(m, "dupont_fin_kaldirac",  pds)   # ratio
    roe  = _series(m, "dupont_roe",           pds)   # %

    if all(v is None for v in roe):
        return _empty_fig(
            "DuPont verisi hesaplanamadı\n"
            "(TTM için en az 5 ardışık çeyrek gerekli)."
        )

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=pds, y=nkm, name="Net Kar Marjı % (TTM)",
        marker_color=_C["blue"], opacity=0.8,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=pds, y=vd, name="Varlık Devir Hızı (x)",
        line={"color": _C["teal"], "width": 2},
        mode="lines+markers", marker={"size": 5},
    ), secondary_y=True)

    fig.add_trace(go.Scatter(
        x=pds, y=fk, name="Finansal Kaldıraç (x)",
        line={"color": _C["orange"], "width": 2, "dash": "dot"},
        mode="lines+markers", marker={"size": 5},
    ), secondary_y=True)

    fig.add_trace(go.Scatter(
        x=pds, y=roe, name="ROE % (DuPont TTM)",
        line={"color": _C["purple"], "width": 3},
        mode="lines+markers", marker={"size": 7},
    ), secondary_y=False)

    fig.update_layout(**_layout(
        title=f"{m['ticker']} — DuPont Ayrıştırma (TTM) | ROE = Marj × Devir × Kaldıraç",
        legend={"bgcolor": "rgba(0,0,0,0)", "x": 0.01, "y": 0.99},
    ))
    fig.update_yaxes(title_text="Marj / ROE (%)", secondary_y=False,
                     gridcolor=_C["grid"], ticksuffix="%")
    fig.update_yaxes(title_text="Oran (x)", secondary_y=True,
                     gridcolor=_C["grid"], ticksuffix="x")
    return fig


# ---------------------------------------------------------------------------
# Grafik 15: İşletme Sermayesi (DSO / DIO / DPO / CCC)
# ---------------------------------------------------------------------------

def chart_isletme_sermaye(m: dict, n: int = 8) -> go.Figure:
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

    # DPO negatif göster (yükümlülük)
    dpo_neg = [(-v if v is not None else None) for v in dpo]

    fig = make_subplots(specs=[[{"secondary_y": False}]])

    fig.add_trace(go.Bar(
        x=pds, y=dso, name="DSO — Alacak Tahsilat (gün)",
        marker_color=_C["blue"], opacity=0.8,
    ))
    fig.add_trace(go.Bar(
        x=pds, y=dio, name="DIO — Stok Tutma (gün)",
        marker_color=_C["teal"], opacity=0.8,
    ))
    fig.add_trace(go.Bar(
        x=pds, y=dpo_neg, name="DPO — Borç Ödeme (gün) [−]",
        marker_color=_C["red"], opacity=0.7,
    ))
    fig.add_trace(go.Scatter(
        x=pds, y=ccc, name="CCC — Nakit Dönüşüm Döngüsü",
        line={"color": _C["orange"], "width": 3},
        mode="lines+markers", marker={"size": 7},
    ))

    fig.update_layout(**_layout(
        title=f"{m['ticker']} — İşletme Sermayesi Döngüsü (Gün)",
        barmode="relative",
        yaxis_title="Gün",
        legend={"bgcolor": "rgba(0,0,0,0)"},
    ))
    return fig


# ---------------------------------------------------------------------------
# Grafik 16: Piotroski F-Score
# ---------------------------------------------------------------------------

def chart_piotroski(m: dict, n: int = 8) -> go.Figure:
    pds        = _periods_display(m["periods"], n)
    score_vals = _series(m, "piotroski", pds)

    if all(v is None for v in score_vals):
        return _empty_fig(
            "Piotroski F-Score için yeterli YoY karşılaştırma verisi yok\n"
            "(en az 2 yıl veri gereklidir)."
        )

    p0     = m["periods"][0]
    detail = m.get("_piotroski_detail", {}).get(p0, {})

    crit_labels = [
        "F1: Net Kar > 0", "F2: İşletme CF > 0", "F3: ROA Arttı",
        "F4: CF > Net Kar", "F5: UV Borç/Varlık ↓", "F6: Cari Oran ↑",
        "F7: Hisse Artmadı", "F8: Brüt Marj ↑", "F9: Varlık Devir ↑",
    ]
    crit_keys = [
        "f1_net_kar_pozitif", "f2_isletme_cf_pozitif", "f3_roa_artan",
        "f4_cf_kar_ustu", "f5_uv_borc_azalan", "f6_cari_oran_artan",
        "f7_hisse_artmadi", "f8_brut_marj_artan", "f9_varlik_devir_artan",
    ]

    crit_vals   = [detail.get(k) for k in crit_keys]
    crit_strs   = ["✓" if v == 1 else ("✗" if v == 0 else "—") for v in crit_vals]
    crit_colors = [
        (_C["green"] if v == 1 else (_C["red"] if v == 0 else _C["gray"]))
        for v in crit_vals
    ]
    row_colors  = [
        "#1a3a2a" if v == 1 else ("#3a1a1a" if v == 0 else "#1e293b")
        for v in crit_vals
    ]

    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.52, 0.48],
        specs=[[{"type": "xy"}, {"type": "table"}]],
        subplot_titles=(
            "F-Score Trend (0–9)",
            f"Kriter Kırılımı ({p0})",
        ),
    )

    score_bar_colors = [
        (_C["green"] if (v or 0) >= 7 else _C["orange"] if (v or 0) >= 5 else _C["red"])
        for v in score_vals
    ]
    fig.add_trace(go.Bar(
        x=pds, y=score_vals, name="Piotroski Skoru",
        marker_color=score_bar_colors, opacity=0.85,
        text=[str(int(v)) if v is not None else "" for v in score_vals],
        textposition="outside",
    ), row=1, col=1)

    fig.add_trace(go.Table(
        header=dict(
            values=["<b>Kriter</b>", f"<b>{p0}</b>"],
            fill_color="#0f172a",
            font=dict(color=_C["text"], size=10),
            align="left", height=26,
        ),
        cells=dict(
            values=[crit_labels, crit_strs],
            fill_color=["#0a1628", row_colors],
            font=dict(color=[_C["text"], crit_colors], size=10),
            align="left", height=28,
        ),
    ), row=1, col=2)

    score0    = m.get("piotroski", {}).get(p0)
    score_str = f"{int(score0)}/9" if score0 is not None else "—"

    fig.update_layout(**_layout(
        title=f"{m['ticker']} — Piotroski F-Score | Son dönem: {score_str}",
        showlegend=False,
    ))
    fig.update_yaxes(range=[0, 10], title_text="F-Score", row=1, col=1,
                     gridcolor=_C["grid"])
    return fig


# ---------------------------------------------------------------------------
# Grafik 17: Temettü Analizi
# ---------------------------------------------------------------------------

def chart_temettu(m: dict, n: int = 8) -> go.Figure:
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
        x=pds, y=tem_abs, name=f"Temettü Ödemesi (mn {currency})",
        marker_color=_C["green"], opacity=0.85,
    ), secondary_y=False)

    fig.add_trace(go.Bar(
        x=pds, y=nk, name=f"Net Kar (mn {currency})",
        marker_color=_C["blue"], opacity=0.35,
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=pds, y=dr, name="Dağıtım Oranı %",
        line={"color": _C["orange"], "width": 2.5},
        mode="lines+markers", marker={"size": 6},
    ), secondary_y=True)

    fig.update_layout(**_layout(
        title=f"{m['ticker']} — Temettü Analizi{tv_str}",
        barmode="group",
        legend={"bgcolor": "rgba(0,0,0,0)"},
    ))
    fig.update_yaxes(title_text=f"mn {currency}", secondary_y=False, gridcolor=_C["grid"])
    fig.update_yaxes(title_text="Dağıtım Oranı %", secondary_y=True,
                     gridcolor=_C["grid"], ticksuffix="%")
    return fig


# ---------------------------------------------------------------------------
# Dashboard birleştirici
# ---------------------------------------------------------------------------

def build_dashboard(m: dict, n_periods: int = 8) -> str:
    """
    Sekmeli HTML dashboard.
    Sekme 1 : Finansal Tablo (dönem seçici, satır paketi, Δ% göstergesi)
    Sekme 2+ : Plotly grafik sekmeleri
    """
    import json as _json

    ticker       = m.get("ticker", "")
    currency     = m.get("currency", "TRY")
    periods      = m["periods"]
    raw_sections = m.get("_raw_sections", {})

    _SORD = ["bilanco", "gelir", "dipnot", "nakit_akim"]
    _SLBL = {
        "bilanco":    "BİLANÇO",
        "gelir":      "GELİR TABLOSU",
        "dipnot":     "DİPNOTLAR",
        "nakit_akim": "NAKİT AKIŞ TABLOSU",
    }

    # ---------- chart sekmeleri ----------
    _CHART_TABS = [
        ("kpi",       "KPI Özeti",            chart_kpi_table(m, n_periods)),
        ("satis",     "Satışlar & Marjlar",   chart_satis_favok(m, n_periods)),
        ("satis_bd",  "Yurtiçi/Yurtdışı",    chart_satis_breakdown(m, n_periods)),
        ("reel",      "Reel Büyüme",          chart_reel_buyume(m, n_periods)),
        ("sezon",     "Sezonsellik",          chart_sezonsellik(m, n_periods)),
        ("bilanco_c", "Bilanço",              chart_bilanco(m, n_periods)),
        ("netborc",   "Net Borç",             chart_net_borc(m, n_periods)),
        ("waterfall", "Gelir Köprüsü",        chart_waterfall(m)),
        ("fcf",       "FCF vs Net Kar",        chart_fcf_vs_netkar(m, n_periods)),
        ("nakit",     "Nakit Akış",            chart_nakit_akis(m, n_periods)),
        ("heatmap",   "YoY Heatmap",           chart_heatmap(m, n_periods)),
        ("bedelsiz",  "Bedelsiz Potansiyel",   chart_bedelsiz(m, n_periods)),
        ("degerleme", "Değerleme",             chart_degerleme(m, n_periods)),
        ("dupont",    "Karlılık (DuPont)",     chart_dupont(m, n_periods)),
        ("isletme",   "İşletme Sermayesi",     chart_isletme_sermaye(m, n_periods)),
        ("fscore",    "Sağlık Skoru",          chart_piotroski(m, n_periods)),
        ("temettu",   "Temettü",               chart_temettu(m, n_periods)),
    ]

    _chart_nav = "".join(
        "<button class='tab-btn' onclick=\"showTab('tab-" + tid + "',this)\">" + lbl + "</button>"
        for tid, lbl, _ in _CHART_TABS
    )
    _chart_panes = "".join(
        "<div id='tab-" + tid + "' class='tab-pane' style='padding:8px'>"
        + fig.to_html(full_html=False, include_plotlyjs=False,
                      config={"responsive": True, "displayModeBar": True})
        + "</div>"
        for tid, _, fig in _CHART_TABS
    )

    # ---------- JS veri bloğu ----------
    _js_data = (
        "const TICKER="         + _json.dumps(ticker)                           + ";\n"
        "const CURRENCY="       + _json.dumps(currency)                         + ";\n"
        "const ALL_PERIODS="    + _json.dumps(periods, ensure_ascii=False)      + ";\n"
        "const RAW_SECTIONS="   + _json.dumps(raw_sections, ensure_ascii=False) + ";\n"
        "const SECTION_ORDER="  + _json.dumps(_SORD)                            + ";\n"
        "const SECTION_LABELS=" + _json.dumps(_SLBL, ensure_ascii=False)        + ";\n"
        "const DEFAULT_N="      + str(n_periods)                                + ";\n"
    )

    # ---------- CSS ----------
    _css = (
        "*, *::before, *::after{box-sizing:border-box;margin:0;padding:0}"
        "body{background:#0f172a;color:#f1f5f9;font-family:Inter,'Segoe UI',sans-serif;padding:16px}"
        "h1{color:#00D4FF;font-size:1.4rem;margin-bottom:4px}"
        ".sub{color:#94a3b8;font-size:.85rem;margin-bottom:12px}"

        # Tabs
        ".tab-nav{display:flex;flex-wrap:wrap;gap:3px;border-bottom:2px solid #334155;padding-bottom:0}"
        ".tab-btn{background:#1e293b;color:#94a3b8;border:1px solid #334155;"
            "border-radius:5px 5px 0 0;border-bottom:none;padding:5px 12px;"
            "cursor:pointer;font-size:.75rem;white-space:nowrap;transition:background .12s}"
        ".tab-btn:hover{background:#2d3f53;color:#f1f5f9}"
        ".tab-btn.active{background:#0f172a;color:#00D4FF;border-color:#334155;"
            "border-bottom:2px solid #0f172a;margin-bottom:-2px}"
        ".tab-pane{display:none;border:1px solid #334155;border-top:none;"
            "border-radius:0 0 8px 8px;background:#0f172a}"
        ".tab-pane.active{display:block}"

        # Controls
        ".ctrl-bar{display:flex;flex-wrap:wrap;gap:10px;align-items:flex-start;"
            "background:#1e293b;border-bottom:1px solid #334155;padding:9px 12px}"
        ".ctrl-grp{display:flex;flex-wrap:wrap;gap:5px;align-items:center}"
        ".ctrl-lbl{font-size:.7rem;color:#64748b;white-space:nowrap;margin-right:2px}"
        ".period-lbl{display:inline-flex;align-items:center;gap:3px;font-size:.73rem;"
            "color:#94a3b8;cursor:pointer;background:#0f172a;border:1px solid #334155;"
            "border-radius:4px;padding:2px 7px}"
        ".period-lbl input{cursor:pointer;accent-color:#00D4FF}"
        ".pkg-sel{background:#0f172a;color:#f1f5f9;border:1px solid #334155;"
            "border-radius:4px;padding:3px 8px;font-size:.75rem}"
        ".btn-s{background:#0f172a;color:#94a3b8;border:1px solid #334155;"
            "border-radius:4px;padding:3px 9px;cursor:pointer;font-size:.75rem}"
        ".btn-s:hover{color:#f1f5f9;border-color:#64748b}"
        ".btn-p{color:#00D4FF;border-color:#00D4FF55}"
        ".btn-p:hover{background:#00D4FF11}"
        ".btn-d:hover{color:#ef4444;border-color:#ef4444}"

        # Table
        ".tbl-wrap{overflow:auto;max-height:68vh}"
        "#fin-tbl{width:100%;border-collapse:collapse;font-size:.76rem}"
        "#fin-tbl thead{position:sticky;top:0;z-index:5}"
        "#fin-tbl thead th{background:#0a1628;color:#64748b;text-align:right;"
            "padding:7px 10px;white-space:nowrap;font-size:.7rem;"
            "border-bottom:2px solid #334155;font-weight:600}"
        "#fin-tbl thead th.kh{text-align:left;min-width:250px;position:sticky;left:0;z-index:6}"
        "#fin-tbl thead th.vh{min-width:150px}"
        ".sec-hdr{cursor:pointer}"
        ".sec-hdr td{color:#00D4FF;font-weight:700;font-size:.68rem;letter-spacing:.07em;"
            "padding:5px 10px;border-top:2px solid #334155;background:#0a1628;user-select:none}"
        ".sec-hdr:hover td{background:#1e293b}"
        ".drow td{padding:4px 10px;border-bottom:1px solid #111827;vertical-align:middle}"
        ".drow:hover td{background:#1a2535}"
        ".drow.hid{display:none}"
        ".kc{text-align:left;position:sticky;left:0;background:#0f172a;z-index:1}"
        ".drow:hover .kc{background:#1a2535}"
        ".klbl{display:flex;align-items:center;gap:5px;color:#cbd5e1}"
        ".klbl input{cursor:pointer;accent-color:#00D4FF;flex-shrink:0}"
        ".vc{text-align:right;white-space:nowrap}"
        ".nv{font-family:'Courier New',monospace;color:#e2e8f0}"
        ".null{color:#475569}"
        ".dp{color:#22c55e;font-size:.68em;margin-left:3px}"
        ".dn{color:#ef4444;font-size:.68em;margin-left:3px}"
        ".dz{color:#64748b;font-size:.68em;margin-left:3px}"
    )

    # ---------- JS logic (raw — süslü parantezler JS'e ait) ----------
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

let selPd=new Set(ALL_PERIODS.slice(0,DEFAULT_N));
let hidRows=new Set();
let colSec={};

function fmtV(v){
  if(v===null||v===undefined) return null;
  return (v/1e6).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
}

function badge(c,p){
  if(c===null||c===undefined||p===null||p===undefined||p===0) return '';
  const pct=(c-p)/Math.abs(p)*100;
  if(Math.abs(pct)<0.005) return '<span class="dz"> →0.0%</span>';
  const s=pct>0?'▲':'▼', cls=pct>0?'dp':'dn';
  return '<span class="'+cls+'"> '+s+Math.abs(pct).toFixed(1)+'%</span>';
}

const PKG_KEY='finlab_'+TICKER;
function getPkgs(){try{return JSON.parse(localStorage.getItem(PKG_KEY)||'[]');}catch(e){return[];}}
function setPkgs(pkgs){try{localStorage.setItem(PKG_KEY,JSON.stringify(pkgs));}catch(e){}}

function refreshPkgSel(){
  const sel=document.getElementById('pkg-sel');
  const pkgs=getPkgs();
  sel.innerHTML='<option value="">Paket seç…</option>'+
    pkgs.map((p,i)=>'<option value="'+i+'">'+p.name+'</option>').join('');
}

function renderTable(){
  const vp=ALL_PERIODS.filter(p=>selPd.has(p));
  let hdr='<tr><th class="kh">Kalem <small style="color:#475569;font-weight:400">(mn '+CURRENCY+')</small></th>';
  vp.forEach(p=>{hdr+='<th class="vh">'+p+'</th>';});
  hdr+='</tr>';
  document.getElementById('fin-thead').innerHTML=hdr;

  let body='';
  SECTION_ORDER.forEach(sec=>{
    const sd=RAW_SECTIONS[sec];
    if(!sd||Object.keys(sd).length===0) return;
    const col=!!colSec[sec];
    body+='<tr class="sec-hdr" data-sec="'+sec+'"><td colspan="'+(1+vp.length)+'">'
      +(col?'▶':'▼')+' '+SECTION_LABELS[sec]+'</td></tr>';
    if(col) return;
    Object.entries(sd).forEach(([k,ser])=>{
      const rk=sec+'::'+k;
      const rkE=rk.replace(/&/g,'&amp;').replace(/"/g,'&quot;');
      const vis=!hidRows.has(rk);
      let tds='<td class="kc"><label class="klbl"><input type="checkbox"'
        +(vis?' checked':'')
        +' data-rk="'+rkE+'"> '+k+'</label></td>';
      vp.forEach(p=>{
        const cur=ser[p]!==undefined?ser[p]:null;
        const ai=ALL_PERIODS.indexOf(p);
        const pp=ai+1<ALL_PERIODS.length?ALL_PERIODS[ai+1]:null;
        const prv=pp?(ser[pp]!==undefined?ser[pp]:null):null;
        const fv=fmtV(cur);
        tds+='<td class="vc">'+(fv?'<span class="nv">'+fv+'</span>':'<span class="null">—</span>')
          +badge(cur,prv)+'</td>';
      });
      body+='<tr class="drow'+(vis?'':' hid')+'" data-rk="'+rkE+'">'+tds+'</tr>';
    });
  });
  document.getElementById('fin-tbody').innerHTML=body;
}

document.addEventListener('click',e=>{
  const sh=e.target.closest('.sec-hdr');
  if(sh){colSec[sh.dataset.sec]=!colSec[sh.dataset.sec];renderTable();}
});
document.addEventListener('change',e=>{
  const inp=e.target;
  if(inp.type==='checkbox'&&inp.dataset.rk){
    if(inp.checked) hidRows.delete(inp.dataset.rk); else hidRows.add(inp.dataset.rk);
    const tr=inp.closest('tr');
    if(tr) tr.classList.toggle('hid',!inp.checked);
  }
});

function buildPdSel(){
  const div=document.getElementById('pd-sel');
  ALL_PERIODS.forEach(p=>{
    const lbl=document.createElement('label');
    lbl.className='period-lbl';
    const inp=document.createElement('input');
    inp.type='checkbox';
    inp.checked=selPd.has(p);
    inp.addEventListener('change',()=>{
      if(inp.checked) selPd.add(p); else selPd.delete(p);
      renderTable();
    });
    lbl.appendChild(inp);
    lbl.appendChild(document.createTextNode(' '+p));
    div.appendChild(lbl);
  });
}

function selAllPd(v){
  if(v) selPd=new Set(ALL_PERIODS); else selPd.clear();
  document.querySelectorAll('#pd-sel input').forEach(i=>i.checked=v);
  renderTable();
}

function savePkg(){
  const n=prompt('Paket adı:');
  if(!n||!n.trim()) return;
  const pkgs=getPkgs();
  pkgs.push({name:n.trim(),hidden:[...hidRows]});
  setPkgs(pkgs); refreshPkgSel();
}
function loadPkg(idx){
  if(idx==='') return;
  const pkg=getPkgs()[Number(idx)];
  if(!pkg) return;
  hidRows=new Set(pkg.hidden);
  renderTable();
}
function delPkg(){
  const sel=document.getElementById('pkg-sel');
  if(!sel.value) return;
  if(!confirm('Bu paketi silmek istiyor musunuz?')) return;
  const pkgs=getPkgs(); pkgs.splice(Number(sel.value),1);
  setPkgs(pkgs); refreshPkgSel(); hidRows.clear(); renderTable();
}
function showAll(){hidRows.clear();renderTable();}

buildPdSel(); refreshPkgSel(); renderTable();
"""

    # ---------- HTML assembly ----------
    return (
        "<!DOCTYPE html>\n<html lang='tr'>\n<head>\n"
        "<meta charset='utf-8'>\n"
        "<title>" + ticker + " Finansal Analiz</title>\n"
        "<script src='https://cdn.plot.ly/plotly-latest.min.js'></script>\n"
        "<style>" + _css + "</style>\n"
        "</head>\n<body>\n"
        "<h1>" + ticker + " — Finansal Analiz Panosu</h1>\n"
        "<p class='sub'>Para birimi: " + currency + " | Kaynak: isyatirim.com.tr</p>\n"
        "<nav class='tab-nav'>"
        "<button class='tab-btn active' onclick=\"showTab('tab-finlist',this)\">"
        "\U0001f4ca Finansal Tablo</button>"
        + _chart_nav +
        "</nav>\n"

        # --- Financial Table Tab ---
        "<div id='tab-finlist' class='tab-pane active'>\n"
        "<div class='ctrl-bar'>\n"
        "  <div class='ctrl-grp'>"
        "<span class='ctrl-lbl'>Dönemler:</span>"
        "<div id='pd-sel'></div>"
        "<button class='btn-s' onclick='selAllPd(true)'>Tümü</button>"
        "<button class='btn-s' onclick='selAllPd(false)'>Temizle</button>"
        "</div>\n"
        "  <div class='ctrl-grp'>"
        "<span class='ctrl-lbl'>Görünüm paketi:</span>"
        "<select id='pkg-sel' class='pkg-sel' onchange='loadPkg(this.value)'></select>"
        "<button class='btn-s btn-p' onclick='savePkg()'>&#128190; Kaydet</button>"
        "<button class='btn-s btn-d' onclick='delPkg()'>&#128465; Sil</button>"
        "<button class='btn-s'       onclick='showAll()'>Tümünü Göster</button>"
        "</div>\n"
        "</div>\n"
        "<div class='tbl-wrap'>"
        "<table id='fin-tbl'>"
        "<thead id='fin-thead'></thead>"
        "<tbody id='fin-tbody'></tbody>"
        "</table></div>\n"
        "</div>\n"

        # --- Chart Tabs ---
        + _chart_panes +

        # --- Scripts ---
        "\n<script>\n" + _js_data + _js + "\n</script>\n"
        "</body>\n</html>"
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _load_or_scrape(ticker: str, n: int, no_scrape: bool) -> tuple[dict, dict]:
    """(raw_data, metrics_dict) döndür."""
    from metrics import compute_metrics

    data_dir = LAB_DIR / "data" / ticker
    json_path = data_dir / f"{ticker.lower()}_try_finansal.json"

    if no_scrape and json_path.exists():
        print(f"[viz] Mevcut JSON yükleniyor: {json_path}")
        with open(json_path, encoding="utf-8") as f:
            raw = json.load(f)
    else:
        from isyatirim_scraper import fetch_financial_data
        raw = fetch_financial_data(ticker, n_quarters=n, currency="TRY")
        data_dir.mkdir(parents=True, exist_ok=True)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(raw, f, ensure_ascii=False, indent=2)

    m = compute_metrics(raw)
    return raw, m


if __name__ == "__main__":
    _fix_stdout()
    parser = argparse.ArgumentParser(description="Finansal görselleştirme prototipi")
    parser.add_argument("ticker",     nargs="?", default="FROTO")
    parser.add_argument("quarters",   nargs="?", type=int, default=12)
    parser.add_argument("--no-scrape", action="store_true",
                        help="Scraping yapma, mevcut JSON'ı kullan")
    parser.add_argument("--n-periods", type=int, default=8,
                        help="Grafiklerde gösterilecek dönem sayısı")
    args = parser.parse_args()

    ticker = args.ticker.upper()
    raw, m = _load_or_scrape(ticker, args.quarters, args.no_scrape)

    print(f"\n[viz] {ticker} için {args.n_periods} dönemlik dashboard oluşturuluyor...")

    html = build_dashboard(m, n_periods=args.n_periods)

    out_dir = LAB_DIR / "data" / ticker
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ticker.lower()}_dashboard.html"
    out_path.write_text(html, encoding="utf-8")

    print(f"[viz] Kaydedildi: {out_path}")
    print(f"[viz] Tarayıcıda açmak için:")
    print(f"      start {out_path}")
