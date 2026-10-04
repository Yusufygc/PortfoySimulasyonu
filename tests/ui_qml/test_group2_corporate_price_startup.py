"""
Grup 2 testleri: kurumsal aksiyon (bedelli/bedelsiz) girişi + KAP/MKK adayları, fiyat verisi sağlığı
paneli ve açılış otomatik veri bakım işleri (QML controller'ları ve yeni QML bileşenleri).
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from src.domain.market_clock import market_today
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QSettings, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.application.services.market.price_data_health_service import (
    PriceDataHealthReport,
    PriceDataUpdateResult,
    StockPriceHealthRow,
)
from src.domain.models.corporate_action import ActionType
from src.domain.models.corporate_action_candidate import (
    CorporateActionCandidate,
    CorporateActionCandidateStatus,
)
from src.ui_qml.controllers.corporate_action_controller import (
    CorporateActionController,
    compute_preview,
)
from src.ui_qml.controllers.price_data_controller import PriceDataController
from src.ui_qml.controllers.startup_jobs_controller import (
    AUTO_BACKFILL_SETTINGS_KEY,
    AUTO_BIST_BACKFILL_SETTINGS_KEY,
    AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY,
    StartupJobsController,
    last_completed_trading_day,
)

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"


class ImmediateExecutor:
    """Worker işlerini aynı thread'de çalıştırır (testlerde asenkronluğu kaldırır)."""

    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


# ---------------------------------------------------------------------------
# Sermaye artırımı ön izleme
# ---------------------------------------------------------------------------

def test_preview_bedelsiz_50_percent():
    p = compute_preview(1000, Decimal("100000"), Decimal("50"), "BEDELSIZ", Decimal("50"), Decimal("0"))
    assert p["valid"] is True
    assert p["newShares"] == 500
    assert p["totalQty"] == 1500
    assert p["newAvgText"] == "66,6667 ₺"
    assert p["theoreticalText"] == "33,3333 ₺"


def test_preview_bedelli_uses_subscription_price():
    p = compute_preview(1000, Decimal("100000"), Decimal("50"), "BEDELLI", Decimal("50"), Decimal("10"))
    assert p["capitalText"] == "5.000,00 ₺"
    assert p["newAvgText"] == "70,0000 ₺"
    assert p["theoreticalText"] == "36,6667 ₺"


def test_preview_floors_new_shares_and_flags_insufficient_lots():
    assert compute_preview(3, Decimal("30"), None, "BEDELSIZ", Decimal("50"), Decimal("0"))["newShares"] == 1
    tiny = compute_preview(1, Decimal("10"), None, "BEDELSIZ", Decimal("10"), Decimal("0"))
    assert tiny["valid"] is False
    assert tiny["theoreticalText"] == "-"


# ---------------------------------------------------------------------------
# CorporateActionController
# ---------------------------------------------------------------------------

def _ca_container():
    container = MagicMock()
    stock = SimpleNamespace(id=7, ticker="THYAO.IS", name="THY")
    container.stock_lookup_service.find_stock.side_effect = lambda t: stock if t == "THYAO" else None
    container.stock_lookup_service.get_stock.return_value = stock
    container.current_price_resolver.price_map.return_value = {7: Decimal("300")}
    container.portfolio_service.get_first_trade_date.return_value = date(2025, 1, 2)
    container.backfill_service.backfill_for_single_stock.return_value = 42
    container.corporate_action_service.register_bedelsiz.return_value = SimpleNamespace(id=11)
    container.corporate_action_service.register_bedelli.return_value = SimpleNamespace(id=12)
    container.corporate_action_service.apply_action.return_value = SimpleNamespace(
        action_type=ActionType.BEDELSIZ, shares_before=1000, shares_after=1500
    )
    container.corporate_action_candidate_review_service.list_reviewable.return_value = []
    return container, stock


def _candidate(candidate_id=5, status=CorporateActionCandidateStatus.READY, **overrides):
    values = dict(
        id=candidate_id, ticker="THYAO", stock_id=7, source="KAP", source_disclosure_id="D1",
        source_url="https://kap.example/1", action_type=ActionType.BEDELLI, status=status,
        ratio=Decimal("0.5"), subscription_price=Decimal("10"), announcement_date=None,
        ex_date=date(2026, 3, 1), confidence=Decimal("0.8"), parse_notes="not",
    )
    values.update(overrides)
    return CorporateActionCandidate(**values)


