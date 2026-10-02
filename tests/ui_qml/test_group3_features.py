"""
Grup 3 testleri: Golden Cross (Hisse Tarayıcı), risk profili anketi, karşılaştırma eklentileri
(özel tarih, para birimi, portföy+hisseleri, AI yorumu), Excel aralığı/dosya, işlem tarih-saat,
işlem etkisi ve yeni QML bileşenleri.
"""
from __future__ import annotations

from datetime import date, datetime, time as dt_time
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

from src.application.services.analysis.technical.technical_analysis_service import ScanResult
from src.application.services.market.price_data_health_service import PRICE_SCOPE_ALL_BIST, PriceDataUpdateResult
from src.application.services.planning.risk_profile_service import RiskProfileService
from src.domain.models.golden_cross_event import CrossType, GoldenCrossEvent
from src.ui_qml.controllers.comparison_controller import ComparisonController
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.golden_cross_controller import GoldenCrossController
from src.ui_qml.controllers.model_portfolio_controller import ModelPortfolioController
from src.ui_qml.controllers.risk_profile_controller import RiskProfileController
from src.ui_qml.controllers.startup_jobs_controller import (
    AUTO_TECHNICAL_SCAN_SETTINGS_KEY,
    StartupJobsController,
)
from src.ui_qml.controllers.stock_detail_controller import StockDetailController

QML_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"


class ImmediateExecutor:
    def submit(self, fn, *args, **kwargs):
        fn(*args, **kwargs)


def _capture(signal):
    received = []
    signal.connect(lambda *args: received.append(args))
    return received


# ---------------------------------------------------------------------------
# Golden Cross
# ---------------------------------------------------------------------------

def _event(ticker="THYAO.IS", kind=CrossType.GOLDEN, day=date(2026, 3, 2)):
    return GoldenCrossEvent(
        id=1, ticker=ticker, cross_date=day, cross_type=kind,
        short_ma=Decimal("101.5"), long_ma=Decimal("99.25"), close_price=Decimal("1234.5"),
    )


def _golden_ctrl(qapp, service=None, **extra):
    container = MagicMock()
    container.technical_analysis_service = service
    for key, value in extra.items():
        setattr(container, key, value)
    ctrl = GoldenCrossController(container=container)
    ctrl._executor = ImmediateExecutor()
    return ctrl, container


def test_golden_cross_refresh_lists_events_with_filters(qapp):
    service = MagicMock()
    service.get_recent_events.return_value = [_event(), _event("AKBNK.IS", CrossType.DEATH)]
    ctrl, _ = _golden_ctrl(qapp, service)

    ctrl.refresh(30, "GOLDEN")

    service.get_recent_events.assert_called_once_with(days=30, cross_type=CrossType.GOLDEN, limit=500)
    rows = ctrl.events
    assert [r["ticker"] for r in rows] == ["THYAO", "AKBNK"]
    assert rows[0]["isGolden"] is True and rows[0]["close"] == "1.234,50"
    assert rows[1]["typeLabel"] == "Death"
    assert "2 sinyal" in ctrl.status


def test_golden_cross_all_period_uses_long_lookback(qapp):
    service = MagicMock()
    service.get_recent_events.return_value = []
    ctrl, _ = _golden_ctrl(qapp, service)

    ctrl.refresh(0, "")

    kwargs = service.get_recent_events.call_args.kwargs
    assert kwargs["days"] > 365 * 10 and kwargs["cross_type"] is None


def test_golden_cross_scan_reports_and_requests_reload(qapp):
    service = MagicMock()
    service.scan_all.return_value = ScanResult(scanned_count=600, new_event_count=4, skipped_count=20)
    ctrl, _ = _golden_ctrl(qapp, service)
    notes, completed = _capture(ctrl.notification), _capture(ctrl.scanCompleted)

    ctrl.scanAll()

    assert completed
    assert notes[-1][0] is True and "4 yeni sinyal" in notes[-1][1]
    assert ctrl.isBusy is False


def test_golden_cross_complete_data_syncs_duckdb_market_history(qapp):
    from src.application.services.market_data.market_data_sync_service import MarketSyncResult

    sync = MagicMock()
    sync.sync_daily_delta.return_value = MarketSyncResult(True, 600, 1200, 1.0, "ok")
    ctrl, _ = _golden_ctrl(qapp, MagicMock(), market_data_sync_service=sync)
    updated = _capture(ctrl.pricesUpdated)

    ctrl.completeData()

    sync.sync_daily_delta.assert_called_once_with()
    assert updated


