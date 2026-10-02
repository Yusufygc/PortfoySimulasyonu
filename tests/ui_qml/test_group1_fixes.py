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
from src.ui_qml.controllers.stock_detail_controller import StockDetailController, parse_trade_moment


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

    ctrl._execute_trade_worker("BUY", 10, 250.0, dt.date.today(), dt.time(9, 30))

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

    ctrl._execute_trade_worker("BUY", 10, 250.0, dt.date.today(), dt.time(9, 30))

    assert results and results[0][0] is False
    assert "Yeterli sermayeniz yoktu" in results[0][1]


def test_stock_detail_backdated_trade_uses_in_session_time(qapp):
    service = MagicMock()
    ctrl, _ = _stock_detail_with_service(qapp, service)

    ctrl._execute_trade_worker("SELL", 5, 260.0, dt.date(2026, 1, 5), dt.time(12, 0))

    req = service.submit_trade.call_args.args[0]
    assert req.trade_date == dt.date(2026, 1, 5)
    assert req.trade_time == dt.time(12, 0)
    assert req.side == TradeSide.SELL


def test_parse_trade_moment_defaults_and_validation():
    today = dt.date.today()

    assert parse_trade_moment("", "")[0] == today
    assert parse_trade_moment("2026-01-05", "") == (dt.date(2026, 1, 5), dt.time(12, 0))
    assert parse_trade_moment("2026-01-05", "14:30") == (dt.date(2026, 1, 5), dt.time(14, 30))
    for date_text, time_text, message in [
        ("05.01.2026", "", "Tarih biçimi"),
        ((today + dt.timedelta(days=1)).isoformat(), "", "Gelecek tarihli"),
        ("2026-01-05", "25:99", "Saat biçimi"),
    ]:
        with pytest.raises(ValueError, match=message):
            parse_trade_moment(date_text, time_text)


def test_parse_trade_moment_rejects_future_time_today():
    future = (dt.datetime.now() + dt.timedelta(minutes=30)).time()
    if future < dt.datetime.now().time():  # gece yarısını aşan çalıştırma
        pytest.skip("gün sınırı")

    with pytest.raises(ValueError, match="Gelecek saatli"):
        parse_trade_moment("", future.strftime("%H:%M"))


def test_submit_trade_reports_invalid_date_without_starting_worker(qapp):
    ctrl, _ = _stock_detail_with_service(qapp, MagicMock())
    emitted = []
    ctrl.tradeExecuted.connect(lambda ok, msg: emitted.append((ok, msg)))

    ctrl.submitTrade("BUY", 10, 250.0, "yarin", "")

    assert emitted == [(False, "Tarih biçimi geçersiz. Örnek: 2026-10-03")] and ctrl.isLoading is False


def test_submit_trade_passes_chosen_time_to_trade_entry_service(qapp):
    service = MagicMock()
    ctrl, _ = _stock_detail_with_service(qapp, service)

    ctrl._execute_trade_worker("BUY", 1, 10.0, *parse_trade_moment("2026-01-05", "10:15"))

    req = service.submit_trade.call_args.args[0]
    assert (req.trade_date, req.trade_time) == (dt.date(2026, 1, 5), dt.time(10, 15))


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


def test_market_sync_uses_container_sync_service_when_available():
    from src.application.services.market_data.market_data_sync_service import MarketDataSyncService

    container_service = MarketDataSyncService(duckdb_path="x.duckdb")
    container = MagicMock()
    container.market_data_sync_service = container_service

    assert MarketSyncController._build_sync_service(container) is container_service
    # container yoksa veya servis sahte ise güvenli varsayılan kurulur
    assert isinstance(MarketSyncController._build_sync_service(None), MarketDataSyncService)
    assert isinstance(MarketSyncController._build_sync_service(MagicMock()), MarketDataSyncService)


def test_dashboard_with_real_container_and_empty_portfolio_shows_no_demo_positions(qapp):
    container = MagicMock()
    container.portfolio_service.get_cash_balance.return_value = Decimal("0")
    container.portfolio_service.get_current_portfolio.return_value = MagicMock(active_positions={})

    ctrl = DashboardController(container=container)

    assert ctrl.holdingsCount == 0
    assert ctrl.positionsModel.rowCount() == 0
