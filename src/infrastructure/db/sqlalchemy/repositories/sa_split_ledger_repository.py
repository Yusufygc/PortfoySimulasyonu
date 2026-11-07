"""Bölünmenin ana portföy, model portföy ve varlık defterine tek SQLite işleminde uygulanması / geri alınması."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from src.domain.models.split_event import (
    SplitCashEntry,
    SplitEvent,
    SplitEventStatus,
    SplitLedger,
    SplitLedgerSnapshot,
    SplitTradeChange,
)
from src.domain.ports.repositories.i_split_ledger_repo import ISplitLedgerRepository
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import (
    CashMovementTypeEnum,
    ORMAssetTrade,
    ORMCashMovement,
    ORMModelPortfolioCashMovement,
    ORMModelPortfolioTrade,
    ORMTrade,
)
from src.infrastructure.db.sqlalchemy.orm_split_models import ORMSplitCashEntry, ORMSplitEvent, ORMSplitTradeChange
from src.infrastructure.db.sqlalchemy.repositories._transaction import commit_or_rollback
from src.infrastructure.db.sqlalchemy.repositories.sa_ledger_reader import SQLAlchemyLedgerReader

_TRADE_TABLE = {SplitLedger.MAIN: ORMTrade, SplitLedger.MODEL: ORMModelPortfolioTrade, SplitLedger.ASSET: ORMAssetTrade}
_CASH_NOTE = "Bölünme küsurat nakdi ({ticker} {multiplier}:1, {ex_date:%d.%m.%Y})"


class SplitLedgerConflict(ValueError):
    """İşlem, bölünme kaydındaki değerden farklı: uygulama veya geri alma güvenli değil."""


def _dec(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _stored_quantity(ledger: SplitLedger, quantity: Decimal):
    return quantity if ledger == SplitLedger.ASSET else int(quantity)


class SQLAlchemySplitLedgerRepository(ISplitLedgerRepository):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    # ---- okuma -------------------------------------------------------------------------
    def load_snapshot(self, stock_id: Optional[int] = None, asset_id: Optional[int] = None) -> SplitLedgerSnapshot:
        """Tek hissenin veya varlığın defter lotları (ortak okuyucu `SQLAlchemyLedgerReader`)."""
        if stock_id is None and asset_id is None:
            return SplitLedgerSnapshot({})
        return SQLAlchemyLedgerReader(self._provider).snapshot(stock_id=stock_id, asset_id=asset_id)

    def get_event(self, event_id: int) -> Optional[SplitEvent]:
        with self._provider.get_session() as session:
            orm = session.get(ORMSplitEvent, event_id)
            return self._to_domain(session, orm) if orm is not None else None

    def list_events(self, ticker: Optional[str] = None) -> List[SplitEvent]:
        with self._provider.get_session() as session:
            query = session.query(ORMSplitEvent)
            if ticker:
                query = query.filter_by(ticker=ticker.strip().upper())
            rows = query.order_by(ORMSplitEvent.ex_date.desc(), ORMSplitEvent.id.desc()).all()
            return [self._to_domain(session, row) for row in rows]

    # ---- yazma -------------------------------------------------------------------------
    def apply(self, event: SplitEvent) -> SplitEvent:
        with self._provider.get_session() as session:
            orm_event = ORMSplitEvent(
                ticker=event.ticker, stock_id=event.stock_id, asset_id=event.asset_id, ex_date=event.ex_date,
                multiplier=event.multiplier, sources=event.sources, auto_applied=event.auto_applied,
                status=SplitEventStatus.APPLIED.value, corporate_action_id=event.corporate_action_id,
                applied_at=datetime.now(), note=event.note,
            )
            session.add(orm_event)
            session.flush()
            for change in event.trade_changes:
                self._write_trade(session, change, (change.pre_quantity, change.pre_price),
                                  (change.post_quantity, change.post_price))
                session.add(self._change_orm(orm_event.id, change))
            for entry in event.cash_entries:
                movement_id = self._insert_cash(session, event, entry)
                session.add(ORMSplitCashEntry(
                    event_id=orm_event.id, ledger=entry.ledger.value, portfolio_id=entry.portfolio_id,
                    movement_id=movement_id, amount=entry.amount, movement_date=entry.movement_date,
                ))
            commit_or_rollback(session)
            return self._to_domain(session, orm_event)

    def revert(self, event_id: int) -> SplitEvent:
        with self._provider.get_session() as session:
            orm_event = session.get(ORMSplitEvent, event_id)
            if orm_event is None:
                raise ValueError(f"Bölünme kaydı bulunamadı: id={event_id}")
            if orm_event.status != SplitEventStatus.APPLIED.value:
                raise ValueError(f"Bölünme kaydı zaten geri alınmış: id={event_id}")
            for row in session.query(ORMSplitTradeChange).filter_by(event_id=event_id).all():
                change = self._change_domain(row)
                self._write_trade(session, change, (change.post_quantity, change.post_price),
                                  (change.pre_quantity, change.pre_price))
            for row in session.query(ORMSplitCashEntry).filter_by(event_id=event_id).all():
                table = ORMCashMovement if row.ledger == SplitLedger.MAIN.value else ORMModelPortfolioCashMovement
                movement = session.get(table, row.movement_id)
                if movement is not None:
                    session.delete(movement)
            orm_event.status = SplitEventStatus.REVERTED.value
            orm_event.reverted_at = datetime.now()
            commit_or_rollback(session)
            return self._to_domain(session, orm_event)

    def set_corporate_action(self, event_id: int, corporate_action_id: int) -> None:
        with self._provider.get_session() as session:
            orm_event = session.get(ORMSplitEvent, event_id)
            if orm_event is None:
                raise ValueError(f"Bölünme kaydı bulunamadı: id={event_id}")
            orm_event.corporate_action_id = corporate_action_id
            commit_or_rollback(session)

    def record_price_adjustment(self, event_id, before_date, count, market_effective_date) -> None:
        with self._provider.get_session() as session:
            orm_event = session.get(ORMSplitEvent, event_id)
            if orm_event is None:
                raise ValueError(f"Bölünme kaydı bulunamadı: id={event_id}")
            orm_event.price_adjusted_before = before_date
            orm_event.price_adjustment_count = int(count)
            orm_event.market_effective_date = market_effective_date
            commit_or_rollback(session)

    # ---- yardımcılar -------------------------------------------------------------------
    @staticmethod
    def _write_trade(session, change: SplitTradeChange, expected: tuple, target: tuple) -> None:
        """İşlemi `expected` (lot, fiyat) değerindeyse `target` değerine yazar; değilse çakışma."""
        (expect_quantity, expect_price), (quantity, price) = expected, target
        row = session.get(_TRADE_TABLE[change.ledger], change.trade_id)
        if row is None:
            raise SplitLedgerConflict(f"İşlem bulunamadı ({change.ledger.value} id={change.trade_id})")
        if _dec(row.quantity) != _dec(expect_quantity) or _dec(row.price) != _dec(expect_price):
            raise SplitLedgerConflict(
                f"İşlem bölünme kaydından farklı ({change.ledger.value} id={change.trade_id}): "
                f"{row.quantity} @ {row.price}, beklenen {expect_quantity} @ {expect_price}"
            )
        row.quantity = _stored_quantity(change.ledger, _dec(quantity))
        row.price = _dec(price)

    @staticmethod
    def _insert_cash(session, event: SplitEvent, entry: SplitCashEntry) -> int:
        note = _CASH_NOTE.format(ticker=event.ticker, multiplier=event.multiplier.normalize(), ex_date=event.ex_date)
        if entry.ledger == SplitLedger.MAIN:
            movement = ORMCashMovement(movement_date=entry.movement_date, movement_time=None,
                                       type=CashMovementTypeEnum.FRACTION, amount=entry.amount, notes=note,
                                       stock_id=event.stock_id)
        else:
            movement = ORMModelPortfolioCashMovement(portfolio_id=entry.portfolio_id, movement_date=entry.movement_date,
                                                     movement_time=None, type=CashMovementTypeEnum.FRACTION,
                                                     amount=entry.amount, notes=note)
        session.add(movement)
        session.flush()
        return movement.id

    @staticmethod
    def _change_orm(event_id: int, change: SplitTradeChange) -> ORMSplitTradeChange:
        return ORMSplitTradeChange(
            event_id=event_id, ledger=change.ledger.value, trade_id=change.trade_id, portfolio_id=change.portfolio_id,
            pre_quantity=change.pre_quantity, post_quantity=change.post_quantity,
            pre_price=change.pre_price, post_price=change.post_price,
        )

    @staticmethod
    def _change_domain(row: ORMSplitTradeChange) -> SplitTradeChange:
        return SplitTradeChange(SplitLedger(row.ledger), row.trade_id, _dec(row.pre_quantity), _dec(row.post_quantity),
                                _dec(row.pre_price), _dec(row.post_price), row.portfolio_id)

    def _to_domain(self, session, orm: ORMSplitEvent) -> SplitEvent:
        changes = session.query(ORMSplitTradeChange).filter_by(event_id=orm.id).order_by(ORMSplitTradeChange.id).all()
        cash = session.query(ORMSplitCashEntry).filter_by(event_id=orm.id).order_by(ORMSplitCashEntry.id).all()
        return SplitEvent(
            id=orm.id, ticker=orm.ticker, ex_date=orm.ex_date, multiplier=_dec(orm.multiplier), sources=orm.sources,
            auto_applied=bool(orm.auto_applied), status=SplitEventStatus(orm.status), stock_id=orm.stock_id,
            asset_id=orm.asset_id, corporate_action_id=orm.corporate_action_id, applied_at=orm.applied_at,
            reverted_at=orm.reverted_at, note=orm.note, price_adjusted_before=orm.price_adjusted_before,
            price_adjustment_count=int(orm.price_adjustment_count or 0), market_effective_date=orm.market_effective_date,
            trade_changes=tuple(self._change_domain(row) for row in changes),
            cash_entries=tuple(
                SplitCashEntry(SplitLedger(row.ledger), _dec(row.amount), row.movement_date, row.portfolio_id, row.movement_id)
                for row in cash
            ),
        )
