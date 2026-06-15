"""Finansal dashboard HTML üretici birim testleri — Plotly/ağ erişimi yok."""
from __future__ import annotations

import json
import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Ortak test metriği — compute_metrics() çıktısını simüle eder
# ---------------------------------------------------------------------------

def _make_metrics(ticker: str = "FROTO") -> dict:
    periods = ["2024/3", "2023/12", "2023/9", "2023/6"]
    return {
        "ticker":   ticker,
        "currency": "TRY",
        "periods":  periods,
        "_raw_sections": {
            "gelir": {
                "Satışlar": {"2024/3": 1_000_000, "2023/12": 900_000},
            },
        },
        "_delta": {"yoy": {}},
        "_tufe":  {},
        "_market_val": {},
        "satis":          {p: 1_000_000 for p in periods},
        "favok":          {p: 200_000   for p in periods},
        "net_kar":        {p: 100_000   for p in periods},
        "net_borc":       {p: 50_000    for p in periods},
        "net_borc_favok": {p: 0.25      for p in periods},
        "fcf":            {p: 80_000    for p in periods},
        "isletme_cf":     {p: 120_000   for p in periods},
        "capex":          {p: -40_000   for p in periods},
        "brut_kar":       {p: 300_000   for p in periods},
        "faaliyet_kar":   {p: 250_000   for p in periods},
        "brut_kar_marji": {p: 30.0      for p in periods},
        "favok_marji":    {p: 20.0      for p in periods},
        "net_kar_marji":  {p: 10.0      for p in periods},
        "roe":            {p: 15.0      for p in periods},
        "donen_varlik":   {p: 500_000   for p in periods},
        "kisa_vadeli_yukuml": {p: 300_000 for p in periods},
        "ozkaynak":       {p: 1_000_000 for p in periods},
        "odenmis_sermaye":{p: 200_000   for p in periods},
        "dupont_net_kar_marji": {p: 10.0 for p in periods},
        "dupont_varlik_devir":  {p: 1.2  for p in periods},
        "dupont_fin_kaldirac":  {p: 2.0  for p in periods},
        "dupont_roe":           {p: 15.0 for p in periods},
        "dso": {p: 45 for p in periods},
        "dio": {p: 30 for p in periods},
        "dpo": {p: 60 for p in periods},
        "ccc": {p: 15 for p in periods},
        "cari_oran":      {p: 1.5  for p in periods},
        "piotroski":      {p: 7    for p in periods},
        "_piotroski_detail": {},
        "satis_ceyrek":   {},
        "temettu_odeme":  {p: -20_000 for p in periods},
        "dagitim_orani":  {p: 20.0    for p in periods},
        "yurtici_satis":  {p: None for p in periods},
        "yurtdisi_satis": {p: None for p in periods},
        "ihracat_orani":  {p: None for p in periods},
        "bedelsiz_potansiyel_x":   {p: 1.5  for p in periods},
        "bedelsiz_potansiyel_pct": {p: 50.0 for p in periods},
        "enflasyon_duzeltildi":    {p: False for p in periods},
    }


# ---------------------------------------------------------------------------
# build_finansal_tablo_pane
# ---------------------------------------------------------------------------

class TestBuildFinansalTabloPane:
    def test_contains_required_js_vars(self):
        from src.ui.pages.financials.utils.finansal_tablo import build_finansal_tablo_pane
        m = _make_metrics("FROTO")
        html = build_finansal_tablo_pane(m, 4)
        assert "const TICKER=" in html
        assert '"FROTO"' in html
        assert "const ALL_PERIODS=" in html
        assert "const RAW_SECTIONS=" in html
        assert "const SECTION_ORDER=" in html
        assert "const DEFAULT_N=4" in html

    def test_raw_sections_serialized(self):
        from src.ui.pages.financials.utils.finansal_tablo import build_finansal_tablo_pane
        m = _make_metrics("THYAO")
        html = build_finansal_tablo_pane(m, 4)
        assert "Satışlar" in html

    def test_empty_raw_sections_does_not_crash(self):
        from src.ui.pages.financials.utils.finansal_tablo import build_finansal_tablo_pane
        m = _make_metrics()
        m["_raw_sections"] = {}
        html = build_finansal_tablo_pane(m, 4)
        assert "fin-tbl" in html

    def test_contains_table_and_controls(self):
        from src.ui.pages.financials.utils.finansal_tablo import build_finansal_tablo_pane
        html = build_finansal_tablo_pane(_make_metrics(), 4)
        assert "fin-thead" in html
        assert "pd-sel" in html
        assert "pkg-sel" in html


# ---------------------------------------------------------------------------
# build_dashboard — sekme sayısı ve yapısı
# ---------------------------------------------------------------------------

