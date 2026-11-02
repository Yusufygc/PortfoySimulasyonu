"""CashPoolController: Döviz Al/Sat, bakiyeler ve doğrulama (gerçek geçici veritabanı, Türkçe sayı girişi)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from PySide6.QtGui import QGuiApplication

from src.application.container import AppContainer
from src.ui_qml.controllers.cash_pool_controller import CashPoolController

D = Decimal


@pytest.fixture(scope="module")
def qapp():
    return QGuiApplication.instance() or QGuiApplication([])


@pytest.fixture
def parts(qapp, tmp_path, monkeypatch):
    monkeypatch.setenv("DB_SQLITE_PATH", str(tmp_path / "pool_ui.db"))
    container = AppContainer()
    container.cash_movement_service.add_deposit(D("10000"), movement_date=date(2026, 1, 1))
    controller = CashPoolController(container=container)
    messages, changes = [], []
    controller.notify.connect(lambda ok, text: messages.append((ok, text)))
    controller.balancesChanged.connect(lambda: changes.append(1))
    return container, controller, messages, changes


def test_initial_balances_are_formatted(parts):
    _, controller, _, _ = parts
    assert (controller.tryBalance, controller.usdBalance) == ("₺10.000,00", "$0,00")
    assert controller.conversions == []


def test_buy_usd_with_turkish_numbers_updates_balances_and_history(parts):
    _, controller, messages, changes = parts

    controller.buyUsd("100", "30,5", "05.01.2026", "10:00", "")

    assert messages == [(True, "100,00 USD alındı.")]
    assert (controller.tryBalance, controller.usdBalance) == ("₺6.950,00", "$100,00")   # 10.000 - 100 x 30,5
    assert changes and controller.conversions[0]["text"] == "05.01.2026 - Döviz alımı: 100,00 USD, kur 30,5000"
    assert (controller.tryBalanceValue, controller.usdBalanceValue) == (6950.0, 100.0)


def test_sell_usd_adds_try_back_and_fee_reduces_it(parts):
    _, controller, messages, _ = parts
    controller.buyUsd("100", "30", "05.01.2026", "10:00", "")

    controller.sellUsd("40", "31", "05.01.2026", "11:00", "2")  # +1.240 - 2 TL

    assert messages[-1] == (True, "40,00 USD satıldı.")
    assert (controller.tryBalance, controller.usdBalance) == ("₺8.238,00", "$60,00")


def test_invalid_inputs_and_insufficient_balances_are_reported_without_change(parts):
    _, controller, messages, changes = parts

    controller.buyUsd("abc", "30", "05.01.2026", "10:00", "")
    controller.buyUsd("100", "0", "05.01.2026", "10:00", "")
    controller.buyUsd("100", "30", "05.01.2026", "10:00", "-1")
    controller.buyUsd("1000", "30", "05.01.2026", "10:00", "")     # 30.000 TL > 10.000
    controller.sellUsd("1", "30", "05.01.2026", "10:00", "")       # USD yok

    assert [ok for ok, _ in messages] == [False] * 5
    assert "Yetersiz TL nakit" in messages[3][1] and "Yetersiz USD nakit" in messages[4][1]
    assert not changes and controller.usdBalance == "$0,00"


def test_delete_conversion_restores_try_and_blocks_when_usd_is_used(parts):
    container, controller, messages, _ = parts
    controller.buyUsd("100", "30", "05.01.2026", "10:00", "")
    first_id = controller.conversions[0]["id"]

    controller.deleteConversion(first_id)
    assert messages[-1] == (True, "Döviz işlemi silindi.") and controller.tryBalance == "₺10.000,00"

    controller.buyUsd("100", "30", "05.01.2026", "10:00", "")
    from src.domain.models.asset import Asset, AssetClass
    from src.domain.models.trade import TradeSide
    asset = container.asset_repo.add_asset(Asset(None, "BTC", "Bitcoin", AssetClass.CRYPTO, "USD", "BTC-USD"))
    from datetime import time
    container.asset_ledger_service.record_trade(asset.id, TradeSide.BUY, "1", "40", trade_date=date(2026, 1, 5),
                                               trade_time=time(12, 0), fx_rate_to_try="30")
    controller.reload()

    controller.deleteConversion(controller.conversions[0]["id"])

    assert messages[-1][0] is False and "silinemez" in messages[-1][1]
    assert controller.usdBalance == "$60,00"


def test_missing_service_and_rate_suggestion(qapp):
    controller = CashPoolController(container=None)
    messages = []
    controller.notify.connect(lambda ok, text: messages.append(ok))
    controller.buyUsd("1", "30", "", "", "")
    assert messages == [False] and controller.suggestRate() == ""
