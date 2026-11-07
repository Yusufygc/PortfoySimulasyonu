from datetime import date, time
from decimal import Decimal as D

import pytest

from src.domain.models.cash_movement import CashMovementType
from src.domain.models.split_event import (
    SplitCashEntry,
    SplitEvent,
    SplitEventStatus,
    SplitLedger,
    SplitTradeChange,
)
from src.infrastructure.db.db_config import SQLiteConfig
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import (
    ORMCashMovement,
    ORMModelPortfolio,
    ORMModelPortfolioCashMovement,
    ORMModelPortfolioTrade,
    ORMStock,
    ORMTrade,
    TradeSideEnum,
)
from src.infrastructure.db.sqlalchemy.repositories.sa_cash_movement_repository import SQLAlchemyCashMovementRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_split_ledger_repository import (
    SplitLedgerConflict,
    SQLAlchemySplitLedgerRepository,
)

EX = date(2026, 8, 21)


@pytest.fixture
def provider(tmp_path):
    return SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(tmp_path / "split.db")))


@pytest.fixture
def seeded(provider):
    with provider.get_session() as s:
        s.add(ORMStock(id=79, ticker="SDTTR"))
        s.add(ORMModelPortfolio(id=9, name="Model"))
        s.flush()
        s.add(ORMTrade(id=1, stock_id=79, trade_date=date(2026, 8, 1), trade_time=time(10), side=TradeSideEnum.BUY,
                       quantity=10, price=D("250"), original_quantity=10, original_price=D("250")))
        s.add(ORMModelPortfolioTrade(id=34, portfolio_id=9, stock_id=79, trade_date=date(2026, 8, 7),
                                     trade_time=time(16, 40), side=TradeSideEnum.BUY, quantity=65, price=D("242")))
        s.commit()
    return provider


def _event(**overrides):
    base = dict(
        id=None, ticker="SDTTR", ex_date=EX, multiplier=D("11"), sources="PRICE_BREAK,YAHOO", auto_applied=True,
        stock_id=79,
        trade_changes=(
            SplitTradeChange(SplitLedger.MAIN, 1, D("10"), D("110"), D("250"), D("22.7273")),
            SplitTradeChange(SplitLedger.MODEL, 34, D("65"), D("715"), D("242"), D("22.0000"), portfolio_id=9),
        ),
        cash_entries=(
            SplitCashEntry(SplitLedger.MAIN, D("1.95"), EX),
            SplitCashEntry(SplitLedger.MODEL, D("0.50"), EX, portfolio_id=9),
        ),
    )
    base.update(overrides)
    return SplitEvent(**base)


def test_snapshot_groups_main_and_model_lots(seeded):
    snapshot = SQLAlchemySplitLedgerRepository(seeded).load_snapshot(stock_id=79)
    assert {k: [(l.trade_id, l.quantity, l.price, l.is_buy) for l in v] for k, v in snapshot.lots.items()} == {
        (SplitLedger.MAIN, None): [(1, D("10"), D("250"), True)],
        (SplitLedger.MODEL, 9): [(34, D("65"), D("242"), True)],
    }


def test_apply_updates_trades_and_writes_fraction_cash(seeded):
    repo = SQLAlchemySplitLedgerRepository(seeded)
    stored = repo.apply(_event())

    assert stored.id is not None and stored.status == SplitEventStatus.APPLIED
    with seeded.get_session() as s:
        main = s.get(ORMTrade, 1)
        model = s.get(ORMModelPortfolioTrade, 34)
        assert (main.quantity, main.price, main.original_quantity) == (110, D("22.7273"), 10)
        assert (model.quantity, model.price) == (715, D("22.0000"))
        cash = s.query(ORMCashMovement).all()
        model_cash = s.query(ORMModelPortfolioCashMovement).all()
        assert [(c.type.value, c.amount, c.stock_id) for c in cash] == [("FRACTION", D("1.95"), 79)]
        assert [(c.type.value, c.amount, c.portfolio_id) for c in model_cash] == [("FRACTION", D("0.50"), 9)]
    # domain okuması küsurat nakdini tanır
    [movement] = SQLAlchemyCashMovementRepository(seeded).get_all_movements()
    assert movement.type == CashMovementType.FRACTION and movement.type.adds_cash and not movement.type.is_external_flow
    assert [e.movement_id for e in stored.cash_entries] == [cash[0].id, model_cash[0].id]


def test_revert_restores_trades_and_removes_cash(seeded):
    repo = SQLAlchemySplitLedgerRepository(seeded)
    stored = repo.apply(_event())
    reverted = repo.revert(stored.id)

    assert reverted.status == SplitEventStatus.REVERTED and reverted.reverted_at is not None
    with seeded.get_session() as s:
        assert (s.get(ORMTrade, 1).quantity, s.get(ORMTrade, 1).price) == (10, D("250"))
        assert (s.get(ORMModelPortfolioTrade, 34).quantity, s.get(ORMModelPortfolioTrade, 34).price) == (65, D("242"))
        assert s.query(ORMCashMovement).count() == 0
        assert s.query(ORMModelPortfolioCashMovement).count() == 0
    with pytest.raises(ValueError):
        repo.revert(stored.id)


def test_apply_is_atomic_when_a_trade_changed(seeded):
    repo = SQLAlchemySplitLedgerRepository(seeded)
    stale = _event(trade_changes=(
        SplitTradeChange(SplitLedger.MAIN, 1, D("10"), D("110"), D("250"), D("22.7273")),
        SplitTradeChange(SplitLedger.MODEL, 34, D("60"), D("660"), D("242"), D("22.0000"), portfolio_id=9),  # bayat
    ))
    with pytest.raises(SplitLedgerConflict):
        repo.apply(stale)
    with seeded.get_session() as s:
        assert s.get(ORMTrade, 1).quantity == 10              # ilk değişiklik de geri alındı
        assert s.query(ORMCashMovement).count() == 0
    assert repo.list_events() == []


def test_revert_refuses_when_trade_edited_after_split(seeded):
    repo = SQLAlchemySplitLedgerRepository(seeded)
    stored = repo.apply(_event(cash_entries=()))
    with seeded.get_session() as s:
        s.get(ORMModelPortfolioTrade, 34).quantity = 700
        s.commit()
    with pytest.raises(SplitLedgerConflict):
        repo.revert(stored.id)
    assert repo.get_event(stored.id).status == SplitEventStatus.APPLIED
    with seeded.get_session() as s:
        assert s.get(ORMTrade, 1).quantity == 110             # kısmi geri alma yok


def test_list_events_filters_by_ticker(seeded):
    repo = SQLAlchemySplitLedgerRepository(seeded)
    repo.apply(_event(cash_entries=()))
    assert [e.ticker for e in repo.list_events("sdttr")] == ["SDTTR"]
    assert repo.list_events("OTHER") == []


def test_ledger_reader_returns_all_ledgers_with_instrument_ids(seeded):
    from src.domain.models.ledger import LedgerKind
    from src.infrastructure.db.sqlalchemy.repositories.sa_ledger_reader import SQLAlchemyLedgerReader

    snapshot = SQLAlchemyLedgerReader(seeded).snapshot()
    assert sorted(snapshot.lots, key=str) == [(LedgerKind.MAIN, None), (LedgerKind.MODEL, 9)]
    assert snapshot.instruments() == {79} and snapshot.open_instruments() == {79}
    assert [l.instrument_id for l in snapshot.lots[(LedgerKind.MODEL, 9)]] == [79]
    assert SQLAlchemyLedgerReader(seeded).snapshot(stock_id=12345).is_empty()
