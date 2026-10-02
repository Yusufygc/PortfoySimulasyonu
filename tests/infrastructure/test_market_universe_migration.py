"""SQLite -> DuckDB piyasa evreni göçü: referanssız hisseleri silme ve düzeltme bilgisini taşıma."""
from datetime import date, timedelta
from decimal import Decimal

import duckdb
import pytest

from src.application.services.corporate_actions.market_action_service import MarketCorporateActionService
from src.application.services.market_data.market_universe_migration_service import MarketUniverseMigrationService
from src.domain.models.market_corporate_action import MarketActionSource, MarketActionStatus
from src.infrastructure.db.db_config import SQLiteConfig
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import (
    ORMDailyPrice,
    ORMStock,
    ORMTrade,
)
from src.infrastructure.db.sqlalchemy.repositories.sa_portfolio_maintenance_repository import (
    SQLAlchemyPortfolioMaintenanceRepository,
)
from src.infrastructure.db.sqlalchemy.repositories.sa_price_repository import SQLAlchemyPriceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_stock_repository import SQLAlchemyStockRepository
from src.infrastructure.market_data.duckdb_corporate_action_store import DuckDBCorporateActionStore
from src.infrastructure.market_data.duckdb_market_history_repo import DuckDBMarketHistoryRepository

DAYS = [d for d in (date(2025, 1, 1) + timedelta(days=i) for i in range(60)) if d.weekday() < 5]
SPLIT_DAY = DAYS[20]


@pytest.fixture
def env(tmp_path):
    provider = SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(tmp_path / "p.db")))
    with provider.get_session() as session:
        for stock_id, ticker in ((1, "HELD.IS"), (2, "SPLT"), (3, "FLAT"), (4, "OLDX")):
            session.add(ORMStock(id=stock_id, ticker=ticker, name=ticker))
        session.flush()
        session.add(ORMTrade(
            id=1, stock_id=1, side="BUY", quantity=1, price=Decimal("5"), original_quantity=1,
            original_price=Decimal("5"), trade_date=DAYS[0],
        ))
        row_id = 0
        for stock_id in (1, 2, 3, 4):
            for day in DAYS:
                row_id += 1
                # SPLT: SQLite düzeltilmiş (bölünme öncesi 10), DuckDB ham (20)
                price = 10 if stock_id == 2 else 5
                session.add(ORMDailyPrice(id=row_id, stock_id=stock_id, price_date=day, close_price=Decimal(price),
                                          currency_code="TRY", source="yfinance"))
        session.commit()

    path = tmp_path / "m.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE bist_stocks (ticker VARCHAR PRIMARY KEY, name VARCHAR)")
    con.execute(
        "CREATE TABLE daily_prices (ticker VARCHAR, price_date DATE, open_price DOUBLE, high_price DOUBLE, "
        "low_price DOUBLE, close_price DOUBLE, volume BIGINT, PRIMARY KEY (ticker, price_date))"
    )
    rows = []
    for ticker in ("HELD", "SPLT", "FLAT"):  # OLDX DuckDB'de yok
        con.execute("INSERT INTO bist_stocks VALUES (?, ?)", [ticker, ticker])
        for day in DAYS:
            price = 5.0
            if ticker == "SPLT":
                price = 20.0 if day < SPLIT_DAY else 10.0
            rows.append((ticker, day, price, price, price, price, 1000))
    con.executemany("INSERT INTO daily_prices VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    con.close()

    history = DuckDBMarketHistoryRepository(path)
    actions = DuckDBCorporateActionStore(path)
    service = MarketUniverseMigrationService(
        stock_repo=SQLAlchemyStockRepository(provider),
        price_repo=SQLAlchemyPriceRepository(provider),
        maintenance_repo=SQLAlchemyPortfolioMaintenanceRepository(provider),
        market_history_repo=history,
        market_action_service=MarketCorporateActionService(history, actions),
    )
    return service, provider, history, actions


def test_plan_separates_referenced_deletable_and_uncovered(env):
    service, *_ = env

    plan = service.plan()

    assert {e.ticker for e in plan.kept_referenced} == {"HELD.IS"}
    assert {e.ticker for e in plan.deletable} == {"SPLT", "FLAT"}
    assert {e.ticker for e in plan.kept_uncovered} == {"OLDX"}  # DuckDB'de yok: veri kaybı olmasın diye silinmez


def test_execute_deletes_unreferenced_keeps_held_and_derives_split(env):
    service, provider, history, actions = env

    result = service.execute(service.plan())

    assert result.deleted_stocks == 2 and result.deleted_prices == 2 * len(DAYS)
    with provider.get_session() as session:
        assert {s.ticker for s in session.query(ORMStock).all()} == {"HELD.IS", "OLDX"}
        assert session.query(ORMDailyPrice).filter_by(stock_id=1).count() == len(DAYS)  # portföy hissesinin fiyatları kalır
    derived = actions.list_actions(ticker="SPLT")
    assert len(derived) == 1 and derived[0].status == MarketActionStatus.CONFIRMED
    assert derived[0].source == MarketActionSource.MIGRATION and derived[0].effective_date == SPLIT_DAY
    assert derived[0].factor == pytest.approx(0.5)
    # düzeltilmiş okuma SQLite'ın düzeltilmiş geçmişiyle aynı bazı verir
    assert {b.close_price for b in history.get_price_series("SPLT", DAYS[0], DAYS[-1])} == {10.0}
    assert actions.list_actions(ticker="FLAT") == []


def test_no_action_derived_when_duckdb_raw_series_is_already_smooth(env):
    service, provider, history, actions = env
    market = service._actions
    # SQLite'ın düzeltilmiş serisinde basamak var ama DuckDB ham serisi sürekli (Yahoo zaten düzeltmiş): SQLite hatalıdır
    broken_sqlite = {day: (5.0 if day < SPLIT_DAY else 55.0) for day in DAYS}

    created = market.import_actions_from_adjusted_history("FLAT", broken_sqlite)

    assert created == [] and actions.list_actions(ticker="FLAT") == []
    assert {b.close_price for b in history.get_price_series("FLAT", DAYS[0], DAYS[-1])} == {5.0}


def test_delete_never_touches_referenced_stock_even_if_requested(env):
    service, provider, *_ = env
    maintenance = SQLAlchemyPortfolioMaintenanceRepository(provider)

    assert maintenance.delete_unreferenced_stocks([1]) == (0, 0)  # 1 numaralı hissenin işlemi var

    with provider.get_session() as session:
        assert session.query(ORMStock).filter_by(id=1).count() == 1
