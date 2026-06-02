from pathlib import Path

import plotly.graph_objects as go

from src.ui.pages.comparison.utils.plotly_html import (
    PATCH_MARKER,
    build_plotly_html,
    ensure_patched_plotly_js,
)


def test_patched_plotly_js_starts_with_insert_rule_patch(tmp_path):
    path = Path(ensure_patched_plotly_js(tmp_path))
    content = path.read_text(encoding="utf-8")

    assert content.startswith(PATCH_MARKER)
    assert "CSSStyleSheet.prototype.insertRule" in content
    assert "plotly.js" in content.lower()


def test_plotly_html_loads_patched_js_before_new_plot():
    fig = go.Figure(data=[go.Scatter(x=[1, 2], y=[3, 4])])

    html = build_plotly_html(fig, "file:///tmp/plotly-shared-patched.min.js")

    assert html.index("plotly-shared-patched.min.js") < html.index("Plotly.newPlot")
    assert "https://cdn.plot.ly" not in html


def test_plotly_html_inline_fallback_injects_css_patch_before_plotly():
    fig = go.Figure(data=[go.Scatter(x=[1, 2], y=[3, 4])])

    html = build_plotly_html(fig, None)

    assert "CSSStyleSheet.prototype.insertRule" in html
    assert html.index("CSSStyleSheet.prototype.insertRule") < html.index("plotly.js")
    assert "Plotly.newPlot" in html