def test_load_context_returns_position_and_price(qapp):
    container, _ = _ca_container()
    position = SimpleNamespace(total_quantity=1000, average_cost=Decimal("100"), total_cost=Decimal("100000"))
    container.portfolio_service.get_current_portfolio.return_value = SimpleNamespace(active_positions={7: position})
    container.current_price_resolver.price_map.return_value = {7: Decimal("300")}
    ctrl = CorporateActionController(container=container)

    ctx = ctrl.loadContext("THYAO")

    assert ctx["found"] is True
    assert ctx["quantity"] == 1000
    assert ctx["totalCost"] == 100000.0
    assert ctx["currentPrice"] == 300.0
    assert ctrl.loadContext("YOKHISSE")["found"] is False


def test_apply_action_registers_applies_and_backfills(qapp):
    container, _ = _ca_container()
    ctrl = CorporateActionController(container=container)
    ctrl._executor = ImmediateExecutor()
    notes = _capture(ctrl.notification)
    changed = _capture(ctrl.portfolioChanged)

    ctrl.applyAction("THYAO", "BEDELSIZ", 50.0, "2026-03-01", 0.0, "not")

    kwargs = container.corporate_action_service.register_bedelsiz.call_args.kwargs
    assert kwargs["ratio"] == Decimal("0.5")
    assert kwargs["ex_date"] == date(2026, 3, 1)
    container.corporate_action_service.apply_action.assert_called_once()
    container.backfill_service.backfill_for_single_stock.assert_called_once()
    assert notes[-1][0] is True and "42 günlük fiyat" in notes[-1][1]
    assert changed
    assert ctrl.isBusy is False


def test_apply_bedelli_passes_subscription_price(qapp):
    container, _ = _ca_container()
    ctrl = CorporateActionController(container=container)
    ctrl._executor = ImmediateExecutor()

    ctrl.applyAction("THYAO", "BEDELLI", 25.0, "2026-03-01", 12.5, "")

    spec = container.corporate_action_service.register_bedelli.call_args.args[0]
    assert spec.subscription_price == Decimal("12.5")
    assert spec.ratio == Decimal("0.25")


def test_apply_failure_removes_pending_action_and_reports(qapp):
    container, _ = _ca_container()
    container.corporate_action_service.apply_action.side_effect = ValueError("yetersiz lot")
    ctrl = CorporateActionController(container=container)
    ctrl._executor = ImmediateExecutor()
    notes = _capture(ctrl.notification)
    changed = _capture(ctrl.portfolioChanged)

    ctrl.applyAction("THYAO", "BEDELSIZ", 50.0, "2026-03-01", 0.0, "")

    container.corporate_action_service.delete_action.assert_called_once_with(11)
    assert notes[-1][0] is False and "yetersiz lot" in notes[-1][1]
    assert not changed


@pytest.mark.parametrize(
    "args, expected",
    [
        (("THYAO", "BEDELSIZ", 50.0, "gecersiz", 0.0, ""), "Ex-date geçersiz"),
        (("THYAO", "BEDELSIZ", 0.0, "2026-03-01", 0.0, ""), "oran"),
        (("THYAO", "BEDELLI", 50.0, "2026-03-01", 0.0, ""), "kullanım fiyatı"),
    ],
)
def test_apply_action_validates_inputs(qapp, args, expected):
    container, _ = _ca_container()
    ctrl = CorporateActionController(container=container)
    ctrl._executor = ImmediateExecutor()
    notes = _capture(ctrl.notification)

    ctrl.applyAction(*args)

    assert notes and notes[-1][0] is False and expected in notes[-1][1]
    container.corporate_action_service.register_bedelsiz.assert_not_called()


