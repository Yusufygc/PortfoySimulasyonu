"""
Ortaklık Yapısı dashboard HTML üretici.

Pay sahipliği tarihçesi için tek HTML çıktı:
- Üst: çoklu çizgi grafiği (Plotly) — X=tarih, Y=pay %, her shareholder bir çizgi
- Alt: snapshot timeline (her bildirim için card + tablo)

Plotly offline (CDN yok) — ensure_patched_plotly_js() kullanır.
"""
from __future__ import annotations

from decimal import Decimal
from html import escape
from typing import Iterable

import plotly.graph_objects as go

from src.domain.models.shareholder import ShareholderSnapshot
from src.ui.pages.comparison.utils.plotly_html import ensure_patched_plotly_js


_C = {
    "blue":   "#00D4FF",
    "green":  "#22c55e",
    "red":    "#ef4444",
    "orange": "#f97316",
    "purple": "#a855f7",
    "teal":   "#14b8a6",
    "yellow": "#facc15",
    "pink":   "#ec4899",
    "gray":   "#64748b",
    "text":   "#f1f5f9",
    "grid":   "#334155",
    "bg":     "#0f172a",
    "panel":  "#1e293b",
}

_PALETTE = [
    _C["blue"], _C["green"], _C["orange"], _C["purple"],
    _C["teal"], _C["yellow"], _C["pink"], _C["red"],
]

_CSS = (
    "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}"
    "body{background:#0f172a;color:#f1f5f9;font-family:Inter,'Segoe UI',sans-serif;padding:12px}"
    "h2{font-size:1.1rem;font-weight:600;color:#00D4FF;margin:18px 0 8px}"
    ".snap-card{background:#1e293b;border:1px solid #334155;border-radius:8px;"
    "padding:14px 18px;margin-bottom:14px}"
    ".snap-head{display:flex;align-items:center;justify-content:space-between;"
    "font-size:.85rem;color:#94a3b8;margin-bottom:10px}"
    ".snap-date{font-weight:700;color:#f1f5f9;font-size:.95rem}"
    ".snap-tbl{width:100%;border-collapse:collapse;font-size:.82rem}"
    ".snap-tbl thead th{background:#0a1628;color:#64748b;text-align:right;"
    "padding:7px 10px;font-weight:600;border-bottom:1px solid #334155}"
    ".snap-tbl thead th:first-child{text-align:left}"
    ".snap-tbl tbody td{padding:6px 10px;border-bottom:1px solid #0f172a;"
    "color:#e2e8f0;text-align:right;font-family:'Courier New',monospace}"
    ".snap-tbl tbody td:first-child{text-align:left;font-family:inherit;color:#cbd5e1}"
    ".snap-tbl tbody tr.total td{background:#0a1628;font-weight:700;color:#f1f5f9}"
    ".snap-tbl tbody tr:hover td{background:#1a2535}"
    ".chart-box{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:8px}"
    ".empty-msg{color:#64748b;text-align:center;padding:60px 20px;font-size:.95rem}"
)


def build_dashboard(ticker: str, snapshots: list[ShareholderSnapshot]) -> str:
    """Tarihçeden tek HTML dashboard üret."""
    js_path     = ensure_patched_plotly_js()
    js_file_url = js_path.replace("\\", "/")
    if not js_file_url.startswith("file://"):
        js_file_url = "file:///" + js_file_url

    head = (
        "<!DOCTYPE html>\n<html lang='tr'>\n<head>\n"
        "<meta charset='utf-8'>\n"
        f"<title>{escape(ticker)} — Ortaklık Yapısı</title>\n"
        f"<script src='{js_file_url}'></script>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n<body>\n"
    )

    if not snapshots:
        body = (
            f"<h2>{escape(ticker)} — Ortaklık Yapısı</h2>"
            "<div class='empty-msg'>KAP'tan veri bulunamadı.</div>"
        )
        return head + body + "</body>\n</html>"

    chart_div = _build_timeline_chart(ticker, snapshots)
    timeline  = _build_snapshot_timeline(snapshots)

    body = (
        f"<h2>{escape(ticker)} — Pay Sahipliği Trendi ({len(snapshots)} bildirim)</h2>"
        f"<div class='chart-box'>{chart_div}</div>"
        f"<h2>Tarihçe — Bildirim Bazında Detay</h2>"
        f"{timeline}"
    )

    return head + body + "</body>\n</html>"


