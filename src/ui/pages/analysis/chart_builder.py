from src.ui.shared.locale_tr import L10N
import pandas as pd
import plotly.graph_objects as go

USD_NATIVE_SYMBOLS = ["XAUUSD=X", "GC=F", "XAGUSD=X", "SI=F"]
TL_NATIVE_SYMBOLS = ["XAUTRY=X", "XAGTRY=X"]
GRAM_SYMBOLS = ["GC=F", "XAUUSD=X", "XAGUSD=X", "SI=F"]
TROY_OZ_TO_GRAM = 31.1034768

BENCHMARK_COLORS = [
    "#F4A460", "#A9A9A9", "#4682B4", "#20B2AA", "#9370DB", "#CD853F"
]
PORTFOLIO_COLOR = "#E63946"
GAIN_COLOR = "#2DC653"
LOSS_COLOR = "#E63946"
TURKISH_MONTHS = [
    "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
    "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık",
]


def format_turkish_date(value) -> str:
    ts = pd.Timestamp(value)
    return f"{ts.day:02d} {TURKISH_MONTHS[ts.month - 1]} {ts.year}"


def format_turkish_period(value, freq: str) -> str:
    ts = pd.Timestamp(value)
    if freq == "ME":
        return f"{TURKISH_MONTHS[ts.month - 1]} {ts.year}"
    quarter = ((ts.month - 1) // 3) + 1
    return f"{quarter}. Çeyrek {ts.year}"


def _apply_turkish_month_axis(fig: go.Figure, dates) -> None:
    idx = pd.DatetimeIndex(pd.to_datetime(dates)).dropna()
    if idx.empty:
        return
    start = idx.min().replace(day=1)
    end = idx.max().replace(day=1)
    ticks = pd.date_range(start, end, freq="MS")
    if len(ticks) == 0:
        return
    step = max(1, len(ticks) // 12)
    ticks = ticks[::step]
    fig.update_xaxes(
        tickmode="array",
        tickvals=ticks,
        ticktext=[f"{TURKISH_MONTHS[t.month - 1]} {t.year}" for t in ticks],
    )


def _add_benchmark_traces(fig: go.Figure, benchmark_series: pd.DataFrame, currency_label: str) -> None:
    for i, col in enumerate(benchmark_series.columns):
        s = benchmark_series[col].dropna()
        color = BENCHMARK_COLORS[i % len(BENCHMARK_COLORS)]
        customdata = pd.DataFrame({
            "date": [format_turkish_date(d) for d in s.index],
            "ret": (s.values - 100).round(2),
        }).values
        fig.add_trace(go.Scatter(
            x=s.index, y=s.values, name=col,
            line=dict(width=1.5, color=color), opacity=0.75, legendgroup=col,
            hovertemplate=(
                f"<b>{col}</b><br>" + L10N.TARIH_CUSTOMDATA0BR +
                f"Değer: %{{y:.1f}} ({currency_label})<br>" +
                "Başlangıçtan: %{customdata[1]:+.2f}%<extra></extra>"
            ),
            customdata=customdata,
        ))


def _add_portfolio_trace(fig: go.Figure, portfolio_series, currency_label: str) -> None:
    if portfolio_series is None:
        return
    p = portfolio_series.dropna()
    customdata = pd.DataFrame({
        "date": [format_turkish_date(d) for d in p.index],
        "ret": (p.values - 100).round(2),
    }).values
    fig.add_trace(go.Scatter(
        x=p.index, y=p.values, name="Portföy",
        line=dict(width=3, color=PORTFOLIO_COLOR), opacity=1.0, legendgroup="Portföy",
        hovertemplate=(
            "<b>Portföy</b><br>" + L10N.TARIH_CUSTOMDATA0BR +
            f"Değer: %{{y:.1f}} ({currency_label})<br>" +
            "Başlangıçtan: %{customdata[1]:+.2f}%<extra></extra>"
        ),
        customdata=customdata,
    ))


def _build_perf_chart_layout(currency_label: str, title: str) -> dict:
    return dict(
        title=dict(text=title, font=dict(size=16)),
        xaxis=dict(
            title=L10N.TARIH,
            rangeselector=dict(
                buttons=[
                    dict(count=1, label="1A", step="month", stepmode="backward"),
                    dict(count=3, label="3A", step="month", stepmode="backward"),
                    dict(count=6, label="6A", step="month", stepmode="backward"),
                    dict(count=1, label="YBB", step="year", stepmode="todate"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                    dict(step="all", label="Tümü"),
                ],
                bgcolor="#313244", activecolor="#585b70",
                font=dict(color="#cdd6f4", size=11),
            ),
            rangeslider=dict(visible=True, bgcolor="#1e1e2e", thickness=0.06),
            type="date",
        ),
        yaxis_title=f"Normalize Getiri (Başlangıç=100, {currency_label})",
        hovermode=L10N.X_UNIFIED,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=580,
    )


def build_performance_line_chart_v2(
    portfolio_series,
    benchmark_series: pd.DataFrame,
    currency_label: str,
    title: str = L10N.PORTFOY_VS_BENCHMARK,
) -> go.Figure:
    fig = go.Figure()
    _add_benchmark_traces(fig, benchmark_series, currency_label)
    _add_portfolio_trace(fig, portfolio_series, currency_label)
    fig.add_hline(
        y=100,
        line=dict(color="#6c7086", width=1, dash="dot"),
        annotation_text=L10N.BASLANGIC_100,
        annotation_position=L10N.BOTTOM_RIGHT,
        annotation_font=dict(size=10, color="#6c7086"),
    )
    fig.update_layout(**_build_perf_chart_layout(currency_label, title))
    all_dates = benchmark_series.index
    if portfolio_series is not None:
        all_dates = all_dates.union(portfolio_series.index)
    _apply_turkish_month_axis(fig, all_dates)
    return fig


def build_pie_chart(title: str, breakdown: list, text_color: str = "#f1f5f9") -> go.Figure:
    labels = [b[0] for b in breakdown]
    values = [b[1] for b in breakdown]
    fig = go.Figure(data=[go.Pie(labels=labels, values=values, hole=.4, textinfo=L10N.LABELPERCENT)])
    fig.update_layout(
        title=dict(text=title, font=dict(size=16, color=text_color)),
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(t=50, b=20, l=20, r=20),
        legend=dict(font=dict(color=text_color)),
        font=dict(color=text_color),
    )
    return fig


def patch_plotly_html(html: str) -> str:
    """
    Older Chromium engine in QWebEngine throws Uncaught SyntaxError when CSSStyleSheet.insertRule
    tries to parse newer CSS rules such as ':focus-visible'. This function patches the HTML output
    by overriding CSSStyleSheet.prototype.insertRule with a try-catch block before Plotly loads.
    Also injects CSS to make the document background transparent.
    """
    transparent_css = """
    <style type="text/css">
        html, body {
            background-color: transparent !important;
            margin: 0px !important;
            padding: 0px !important;
            overflow: hidden !important;
        }
        .plotly-graph-div {
            background-color: transparent !important;
        }
    </style>
    """
    patch_script = transparent_css + """
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