def test_candidates_list_and_apply_flow(qapp):
    container, stock = _ca_container()
    review = container.corporate_action_candidate_review_service
    review.list_reviewable.return_value = [_candidate(5), _candidate(6, status=CorporateActionCandidateStatus.NEEDS_REVIEW)]
    ctrl = CorporateActionController(container=container)
    ctrl._executor = ImmediateExecutor()

    rows = ctrl.candidates
    assert [r["id"] for r in rows] == [5, 6]
    assert rows[0]["canApply"] is True and rows[1]["canApply"] is False
    assert rows[0]["ratioPct"] == 50.0 and rows[0]["ticker"] == "THYAO"

    review.approve_and_apply.return_value = SimpleNamespace(
        result=SimpleNamespace(description="Uygulandı."), candidate=_candidate(5)
    )
    notes = _capture(ctrl.notification)
    ctrl.applyCandidate(5)
    review.approve_and_apply.assert_called_once_with(5)
    assert notes[-1][0] is True and notes[-1][1].startswith("Uygulandı.")


def test_candidate_ignore_update_and_detail(qapp):
    container, _ = _ca_container()
    review = container.corporate_action_candidate_review_service
    review.list_reviewable.return_value = [_candidate(5)]
    ctrl = CorporateActionController(container=container)

    ctrl.selectCandidate(5)
    assert "Kaynak: KAP:D1" in ctrl.detailText
    ctrl.selectCandidate(-1)
    assert ctrl.detailText == ""

    ctrl.ignoreCandidate(5)
    review.ignore.assert_called_once_with(5)

    ctrl.updateCandidate(5, "THYAO", "BEDELLI", 40.0, 8.0, "2026-04-01", "yeni not")
    updated = review.update_candidate.call_args.args[0]
    assert updated.ratio == Decimal("0.4")
    assert updated.subscription_price == Decimal("8.0")
    assert updated.ex_date == date(2026, 4, 1)
    assert updated.parse_notes == "yeni not"


def test_discover_reports_unavailable_source(qapp):
    container, _ = _ca_container()
    container.corporate_action_discovery_service.discover.return_value = SimpleNamespace(
        source_unavailable=True, errors=["zaman aşımı"], saved_count=0
    )
    ctrl = CorporateActionController(container=container)
    ctrl._executor = ImmediateExecutor()
    notes = _capture(ctrl.notification)

    ctrl.discoverCandidates()

    assert notes[-1][0] is False
    assert "zaman aşımı" in ctrl.detailText


def test_controller_without_services_is_safe(qapp):
    ctrl = CorporateActionController(container=None)
    notes = _capture(ctrl.notification)

    ctrl.applyAction("THYAO", "BEDELSIZ", 50.0, "2026-03-01", 0.0, "")
    ctrl.discoverCandidates()

    assert ctrl.candidateServicesAvailable is False
    assert len(notes) == 2 and not any(n[0] for n in notes)


# ---------------------------------------------------------------------------
# PriceDataController
# ---------------------------------------------------------------------------

def _health_report():
    healthy = StockPriceHealthRow(1, "AKBNK.IS", date(2026, 3, 10), [], None, None, "Sağlıklı")
    broken = StockPriceHealthRow(
        2, "THYAO.IS", date(2026, 3, 5), [date(2026, 3, 6), date(2026, 3, 9)],
        date(2026, 3, 6), date(2026, 3, 9), "Eksik Var",
    )
    return PriceDataHealthReport(
        start_date=date(2026, 3, 1), end_date=date(2026, 3, 10), total_stock_count=2,
        expected_business_days=[date(2026, 3, d) for d in (2, 3, 4, 5, 6, 9, 10)],
        weekend_days=[], empty_weekdays=[], holiday_candidate_dates=[],
        rows=[healthy, broken], latest_price_date=date(2026, 3, 10),
    )


def _price_container():
    container = MagicMock()
    service = container.price_data_health_service
    service.portfolio_scope_options.return_value = [
        SimpleNamespace(value="all_active", label="Tüm aktif portföyler"),
        SimpleNamespace(value="dashboard", label="Ana Portföy"),
    ]
    service.default_start_date.return_value = date(2026, 2, 1)
    service.minimum_start_date.return_value = None
    service.analyze.return_value = _health_report()
    container.trading_calendar.is_trading_day.return_value = True
    return container, service


def _price_ctrl(qapp, container):
    ctrl = PriceDataController(container=container)
    ctrl._executor = ImmediateExecutor()
    return ctrl


def test_price_data_scope_and_default_range(qapp):
    container, _ = _price_container()
    ctrl = _price_ctrl(qapp, container)

    assert [o["value"] for o in ctrl.scopeOptions] == ["all_active", "dashboard"]
    assert ctrl.startText == "01.02.2026"
    assert ctrl.serviceAvailable is True


