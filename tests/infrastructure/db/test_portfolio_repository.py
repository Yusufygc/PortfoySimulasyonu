"""SQLAlchemyPortfolioRepository: ana BIST işlem deposu (gerçek geçici SQLite)."""
from __future__ import annotations

from datetime import date, time
from decimal import Decimal

import pytest

from src.domain.models.stock import Stock
from src.domain.models.trade import Trade, TradeSide
from src.infrastructure.db.db_config import SQLiteConfig
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.repositories.sa_portfolio_repository import SQLAlchemyPortfolioRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_stock_repository import SQLAlchemyStockRepository

D = Decimal


@pytest.fixture
def provider(tmp_path):
    return SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(tmp_path / "trades.db")))


@pytest.fixture
def repo(provider):
    return SQLAlchemyPortfolioRepository(provider)


@pytest.fixture
def stocks(provider):
    stock_repo = SQLAlchemyStockRepository(provider)
    return [stock_repo.save_stock(Stock(id=None, ticker=t, name=t)) for t in ("AAA", "BBB")]


def _buy(stock_id, day, qty=10, price="100", at=None):
    return Trade.create_buy(stock_id=stock_id, trade_date=day, quantity=qty, price=D(price), trade_time=at)


class TestPortfolioRepository:
    def test_insert_roundtrip_keeps_decimal_price_and_time(self, repo, stocks):
        saved = repo.insert_trade(_buy(stocks[0].id, date(2026, 3, 2), price="12.3456", at=time(10, 15)))

        loaded = repo.get_trade_by_id(saved.id)
        assert loaded.price == D("12.3456") and loaded.trade_time == time(10, 15) and loaded.side == TradeSide.BUY
        assert loaded.total_amount == D("123.456")
        assert repo.get_trade_by_id(999) is None

    def test_queries_by_stock_date_range_and_first_date(self, repo, stocks):
        a, b = stocks[0].id, stocks[1].id
        repo.insert_trades_bulk([
            _buy(a, date(2026, 3, 2)), _buy(b, date(2026, 3, 5)), _buy(a, date(2026, 3, 9)),
        ])
        repo.insert_trades_bulk([])  # boş liste sessizce geçilir

        assert [t.trade_date for t in repo.get_trades_by_stock(a)] == [date(2026, 3, 2), date(2026, 3, 9)]
        assert [t.stock_id for t in repo.get_trades_by_date_range(date(2026, 3, 3), date(2026, 3, 9))] == [b, a]
        assert sorted(repo.get_all_stock_ids_in_portfolio()) == sorted({a, b})
        assert repo.get_first_trade_date() == date(2026, 3, 2)
        assert len(repo.get_all_trades()) == 3

    def test_update_changes_fields_and_unknown_id_is_rejected(self, repo, stocks):
        saved = repo.insert_trade(_buy(stocks[0].id, date(2026, 3, 2)))
        updated = Trade(
            id=saved.id, stock_id=stocks[1].id, trade_date=date(2026, 3, 3), trade_time=time(11, 0),
            side=TradeSide.SELL, quantity=5, price=D("110"),
        )

        repo.update_trade(updated)

        loaded = repo.get_trade_by_id(saved.id)
        assert (loaded.stock_id, loaded.side, loaded.quantity, loaded.price) == (stocks[1].id, TradeSide.SELL, 5, D("110"))
        with pytest.raises(ValueError):
            repo.update_trade(Trade(id=None, stock_id=1, trade_date=date(2026, 3, 3), trade_time=None,
                                    side=TradeSide.BUY, quantity=1, price=D("1")))
        with pytest.raises(ValueError, match="bulunamadı"):
            repo.update_trade(Trade(id=999, stock_id=stocks[0].id, trade_date=date(2026, 3, 3), trade_time=None,
                                    side=TradeSide.BUY, quantity=1, price=D("1")))

    def test_delete_one_and_all(self, repo, stocks):
        first = repo.insert_trade(_buy(stocks[0].id, date(2026, 3, 2)))
        repo.insert_trade(_buy(stocks[1].id, date(2026, 3, 3)))

        repo.delete_trade(first.id)
        repo.delete_trade(999)  # olmayan işlem hata vermez
        assert [t.stock_id for t in repo.get_all_trades()] == [stocks[1].id]

        repo.delete_all_trades()
        assert repo.get_all_trades() == [] and repo.get_first_trade_date() is None
