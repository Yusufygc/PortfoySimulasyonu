from __future__ import annotations

import logging
import tempfile
from pathlib import Path

import plotly
import plotly.graph_objects as go

def patch_plotly_html(html: str) -> str:
    dark_css = """
    <style>
        html, body {
            background-color: #0f172a !important;
            color: #f1f5f9 !important;
            margin: 0 !important;
            padding: 0 !important;
            width: 100% !important;
            height: 100% !important;
            overflow: hidden !important;
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif !important;
        }
        .js-plotly-plot, .plot-container, .plotly, .svg-container {
            background-color: #0f172a !important;
            width: 100% !important;
            height: 100% !important;
        }
        .main-svg {
            background-color: #0f172a !important;
        }
        .modebar-container {
            background-color: transparent !important;
        }
        .modebar-btn path {
            fill: #94a3b8 !important;
        }
        .modebar-btn:hover path {
            fill: #38bdf8 !important;
        }
    </style>
    """
    patch_script = dark_css + """
    <script type="text/javascript">
    (function() {
        try {
            var orig = CSSStyleSheet.prototype.insertRule;
            CSSStyleSheet.prototype.insertRule = function(rule, index) {
                try {
                    return orig.call(this, rule, index);
                } catch (e) {
                    console.warn("Ignored CSSStyleSheet.insertRule error: ", rule, e);
                    return 0;
                }
            };
        } catch (e) {
            console.error("Failed to patch CSSStyleSheet.insertRule", e);
        }
    })();
    </script>
    """
    if "<head>" in html:
        return html.replace("<head>", "<head>\n" + patch_script, 1)
    elif "<html>" in html:
        return html.replace("<html>", "<html>\n" + patch_script, 1)
    else:
        return patch_script + "\n" + html


logger = logging.getLogger(__name__)

PATCHED_PLOTLY_FILENAME = "plotly-shared-patched.min.js"
PATCH_MARKER = "/* PortfoySim Plotly insertRule patch */"

INSERT_RULE_PATCH = f"""
{PATCH_MARKER}
(function() {{
    try {{
        var orig = CSSStyleSheet.prototype.insertRule;
        if (!CSSStyleSheet.prototype.__portfoySimInsertRulePatched) {{
            CSSStyleSheet.prototype.insertRule = function(rule, index) {{
                try {{
                    return orig.call(this, rule, index);
                }} catch (e) {{
                    console.warn("Ignored CSSStyleSheet.insertRule error: ", rule, e);
                    return 0;
                }}
            }};
            CSSStyleSheet.prototype.__portfoySimInsertRulePatched = true;
        }}
    }} catch (e) {{
        console.error("Failed to patch CSSStyleSheet.insertRule", e);
    }}
}})();
""".strip()


def ensure_patched_plotly_js(directory: str | Path | None = None) -> str:
    target = Path(directory or tempfile.gettempdir()) / PATCHED_PLOTLY_FILENAME
    if _is_valid_patched_file(target):
        return str(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        INSERT_RULE_PATCH + "\n" + plotly.offline.get_plotlyjs(),
        encoding="utf-8",
    )
    return str(target)


def build_plotly_html(
    fig: go.Figure,
    plotly_js_url: str | None,
    download_filename: str | None = None,
) -> str:
    config = {
        "responsive": True,
        "displayModeBar": True,
        "toImageButtonOptions": {
            "format": "png",
            "filename": download_filename or "newplot",
        },
    }
    if plotly_js_url:
        html = fig.to_html(include_plotlyjs=False, full_html=True, config=config)
        script_tag = f'<script type="text/javascript" src="{plotly_js_url}"></script>'
        return patch_plotly_html(_inject_first_head_script(html, script_tag))

    return patch_plotly_html(fig.to_html(include_plotlyjs=True, full_html=True, config=config))


def _inject_first_head_script(html: str, script_tag: str) -> str:
    if "<head>" in html:
        return html.replace("<head>", f"<head>\n{script_tag}", 1)
    if "<html>" in html:
        return html.replace("<html>", f"<html>\n{script_tag}", 1)
    return f"{script_tag}\n{html}"


def _is_valid_patched_file(path: Path) -> bool:
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        with path.open("r", encoding="utf-8") as handle:
            return handle.read(len(PATCH_MARKER)) == PATCH_MARKER
    except OSError:
        logger.exception("Could not inspect patched Plotly JS file: %s", path)
        return False