def test_price_data_analyze_builds_rows_and_detail(qapp):
    container, service = _price_container()
    ctrl = _price_ctrl(qapp, container)
    notes = _capture(ctrl.notification)

    ctrl.analyze("01.03.2026", "10.03.2026", "all_active")

    service.analyze.assert_called_once_with(date(2026, 3, 1), date(2026, 3, 10), "all_active")
    assert ctrl.hasReport is True
    assert ctrl.stockCount == "2" and ctrl.missingCount == "2"
    assert [r["ticker"] for r in ctrl.rows] == ["AKBNK", "THYAO"]
    assert "Sağlık Raporu" in ctrl.detailHtml
    assert notes[-1][0] is True

    ctrl.setProblemOnly(True)
    assert [r["ticker"] for r in ctrl.rows] == ["THYAO"]

    ctrl.selectStock(2)
    assert "THYAO" in ctrl.detailHtml and "06.03.2026" in ctrl.detailHtml


def test_price_data_rejects_invalid_dates(qapp):
    container, service = _price_container()
    ctrl = _price_ctrl(qapp, container)
    notes = _capture(ctrl.notification)

    ctrl.analyze("abc", "10.03.2026", "all_active")
    ctrl.analyze("10.03.2026", "01.03.2026", "all_active")

    service.analyze.assert_not_called()
    assert len(notes) == 2 and not any(n[0] for n in notes)


def test_price_data_clamps_start_to_portfolio_minimum(qapp):
    container, service = _price_container()
    service.minimum_start_date.return_value = date(2026, 3, 3)
    ctrl = _price_ctrl(qapp, container)

    ctrl.analyze("01.03.2026", "10.03.2026", "all_active")

    assert service.analyze.call_args.args[0] == date(2026, 3, 3)
    assert ctrl.startText == "03.03.2026"


def test_price_data_update_publishes_prices_and_reanalyzes(qapp):
    container, service = _price_container()
    service.update_missing_prices.return_value = PriceDataUpdateResult(
        scanned_stock_count=2, updated_count=3, skipped_holiday_count=1, prices={2: Decimal("301")}
    )
    ctrl = _price_ctrl(qapp, container)
    ctrl.analyze("01.03.2026", "10.03.2026", "all_active")
    updated = _capture(ctrl.pricesUpdated)

    ctrl.updateMissing("01.03.2026", "10.03.2026", "all_active")

    service.update_missing_prices.assert_called_once_with(date(2026, 3, 1), date(2026, 3, 10), None, "all_active")
    assert updated
    assert container.event_bus.prices_updated.emit.call_args.args[0] == {2: Decimal("301")}
    assert service.analyze.call_count == 2  # güncelleme sonrası otomatik yeniden analiz


def test_price_data_update_selected_requires_selection(qapp):
    container, service = _price_container()
    ctrl = _price_ctrl(qapp, container)
    notes = _capture(ctrl.notification)

    ctrl.updateSelected(-1, "01.03.2026", "10.03.2026", "all_active")
    assert notes and notes[-1][0] is False

    service.update_stock_range.return_value = PriceDataUpdateResult(1, 0)
    ctrl.updateSelected(2, "01.03.2026", "10.03.2026", "all_active")
    service.update_stock_range.assert_called_once_with(2, date(2026, 3, 1), date(2026, 3, 10))


def test_price_data_update_from_latest_uses_last_trading_day(qapp):
    container, service = _price_container()
    service.update_from_latest_to_today.return_value = PriceDataUpdateResult(1, 0)
    container.trading_calendar.is_trading_day.side_effect = lambda d: d.weekday() < 5
    ctrl = _price_ctrl(qapp, container)

    ctrl.updateFromLatest("dashboard")

    target, scope = service.update_from_latest_to_today.call_args.args
    assert scope == "dashboard"
    assert target < date.today() and target.weekday() < 5


def test_price_data_delete_range(qapp):
    container, service = _price_container()
    service.delete_range.return_value = 12
    ctrl = _price_ctrl(qapp, container)
    notes = _capture(ctrl.notification)
    updated = _capture(ctrl.pricesUpdated)

    ctrl.deleteRange("01.03.2026", "10.03.2026", "dashboard")

    service.delete_range.assert_called_once_with(date(2026, 3, 1), date(2026, 3, 10), "dashboard")
    assert "12 fiyat kaydı silindi" in notes[-1][1]
    assert updated