def test_golden_cross_complete_data_without_sync_service_is_reported(qapp):
    ctrl, _ = _golden_ctrl(qapp, MagicMock(), market_data_sync_service=None)
    notes = _capture(ctrl.notification)

    ctrl.completeData()

    assert notes and notes[-1][0] is False


def test_golden_cross_ticker_history_and_error_path(qapp):
    service = MagicMock()
    service.get_events_for_ticker.side_effect = lambda t: [_event()] if t == "THYAO" else []
    ctrl, _ = _golden_ctrl(qapp, service)

    ctrl.loadTickerEvents("thyao")
    assert ctrl.tickerName == "THYAO" and len(ctrl.tickerEvents) == 1

    service.scan_all.side_effect = RuntimeError("db kilitli")
    notes = _capture(ctrl.notification)
    ctrl.scanAll()
    assert notes[-1][0] is False and "db kilitli" in notes[-1][1]
    assert ctrl.isBusy is False


def test_golden_cross_without_service_is_safe(qapp):
    ctrl = GoldenCrossController(container=None)
    ctrl.refresh(30, "")
    ctrl.scanAll()
    assert ctrl.serviceAvailable is False and ctrl.events == []


# ---------------------------------------------------------------------------
# Açılışta otomatik teknik tarama
# ---------------------------------------------------------------------------

def _startup(qapp, tmp_path, scan_result=None):
    from PySide6.QtCore import QSettings

    container = MagicMock()
    container.price_data_health_service = None
    container.corporate_action_discovery_service = None
    container.technical_analysis_service.scan_all.return_value = scan_result or ScanResult(10, 3, 0)
    settings = QSettings(str(tmp_path / "s.ini"), QSettings.Format.IniFormat)
    ctrl = StartupJobsController(container=container, settings=settings, autostart=False)
    ctrl._executor = ImmediateExecutor()
    return ctrl, container, settings


def test_startup_technical_scan_runs_when_stale_and_notifies(qapp, tmp_path):
    ctrl, container, settings = _startup(qapp, tmp_path)
    notes = _capture(ctrl.jobNotification)

    ctrl.runAll()

    container.technical_analysis_service.scan_all.assert_called_once()
    assert settings.value(AUTO_TECHNICAL_SCAN_SETTINGS_KEY, "", type=str) != ""
    assert notes and "3 yeni sinyal" in notes[-1][1]


def test_startup_technical_scan_skipped_within_24_hours(qapp, tmp_path):
    ctrl, container, settings = _startup(qapp, tmp_path)
    settings.setValue(AUTO_TECHNICAL_SCAN_SETTINGS_KEY, datetime.now().isoformat())

    ctrl.runAll()

    container.technical_analysis_service.scan_all.assert_not_called()


def test_startup_technical_scan_runs_with_corrupt_marker(qapp, tmp_path):
    ctrl, container, settings = _startup(qapp, tmp_path)
    settings.setValue(AUTO_TECHNICAL_SCAN_SETTINGS_KEY, "bozuk-tarih")

    ctrl.runAll()

    container.technical_analysis_service.scan_all.assert_called_once()


# ---------------------------------------------------------------------------
# Risk profili anketi
# ---------------------------------------------------------------------------

class _MemoryRiskRepo:
    def __init__(self):
        self.saved = None

    def get_latest_profile(self):
        return self.saved

    def save_profile(self, profile):
        self.saved = profile
        return profile


def _risk_ctrl(qapp):
    repo = _MemoryRiskRepo()
    container = SimpleNamespace(risk_profile_service=RiskProfileService(repo))
    return RiskProfileController(container=container), repo


def _first_option_answers(ctrl):
    return {q["id"]: q["options"][0]["value"] for s in ctrl.sections for q in s["questions"]}


def test_risk_questionnaire_sections_are_exposed(qapp):
    ctrl, _ = _risk_ctrl(qapp)
    assert len(ctrl.sections) >= 2
    first_question = ctrl.sections[0]["questions"][0]
    assert {"id", "title", "dimension", "options"} <= set(first_question)
    assert ctrl.profile["exists"] is False


