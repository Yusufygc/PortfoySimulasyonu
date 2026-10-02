"""
Kırık/yanlış bağlı QML akışları için regresyon testleri:
- API anahtarı kalıcılığı (frozen ayarlar + .env)
- Hisse detay işleminin TradeEntryService üzerinden geçmesi
- Shell seans durumunun seans servisinden okunması
- Piyasa senkronu sonrası dataSynced sinyali
- Gerçek DB'de boş portföyün demo veriyle doldurulmaması
"""
from __future__ import annotations

import datetime as dt
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from config.settings_loader import AISettings, MarketSettings, persist_api_keys
from src.application.services.market_data.market_data_sync_service import MarketSyncResult
from src.domain.models.trade import TradeSide
from src.ui_qml.controllers.dashboard_controller import DashboardController
from src.ui_qml.controllers.market_sync_controller import MarketSyncController
from src.ui_qml.controllers.shell_controller import ShellController
from src.ui_qml.controllers.stock_detail_controller import StockDetailController


def test_persist_api_keys_writes_env_and_updates_frozen_settings(tmp_path):
    settings = MagicMock()
    settings.ai = AISettings(gemini_api_key=None, core_api_url="http://localhost:8000")
    settings.market = MarketSettings(evds_api_key="old", tcmb_deposit_rate_fallback=Decimal("45"))

    env_path = persist_api_keys(settings, gemini_key=" abc ", evds_key=None)

    assert settings.ai.gemini_api_key == "abc"
    assert settings.market.evds_api_key == "old"  # None verilen anahtara dokunulmaz
    assert env_path == tmp_path / ".env"
    assert "GEMINI_API_KEY=abc" in env_path.read_text(encoding="utf-8")
    assert "EVDS_API_KEY" not in env_path.read_text(encoding="utf-8")


def test_persist_api_keys_empty_value_clears_runtime_key(tmp_path):
    settings = MagicMock()
    settings.ai = AISettings(gemini_api_key="x", core_api_url="http://localhost:8000")
    settings.market = MarketSettings(evds_api_key=None, tcmb_deposit_rate_fallback=Decimal("45"))

    persist_api_keys(settings, gemini_key="")

    assert settings.ai.gemini_api_key is None


def _stock_detail_with_service(qapp, trade_entry_service):
    container = MagicMock()
    container.trade_entry_service = trade_entry_service
    ctrl = StockDetailController(container=container)
    ctrl._ticker = "THYAO"
    ctrl._raw_ticker = "THYAO.IS"
    ctrl._company_name = "Türk Hava Yolları"
    ctrl._context_type = "main"
    results = []
    ctrl._asyncTradeResult.connect(lambda ok, msg: results.append((ok, msg)))
    return ctrl, results


def test_stock_detail_trade_goes_through_trade_entry_service(qapp):
    service = MagicMock()
    ctrl, results = _stock_detail_with_service(qapp, service)

    ctrl._execute_trade_worker("BUY", 10, 250.0, "")

    service.submit_trade.assert_called_once()
    req = service.submit_trade.call_args.args[0]
    assert req.ticker == "THYAO.IS"
    assert req.side == TradeSide.BUY
    assert req.quantity == 10
    assert req.price == Decimal("250.0")
    assert req.trade_date == dt.date.today()
    assert results and results[0][0] is True


def test_stock_detail_trade_validation_error_is_reported(qapp):
    service = MagicMock()
    service.submit_trade.side_effect = ValueError("Yeterli sermayeniz yoktu")
    ctrl, results = _stock_detail_with_service(qapp, service)

    ctrl._execute_trade_worker("BUY", 10, 250.0, "")

    assert results and results[0][0] is False
    assert "Yeterli sermayeniz yoktu" in results[0][1]


def test_stock_detail_backdated_trade_uses_in_session_time(qapp):
    service = MagicMock()
    ctrl, _ = _stock_detail_with_service(qapp, service)

    ctrl._execute_trade_worker("SELL", 5, 260.0, "2026-01-05")

    req = service.submit_trade.call_args.args[0]
    assert req.trade_date == dt.date(2026, 1, 5)
    assert req.trade_time == dt.time(12, 0)
    assert req.side == TradeSide.SELL


@pytest.mark.parametrize("service_open", [True, False])
def test_shell_session_state_comes_from_session_service(qapp, service_open):
    container = MagicMock()
    container.bist_market_session_service.status_for.return_value = MagicMock(is_open=service_open)

    shell = ShellController(container=container)

    assert shell.isBistOpen is service_open
    assert "Açık" in shell.sessionText if service_open else "Kapalı" in shell.sessionText


def test_shell_falls_back_when_session_service_fails(qapp):
    container = MagicMock()
    container.bist_market_session_service.status_for.side_effect = RuntimeError("takvim yok")

    shell = ShellController(container=container)

    assert isinstance(shell.isBistOpen, bool)


def test_market_sync_emits_data_synced_when_bars_added(qapp):
    svc = MagicMock()
    ctrl = MarketSyncController(sync_service=svc)
    emitted = []
    ctrl.dataSynced.connect(lambda: emitted.append(True))

    ctrl._on_sync_finished(MarketSyncResult(True, 3, 12, 0.1, "ok"))
    ctrl._on_sync_finished(MarketSyncResult(True, 0, 0, 0.1, "güncel"))

    assert emitted == [True]


def test_market_sync_builds_service_from_container_paths():
    container = MagicMock()
    container.db_config.db_path = "veri/portfolio.db"
    calendar = object()
    container.trading_calendar = calendar

    svc = MarketSyncController._build_sync_service(container)

    assert svc._sqlite_path == "veri/portfolio.db"
    assert svc._duckdb_path.replace("\\", "/") == "veri/market_history.duckdb"
    assert svc._trading_calendar is calendar


def test_dashboard_with_real_container_and_empty_portfolio_shows_no_demo_positions(qapp):
    container = MagicMock()
    container.portfolio_service.get_cash_balance.return_value = Decimal("0")
    container.portfolio_service.get_current_portfolio.return_value = MagicMock(active_positions={})

    ctrl = DashboardController(container=container)

    assert ctrl.holdingsCount == 0
    assert ctrl.positionsModel.rowCount() == 0
