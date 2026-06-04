from src.infrastructure.db.sqlalchemy.orm_models import (
    ORMCorporateAction,
    ORMCorporateActionCandidate,
    ORMDailyPrice,
    ORMBudgetPinnedItem,
    ORMModelPortfolioCashMovement,
    ORMStock,
    ORMWatchlistItem,
)


def constraint_names(model) -> set[str]:
    return {constraint.name for constraint in model.__table__.constraints if constraint.name}


def test_daily_prices_declares_upsert_unique_constraint():
    assert "uq_daily_price" in constraint_names(ORMDailyPrice)


def test_watchlist_items_declares_duplicate_guard_constraint():
    assert "unique_watchlist_stock" in constraint_names(ORMWatchlistItem)


def test_stocks_declares_ticker_unique_constraint():
    assert "uq_stocks_ticker" in constraint_names(ORMStock)


def test_corporate_actions_track_price_adjustment_state():
    columns = ORMCorporateAction.__table__.columns

    assert "prices_adjusted" in columns
    assert "prices_adjusted_at" in columns
    assert "price_adjustment_factor" in columns
    assert "price_adjustment_count" in columns
    assert columns["ratio"].type.precision == 12
    assert columns["ratio"].type.scale == 8


def test_corporate_action_candidates_declares_duplicate_guard():
    columns = ORMCorporateActionCandidate.__table__.columns

    assert "raw_payload_json" in columns
    assert "uq_corp_action_candidate_source" in constraint_names(ORMCorporateActionCandidate)
    assert columns["ratio"].type.precision == 12
    assert columns["ratio"].type.scale == 8


def test_model_portfolio_cash_movements_schema_declares_timeline_index():
    columns = ORMModelPortfolioCashMovement.__table__.columns
    index_names = {index.name for index in ORMModelPortfolioCashMovement.__table__.indexes}

    assert "portfolio_id" in columns
    assert "movement_date" in columns
    assert "movement_time" in columns
    assert "type" in columns
    assert "amount" in columns
    assert "idx_model_portfolio_cash_movements_portfolio_date" in index_names


def test_budget_pinned_items_declares_duplicate_guard():
    columns = ORMBudgetPinnedItem.__table__.columns

    assert "item_type" in columns
    assert "name" in columns
    assert "default_amount" in columns
    assert "uq_budget_pinned_item_type_name" in constraint_names(ORMBudgetPinnedItem)