def test_risk_calculate_saves_profile_and_emits_signals(qapp):
    ctrl, repo = _risk_ctrl(qapp)
    saved, notes = _capture(ctrl.profileSaved), _capture(ctrl.notification)

    assert ctrl.calculate(_first_option_answers(ctrl)) is True

    assert repo.saved is not None
    profile = ctrl.profile
    assert profile["exists"] is True and 0 <= profile["score"] <= 100
    assert profile["labelText"] and profile["dimensions"] and profile["allocation"]
    assert saved and notes[-1][0] is True and "/100" in notes[-1][1]
    assert ctrl.isBusy is False

    reloaded = RiskProfileController(container=SimpleNamespace(risk_profile_service=RiskProfileService(repo)))
    assert reloaded.profile["exists"] is True and reloaded.profile["answers"]


def test_risk_calculate_requires_all_answers(qapp):
    ctrl, repo = _risk_ctrl(qapp)
    answers = _first_option_answers(ctrl)
    answers.pop(next(iter(answers)))
    notes = _capture(ctrl.notification)

    assert ctrl.calculate(answers) is False

    assert repo.saved is None and notes[-1][0] is False


def test_risk_controller_without_service_is_safe(qapp):
    ctrl = RiskProfileController(container=None)
    notes = _capture(ctrl.notification)
    assert ctrl.calculate({"a": "b"}) is False
    assert ctrl.serviceAvailable is False and ctrl.sections == [] and notes[-1][0] is False


def test_optimization_reload_risk_profile_follows_saved_profile(qapp):
    from src.domain.models.risk_profile import RiskLabel
    from src.ui_qml.controllers.optimization_controller import OptimizationController

    container = MagicMock()
    container.risk_profile_service.get_current_profile.return_value = SimpleNamespace(risk_label=RiskLabel.AGRESIF)
    ctrl = OptimizationController(container=container)

    ctrl.reloadRiskProfile()

    assert ctrl.selectedRiskProfile == RiskLabel.AGRESIF
    assert ctrl.maxSingleWeight == 35.0


# ---------------------------------------------------------------------------
# Karşılaştırma: özel tarih, para birimi, portföy + hisseleri, AI yorumu
# ---------------------------------------------------------------------------

def _comparison(qapp):
    container = MagicMock()
    container.analysis_service.get_portfolio_options.return_value = [
        SimpleNamespace(code="dashboard", label="Ana Portföy", kind="PORTFÖY")
    ]
    container.analysis_service.get_benchmark_definitions.return_value = [
        SimpleNamespace(code="bist100", label="BIST 100", kind="ENDEKS")
    ]
    ctrl = ComparisonController(container=container)
    ctrl._executor = ImmediateExecutor()
    ctrl._executor_ai = ImmediateExecutor()
    return ctrl, container


def test_comparison_asset_options_include_portfolio_holdings(qapp):
    ctrl, _ = _comparison(qapp)

    ctrl.loadAssetOptions()

    codes = [o["code"] for o in ctrl.assetOptions]
    assert "dashboard" in codes and "holdings:dashboard" in codes and "bist100" in codes


def test_comparison_custom_range_validation_and_resolution(qapp):
    ctrl, _ = _comparison(qapp)
    ctrl._executor = MagicMock()  # runComparison arka planda çalışmasın
    results = _capture(ctrl.operationResult)

    assert ctrl.setCustomRange("abc", "01.03.2026") is False
    assert ctrl.setCustomRange("01.03.2026", "01.02.2026") is False
    assert [r[0] for r in results] == [False, False]

    assert ctrl.setCustomRange("01.01.2026", "01.03.2026") is True
    assert ctrl.periodLabel == "ÖZEL"
    assert ctrl._resolve_range() == (date(2026, 1, 1), date(2026, 3, 1))
    assert ctrl.customStart == "01.01.2026"


def test_comparison_custom_range_clamps_future_end_to_today(qapp):
    ctrl, _ = _comparison(qapp)
    ctrl._executor = MagicMock()

    ctrl.setCustomRange("01.01.2026", "31.12.2999")

    assert ctrl._resolve_range()[1] == date.today()


def test_comparison_currency_mode_triggers_rerun(qapp):
    ctrl, _ = _comparison(qapp)
    ctrl._executor = MagicMock()

    ctrl.setCurrencyMode("usd")
    ctrl.setCurrencyMode("geçersiz")

    assert ctrl.currencyMode == "USD"
    ctrl._executor.submit.assert_called_once()
    assert ctrl._executor.submit.call_args.args[-1] == "USD"


