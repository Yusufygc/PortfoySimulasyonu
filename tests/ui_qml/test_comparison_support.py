"""Karşılaştırma Laboratuvarı saf yardımcıları ve grafik HTML üreticileri."""
from __future__ import annotations

from datetime import date

import pandas as pd

from src.ui_qml.controllers import comparison_chart_html as charts
from src.ui_qml.controllers import comparison_support as support


def test_parse_date_accepts_both_formats_and_rejects_garbage():
    assert support.parse_date("01.02.2026") == date(2026, 2, 1)
    assert support.parse_date("2026-02-01") == date(2026, 2, 1)
    assert support.parse_date("zz") is None
    assert support.parse_date("") is None


def test_resolve_start_date_labels():
    end = date(2026, 10, 4)
    assert support.resolve_start_date("1A", end) == date(2026, 9, 4)
    assert support.resolve_start_date("1Y", end) == date(2025, 10, 4)
    assert support.resolve_start_date("YBB", end) == date(2026, 1, 1)
    assert support.resolve_start_date("TÜMÜ", end) == date(2022, 1, 1)


def test_resolve_range_custom_falls_back_when_invalid():
    start, end = support.resolve_range("ÖZEL", "01.01.2026", "01.03.2026")
    assert (start, end) == (date(2026, 1, 1), date(2026, 3, 1))
    start, end = support.resolve_range("ÖZEL", "01.03.2026", "01.01.2026")
    assert end == date.today() and start == date(2022, 1, 1)


def test_split_selection_routes_each_code_kind():
    sources, benchmarks, stock_ids = support.split_selection(
        ["dashboard", "model:7", "holdings:model:7", "42", "42", "bist100"],
        lambda source: {10: "THYAO", 11: "ASELS"} if source == "model:7" else {},
    )
    assert sources == ["dashboard", "model:7"]
    assert benchmarks == ["bist100"]
    assert stock_ids == [10, 11, 42]


def test_split_selection_survives_failing_holdings_lookup():
    def boom(_source):
        raise RuntimeError("okunamadı")

    sources, benchmarks, stock_ids = support.split_selection(["holdings:dashboard"], boom)
    assert (sources, benchmarks, stock_ids) == (["dashboard"], [], [])


def test_build_filter_state_defaults_primary_source_to_dashboard():
    state = support.build_filter_state(["bist100"], date(2026, 1, 1), date(2026, 2, 1), "USD", lambda _s: [])
    assert state.portfolio_source == "dashboard"
    assert state.selected_benchmarks == ["bist100"]
    assert state.currency_mode == "USD"


def test_find_column_prefers_exact_then_substring_then_first():
    df = pd.DataFrame({"Ana Portföy": [1.0], "BIST 100": [2.0]})
    assert support.find_column(df, "BIST 100") == "BIST 100"
    assert support.find_column(df, "bist") == "BIST 100"
    assert support.find_column(df, "yok") == "Ana Portföy"
    assert support.find_column(pd.DataFrame(), "x") is None


def test_commentary_prompt_lists_metrics_and_period():
    metrics = [{"label": "A", "totalReturn": 12.5, "volatility": 8.1}]
    prompt = support.build_commentary_prompt((date(2026, 1, 1), date(2026, 2, 1)), metrics, "NORMAL", "USD")
    assert "01.01.2026 ile 01.02.2026" in prompt
    assert "**A**: Toplam Getiri: %12.5" in prompt
    assert "Normal biçiminde, USD cinsinden" in prompt
    assert "seçili dönemde" in support.build_commentary_prompt((None, None), metrics, "NORMAL", "TL")


def test_fetch_portfolio_holdings_without_service_returns_empty():
    assert support.fetch_portfolio_holdings(None, "dashboard", "3A") == []


def test_treemap_items_from_metrics_weights_by_abs_return():
    items = charts.treemap_items_from_metrics([{"code": "A", "label": "A", "totalReturn": -4.0, "volatility": 2.0}])
    assert items[0]["ret"] == -4.0
    assert items[0]["weight"] == 4.0
    assert charts.treemap_items_from_metrics([{"code": "B", "totalReturn": 0.2}])[0]["weight"] == 1.0


def test_chart_builders_embed_series_titles():
    index = pd.date_range("2026-01-01", periods=3, freq="D")
    df = pd.DataFrame({"A": [100.0, 101.0, 102.0]}, index=index)
    assert "title: 'A'" in charts.build_line_chart_html(df, is_normalized=True)
    assert "AreaSeries" in charts.build_drawdown_html(df)
    assert "type: 'bar'" in charts.build_periodic_html(df)
    assert "type: 'scatter'" in charts.build_scatter_html([{"label": "A", "volatility": 1.0, "totalReturn": 2.0}])
    html = charts.build_treemap_html([], True, "Model1")
    assert 'const portfolioName = "Model1"' in html and "const isHoldings = true" in html
