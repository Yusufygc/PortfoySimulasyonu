# tests/application/test_corporate_action_service.py
"""
CorporateActionService birim testleri.
Repository'ler mock'lanır; DB bağlantısı gerekmez.
"""

import pytest
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, call

from src.domain.models.corporate_action import ActionType, CorporateAction
from src.domain.models.trade import Trade, TradeSide
from src.application.services.corporate_actions.corporate_action_service import (
    CorporateActionService,
    CorporateActionResult,
)
from src.application.services.corporate_actions.price_adjustment_service import (
    CorporateActionPriceAdjustmentService,
    adjusted_market_price,
    calculate_price_adjustment_factor,
)


# ══════════════════════════════════════════════════════════
#  Test yardımcıları
# ══════════════════════════════════════════════════════════

def _make_buy_trade(stock_id, quantity, price, trade_date=None):
    return Trade(
        id=1,
        stock_id=stock_id,
        trade_date=trade_date or date(2025, 1, 1),
        trade_time=None,
        side=TradeSide.BUY,
        quantity=quantity,
        price=Decimal(str(price)),
    )

def _make_action(
    action_id: int,
    stock_id: int,
    action_type: ActionType,
    ratio: str,
    subscription_price: str = None,
    applied: bool = False,
) -> CorporateAction:
    return CorporateAction(
        id=action_id,
        stock_id=stock_id,
        action_type=action_type,
        ex_date=date(2026, 3, 15),
        ratio=Decimal(ratio),
        subscription_price=Decimal(subscription_price) if subscription_price else None,
        announcement_date=None,
        notes=None,
        applied=applied,
    )

@pytest.fixture
def mock_action_repo():
    repo = MagicMock()
    repo.get_by_stock.return_value = []
    return repo

@pytest.fixture
def mock_portfolio_repo():
    return MagicMock()

@pytest.fixture
def service(mock_action_repo, mock_portfolio_repo):
    return CorporateActionService(
        action_repo=mock_action_repo,
        portfolio_repo=mock_portfolio_repo,
    )


# ══════════════════════════════════════════════════════════
#  register_bedelsiz
# ══════════════════════════════════════════════════════════

class TestRegisterBedelsiz:

    def test_calls_insert(self, service, mock_action_repo):
        expected = _make_action(1, 10, ActionType.BEDELSIZ, "0.50")
        mock_action_repo.insert.return_value = expected

        result = service.register_bedelsiz(
            stock_id=10, ex_date=date(2026, 3, 15), ratio=Decimal("0.50")
        )

        assert mock_action_repo.insert.call_count == 1
        inserted_action = mock_action_repo.insert.call_args[0][0]
        assert inserted_action.action_type == ActionType.BEDELSIZ
        assert inserted_action.ratio == Decimal("0.50")
        assert inserted_action.applied is False
        assert result is expected

    def test_invalid_ratio_raises(self, service):
        with pytest.raises(ValueError):
            service.register_bedelsiz(stock_id=1, ex_date=date(2026, 1, 1), ratio=Decimal("0"))

    def test_duplicate_stock_type_ex_date_raises(self, service, mock_action_repo):
        mock_action_repo.get_by_stock.return_value = [
            _make_action(99, 10, ActionType.BEDELSIZ, "6.38340000", applied=True)
        ]

        with pytest.raises(ValueError, match="zaten kayitli"):
            service.register_bedelsiz(
                stock_id=10,
                ex_date=date(2026, 3, 15),
                ratio=Decimal("6.3833834"),
            )

        mock_action_repo.insert.assert_not_called()


# ══════════════════════════════════════════════════════════
#  register_bedelli
# ══════════════════════════════════════════════════════════

class TestRegisterBedelli:

    def test_calls_insert(self, service, mock_action_repo):
        expected = _make_action(2, 5, ActionType.BEDELLI, "0.20", "1.00")
        mock_action_repo.insert.return_value = expected

        service.register_bedelli(
            stock_id=5, ex_date=date(2026, 4, 1),
            ratio=Decimal("0.20"), subscription_price=Decimal("1.00")
        )

        inserted = mock_action_repo.insert.call_args[0][0]
        assert inserted.action_type == ActionType.BEDELLI
        assert inserted.subscription_price == Decimal("1.00")

    def test_zero_subscription_price_raises(self, service):
        with pytest.raises(ValueError):
            service.register_bedelli(
                stock_id=1, ex_date=date(2026, 1, 1),
                ratio=Decimal("0.20"), subscription_price=Decimal("0")
            )

    def test_duplicate_bedelli_stock_type_ex_date_raises(self, service, mock_action_repo):
        mock_action_repo.get_by_stock.return_value = [
            _make_action(100, 5, ActionType.BEDELLI, "0.20", "1.00")
        ]

        with pytest.raises(ValueError, match="zaten kayitli"):
            service.register_bedelli(
                stock_id=5,
                ex_date=date(2026, 3, 15),
                ratio=Decimal("0.20"),
                subscription_price=Decimal("1.00"),
            )

        mock_action_repo.insert.assert_not_called()


