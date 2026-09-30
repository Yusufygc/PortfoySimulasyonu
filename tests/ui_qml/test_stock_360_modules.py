"""
Stock 360 Modüler Alt Bileşen Birim Testleri.

Ayrıştırılan formatters, fallback, calc ve html modüllerinin
işlevsellik ve sınır durumlarını doğrular.
"""
from __future__ import annotations

from decimal import Decimal
from datetime import datetime
from unittest.mock import MagicMock

from src.domain.models.shareholder import ShareholderSnapshot, ShareholderRow
from src.ui_qml.controllers.stock_360_formatters import (
    format_currency,
    format_price,
    format_volume,
    DONUT_COLORS,
)
from src.ui_qml.controllers.stock_360_fallback import (
    guess_sector,
    get_default_overview,
    get_default_technical,
    get_fallback_financials,
    get_fallback_shareholders,
)
from src.ui_qml.controllers.stock_360_html import (
    write_temp_html,
    cleanup_temp_files,
)
from src.ui_qml.controllers.stock_360_calc import (
    parse_valuation_ratios,
    compute_financial_bars,
    compute_revenue_chart,
    compute_dupont_data,
    compute_cash_flow_data,
    compute_financial_table_rows,
    compute_shareholder_timeline,
    parse_shareholder_data,
)


def test_formatters():
    # Para birimi
    assert format_currency(None) == "—"
    assert format_currency(1_500_000_000) == "₺1.50 Mr"
    assert format_currency(25_000_000) == "₺25.00 Mn"
    assert format_currency(1_500) == "₺1,500.00"
    assert format_currency(45.5) == "₺45.50"

    # Fiyat
    assert format_price(None) == "₺0.00"
    assert format_price(123.456) == "₺123.46"

    # Hacim
    assert format_volume(None) == "0"
    assert format_volume(0) == "0"
    assert format_volume(2_500_000_000) == "2.5 Mr"
    assert format_volume(15_000_000) == "15.0 Mn"
    assert format_volume(5_000) == "5.0 Bin"


def test_fallback_data():
    assert guess_sector("THYAO") == "Ulaştırma & Havacılık"
    assert guess_sector("BIMAS") == "Perakende Ticaret"
    assert guess_sector("UNKNOWN") == "Borsa İstanbul Sanayi & Hizmet"

    ov = get_default_overview("BIMAS")
    assert ov["last_price_raw"] == 394.00
    assert ov["is_daily_positive"] is True

    tech = get_default_technical()
    assert tech["rsi_status"] == "Dengeli"
    assert tech["trend_status"] == "Boğa / Golden Cross"

    fin = get_fallback_financials("BIMAS")
    assert "ratios" in fin
    assert "raw_data" in fin
    assert fin["ratios"]["pe_ratio"] == "13.4"

    sh = get_fallback_shareholders("BIMAS")
    assert sh["free_float_ratio_str"] == "%43.11"
    assert len(sh["shareholders_list"]) == 2


def test_calc_revenue_chart_and_dupont():
    metrics = {
        "periods": ["2026/3", "2025/12", "2025/9", "2025/6"],
        "satis_ceyrek": {
            "2026/3": 100.0,
            "2025/12": 80.0,
            "2025/9": 70.0,
            "2025/6": 60.0,
            "2025/3": 50.0,
        },
        "net_kar_ceyrek": {
            "2026/3": 15.0,
            "2025/12": 10.0,
            "2025/9": 8.0,
            "2025/6": 6.0,
        },
        "net_kar_marji": {
            "2026/3": 15.0,
            "2025/12": 12.5,
        },
        "dupont_net_kar_marji": {"2026/3": 15.0},
        "dupont_varlik_devir": {"2026/3": 1.5},
        "dupont_fin_kaldirac": {"2026/3": 2.0},
        "dupont_roe": {"2026/3": 45.0},
        "piotroski": {"2026/3": 8},
    }

    # Revenue chart
    chart_data, kpis = compute_revenue_chart(metrics, metrics["periods"])
    assert len(chart_data) == 4
    assert kpis["latest_quarter_revenue"] == "₺100.00"
    assert kpis["revenue_yoy_growth"] == "+100.0%"

    # DuPont
    dupont = compute_dupont_data(metrics, metrics["periods"])
    assert dupont["netMargin"] == "%15.00"
    assert dupont["piotroski"] == "8/9"
    assert dupont["piotroskiStatus"] == "Yüksek Finansal Güç"


def test_calc_cash_flow_and_bars():
    metrics = {
        "isletme_cf": {"2026/3": 50.0},
        "capex": {"2026/3": 20.0},
        "fcf": {"2026/3": 30.0},
        "net_borc": {"2026/3": 40.0},
        "net_borc_favok_ttm": {"2026/3": 1.2},
    }
    cf = compute_cash_flow_data(metrics, ["2026/3"])
    assert cf["operatingCf"] == "₺50.00"
    assert cf["isDebtSafe"] is True
    assert cf["debtStatus"] == "Sürdürülebilir & Sağlıklı"

    # Financial bars
    raw = {
        "satis_ceyrek": {"2026/3": 1000.0, "2025/12": 900.0},
    }
    bars, summary = compute_financial_bars(raw, ["2026/3", "2025/12"], "satis")
    assert len(bars) == 2
    assert "Net Satışlar" in summary


def test_calc_shareholder_data_and_timeline():
    snap = ShareholderSnapshot(
        creation_date=datetime(2026, 1, 15).date(),
        rows=(
            ShareholderRow(
                shareholder_name="KURUCU ORTAK",
                share_in_capital=Decimal("600"),
                ratio_in_capital=Decimal("60.0"),
                voting_right_ratio=Decimal("60.0"),
            ),
            ShareholderRow(
                shareholder_name="DİĞER (HALKA AÇIK)",
                share_in_capital=Decimal("400"),
                ratio_in_capital=Decimal("40.0"),
                voting_right_ratio=Decimal("40.0"),
            ),
            ShareholderRow(
                shareholder_name="TOPLAM",
                is_total=True,
                share_in_capital=Decimal("1000"),
                ratio_in_capital=Decimal("100.0"),
                voting_right_ratio=Decimal("100.0"),
            ),
        ),
    )

    parsed = parse_shareholder_data(snap)
    assert parsed["date_str"] == "15.01.2026"
    assert len(parsed["shareholders_list"]) == 2
    assert parsed["free_float_ratio_str"] == "%40.00"
    assert parsed["free_float_pct"] == 0.40

    prev_snap = ShareholderSnapshot(
        creation_date=datetime(2025, 6, 1).date(),
        rows=(
            ShareholderRow(
                shareholder_name="KURUCU ORTAK",
                share_in_capital=Decimal("550"),
                ratio_in_capital=Decimal("55.0"),
                voting_right_ratio=Decimal("55.0"),
            ),
            ShareholderRow(
                shareholder_name="DİĞER (HALKA AÇIK)",
                share_in_capital=Decimal("450"),
                ratio_in_capital=Decimal("45.0"),
                voting_right_ratio=Decimal("45.0"),
            ),
        ),
    )

    timeline = compute_shareholder_timeline([snap, prev_snap])
    assert len(timeline) == 2
    assert timeline[0]["diff"] == 5.0
    assert timeline[0]["isIncrease"] is True


def test_temp_html_management():
    url, path = write_temp_html("test_fin", "THYAO", "<html><body>Test</body></html>")
    assert url.startswith("file:///")
    assert path is not None

    cleanup_temp_files([path])
