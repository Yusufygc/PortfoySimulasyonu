"""Nakit temettü: bakiyeye girer, getiri (TWR) olarak sayılır, dış sermaye akışı değildir; ekleme/silme doğrulamaları."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from src.application.services.analysis.portfolio_series_builder import (
    PortfolioSeriesBuilder,
    PortfolioSeriesRequest,
)
from src.application.services.portfolio.cash_movement_service import CashMovementService
from src.application.services.portfolio.portfolio_service import PortfolioService
from src.domain.models.cash_movement import CashMovement, CashMovementType
from src.domain.models.portfolio import Portfolio
from src.domain.models.trade import Trade

D1, D2, D3 = date(2026, 3, 2), date(2026, 3, 3), date(2026, 3, 4)


class FakeCashMovementRepo:
    def __init__(self, movements=None):
        self.movements = list(movements or [])
        self._next_id = 1

    def insert_movement(self, movement):
        saved = CashMovement(
            id=self._next_id, movement_date=movement.movement_date, movement_time=movement.movement_time,
            type=movement.type, amount=movement.amount, notes=movement.notes, stock_id=movement.stock_id,
        )
        self._next_id += 1
        self.movements.append(saved)
        return saved

    def get_all_movements(self):
        return list(self.movements)

    def get_movements_until(self, movement_date, movement_time=None):
        return [m for m in self.movements if m.movement_date <= movement_date]

    def get_movements_by_type(self, movement_type, stock_id=None):
        return [m for m in self.movements if m.type == movement_type and (stock_id is None or m.stock_id == stock_id)]

    def get_movement(self, movement_id):
        return next((m for m in self.movements if m.id == movement_id), None)

    def delete_movement(self, movement_id):
        self.movements = [m for m in self.movements if m.id != movement_id]


def _deposit(amount, day, movement_id):
    return CashMovement(id=movement_id, movement_date=day, movement_time=None, type=CashMovementType.DEPOSIT, amount=Decimal(amount))


def _dividend(amount, day, movement_id, stock_id=1):
    return CashMovement(
        id=movement_id, movement_date=day, movement_time=None, type=CashMovementType.DIVIDEND,
        amount=Decimal(amount), stock_id=stock_id,
    )


def _services(trades, movements):
    portfolio_repo = MagicMock()
    portfolio_repo.get_all_trades.return_value = trades
    cash_repo = FakeCashMovementRepo(movements)
    portfolio_service = PortfolioService(portfolio_repo, MagicMock(), cash_repo)
    return CashMovementService(cash_repo, portfolio_service), portfolio_service, cash_repo


BUY_10_AT_100 = Trade.create_buy(stock_id=1, trade_date=D1, quantity=10, price=Decimal("100"))


class TestDomain:
    def test_dividend_requires_a_stock(self):
        with pytest.raises(ValueError):
            CashMovement(id=None, movement_date=D1, movement_time=None, type=CashMovementType.DIVIDEND, amount=Decimal("5"))

    def test_dividend_amount_must_be_positive(self):
        with pytest.raises(ValueError):
            CashMovement.create_dividend(stock_id=1, amount=Decimal("0"), movement_date=D1)

    def test_dividend_adds_cash_but_is_not_external_flow(self):
        assert CashMovementType.DIVIDEND.adds_cash is True
        assert CashMovementType.DIVIDEND.is_external_flow is False
        assert CashMovementType.DEPOSIT.is_external_flow is True
        assert CashMovementType.WITHDRAW.adds_cash is False


class TestCashBalance:
    def test_dividend_increases_cash_balance(self):
        service, portfolio_service, _ = _services([BUY_10_AT_100], [_deposit("1000", D1, 1), _dividend("50", D3, 2)])

        assert portfolio_service.get_cash_balance() == Decimal("50")
        assert service.get_cash_balance() == Decimal("50")

    def test_dividend_cash_can_fund_a_later_buy(self):
        service, portfolio_service, _ = _services([BUY_10_AT_100], [_deposit("1000", D1, 1), _dividend("50", D2, 2)])

        portfolio_service.validate_trade(Trade.create_buy(stock_id=1, trade_date=D3, quantity=1, price=Decimal("50")))


class TestAddDividend:
    def test_adds_dividend_for_held_stock(self):
        service, _, repo = _services([BUY_10_AT_100], [_deposit("1000", D1, 1)])

        saved = service.add_dividend(1, Decimal("25.50"), D2, notes="Temettü")

        assert saved.type == CashMovementType.DIVIDEND and saved.stock_id == 1
        assert service.get_total_dividends() == Decimal("25.50")
        assert service.get_total_dividends(stock_id=2) == Decimal("0")
        assert [m.id for m in service.get_dividends(1)] == [saved.id]

    def test_rejects_dividend_before_position_existed(self):
        service, _, _ = _services([BUY_10_AT_100], [_deposit("1000", D1, 1)])

        with pytest.raises(ValueError, match="pozisyonu yoktu"):
            service.add_dividend(1, Decimal("5"), date(2026, 3, 1))

    def test_rejects_dividend_for_unheld_stock(self):
        service, _, _ = _services([BUY_10_AT_100], [_deposit("1000", D1, 1)])

        with pytest.raises(ValueError, match="pozisyonu yoktu"):
            service.add_dividend(99, Decimal("5"), D2)

    def test_rejects_future_date(self):
        service, _, _ = _services([BUY_10_AT_100], [_deposit("1000", D1, 1)])

        with pytest.raises(ValueError, match="gelecekte"):
            service.add_dividend(1, Decimal("5"), date.today().replace(year=date.today().year + 1))


class TestDeleteDividend:
    def test_deletes_unneeded_dividend(self):
        service, _, repo = _services([BUY_10_AT_100], [_deposit("1000", D1, 1), _dividend("50", D2, 2)])

        service.delete_dividend(2)

        assert service.get_dividends() == []

    def test_cannot_delete_dividend_that_funded_a_later_buy(self):
        buy_with_dividend_cash = Trade.create_buy(stock_id=1, trade_date=D3, quantity=1, price=Decimal("50"))
        service, _, repo = _services(
            [BUY_10_AT_100, buy_with_dividend_cash], [_deposit("1000", D1, 1), _dividend("50", D2, 2)]
        )

        with pytest.raises(ValueError, match="yetersiz"):
            service.delete_dividend(2)
        assert len(service.get_dividends()) == 1

    def test_cannot_delete_non_dividend_movement(self):
        service, _, _ = _services([BUY_10_AT_100], [_deposit("1000", D1, 1)])

        with pytest.raises(ValueError, match="bulunamadı"):
            service.delete_dividend(1)

    def test_unknown_id_is_rejected(self):
        service, _, _ = _services([], [])

        with pytest.raises(ValueError, match="bulunamadı"):
            service.delete_dividend(123)


class TestSeriesTreatsDividendAsReturn:
    def _run(self, movements):
        price_repo = MagicMock()
        price_repo.get_price_series.return_value = [
            SimpleNamespace(price_date=day, close_price=Decimal("100")) for day in (D1, D2, D3)
        ]
        price_repo.get_last_price_before.return_value = None
        builder = PortfolioSeriesBuilder(price_repo, MagicMock())
        request = PortfolioSeriesRequest(
            trades=[BUY_10_AT_100],
            cash_movements=movements,
            stock_ids=[1],
            ticker_map={1: "AAA"},
            start_date=D1,
            end_date=D3,
            portfolio=Portfolio.from_trades([BUY_10_AT_100]),
        )
        return builder.compute_portfolio_series(request)

    def test_dividend_lifts_value_and_twr(self):
        values, twr, _, _ = self._run([_deposit("1000", D1, 1), _dividend("50", D3, 2)])

        assert values[D2] == Decimal("1000")
        assert values[D3] == Decimal("1050")
        assert twr[D3] == Decimal("105")  # %5 getiri: 50 / 1000

    def test_same_amount_as_deposit_is_not_a_return(self):
        values, twr, _, _ = self._run([_deposit("1000", D1, 1), _deposit("50", D3, 2)])

        assert values[D3] == Decimal("1050")
        assert twr[D3] == Decimal("100")  # dış sermaye getiri değildir