def test_comparison_worker_expands_holdings_and_passes_currency(qapp):
    ctrl, container = _comparison(qapp)
    container.analysis_service.get_stock_map_for_source.return_value = {11: "THYAO", 12: "AKBNK"}
    container.analysis_service.get_comparison_view.return_value = SimpleNamespace()
    empty = _capture(ctrl._calcEmpty)

    with patch(
        "src.ui_qml.controllers.comparison_controller.ComparisonSeriesBuilder.build_global_series",
        return_value=({}, {}),
    ) as build:
        ctrl._worker_calculate(["holdings:dashboard", "bist100", "55"], date(2026, 1, 1), date(2026, 3, 1), "USD")

    state = container.analysis_service.get_comparison_view.call_args.args[0]
    assert state.selected_stock_ids == [11, 12, 55]
    assert state.comparison_portfolio_sources == ["dashboard"]
    assert state.selected_benchmarks == ["bist100"]
    assert state.currency_mode == "USD"
    assert build.call_args.args[1] == [11, 12, 55]
    assert empty


def test_comparison_ai_comment_flow(qapp):
    ctrl, container = _comparison(qapp)
    container.ai_chat_service.generate.return_value = "**Özet** Ana Portföy öne çıktı."
    ctrl._metrics_list = [{"label": "Ana Portföy", "totalReturn": 12.5, "volatility": 20.1}]
    ctrl._last_range = (date(2026, 1, 1), date(2026, 3, 1))

    ctrl.generateAiComment()

    prompt = container.ai_chat_service.generate.call_args.args[0][0].content
    assert "01.01.2026" in prompt and "Ana Portföy" in prompt and "%12.5" in prompt
    assert "Özet" in ctrl.aiComment and ctrl.aiBusy is False
    ctrl.clearAiComment()
    assert ctrl.aiComment == ""


def test_comparison_ai_comment_errors_and_empty_data(qapp):
    ctrl, container = _comparison(qapp)
    results = _capture(ctrl.operationResult)

    ctrl.generateAiComment()  # metrik yok
    assert results[-1][0] is False

    ctrl._metrics_list = [{"label": "X", "totalReturn": 1.0, "volatility": 2.0}]
    container.ai_chat_service.generate.side_effect = RuntimeError("anahtar yok")
    ctrl.generateAiComment()
    assert results[-1][0] is False and "anahtar yok" in results[-1][1]
    assert ctrl.aiBusy is False


def test_gemini_chat_provider_reads_key_lazily():
    from src.infrastructure.ai.gemini_chat_provider import GeminiChatProvider

    holder = {"key": None}
    provider = GeminiChatProvider(api_key=lambda: holder["key"])
    with pytest.raises(RuntimeError, match="anahtar"):
        provider.generate("sistem", [("user", "merhaba")])
    holder["key"] = "yeni-anahtar"
    assert provider._api_key == "yeni-anahtar"
    assert GeminiChatProvider(api_key="sabit")._api_key == "sabit"


# ---------------------------------------------------------------------------
# Hızlı işlem: tarih / saat / hisse arama
# ---------------------------------------------------------------------------

def _dashboard(qapp):
    container = MagicMock()
    container.portfolio_service.get_current_portfolio.return_value = SimpleNamespace(active_positions={})
    container.portfolio_service.get_cash_balance.return_value = Decimal("100000")
    container.portfolio_service.get_first_trade_date.return_value = date(2025, 1, 2)
    stock = SimpleNamespace(id=7, ticker="THYAO.IS", name="Türk Hava Yolları")
    container.stock_lookup_service.find_stock.side_effect = lambda t: stock if t == "THYAO" else None
    container.current_price_resolver.price_map.return_value = {7: Decimal("301.5")}
    return DashboardController(container=container), container


def test_dashboard_lookup_ticker(qapp):
    ctrl, _ = _dashboard(qapp)

    found = ctrl.lookupTicker("thyao")
    assert found["found"] is True and found["name"] == "Türk Hava Yolları" and found["price"] == 301.5
    assert ctrl.lookupTicker("YOKTUR")["found"] is False
    assert ctrl.lookupTicker("")["found"] is False


def test_dashboard_submit_trade_at_uses_given_date_and_time(qapp):
    ctrl, container = _dashboard(qapp)
    results = _capture(ctrl.tradeExecuted)

    ctrl.submitTradeAt("THYAO", "BUY", 10, 250.0, "not", "05.01.2026", "11:30")

    request = container.trade_entry_service.submit_trade.call_args.args[0]
    assert request.trade_date == date(2026, 1, 5) and request.trade_time == dt_time(11, 30)
    assert request.quantity == 10 and results[-1][0] is True