def test_price_data_copy_report_to_clipboard(qapp):
    container, _ = _price_container()
    ctrl = _price_ctrl(qapp, container)
    notes = _capture(ctrl.notification)

    ctrl.copyReport()
    assert notes[-1][0] is False

    ctrl.analyze("01.03.2026", "10.03.2026", "all_active")
    ctrl.copyReport()
    text = QGuiApplication.clipboard().text()
    assert "Fiyat Verisi Sağlık Raporu" in text and "THYAO: 2 eksik" in text


def test_price_data_without_service_is_safe(qapp):
    ctrl = PriceDataController(container=None)
    notes = _capture(ctrl.notification)

    ctrl.analyze("01.03.2026", "10.03.2026", "all_active")

    assert ctrl.serviceAvailable is False
    assert notes and notes[-1][0] is False
    assert [o["value"] for o in ctrl.scopeOptions] == ["all_active", "dashboard"]


# ---------------------------------------------------------------------------
# StartupJobsController
# ---------------------------------------------------------------------------

def _startup_ctrl(qapp, tmp_path, container):
    settings = QSettings(str(tmp_path / "startup.ini"), QSettings.Format.IniFormat)
    ctrl = StartupJobsController(container=container, settings=settings, autostart=False)
    ctrl._executor = ImmediateExecutor()
    return ctrl, settings


def _startup_container(updated=5):
    container = MagicMock()
    container.trading_calendar.is_trading_day.return_value = True
    container.price_data_health_service.update_from_latest_to_today.return_value = PriceDataUpdateResult(
        scanned_stock_count=3, updated_count=updated, prices={1: Decimal("10")}
    )
    container.corporate_action_discovery_service.discover.return_value = SimpleNamespace(saved_count=2)
    container.market_data_sync_service.sync_daily_delta.return_value = SimpleNamespace(added_bars=7, errors=[])
    container.technical_analysis_service = None  # teknik tarama ayrı test edilir
    return container


def test_last_completed_trading_day_skips_closed_days():
    calendar = MagicMock()
    calendar.is_trading_day.side_effect = lambda d: d.weekday() < 5
    monday = date(2026, 3, 9)
    assert last_completed_trading_day(monday, calendar) == date(2026, 3, 6)
    assert last_completed_trading_day(monday, None) == monday - timedelta(days=1)


def test_startup_jobs_run_once_per_day_and_notify(qapp, tmp_path, monkeypatch):
    container = _startup_container()
    ctrl, settings = _startup_ctrl(qapp, tmp_path, container)
    monkeypatch.setattr(
        "src.ui_qml.controllers.startup_jobs_controller.market_now",
        lambda: datetime.combine(market_today(), time(19, 0)),
    )
    notes = _capture(ctrl.jobNotification)
    refreshed = _capture(ctrl.pricesUpdated)

    ctrl.runAll()

    target = last_completed_trading_day(market_today(), container.trading_calendar)
    # Portföy backfill (SQLite) + tüm BIST için DuckDB artımlı senkron (18:30 sonrası) çalıştı
    assert container.price_data_health_service.update_from_latest_to_today.call_count == 1
    container.market_data_sync_service.sync_daily_delta.assert_called_once_with()
    assert settings.value(AUTO_BACKFILL_SETTINGS_KEY, "", type=str) == target.isoformat()
    assert settings.value(AUTO_BIST_BACKFILL_SETTINGS_KEY, "", type=str) == target.isoformat()
    assert settings.value(AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY, "", type=str) == market_today().isoformat()
    assert container.event_bus.prices_updated.emit.called
    assert refreshed
    assert any("kurumsal aksiyon adayı" in n[1] for n in notes)
    assert any("BIST güncellemesi tamamlandı: 7" in n[1] for n in notes)

    ctrl.runAll()  # aynı gün tekrar çalışmaz
    assert container.price_data_health_service.update_from_latest_to_today.call_count == 1
    container.market_data_sync_service.sync_daily_delta.assert_called_once_with()
    container.corporate_action_discovery_service.discover.assert_called_once()


