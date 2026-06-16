"""
Tek ticker için teknik analiz grafiği — kapanış + SMA50 + SMA200 + cross marker'lar.

Plotly offline (CDN yok); ensure_patched_plotly_js() kullanır.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from html import escape
from typing import Sequence

import pandas as pd
import plotly.graph_objects as go

from src.domain.models.daily_price import DailyPrice
from src.domain.models.golden_cross_event import CrossType, GoldenCrossEvent
from src.ui.pages.comparison.utils.plotly_html import ensure_patched_plotly_js

_C = {
    "blue":   "#00D4FF",
    "orange": "#f97316",
    "purple": "#a855f7",
    "green":  "#22c55e",
    "red":    "#ef4444",
    "text":   "#f1f5f9",
    "grid":   "#334155",
    "bg":     "#0f172a",
    "panel":  "#1e293b",
    "gray":   "#64748b",
}

_CSS = (
    "*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}"
    "body{background:#0f172a;color:#f1f5f9;font-family:Inter,'Segoe UI',sans-serif;padding:12px}"
    "h2{font-size:1.1rem;font-weight:600;color:#00D4FF;margin:8px 0}"
    ".empty-msg{color:#64748b;text-align:center;padding:60px 20px;font-size:.95rem}"
    ".chart-box{background:#1e293b;border:1px solid #334155;border-radius:8px;padding:8px;margin-bottom:14px}"
    ".events-tbl{width:100%;border-collapse:collapse;font-size:.82rem;"
    "background:#1e293b;border:1px solid #334155;border-radius:8px;overflow:hidden}"
    ".events-tbl thead th{background:#0a1628;color:#64748b;text-align:right;"
    "padding:7px 10px;font-weight:600;border-bottom:1px solid #334155}"
    ".events-tbl thead th:first-child{text-align:left}"
    ".events-tbl tbody td{padding:6px 10px;border-bottom:1px solid #0f172a;"
    "color:#e2e8f0;text-align:right;font-family:'Courier New',monospace}"
    ".events-tbl tbody td:first-child{text-align:left;font-family:inherit}"
    ".events-tbl tbody tr.golden td.tip{color:#22c55e;font-weight:700}"
    ".events-tbl tbody tr.death td.tip{color:#ef4444;font-weight:700}"
    ".events-tbl tbody tr:hover td{background:#1a2535}"
)


def build_detail_dashboard(
    ticker: str,
    prices: Sequence[DailyPrice],
    events: Sequence[GoldenCrossEvent],
    short: int = 50,
    long: int = 200,
) -> str:
    """Tek ticker için teknik analiz HTML dashboard'u."""
    js_path = ensure_patched_plotly_js()
    js_file_url = js_path.replace("\\", "/")
    if not js_file_url.startswith("file://"):
        js_file_url = "file:///" + js_file_url

    head = (
        "<!DOCTYPE html>\n<html lang='tr'>\n<head>\n"
        "<meta charset='utf-8'>\n"
        f"<title>{escape(ticker)} — Teknik Analiz</title>\n"
        f"<script src='{js_file_url}'></script>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n<body>\n"
    )

    if not prices:
        body = (
            f"<h2>{escape(ticker)}</h2>"
            "<div class='empty-msg'>Fiyat verisi bulunamadı.</div>"
        )
        return head + body + "</body>\n</html>"

    chart_div = _build_price_chart(ticker, prices, events, short, long)
    events_tbl = _build_events_table(events)

    body = (
        f"<h2>{escape(ticker)} — Kapanış + EMA{short}/EMA{long}</h2>"
        f"<div class='chart-box'>{chart_div}</div>"
        f"<h2>Cross Olayları ({len(events)} kayıt)</h2>"
        f"{events_tbl}"
    )
    return head + body + "</body>\n</html>"