@pytest.mark.parametrize(
    "date_text, time_text, expected",
    [
        ("32.13.2026", "10:00", "Tarih biçimi"),
        ("01.01.2999", "10:00", "Gelecek tarihli"),
        ("05.01.2026", "25:99", "Saat biçimi"),
    ],
)
def test_dashboard_submit_trade_at_validates_input(qapp, date_text, time_text, expected):
    ctrl, container = _dashboard(qapp)
    results = _capture(ctrl.tradeExecuted)

    ctrl.submitTradeAt("THYAO", "BUY", 10, 250.0, "", date_text, time_text)

    assert results[-1][0] is False and expected in results[-1][1]
    container.trade_entry_service.submit_trade.assert_not_called()


def test_dashboard_submit_trade_keeps_default_now(qapp):
    ctrl, container = _dashboard(qapp)

    ctrl.submitTrade("THYAO", "BUY", 5, 100.0, "")

    request = container.trade_entry_service.submit_trade.call_args.args[0]
    assert request.trade_date == date.today()


# ---------------------------------------------------------------------------
# Excel: aralık + dosya yolu
# ---------------------------------------------------------------------------

def test_dashboard_excel_file_export_uses_range_and_path(qapp, tmp_path):
    ctrl, container = _dashboard(qapp)
    ctrl._executor = ImmediateExecutor()
    results = _capture(ctrl.excelExported)
    target = tmp_path / "rapor"

    ctrl.exportToExcelFile("01.02.2026", "01.03.2026", str(target))

    kwargs = container.excel_export_service.export_history.call_args.kwargs
    assert kwargs["start_date"] == date(2026, 2, 1) and kwargs["end_date"] == date(2026, 3, 1)
    assert Path(kwargs["file_path"]) == target.with_suffix(".xlsx")
    assert results[-1][0] is True


def test_dashboard_excel_file_export_validates_dates(qapp):
    ctrl, container = _dashboard(qapp)
    ctrl._executor = ImmediateExecutor()
    results = _capture(ctrl.excelExported)

    ctrl.exportToExcelFile("yanlış", "", "")
    ctrl.exportToExcelFile("01.03.2026", "01.02.2026", "")

    assert [r[0] for r in results] == [False, False]
    container.excel_export_service.export_history.assert_not_called()
    assert ctrl.firstTradeDateText() == "02.01.2025"


def test_model_portfolio_history_export(qapp, tmp_path):
    container = MagicMock()
    ctrl = ModelPortfolioController(container=container)
    ctrl._executor = ImmediateExecutor()
    ctrl._current_portfolio_id = 3
    ctrl._service = MagicMock()
    ctrl._service.get_first_trade_date.return_value = date(2026, 1, 10)
    results = _capture(ctrl.operationResult)

    ctrl.exportHistoryToFile("", "01.03.2026", str(tmp_path / "model.xlsx"))

    kwargs = container.model_portfolio_excel_export_service.export_model_portfolio_history.call_args.kwargs
    assert kwargs["portfolio_id"] == 3
    assert kwargs["start_date"] == date(2026, 1, 10) and kwargs["end_date"] == date(2026, 3, 1)
    assert results[-1][0] is True
    assert ctrl.firstTradeDateText() == "10.01.2026"

    ctrl.exportHistoryToFile("kötü", "", "")
    assert results[-1][0] is False


# ---------------------------------------------------------------------------
# Hisse detay: işlem etkisi tahmini
# ---------------------------------------------------------------------------

def test_stock_detail_trade_impact(qapp):
    ctrl = StockDetailController(container=MagicMock())
    ctrl._quantity, ctrl._avg_cost, ctrl._cash = 100, 10.0, 5000.0

    buy = ctrl.tradeImpact("BUY", 100, 20.0)
    assert buy["valid"] is True
    assert buy["newQty"] == "200" and buy["newAvg"] == "₺15,00" and buy["cashAfter"] == "₺3.000,00"

    too_much = ctrl.tradeImpact("BUY", 1000, 20.0)
    assert too_much["valid"] is False and too_much["message"] == "Yetersiz nakit"

    sell_all = ctrl.tradeImpact("SELL", 100, 20.0)
    assert sell_all["valid"] is True and sell_all["newQty"] == "0" and sell_all["newAvg"] == "-"

    oversell = ctrl.tradeImpact("SELL", 150, 20.0)
    assert oversell["valid"] is False and oversell["message"] == "Yetersiz lot"