# ══════════════════════════════════════════════════════════
#  apply_action — Bedelsiz
# ══════════════════════════════════════════════════════════

class TestApplyBedelsiz:

    def _setup(self, mock_action_repo, mock_portfolio_repo):
        """100 lot × 10 TL pozisyonu olan senaryo, %50 bedelsiz aksiyon."""
        action = _make_action(1, 10, ActionType.BEDELSIZ, "0.50")
        mock_action_repo.get_by_id.return_value = action

        trades = [_make_buy_trade(stock_id=10, quantity=100, price=10.0)]
        mock_portfolio_repo.get_trades_by_stock.return_value = trades

        inserted_trade = Trade(
            id=99, stock_id=10, trade_date=date(2026, 3, 15),
            trade_time=None, side=TradeSide.BUY, quantity=50, price=Decimal("0"),
        )
        mock_portfolio_repo.insert_trade.return_value = inserted_trade
        return action

    def test_result_quantities(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        result = service.apply_action(action_id=1)

        assert result.shares_before == 100
        assert result.new_shares == 50           # 100 * 0.50
        assert result.shares_after == 150

    def test_result_avg_cost_drops(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        result = service.apply_action(action_id=1)

        # Önceki avg cost: 10 TL
        assert result.avg_cost_before == Decimal("10")
        # Yeni avg cost: 1000 TL toplam maliyet / 150 lot ≈ 6.6667 TL
        expected_avg = Decimal("1000") / Decimal("150")
        assert abs(result.avg_cost_after - expected_avg) < Decimal("0.001")

    def test_capital_spent_is_zero(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        result = service.apply_action(action_id=1)
        assert result.capital_spent == Decimal("0")

    def test_original_trade_is_adjusted(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        service.apply_action(action_id=1)

        assert mock_portfolio_repo.update_trade.call_count == 1
        updated = mock_portfolio_repo.update_trade.call_args[0][0]
        assert updated.quantity == 150
        assert abs(updated.price - Decimal("6.6667")) < Decimal("0.001")

    def test_mark_applied_called(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        service.apply_action(action_id=1)

        mock_action_repo.mark_applied.assert_called_once_with(1)

    def test_update_failure_does_not_mark_action_applied(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        mock_portfolio_repo.update_trade.side_effect = RuntimeError("update failed")

        with pytest.raises(RuntimeError, match="update failed"):
            service.apply_action(action_id=1)

        mock_action_repo.mark_applied.assert_not_called()

    def test_theoretical_price_included_when_given(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        # Mevcut fiyat = 15 TL, teorik = 15 / 1.50 = 10.00
        result = service.apply_action(action_id=1, current_price=Decimal("15"))
        expected = Decimal("15") / Decimal("1.50")
        assert abs(result.theoretical_ex_price - expected) < Decimal("0.001")

    def test_already_applied_raises(self, service, mock_action_repo, mock_portfolio_repo):
        action = _make_action(1, 10, ActionType.BEDELSIZ, "0.50", applied=True)
        mock_action_repo.get_by_id.return_value = action

        with pytest.raises(ValueError, match="zaten uygulanmış"):
            service.apply_action(action_id=1)

    def test_no_position_raises(self, service, mock_action_repo, mock_portfolio_repo):
        action = _make_action(1, 10, ActionType.BEDELSIZ, "0.50")
        mock_action_repo.get_by_id.return_value = action
        mock_portfolio_repo.get_trades_by_stock.return_value = []  # boş portföy

        with pytest.raises(ValueError, match="pozisyon"):
            service.apply_action(action_id=1)

    def test_action_not_found_raises(self, service, mock_action_repo, mock_portfolio_repo):
        mock_action_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="bulunamadı"):
            service.apply_action(action_id=999)


# ══════════════════════════════════════════════════════════
#  apply_action — Bedelli
# ══════════════════════════════════════════════════════════

class TestApplyBedelli:

    def _setup(self, mock_action_repo, mock_portfolio_repo):
        """500 lot × 20 TL pozisyonu, %20 bedelli @ 1 TL kullanım fiyatı."""
        action = _make_action(2, 10, ActionType.BEDELLI, "0.20", "1.00")
        mock_action_repo.get_by_id.return_value = action

        trades = [_make_buy_trade(stock_id=10, quantity=500, price=20.0)]
        mock_portfolio_repo.get_trades_by_stock.return_value = trades

        inserted_trade = Trade(
            id=100, stock_id=10, trade_date=date(2026, 3, 15),
            trade_time=None, side=TradeSide.BUY, quantity=100, price=Decimal("1.00"),
        )
        mock_portfolio_repo.insert_trade.return_value = inserted_trade
        return action

    def test_result_quantities(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        result = service.apply_action(action_id=2)

        assert result.shares_before == 500
        assert result.new_shares == 100          # 500 * 0.20
        assert result.shares_after == 600

    def test_capital_spent(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        result = service.apply_action(action_id=2)
        # 100 yeni lot × 1 TL = 100 TL
        assert result.capital_spent == Decimal("100")

    def test_new_avg_cost(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        result = service.apply_action(action_id=2)

        # Eski toplam maliyet: 500 * 20 = 10000
        # Yeni maliyet: 10000 + 100 = 10100
        # Yeni avg: 10100 / 600 ≈ 16.8333
        expected_avg = Decimal("10100") / Decimal("600")
        assert abs(result.avg_cost_after - expected_avg) < Decimal("0.001")

    def test_original_trade_is_updated(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        service.apply_action(action_id=2)

        assert mock_portfolio_repo.update_trade.call_count == 1
        updated = mock_portfolio_repo.update_trade.call_args[0][0]
        assert updated.quantity == 500
        assert updated.price == Decimal("20.0000")

    def test_theoretical_price_bedelli(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        # P=20 TL, oran=0.20, K=1 TL
        # Teorik = (20 + 0.20 * 1) / 1.20 = 20.20 / 1.20 ≈ 16.8333
        result = service.apply_action(action_id=2, current_price=Decimal("20"))
        expected = (Decimal("20") + Decimal("0.20") * Decimal("1")) / Decimal("1.20")
        assert abs(result.theoretical_ex_price - expected) < Decimal("0.001")

    def test_mark_applied_called(self, service, mock_action_repo, mock_portfolio_repo):
        self._setup(mock_action_repo, mock_portfolio_repo)
        service.apply_action(action_id=2)
        mock_action_repo.mark_applied.assert_called_once_with(2)


# ══════════════════════════════════════════════════════════
#  delete_action
# ══════════════════════════════════════════════════════════

class TestDeleteAction:

    def test_deletes_pending_action(self, service, mock_action_repo, mock_portfolio_repo):
        action = _make_action(5, 1, ActionType.BEDELSIZ, "0.25", applied=False)
        mock_action_repo.get_by_id.return_value = action

        service.delete_action(5)
        mock_action_repo.delete.assert_called_once_with(5)

    def test_cannot_delete_applied_action(self, service, mock_action_repo, mock_portfolio_repo):
        action = _make_action(5, 1, ActionType.BEDELSIZ, "0.25", applied=True)
        mock_action_repo.get_by_id.return_value = action

        with pytest.raises(ValueError, match="silinemez"):
            service.delete_action(5)

    def test_not_found_raises(self, service, mock_action_repo, mock_portfolio_repo):
        mock_action_repo.get_by_id.return_value = None

        with pytest.raises(ValueError, match="bulunamadı"):
            service.delete_action(999)


# ══════════════════════════════════════════════════════════
#  Senaryo: Küsurat lot testi
# ══════════════════════════════════════════════════════════

def test_floor_rounding_in_service(service, mock_action_repo, mock_portfolio_repo):
    """99 lot × %50 → 49 yeni lot (küsurat atılır, BİST kuralı)."""
    action = _make_action(10, 7, ActionType.BEDELSIZ, "0.50")
    mock_action_repo.get_by_id.return_value = action

    trades = [_make_buy_trade(stock_id=7, quantity=99, price=10.0)]
    mock_portfolio_repo.get_trades_by_stock.return_value = trades
    mock_portfolio_repo.insert_trade.return_value = MagicMock()

    result = service.apply_action(action_id=10)

    assert result.new_shares == 49   # int(99 * 0.50) = 49
    assert result.shares_after == 148


def test_bedelsiz_price_adjustment_factor_for_merko_ratio():
    action = _make_action(10, 7, ActionType.BEDELSIZ, "6.3833834")

    factor = calculate_price_adjustment_factor(action)

    assert abs(factor - (Decimal("1") / Decimal("7.3833834"))) < Decimal("0.0000000001")


def test_bedelli_price_adjustment_factor_uses_previous_close_and_subscription_price():
    action = _make_action(11, 7, ActionType.BEDELLI, "0.20", "1.00")

    factor = calculate_price_adjustment_factor(action, previous_close=Decimal("20"))

    assert abs(factor - (Decimal("20.20") / Decimal("24.00"))) < Decimal("0.0000000001")


def test_apply_action_adjusts_historical_prices(
    mock_action_repo,
    mock_portfolio_repo,
):
    action = _make_action(12, 10, ActionType.BEDELSIZ, "0.50")
    mock_action_repo.get_by_id.return_value = action
    mock_portfolio_repo.get_trades_by_stock.return_value = [_make_buy_trade(10, 100, 10)]
    price_repo = MagicMock()
    price_repo.adjust_prices_before_date.return_value = 3
    adjustment_service = CorporateActionPriceAdjustmentService(mock_action_repo, price_repo)
    service = CorporateActionService(
        action_repo=mock_action_repo,
        portfolio_repo=mock_portfolio_repo,
        price_adjustment_service=adjustment_service,
    )

    result = service.apply_action(12)

    mock_portfolio_repo.update_trade.assert_called_once()
    mock_action_repo.mark_applied.assert_called_once_with(12)
    price_repo.adjust_prices_before_date.assert_called_once_with(
        stock_id=10,
        before_date=date(2026, 3, 15),
        factor=Decimal("1") / Decimal("1.50"),
    )
    mock_action_repo.mark_prices_adjusted.assert_called_once_with(
        12,
        Decimal("1") / Decimal("1.50"),
        3,
    )
    assert result.price_adjustment_count == 3


def test_apply_action_does_not_adjust_prices_when_trade_update_fails(
    mock_action_repo,
    mock_portfolio_repo,
):
    action = _make_action(13, 10, ActionType.BEDELSIZ, "0.50")
    mock_action_repo.get_by_id.return_value = action
    mock_portfolio_repo.get_trades_by_stock.return_value = [_make_buy_trade(10, 100, 10)]
    mock_portfolio_repo.update_trade.side_effect = RuntimeError("update failed")
    price_repo = MagicMock()
    service = CorporateActionService(
        action_repo=mock_action_repo,
        portfolio_repo=mock_portfolio_repo,
        price_adjustment_service=CorporateActionPriceAdjustmentService(mock_action_repo, price_repo),
    )

    with pytest.raises(RuntimeError, match="update failed"):
        service.apply_action(13)

    price_repo.adjust_prices_before_date.assert_not_called()
    mock_action_repo.mark_prices_adjusted.assert_not_called()


def test_adjust_prices_for_action_is_idempotent_for_already_adjusted_action(mock_action_repo):
    action = CorporateAction(
        id=14,
        stock_id=10,
        action_type=ActionType.BEDELSIZ,
        ex_date=date(2026, 3, 15),
        ratio=Decimal("0.50"),
        subscription_price=None,
        announcement_date=None,
        notes=None,
        applied=True,
        prices_adjusted=True,
        price_adjustment_factor=Decimal("0.6666666667"),
        price_adjustment_count=4,
    )
    mock_action_repo.get_by_id.return_value = action
    price_repo = MagicMock()
    service = CorporateActionPriceAdjustmentService(mock_action_repo, price_repo)

    result = service.adjust_prices_for_action(14)

    price_repo.adjust_prices_before_date.assert_not_called()
    mock_action_repo.mark_prices_adjusted.assert_not_called()
    assert result.already_adjusted is True
    assert result.adjusted_count == 4


def test_adjusted_market_price_applies_multiple_adjusted_actions():
    actions = [
        CorporateAction(
            id=1,
            stock_id=10,
            action_type=ActionType.BEDELSIZ,
            ex_date=date(2026, 5, 5),
            ratio=Decimal("1"),
            subscription_price=None,
            announcement_date=None,
            notes=None,
            applied=True,
            prices_adjusted=True,
            price_adjustment_factor=Decimal("0.5"),
        ),
        CorporateAction(
            id=2,
            stock_id=10,
            action_type=ActionType.BEDELSIZ,
            ex_date=date(2026, 6, 5),
            ratio=Decimal("1"),
            subscription_price=None,
            announcement_date=None,
            notes=None,
            applied=True,
            prices_adjusted=True,
            price_adjustment_factor=Decimal("0.25"),
        ),
    ]

    assert adjusted_market_price(Decimal("80"), date(2026, 5, 1), actions) == Decimal("10.00")
    assert adjusted_market_price(Decimal("80"), date(2026, 5, 10), actions) == Decimal("20.00")
    assert adjusted_market_price(Decimal("80"), date(2026, 6, 5), actions) == Decimal("80")