def _build_price_chart(
    ticker: str,
    prices: Sequence[DailyPrice],
    events: Sequence[GoldenCrossEvent],
    short: int,
    long: int,
) -> str:
    dates = [p.price_date for p in prices]
    closes = [float(p.close_price) for p in prices]
    ser = pd.Series(closes, index=dates).sort_index()
    ema_s = ser.ewm(span=short, adjust=False).mean()
    ema_l = ser.ewm(span=long, adjust=False).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[d.isoformat() for d in ser.index], y=ser.values,
        name="Kapanış", line={"color": _C["blue"], "width": 1.6}, mode="lines",
        hovertemplate="<b>%{x}</b><br>Kapanış: %{y:,.2f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[d.isoformat() for d in ema_s.index], y=ema_s.values,
        name=f"EMA{short}", line={"color": _C["orange"], "width": 1.4}, mode="lines",
        hovertemplate=f"<b>%{{x}}</b><br>EMA{short}: %{{y:,.2f}}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=[d.isoformat() for d in ema_l.index], y=ema_l.values,
        name=f"EMA{long}", line={"color": _C["purple"], "width": 1.4}, mode="lines",
        hovertemplate=f"<b>%{{x}}</b><br>EMA{long}: %{{y:,.2f}}<extra></extra>",
    ))
    _add_cross_markers(fig, events)

    fig.update_layout(
        paper_bgcolor=_C["bg"], plot_bgcolor=_C["panel"],
        font={"color": _C["text"], "family": "Inter, Segoe UI, sans-serif", "size": 12},
        margin={"t": 30, "b": 50, "l": 70, "r": 30}, height=560,
        xaxis={"gridcolor": _C["grid"], "title": "Tarih"},
        yaxis={"gridcolor": _C["grid"], "title": "Fiyat (TRY)", "tickformat": ",.2f"},
        legend={"bgcolor": "rgba(0,0,0,0)", "orientation": "h", "y": 1.08, "x": 0},
        hovermode="x unified",
    )
    return fig.to_html(
        full_html=False, include_plotlyjs=False,
        config={"responsive": True, "displayModeBar": True},
    )


def _add_cross_markers(fig: go.Figure, events: Sequence[GoldenCrossEvent]) -> None:
    golden = [e for e in events if e.cross_type == CrossType.GOLDEN]
    death  = [e for e in events if e.cross_type == CrossType.DEATH]
    if golden:
        fig.add_trace(go.Scatter(
            x=[e.cross_date.isoformat() for e in golden],
            y=[float(e.close_price) for e in golden],
            name="Golden Cross", mode="markers",
            marker={"color": _C["green"], "size": 12, "symbol": "triangle-up", "line": {"color": "#0f172a", "width": 1.5}},
            hovertemplate="<b>Golden Cross</b><br>%{x}<br>Fiyat: %{y:,.2f}<extra></extra>",
        ))
    if death:
        fig.add_trace(go.Scatter(
            x=[e.cross_date.isoformat() for e in death],
            y=[float(e.close_price) for e in death],
            name="Death Cross", mode="markers",
            marker={"color": _C["red"], "size": 12, "symbol": "triangle-down", "line": {"color": "#0f172a", "width": 1.5}},
            hovertemplate="<b>Death Cross</b><br>%{x}<br>Fiyat: %{y:,.2f}<extra></extra>",
        ))


def _build_events_table(events: Sequence[GoldenCrossEvent]) -> str:
    if not events:
        return "<div class='empty-msg'>Cross olayı yok.</div>"
    rows = []
    for e in sorted(events, key=lambda x: x.cross_date, reverse=True):
        cls = "golden" if e.cross_type == CrossType.GOLDEN else "death"
        label = "▲ Golden" if e.cross_type == CrossType.GOLDEN else "▼ Death"
        rows.append(
            f"<tr class='{cls}'>"
            f"<td>{e.cross_date.strftime('%d/%m/%Y')}</td>"
            f"<td class='tip'>{label}</td>"
            f"<td>{_fmt(e.close_price)}</td>"
            f"<td>{_fmt(e.short_ma)}</td>"
            f"<td>{_fmt(e.long_ma)}</td>"
            "</tr>"
        )
    return (
        "<table class='events-tbl'>"
        "<thead><tr>"
        "<th>Tarih</th><th>Tip</th><th>Kapanış</th><th>EMA50</th><th>EMA200</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
    )


def _fmt(v) -> str:
    if v is None:
        return "<span style='color:#475569'>—</span>"
    try:
        return f"{Decimal(v):,.2f}"
    except Exception:
        return escape(str(v))
