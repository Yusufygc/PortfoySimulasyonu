"""ExcelReportBuilder ve ExcelExportService birim testleri."""
from __future__ import annotations

import pytest

pd = pytest.importorskip("pandas")

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from src.application.services.reporting.daily_history_models import (
    DailyPosition,
    DailyPortfolioSnapshot,
    ExportMode,
    PortfolioStatus,
    SUMMARY_ROW_LABEL,
)
from src.application.services.reporting.excel_report_builder import ExcelReportBuilder
from src.application.services.reporting.excel_export_service import ExcelExportService


# ────── Yardımcı fabrikalar ──────────────────────────────────────────────────

def _pos(
    ticker: str,
    d: date = date(2026, 1, 2),
    qty: int = 10,
    avg_cost: Decimal = Decimal("10"),
    close_price: Decimal | None = Decimal("10"),
    unrealized_pnl_tl: Decimal | None = Decimal("0"),
    unrealized_pnl_pct: Decimal | None = Decimal("0"),
) -> DailyPosition:
    cost_basis = avg_cost * qty
    pos_val = close_price * qty if close_price is not None else None
    return DailyPosition(
        date=d,
        ticker=ticker,
        quantity=qty,
        avg_cost=avg_cost,
        cost_basis=cost_basis,
        close_price=close_price,
        position_value=pos_val,
        daily_price_change_pct=None,
        daily_pnl_tl=None,
        unrealized_pnl_tl=unrealized_pnl_tl,
        unrealized_pnl_pct=unrealized_pnl_pct,
        weight_pct=Decimal("1"),
    )


def _snap(
    d: date = date(2026, 1, 2),
    total_value: Decimal | None = Decimal("100"),
    daily_pnl: Decimal | None = Decimal("0"),
    cumulative_pnl: Decimal | None = Decimal("0"),
    status: str = PortfolioStatus.OPEN,
) -> DailyPortfolioSnapshot:
    return DailyPortfolioSnapshot(
        date=d,
        total_cost_basis=Decimal("100"),
        total_value=total_value,
        daily_return_pct=None,
        cumulative_return_pct=None,
        daily_pnl=daily_pnl,
        cumulative_pnl=cumulative_pnl,
        status=status,
    )


def _builder() -> ExcelReportBuilder:
    return ExcelReportBuilder(formatter=MagicMock())


# ────── BUG 1: Decimal sıfır değerleri kaybolmamalı ─────────────────────────

def test_decimal_zero_shows_as_zero_not_none():
    """Breakeven (unrealized_pnl_tl=0) pozisyon None değil 0.0 yazmalı."""
    builder = _builder()
    positions = [_pos("AAA.IS", unrealized_pnl_tl=Decimal("0"))]
    snapshots = [_snap()]

    df = builder._build_detail_df(positions, snapshots)
    data_row = df[df["Hisse"] == "AAA.IS"].iloc[0]

    assert data_row["Toplam K/Z (TL)"] == 0.0, "Sıfır K/Z None değil 0.0 olmalı"


def test_zero_daily_pnl_in_summary_is_not_none():
    """Snapshot'ta daily_pnl=0 ise Summary'de None değil 0.0 yazmalı."""
    builder = _builder()
    snapshots = [_snap(daily_pnl=Decimal("0"))]

    df = builder._build_summary_df(snapshots)
    assert df.iloc[0]["Günlük K/Z (TL)"] == 0.0


# ────── BUG 2: APPEND modunda TOPLAM satırları birikmemeli ──────────────────

def test_toplam_rows_not_duplicated_in_append_mode(tmp_path):
    """Aynı aralığı iki kez APPEND ile dışa aktar — TOPLAM satırı ikişer olmamalı."""
    builder = _builder()
    file_path = tmp_path / "test.xlsx"

    positions = [_pos("AAA.IS")]
    snapshots = [_snap()]

    # İlk yazma (fresh)
    detail_df    = builder._build_detail_df(positions, snapshots)
    summary_df   = builder._build_summary_df(snapshots)
    stock_df     = builder._build_stock_summary_df(positions)
    dashboard_df = builder._build_dashboard_df(snapshots, positions)
    builder._write_fresh_excel(file_path, summary_df, detail_df, stock_df, dashboard_df)

    # İkinci yazma (append — aynı veri)
    builder._append_to_existing_excel(file_path, summary_df, detail_df, stock_df, dashboard_df)

    result = pd.read_excel(file_path, sheet_name="Günlük Detaylar")
    toplam_count = result["Hisse"].str.contains("GÜNLÜK TOPLAM", na=False).sum()
    assert toplam_count == 1, f"TOPLAM satırı sadece 1 kez olmalı, {toplam_count} bulundu"


# ────── TASARIM 2: _fmt_tr_money(None) → "—" ────────────────────────────────

def test_fmt_tr_money_none_returns_dash():
    builder = _builder()
    assert builder._fmt_tr_money(None) == "—"


def test_fmt_tr_money_zero_returns_formatted():
    builder = _builder()
    result = builder._fmt_tr_money(Decimal("0"))
    assert result == "0,00"


# ────── TASARIM 3: Boş veri → ValueError ─────────────────────────────────────

def test_export_raises_on_empty_data(tmp_path):
    """Hiç trade/fiyat verisi yoksa anlamlı hata fırlatılmalı."""
    sim_service = MagicMock()
    sim_service.simulate_history.return_value = ([], [])

    svc = ExcelExportService(simulation_service=sim_service, report_builder=MagicMock())

    with pytest.raises(ValueError, match="veri bulunamadı"):
        svc.export_history(date(2026, 1, 1), date(2026, 1, 5), tmp_path / "out.xlsx")


# ────── Summary hafta sonu filtreleme ────────────────────────────────────────

def test_summary_df_excludes_weekend_snapshots():
    builder = _builder()
    snapshots = [
        _snap(d=date(2026, 1, 2), status=PortfolioStatus.OPEN),
        _snap(d=date(2026, 1, 3), status=PortfolioStatus.WEEKEND),
        _snap(d=date(2026, 1, 4), status=PortfolioStatus.WEEKEND),
        _snap(d=date(2026, 1, 5), status=PortfolioStatus.OPEN),
    ]
    df = builder._build_summary_df(snapshots)
    assert len(df) == 2
    assert set(df["Tarih"].tolist()) == {date(2026, 1, 2), date(2026, 1, 5)}


# ────── Stock summary — her hisse için en son pozisyon ───────────────────────

def test_stock_summary_df_uses_latest_position_per_ticker():
    """Aynı hisse birden fazla günde varsa son güne ait pozisyon kullanılmalı."""
    builder = _builder()
    positions = [
        _pos("AAA.IS", d=date(2026, 1, 2), avg_cost=Decimal("10"), qty=5),
        _pos("AAA.IS", d=date(2026, 1, 5), avg_cost=Decimal("12"), qty=10),
    ]
    df = builder._build_stock_summary_df(positions)
    row = df[df["Hisse"] == "AAA.IS"].iloc[0]
    assert row["Son Adet"] == 10
    assert row["Ort. Maliyet (TL)"] == pytest.approx(12.0)
    assert row["Toplam Gün Sayısı"] == 2