# ---------------------------------------------------------------------------
# QML bileşenleri
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "relative_path",
    [
        "components/ModernComboBox.qml",
        "components/GoldenCrossTab.qml",
        "components/ScreenerStrategiesTab.qml",
        "components/RiskQuestionnaireDialog.qml",
        "components/ComparisonAiDialog.qml",
        "components/ExcelExportDialog.qml",
        "components/QuickTradeModal.qml",
    ],
)
def test_group3_qml_components_compile_without_warnings(qapp, relative_path):
    golden_service = MagicMock()
    golden_service.get_recent_events.return_value = [_event()]
    golden, _ = _golden_ctrl(qapp, golden_service)
    risk, _ = _risk_ctrl(qapp)
    dash, _ = _dashboard(qapp)
    comparison, _ = _comparison(qapp)
    from src.ui_qml.controllers.screener_controller import ScreenerController

    screener = ScreenerController(container=SimpleNamespace(screener_service=None))

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(QML_DIR))
    warnings = []
    engine.warnings.connect(lambda items: warnings.extend(w.toString() for w in items))
    context = engine.rootContext()
    for name, controller in (
        ("goldenCrossController", golden), ("riskProfileController", risk),
        ("dashboardController", dash), ("comparisonController", comparison),
        ("screenerController", screener),
    ):
        context.setContextProperty(name, controller)

    component = QQmlComponent(engine, QUrl.fromLocalFile(str(QML_DIR / relative_path)))
    if not component.isReady():
        pytest.fail(f"{relative_path} derlenemedi:\n" + "\n".join(e.toString() for e in component.errors()))
    item = component.create()

    assert item is not None
    assert warnings == [], f"{relative_path} uyarı üretti:\n" + "\n".join(warnings)


def test_dashboard_excel_export_append_mode_is_forwarded(qapp, tmp_path):
    from src.application.services.reporting.daily_history_models import ExportMode

    ctrl, container = _dashboard(qapp)
    ctrl._executor = ImmediateExecutor()

    ctrl.exportToExcelFile("01.02.2026", "01.03.2026", str(tmp_path / "var.xlsx"), True)
    assert container.excel_export_service.export_history.call_args.kwargs["mode"] == ExportMode.APPEND

    ctrl.exportToExcelFile("01.02.2026", "01.03.2026", str(tmp_path / "var.xlsx"))
    assert container.excel_export_service.export_history.call_args.kwargs["mode"] == ExportMode.OVERWRITE


def test_model_portfolio_export_append_mode_is_forwarded(qapp, tmp_path):
    from src.application.services.reporting.daily_history_models import ExportMode

    container = MagicMock()
    ctrl = ModelPortfolioController(container=container)
    ctrl._executor = ImmediateExecutor()
    ctrl._current_portfolio_id = 3
    ctrl._service = MagicMock()
    ctrl._service.get_first_trade_date.return_value = date(2026, 1, 10)
    export = container.model_portfolio_excel_export_service.export_model_portfolio_history

    ctrl.exportHistoryToFile("", "01.03.2026", str(tmp_path / "m.xlsx"), True)
    assert export.call_args.kwargs["mode"] == ExportMode.APPEND

    ctrl.exportHistoryToFile("", "01.03.2026", str(tmp_path / "m.xlsx"))
    assert export.call_args.kwargs["mode"] == ExportMode.OVERWRITE


def test_excel_dialog_append_option_resets_on_open(qapp):
    from PySide6.QtCore import Q_ARG, QMetaObject, QUrl
    from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent

    qml_dir = Path(__file__).resolve().parent.parent.parent / "src" / "ui_qml" / "qml"
    engine = QQmlApplicationEngine()
    engine.addImportPath(str(qml_dir))
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_dir / "components/ExcelExportDialog.qml")))
    if not component.isReady():
        pytest.fail("; ".join(e.toString() for e in component.errors()))
    item = component.create()

    item.setProperty("appendMode", True)
    assert item.property("appendMode") is True
    QMetaObject.invokeMethod(item, "open", Q_ARG("QVariant", "01.01.2026"), Q_ARG("QVariant", "r.xlsx"))

    assert item.property("isOpen") is True and item.property("appendMode") is False