class TestBuildDashboard:
    @pytest.fixture(autouse=True)
    def _patch_plotly_js(self, tmp_path):
        js_file = tmp_path / "plotly.min.js"
        js_file.write_text("/* stub */")
        with patch(
            "src.ui.pages.financials.utils.dashboard_html.ensure_patched_plotly_js",
            return_value=str(js_file),
        ):
            yield

    def test_has_18_tabs(self):
        from src.ui.pages.financials.utils.dashboard_html import build_dashboard
        html = build_dashboard(_make_metrics(), n_periods=4)
        assert html.count("class='tab-btn") == 18

    def test_finansal_tablo_is_first_tab(self):
        from src.ui.pages.financials.utils.dashboard_html import build_dashboard
        html = build_dashboard(_make_metrics(), n_periods=4)
        ftablo_pos = html.index("'ftablo'")
        kpi_pos    = html.index("'kpi'")
        assert ftablo_pos < kpi_pos

    def test_offline_plotly_no_cdn(self):
        from src.ui.pages.financials.utils.dashboard_html import build_dashboard
        html = build_dashboard(_make_metrics(), n_periods=4)
        assert "cdn.plot.ly" not in html
        assert "file:///" in html

    def test_returns_valid_html_string(self):
        from src.ui.pages.financials.utils.dashboard_html import build_dashboard
        html = build_dashboard(_make_metrics(), n_periods=4)
        assert html.startswith("<!DOCTYPE html>")
        assert "</html>" in html


# ---------------------------------------------------------------------------
# Yeni chart fonksiyonları — None/boş graceful
# ---------------------------------------------------------------------------

class TestNewChartFunctions:
    def test_chart_net_borc_returns_figure(self):
        from src.ui.pages.financials.utils.charts import _chart_net_borc
        import plotly.graph_objects as go
        assert isinstance(_chart_net_borc(_make_metrics(), 4), go.Figure)

    def test_chart_waterfall_returns_figure(self):
        from src.ui.pages.financials.utils.charts import _chart_waterfall
        import plotly.graph_objects as go
        assert isinstance(_chart_waterfall(_make_metrics(), 4), go.Figure)

    def test_chart_waterfall_empty_periods(self):
        from src.ui.pages.financials.utils.charts import _chart_waterfall
        m = _make_metrics(); m["periods"] = []
        fig = _chart_waterfall(m, 4)
        assert fig is not None

    def test_chart_fcf_vs_netkar_returns_figure(self):
        from src.ui.pages.financials.utils.charts import _chart_fcf_vs_netkar
        import plotly.graph_objects as go
        assert isinstance(_chart_fcf_vs_netkar(_make_metrics(), 4), go.Figure)

    def test_chart_nakit_akis_returns_figure(self):
        from src.ui.pages.financials.utils.charts import _chart_nakit_akis
        import plotly.graph_objects as go
        assert isinstance(_chart_nakit_akis(_make_metrics(), 4), go.Figure)

    def test_chart_heatmap_returns_figure(self):
        from src.ui.pages.financials.utils.charts import _chart_heatmap
        import plotly.graph_objects as go
        assert isinstance(_chart_heatmap(_make_metrics(), 4), go.Figure)

    def test_chart_bedelsiz_returns_figure(self):
        from src.ui.pages.financials.utils.charts import _chart_bedelsiz
        import plotly.graph_objects as go
        assert isinstance(_chart_bedelsiz(_make_metrics(), 4), go.Figure)

    def test_chart_satis_breakdown_empty_data(self):
        from src.ui.pages.financials.utils.charts import _chart_satis_breakdown
        import plotly.graph_objects as go
        fig = _chart_satis_breakdown(_make_metrics(), 4)
        assert isinstance(fig, go.Figure)

    def test_chart_satis_breakdown_with_data(self):
        from src.ui.pages.financials.utils.charts import _chart_satis_breakdown
        import plotly.graph_objects as go
        m = _make_metrics()
        for p in m["periods"]:
            m["yurtici_satis"][p]  = 600_000
            m["yurtdisi_satis"][p] = 400_000
            m["ihracat_orani"][p]  = 40.0
        assert isinstance(_chart_satis_breakdown(m, 4), go.Figure)

    def test_bedelsiz_ef_info_enflasyon_true(self):
        from src.ui.pages.financials.utils.charts import _bedelsiz_ef_info
        m = _make_metrics()
        m["enflasyon_duzeltildi"]["2024/3"] = True
        subtitle, color = _bedelsiz_ef_info(m, "2024/3")
        assert "TMS 29" in subtitle
        assert color == "#22c55e"

    def test_bedelsiz_ef_info_enflasyon_false(self):
        from src.ui.pages.financials.utils.charts import _bedelsiz_ef_info
        _, color = _bedelsiz_ef_info(_make_metrics(), "2024/3")
        assert color == "#f97316"
