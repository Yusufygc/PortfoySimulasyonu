"""Teknik analiz ticker detay HTML üretici testleri (Plotly/ağ erişimi yok)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

import pytest

from src.domain.models.daily_price import DailyPrice
from src.domain.models.golden_cross_event import CrossType, GoldenCrossEvent


def _prices(n: int = 250) -> list[DailyPrice]:
    start = date(2020, 1, 1)
    return [
        DailyPrice(
            id=None, stock_id=1,
            price_date=start + timedelta(days=i),
            close_price=Decimal(str(100 + i * 0.1)),
        )
        for i in range(n)
    ]


def _events() -> list[GoldenCrossEvent]:
    return [
        GoldenCrossEvent(
            id=None, stock_id=1, ticker="FROTO",
            cross_date=date(2020, 6, 1),
            cross_type=CrossType.GOLDEN,
            short_ma=Decimal("110.5"), long_ma=Decimal("108.2"),
            close_price=Decimal("115"),
        ),
        GoldenCrossEvent(
            id=None, stock_id=1, ticker="FROTO",
            cross_date=date(2020, 8, 1),
            cross_type=CrossType.DEATH,
            short_ma=Decimal("120.1"), long_ma=Decimal("121.4"),
            close_price=Decimal("119"),
        ),
    ]


@pytest.fixture
def patched_plotly(tmp_path):
    js_file = tmp_path / "plotly.min.js"
    js_file.write_text("/* stub */")
    with patch(
        "src.ui.pages.technical.utils.detail_chart_html.ensure_patched_plotly_js",
        return_value=str(js_file),
    ):
        yield


class TestBuildDetailDashboard:
    def test_empty_prices_returns_empty_message(self, patched_plotly):
        from src.ui.pages.technical.utils.detail_chart_html import build_detail_dashboard
        html = build_detail_dashboard("FROTO", prices=[], events=[])
        assert "Fiyat verisi bulunamadı" in html
        assert "<html" in html and "</html>" in html

    def test_with_prices_and_events(self, patched_plotly):
        from src.ui.pages.technical.utils.detail_chart_html import build_detail_dashboard
        html = build_detail_dashboard("FROTO", prices=_prices(), events=_events())
        assert "FROTO" in html
        assert "Kapanış" in html
        assert "SMA50" in html
        assert "SMA200" in html
        assert "Golden" in html
        assert "Death" in html

    def test_offline_plotly_no_cdn(self, patched_plotly):
        from src.ui.pages.technical.utils.detail_chart_html import build_detail_dashboard
        html = build_detail_dashboard("FROTO", prices=_prices(), events=[])
        assert "cdn.plot.ly" not in html
        assert "file:///" in html

    def test_events_table_sorted_newest_first(self, patched_plotly):
        from src.ui.pages.technical.utils.detail_chart_html import build_detail_dashboard
        html = build_detail_dashboard("FROTO", prices=_prices(), events=_events())
        i_aug = html.find("01/08/2020")
        i_jun = html.find("01/06/2020")
        assert i_aug != -1 and i_jun != -1
        assert i_aug < i_jun  # newest first

    def test_renders_with_no_events(self, patched_plotly):
        from src.ui.pages.technical.utils.detail_chart_html import build_detail_dashboard
        html = build_detail_dashboard("FROTO", prices=_prices(), events=[])
        assert "Cross olayı yok" in html
