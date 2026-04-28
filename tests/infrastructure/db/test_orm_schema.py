from src.infrastructure.db.sqlalchemy.orm_models import ORMDailyPrice, ORMStock, ORMWatchlistItem


def constraint_names(model) -> set[str]:
    return {constraint.name for constraint in model.__table__.constraints if constraint.name}


def test_daily_prices_declares_upsert_unique_constraint():
    assert "uq_daily_price" in constraint_names(ORMDailyPrice)


def test_watchlist_items_declares_duplicate_guard_constraint():
    assert "unique_watchlist_stock" in constraint_names(ORMWatchlistItem)


def test_stocks_declares_ticker_unique_constraint():
    assert "uq_stocks_ticker" in constraint_names(ORMStock)
