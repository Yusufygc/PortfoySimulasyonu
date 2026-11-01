"""E3 ile denetleyicilerden ayrılan Qt'siz yardımcılar: bütçe ayları, model portföy değerleme ve dışa aktarım aralığı."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace

from src.ui_qml.controllers.model_portfolio_export import parse_date, resolve_range, run_history_export
from src.ui_qml.controllers.model_portfolio_valuation import ModelPortfolioValuation, empty_summary, profit_loss_state
from src.ui_qml.controllers.planning_dca_chart import build_dca_chart_html
from src.ui_qml.controllers.planning_months import budget_months

D = Decimal


def test_budget_months_goes_back_to_oldest_budget_or_first_trade_and_is_newest_first():
    service = SimpleNamespace(get_all_budgets=lambda: [SimpleNamespace(month="2025-11"), SimpleNamespace(month=None)])
    portfolio = SimpleNamespace(get_first_trade_date=lambda: date(2025, 12, 5))

    months = budget_months(service, portfolio, "2026-02", now=datetime(2026, 2, 10))

    assert months[0] == "2026-02" and months[-1] == "2025-01"  # varsayılan başlangıç: önceki yılın Ocak'ı
    assert months == sorted(months, reverse=True) and len(months) == 14


def test_budget_months_without_services_and_unlisted_current_month():
    months = budget_months(None, None, "2027-01", now=datetime(2026, 3, 1))
    assert months[0] == "2027-01" and "2026-03" in months and "2025-01" in months


def test_budget_months_survives_service_error():
    broken = SimpleNamespace(get_all_budgets=lambda: (_ for _ in ()).throw(RuntimeError("db")))
    assert budget_months(broken, None, "2026-03", now=datetime(2026, 3, 1))[0] == "2026-03"


def test_dca_chart_html_is_empty_without_series_and_embeds_points():
    assert build_dca_chart_html({}) == ""
    html = build_dca_chart_html({date(2026, 1, 2): D("1000.5")})
    assert "{time:'2026-01-02',value:1000.50}" in html and "createChart" in html


def test_resolve_range_defaults_and_errors():
    first = date(2026, 1, 5)
    start, end, error = resolve_range("", "", first)
    assert (start, error) == (first, "") and end == date.today()
    assert resolve_range("01.02.2026", "2026-03-01", first)[:2] == (date(2026, 2, 1), date(2026, 3, 1))
    assert resolve_range("31/02/2026", "", first)[2]  # biçim hatası
    assert resolve_range("", "", None)[2]  # işlem yok
    assert resolve_range("01.03.2026", "01.02.2026", first)[2]  # başlangıç > bitiş
    assert parse_date("x") is None


def test_run_history_export_reports_missing_service_and_failure(tmp_path):
    ok, text = run_history_export(None, 1, date(2026, 1, 1), date(2026, 1, 2), "", False)
    assert not ok and text

    class Failing:
        def export_model_portfolio_history(self, **_):
            raise RuntimeError("disk")

    ok, text = run_history_export(Failing(), 1, date(2026, 1, 1), date(2026, 1, 2), str(tmp_path / "a.xlsx"), False)
    assert not ok and "disk" in text


def test_run_history_export_forces_xlsx_suffix_and_reports_name(tmp_path):
    calls = []
    service = SimpleNamespace(export_model_portfolio_history=lambda **kw: calls.append(kw))

    ok, text = run_history_export(service, 7, date(2026, 1, 1), date(2026, 1, 2), str(tmp_path / "rapor"), True)

    assert ok and "rapor.xlsx" in text
    assert calls[0]["file_path"].suffix == ".xlsx" and calls[0]["mode"].name == "APPEND"


class _Service:
    def get_positions(self, portfolio_id):
        return {1: SimpleNamespace(), 2: SimpleNamespace()}

    def get_portfolio_summary(self, portfolio_id, price_map):
        return {"net_capital": D("1000"), "remaining_cash": D("100"), "total_value": D("1200"),
                "profit_loss": D("200"), "profit_loss_pct": D("20")}

    def get_positions_with_details(self, portfolio_id, price_map):
        return [{"stock_id": 1, "ticker": "AAA.IS", "name": "A", "quantity": 10, "avg_cost": D("100"),
                 "current_price": D("110"), "current_value": D("1100"), "total_cost": D("1000"), "profit_loss": D("100")}]


class _Lookup:
    def get_latest_price_map(self, ids):
        return {1: D("110")}

    def get_previous_close(self, stock_id):
        return D("100") if stock_id == 1 else D("50")


def test_valuation_summary_and_rows_match_hand_calculation():
    valuation = ModelPortfolioValuation(_Service(), _Lookup())

    prices = valuation.price_map(5)
    assert prices == {1: D("110"), 2: D("50")}  # fiyatı olmayan hisse son kapanışa düşer

    summary = valuation.summary(5, prices)
    assert summary["total_value"] == "1.200,00 ₺" and summary["state"] == "positive" and summary["profit_loss_pct"] == 20.0

    row = valuation.position_rows(5, prices)[0]
    assert row["ticker"] == "AAA"
    assert row["dailyChangePct"] == 10.0 and row["totalChangePct"] == 10.0  # 110/100 ve 110/100
    assert round(row["weight"], 2) == round(1100 / 1200 * 100, 2)
    assert row["dailyChangeFormatted"] == "+%10,00"


def test_valuation_price_map_is_empty_when_service_fails():
    class Broken:
        def get_positions(self, _):
            raise RuntimeError("db")

    assert ModelPortfolioValuation(Broken(), None).price_map(1) == {}


def test_profit_loss_state_and_empty_summary():
    assert [profit_loss_state(D(v)) for v in ("0.004", "1", "-1")] == ["neutral", "positive", "negative"]
    assert empty_summary()["state"] == "neutral" and empty_summary()["remaining_cash_raw"] == D("0")