def test_startup_bist_backfill_skipped_before_market_close_time(qapp, tmp_path, monkeypatch):
    container = _startup_container()
    ctrl, settings = _startup_ctrl(qapp, tmp_path, container)
    monkeypatch.setattr(
        "src.ui_qml.controllers.startup_jobs_controller.datetime",
        SimpleNamespace(now=lambda: SimpleNamespace(time=lambda: __import__("datetime").time(12, 0))),
    )

    ctrl.runAll()

    assert container.price_data_health_service.update_from_latest_to_today.call_count == 1
    container.market_data_sync_service.sync_daily_delta.assert_not_called()
    assert settings.value(AUTO_BIST_BACKFILL_SETTINGS_KEY, "", type=str) == ""


def test_startup_job_error_does_not_mark_as_done(qapp, tmp_path, monkeypatch):
    container = _startup_container()
    container.price_data_health_service.update_from_latest_to_today.side_effect = RuntimeError("ağ yok")
    container.corporate_action_discovery_service.discover.side_effect = RuntimeError("kap yok")
    ctrl, settings = _startup_ctrl(qapp, tmp_path, container)
    monkeypatch.setattr(
        "src.ui_qml.controllers.startup_jobs_controller.datetime",
        SimpleNamespace(now=lambda: SimpleNamespace(time=lambda: __import__("datetime").time(10, 0))),
    )
    notes = _capture(ctrl.jobNotification)

    ctrl.runAll()

    assert settings.value(AUTO_BACKFILL_SETTINGS_KEY, "", type=str) == ""
    assert settings.value(AUTO_CORPORATE_ACTION_DISCOVERY_SETTINGS_KEY, "", type=str) == ""
    assert len(notes) == 2 and not any(n[0] for n in notes)


def test_startup_jobs_without_services_do_nothing(qapp, tmp_path):
    ctrl, _ = _startup_ctrl(qapp, tmp_path, None)
    notes = _capture(ctrl.jobNotification)

    ctrl.runAll()

    assert notes == []


# ---------------------------------------------------------------------------
# QML bileşenleri derleme / örnekleme
# ---------------------------------------------------------------------------

def _load_component(engine, relative_path):
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / relative_path)))
    if not component.isReady():
        pytest.fail(f"{relative_path} derlenemedi:\n" + "\n".join(e.toString() for e in component.errors()))
    return component


@pytest.mark.parametrize(
    "relative_path",
    [
        "components/ModernInput.qml",
        "components/CorporateActionDialog.qml",
        "components/CorporateActionCandidateEditDialog.qml",
        "components/SettingsCorporateActionsTab.qml",
        "components/SettingsPriceDataTab.qml",
    ],
)
def test_new_qml_components_compile_and_instantiate_without_warnings(qapp, relative_path):
    container, _ = _ca_container()
    price_container, _ = _price_container()
    ca_ctrl = CorporateActionController(container=container)
    price_ctrl = PriceDataController(container=price_container)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    context = engine.rootContext()
    context.setContextProperty("corporateActionController", ca_ctrl)
    context.setContextProperty("priceDataController", price_ctrl)

    item = _load_component(engine, relative_path).create()

    assert item is not None, f"{relative_path} örneklenemedi"
    assert warnings == [], f"{relative_path} uyarı üretti:\n" + "\n".join(warnings)


def test_corporate_action_dialog_open_computes_preview(qapp):
    container, _ = _ca_container()
    position = SimpleNamespace(total_quantity=1000, average_cost=Decimal("100"), total_cost=Decimal("100000"))
    container.portfolio_service.get_current_portfolio.return_value = SimpleNamespace(active_positions={7: position})
    ctrl = CorporateActionController(container=container)

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("corporateActionController", ctrl)
    component = _load_component(engine, "components/CorporateActionDialog.qml")
    item = component.create()

    from PySide6.QtCore import Q_ARG, QMetaObject

    QMetaObject.invokeMethod(item, "open", Q_ARG("QVariant", "THYAO"))
    assert item.property("isOpen") is True
    preview = item.property("preview")
    preview = preview.toVariant() if hasattr(preview, "toVariant") else preview
    assert preview["valid"] is True
    assert preview["newShares"] == 500
