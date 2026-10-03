"""SQLite: BIGINT birincil anahtar otomatik atama, temettü sütunu göçü ve temettü kalıcılığı (gerçek geçici veritabanı)."""
from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

import pytest

from src.domain.models.cash_movement import CashMovement, CashMovementType
from src.domain.models.stock import Stock
from src.domain.models.trade import Trade
from src.infrastructure.db.db_config import SQLiteConfig
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.repositories.sa_cash_movement_repository import SQLAlchemyCashMovementRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_portfolio_repository import SQLAlchemyPortfolioRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_stock_repository import SQLAlchemyStockRepository

DAY = date(2026, 3, 2)


@pytest.fixture
def provider(tmp_path):
    return SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(tmp_path / "test.db")))


@pytest.fixture
def stock(provider):
    return SQLAlchemyStockRepository(provider).save_stock(Stock(id=None, ticker="AAA", name="A"))


class TestBigintIdAssignment:
    def test_cash_movements_get_sequential_ids(self, provider):
        repo = SQLAlchemyCashMovementRepository(provider)

        first = repo.insert_movement(CashMovement.create_deposit(Decimal("10"), DAY))
        second = repo.insert_movement(CashMovement.create_withdraw(Decimal("5"), DAY))

        assert (first.id, second.id) == (1, 2)

    def test_bulk_insert_gets_distinct_ids(self, provider):
        repo = SQLAlchemyCashMovementRepository(provider)

        repo.insert_movements_bulk([CashMovement.create_deposit(Decimal(i + 1), DAY) for i in range(4)])

        assert [m.id for m in repo.get_all_movements()] == [1, 2, 3, 4]

    def test_trades_can_be_inserted_without_explicit_id(self, provider, stock):
        repo = SQLAlchemyPortfolioRepository(provider)

        saved = repo.insert_trade(Trade.create_buy(stock_id=stock.id, trade_date=DAY, quantity=1, price=Decimal("10")))
        repo.insert_trades_bulk(
            [Trade.create_buy(stock_id=stock.id, trade_date=DAY, quantity=1, price=Decimal("10")) for _ in range(3)]
        )

        assert saved.id == 1
        assert [t.id for t in repo.get_all_trades()] == [1, 2, 3, 4]

    def test_new_ids_never_collide_with_remaining_rows(self, provider):
        repo = SQLAlchemyCashMovementRepository(provider)
        repo.insert_movement(CashMovement.create_deposit(Decimal("10"), DAY))
        repo.insert_movement(CashMovement.create_deposit(Decimal("20"), DAY))
        repo.delete_movement(1)
        repo.insert_movement(CashMovement.create_deposit(Decimal("30"), DAY))

        ids = [m.id for m in repo.get_all_movements()]
        assert len(ids) == len(set(ids)) == 2 and 2 in ids


class TestDividendPersistence:
    def test_dividend_round_trip_keeps_stock_and_type(self, provider, stock):
        repo = SQLAlchemyCashMovementRepository(provider)

        saved = repo.insert_movement(CashMovement.create_dividend(stock.id, Decimal("12.5"), DAY, notes="Temettü"))

        loaded = repo.get_movement(saved.id)
        assert loaded.type == CashMovementType.DIVIDEND
        assert loaded.stock_id == stock.id
        assert loaded.amount == Decimal("12.5")

    def test_filter_by_type_and_stock(self, provider, stock):
        other = SQLAlchemyStockRepository(provider).save_stock(Stock(id=None, ticker="BBB", name="B"))
        repo = SQLAlchemyCashMovementRepository(provider)
        repo.insert_movement(CashMovement.create_deposit(Decimal("100"), DAY))
        repo.insert_movement(CashMovement.create_dividend(stock.id, Decimal("1"), DAY))
        repo.insert_movement(CashMovement.create_dividend(other.id, Decimal("2"), DAY))

        assert len(repo.get_movements_by_type(CashMovementType.DIVIDEND)) == 2
        assert [m.amount for m in repo.get_movements_by_type(CashMovementType.DIVIDEND, stock.id)] == [Decimal("1")]
        assert len(repo.get_all_movements()) == 3

    def test_delete_movement_removes_only_that_row(self, provider, stock):
        repo = SQLAlchemyCashMovementRepository(provider)
        keep = repo.insert_movement(CashMovement.create_deposit(Decimal("100"), DAY))
        gone = repo.insert_movement(CashMovement.create_dividend(stock.id, Decimal("1"), DAY))

        repo.delete_movement(gone.id)

        assert repo.get_movement(gone.id) is None
        assert repo.get_movement(keep.id) is not None


class TestStockIdColumnMigration:
    OLD_SCHEMA = """
        CREATE TABLE cash_movements (
            id BIGINT NOT NULL, movement_date DATE NOT NULL, movement_time TIME, type VARCHAR(8) NOT NULL,
            amount NUMERIC(18, 4) NOT NULL, notes VARCHAR(255),
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id)
        )
    """

    def _columns(self, path):
        with sqlite3.connect(path) as conn:
            return {row[1] for row in conn.execute("PRAGMA table_info(cash_movements)")}

    def test_old_database_gains_stock_id_and_keeps_rows(self, tmp_path):
        path = str(tmp_path / "old.db")
        with sqlite3.connect(path) as conn:
            conn.execute(self.OLD_SCHEMA)
            conn.execute("INSERT INTO cash_movements (id, movement_date, type, amount) VALUES (1, '2026-01-01', 'DEPOSIT', 100)")
        assert "stock_id" not in self._columns(path)

        provider = SQLAlchemyEngineProvider(SQLiteConfig(db_path=path))

        assert "stock_id" in self._columns(path)
        repo = SQLAlchemyCashMovementRepository(provider)
        assert [m.amount for m in repo.get_all_movements()] == [Decimal("100")]
        assert repo.get_all_movements()[0].stock_id is None

    def test_migration_is_idempotent(self, tmp_path):
        path = str(tmp_path / "old.db")
        with sqlite3.connect(path) as conn:
            conn.execute(self.OLD_SCHEMA)

        SQLAlchemyEngineProvider(SQLiteConfig(db_path=path))
        SQLAlchemyEngineProvider(SQLiteConfig(db_path=path))

        assert "stock_id" in self._columns(path)