# ---------------------------------------------------------------------------
# Plotly çoklu çizgi grafiği — X=tarih, Y=pay %, her shareholder ayrı çizgi
# ---------------------------------------------------------------------------

def _build_timeline_chart(ticker: str, snapshots: list[ShareholderSnapshot]) -> str:
    series: dict[str, list[tuple]] = {}
    all_dates = sorted({s.creation_date for s in snapshots})
    for snap in snapshots:
        for r in snap.rows:
            if r.is_total or r.ratio_in_capital is None:
                continue
            series.setdefault(r.shareholder_name, []).append(
                (snap.creation_date, float(r.ratio_in_capital))
            )

    fig = go.Figure()
    for i, (name, pts) in enumerate(sorted(series.items(), key=lambda x: -len(x[1]))):
        pts.sort(key=lambda p: p[0])
        xs = [p[0].isoformat() for p in pts]
        ys = [p[1] for p in pts]
        fig.add_trace(go.Scatter(
            x=xs, y=ys, name=_truncate(name, 40), mode="lines+markers",
            line={"color": _PALETTE[i % len(_PALETTE)], "width": 2.2},
            marker={"size": 6},
            hovertemplate=f"<b>%{{x}}</b><br>{escape(name)}: %{{y:.2f}}%<extra></extra>",
        ))

    fig.update_layout(
        paper_bgcolor=_C["bg"],
        plot_bgcolor=_C["panel"],
        font={"color": _C["text"], "family": "Inter, Segoe UI, sans-serif", "size": 12},
        margin={"t": 40, "b": 50, "l": 60, "r": 30},
        height=520,
        xaxis={"gridcolor": _C["grid"], "title": "Bildirim Tarihi"},
        yaxis={
            "gridcolor": _C["grid"], "title": "Sermayedeki Pay (%)",
            "ticksuffix": "%", "tickformat": ".2f", "rangemode": "tozero",
        },
        legend={"bgcolor": "rgba(0,0,0,0)", "orientation": "h", "y": -0.18},
        hovermode="closest",
    )

    return fig.to_html(
        full_html=False, include_plotlyjs=False,
        config={"responsive": True, "displayModeBar": True},
    )


# ---------------------------------------------------------------------------
# Snapshot timeline — her bildirim için card + tablo
# ---------------------------------------------------------------------------

def _build_snapshot_timeline(snapshots: list[ShareholderSnapshot]) -> str:
    parts: list[str] = []
    for snap in snapshots:
        date_str = snap.creation_date.strftime("%d/%m/%Y")
        rows_html = "".join(
            _row_html(r) for r in snap.rows
        )
        parts.append(
            "<div class='snap-card'>"
            "<div class='snap-head'>"
            f"<span class='snap-date'>{date_str}</span>"
            f"<span>{_non_total_count(snap.rows)} ortak</span>"
            "</div>"
            "<table class='snap-tbl'>"
            "<thead><tr>"
            "<th>Ortağın Adı/Ticaret Ünvanı</th>"
            "<th>Sermayedeki Payı (TL)</th>"
            "<th>Sermayedeki Payı (%)</th>"
            "<th>Oy Hakkı Oranı (%)</th>"
            "</tr></thead>"
            f"<tbody>{rows_html}</tbody>"
            "</table>"
            "</div>"
        )
    return "".join(parts)


def _row_html(row) -> str:
    tr_cls = " class='total'" if row.is_total else ""
    return (
        f"<tr{tr_cls}>"
        f"<td>{escape(row.shareholder_name)}</td>"
        f"<td>{_fmt_int(row.share_in_capital)}</td>"
        f"<td>{_fmt_pct(row.ratio_in_capital)}</td>"
        f"<td>{_fmt_pct(row.voting_right_ratio)}</td>"
        "</tr>"
    )


def _non_total_count(rows: Iterable) -> int:
    return sum(1 for r in rows if not r.is_total)


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 1] + "…"


def _fmt_int(v) -> str:
    if v is None:
        return "<span style='color:#475569'>—</span>"
    try:
        return f"{Decimal(v):,.0f}"
    except Exception:
        return escape(str(v))


def _fmt_pct(v) -> str:
    if v is None:
        return "<span style='color:#475569'>—</span>"
    try:
        return f"{Decimal(v):,.2f}"
    except Exception:
        return escape(str(v))
