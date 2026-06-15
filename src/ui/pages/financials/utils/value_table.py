"""
Grafik altında gösterilen yardımcı değer tabloları (dark-tema HTML).

Plotly değildir — saf HTML. dashboard_html.py her sekme için (varsa) bir tablo
enjekte eder. CSS `.val-tbl` `dashboard_html.py._CSS` içinde tanımlıdır.
"""
from __future__ import annotations

from typing import Any


def _periods_display(periods: list[str], n: int) -> list[str]:
    """charts.py ile aynı kontrat — son n dönem, eski → yeni sırayla."""
    return list(reversed(periods[:n]))


def _cell(val: Any, fmt_spec: str, scale: float) -> str:
    if val is None:
        return "<span style='color:#475569'>—</span>"
    try:
        return format(val / scale, fmt_spec)
    except (TypeError, ValueError):
        return "<span style='color:#475569'>—</span>"


def build_value_table(
    m: dict,
    n: int,
    rows: list[tuple[str, str, str, float]],
) -> str:
    """
    Grafik altında gösterilecek HTML değer tablosu.

    rows: [(metric_key, display_label, fmt_spec, scale), ...]
      fmt_spec: ",.2f" / ",.0f" / ".1f" / ".2f"
      scale:    1e6 (mn), 1e9 (milyar), 1 (orijinal)
    """
    pds = _periods_display(m.get("periods", []), n)
    if not pds or not rows:
        return ""

    head = "<tr><th>Metrik</th>" + "".join(f"<th>{p}</th>" for p in pds) + "</tr>"

    body_rows = []
    for key, label, fmt_spec, scale in rows:
        bucket = m.get(key, {}) or {}
        cells = "".join(
            f"<td>{_cell(bucket.get(p), fmt_spec, scale)}</td>" for p in pds
        )
        body_rows.append(f"<tr><td>{label}</td>{cells}</tr>")
    body = "".join(body_rows)

    return (
        "<table class='val-tbl'>"
        f"<thead>{head}</thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
    )
