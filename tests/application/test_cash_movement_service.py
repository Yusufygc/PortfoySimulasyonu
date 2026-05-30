from datetime import date
from decimal import Decimal

from src.application.services.portfolio.cash_movement_service import CashMovementService
from src.domain.models.cash_movement import CashMovementType


class FakeCashMovementRepo:
    def __init__(self):
        self.movements = []

    def insert_movement(self, movement):
        self.movements.append(movement)
        return movement

    def get_all_movements(self):
        return list(self.movements)

    def get_movements_until(self, movement_date, movement_time=None):
        return [movement for movement in self.movements if movement.movement_date <= movement_date]


def test_cash_movement_service_adds_deposit_and_withdraw():
    repo = FakeCashMovementRepo()
    service = CashMovementService(repo)

    deposit = service.add_deposit(Decimal("100"), movement_date=date(2026, 1, 1))
    withdraw = service.add_withdraw(Decimal("25"), movement_date=date(2026, 1, 2))

    assert deposit.type == CashMovementType.DEPOSIT
    assert withdraw.type == CashMovementType.WITHDRAW
    assert service.get_cash_balance() == Decimal("75")


def test_cash_movement_service_rejects_withdraw_above_portfolio_balance():
    repo = FakeCashMovementRepo()
    service = CashMovementService(
        repo,
        portfolio_service=type("PortfolioService", (), {"get_cash_balance": lambda self: Decimal("10")})(),
    )

    try:
        service.add_withdraw(Decimal("11"), movement_date=date(2026, 1, 2))
    except ValueError as exc:
        assert "Yetersiz nakit" in str(exc)
    else:
        raise AssertionError("Expected insufficient cash error")

    assert repo.movements == []
