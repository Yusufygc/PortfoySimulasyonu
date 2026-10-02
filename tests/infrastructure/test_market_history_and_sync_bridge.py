"""DuckDB piyasa geçmişi okuyucusu, DCA fallback'i ve DuckDB -> SQLite fiyat köprüsü."""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import duckdb
import pandas as pd
import pytest

from src.application.services.market_data.market_data_sync_service import MarketDataSyncService
from src.application.services.simulation.dca_backtest_service import DCABacktestService
from src.infrastructure.db.db_config import SQLiteConfig
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMStock
from src.infrastructure.db.sqlalchemy.repositories.sa_price_repository import SQLAlchemyPriceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_stock_repository import SQLAlchemyStockRepository
from src.infrastructure.market_data.duckdb_market_history_repo import DuckDBMarketHistoryRepository


@pytest.fixture
def duck_file(tmp_path):
    path = tmp_path / "market.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE bist_stocks (ticker VARCHAR PRIMARY KEY, name VARCHAR)")
    con.execute(
        "CREATE TABLE daily_prices (ticker VARCHAR, price_date DATE, open_price DOUBLE, high_price DOUBLE, "
        "low_price DOUBLE, close_price DOUBLE, volume BIGINT, PRIMARY KEY (ticker, price_date))"
    )
    con.execute("INSERT INTO bist_stocks VALUES ('ASELS', 'Aselsan')")
    con.execute(
        "INSERT INTO daily_prices VALUES "
        "('ASELS', '2026-03-02', 10, 11, 9, 10.5, 1000), "
        "('ASELS', '2026-03-03', 10.5, 12, 10, 11.0, 2000), "
        "('ASELS', '2026-03-04', NULL, NULL, NULL, NULL, NULL)"
    )
    con.close()
    return path


def test_market_history_reads_series_and_last_bars(duck_file):
    repo = DuckDBMarketHistoryRepository(duck_file)

    assert repo.is_available() and repo.has_ticker("asels.is") and not repo.has_ticker("YOKTUR")
    assert repo.get_company_name("ASELS.IS") == "Aselsan"

    bars = repo.get_price_series("ASELS.IS", date(2026, 3, 1), date(2026, 3, 31))
    assert [b.close_price for b in bars] == [10.5, 11.0]  # NULL kapanışlı bar elenir
    assert bars[0].open_price == 10 and bars[1].volume == 2000

    last = repo.get_last_bars("ASELS", 2)
    assert [b.price_date for b in last] == [date(2026, 3, 3), date(2026, 3, 2)]


def test_market_history_is_safe_when_file_missing_or_table_absent(tmp_path):
    missing = DuckDBMarketHistoryRepository(tmp_path / "yok.duckdb")
    assert not missing.is_available()
    assert missing.get_price_series("ASELS", date(2026, 1, 1), date(2026, 2, 1)) == []
    assert missing.get_last_bars("ASELS") == [] and not missing.has_ticker("ASELS")

    empty = tmp_path / "bos.duckdb"
    duckdb.connect(str(empty)).close()
    assert DuckDBMarketHistoryRepository(empty).get_last_bars("ASELS") == []


def test_dca_uses_market_history_for_tickers_outside_portfolio(duck_file):
    class NoStocks:
        def get_stock_by_ticker(self, ticker):
            return None

    class NoPrices:
        def get_price_series(self, *args):
            return []

    service = DCABacktestService(NoPrices(), NoStocks(), market_history_repo=DuckDBMarketHistoryRepository(duck_file))

    series = service._build_price_series(["ASELS"], date(2026, 3, 1), date(2026, 3, 31))

    assert series == {date(2026, 3, 2): {"ASELS": Decimal("10.5")}, date(2026, 3, 3): {"ASELS": Decimal("11.0")}}


@pytest.fixture
def sqlite_repos(tmp_path):
    provider = SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(tmp_path / "p.db")))
    with provider.get_session() as session:
        session.add(ORMStock(id=1, ticker="ASELS.IS", name="Aselsan"))
        session.add(ORMStock(id=2, ticker="THYAO", name="THY"))
        session.commit()
    return SQLAlchemyPriceRepository(provider), SQLAlchemyStockRepository(provider)


def _delta_frame():
    return pd.DataFrame([
        {"ticker": "ASELS", "price_date": date(2026, 3, 5), "open_price": 11.0, "high_price": 12.0,
         "low_price": 10.5, "close_price": 11.5, "volume": 5000},
        {"ticker": "THYAO", "price_date": date(2026, 3, 5), "open_price": float("nan"), "high_price": float("nan"),
         "low_price": float("nan"), "close_price": 300.0, "volume": 0},
        {"ticker": "YOKHISSE", "price_date": date(2026, 3, 5), "open_price": 1.0, "high_price": 1.0,
         "low_price": 1.0, "close_price": 1.0, "volume": 1},
    ])


def test_sync_bridge_writes_new_bars_into_sqlite_via_repositories(tmp_path, sqlite_repos):
    """Eski ham sqlite3 köprüsü 'NOT NULL constraint failed: daily_prices.id' ile sessizce başarısız oluyordu."""
    price_repo, stock_repo = sqlite_repos
    service = MarketDataSyncService(duckdb_path=str(tmp_path / "x.duckdb"), price_repo=price_repo, stock_repo=stock_repo)

    assert service._sync_to_sqlite(_delta_frame()) == 2  # portföyde olmayan hisse atlanır

    asels = price_repo.get_price_series(1, date(2026, 3, 1), date(2026, 3, 31))
    assert [p.close_price for p in asels] == [Decimal("11.5")] and asels[0].high_price == Decimal("12.0")
    thyao = price_repo.get_price_series(2, date(2026, 3, 1), date(2026, 3, 31))
    assert thyao[0].open_price is None  # NaN -> None

    # tekrar çalıştırma idempotent: aynı gün güncellenir, çoğalmaz
    service._sync_to_sqlite(_delta_frame())
    assert len(price_repo.get_price_series(1, date(2026, 3, 1), date(2026, 3, 31))) == 1


def test_sync_bridge_is_noop_without_repositories(tmp_path):
    service = MarketDataSyncService(duckdb_path=str(tmp_path / "x.duckdb"))
    assert service._sync_to_sqlite(_delta_frame()) == 0


def test_container_exposes_single_duckdb_reader_and_sync_service():
    from src.application.container import AppContainer

    container = AppContainer()
    assert isinstance(container.market_history_repo, DuckDBMarketHistoryRepository)
    assert container.market_data_sync_service._price_repo is container.price_repo
    assert not hasattr(container, "duckdb_price_repo")


def test_reconcile_copies_only_newer_bars_and_never_overwrites_history(tmp_path, sqlite_repos):
    from src.domain.models.daily_price import DailyPrice

    price_repo, stock_repo = sqlite_repos
    # SQLite'ta (düzeltilmiş) geçmiş: 2 Mart
    price_repo.upsert_daily_prices_bulk([DailyPrice(None, 1, date(2026, 3, 2), Decimal("5.00"))])

    duck = tmp_path / "m.duckdb"
    con = duckdb.connect(str(duck))
    con.execute("CREATE TABLE bist_stocks (ticker VARCHAR PRIMARY KEY, last_date DATE)")
    con.execute(
        "CREATE TABLE daily_prices (ticker VARCHAR, price_date DATE, open_price DOUBLE, high_price DOUBLE, "
        "low_price DOUBLE, close_price DOUBLE, volume BIGINT, PRIMARY KEY (ticker, price_date))"
    )
    con.execute(
        "INSERT INTO daily_prices VALUES "
        "('ASELS', '2026-03-02', 9, 9, 9, 10.0, 1), "   # ham (düzeltilmemiş) eski bar: ezilmemeli
        "('ASELS', '2026-03-03', 10, 11, 10, 10.5, 2), ('ASELS', '2026-03-04', 10, 12, 10, 11.0, 3), "
        "('THYAO', '2026-03-03', 300, 301, 299, 300.5, 4), "
        "('VAKFN', '2026-03-03', 1, 1, 1, 1.0, 5)"      # portföyde yok
    )
    con.close()
    service = MarketDataSyncService(duckdb_path=str(duck), price_repo=price_repo, stock_repo=stock_repo)

    assert service.reconcile_sqlite_from_duckdb() == 3

    asels = {p.price_date: p.close_price for p in price_repo.get_price_series(1, date(2026, 3, 1), date(2026, 3, 31))}
    assert asels == {date(2026, 3, 2): Decimal("5.00"), date(2026, 3, 3): Decimal("10.5"), date(2026, 3, 4): Decimal("11.0")}
    assert len(price_repo.get_price_series(2, date(2026, 3, 1), date(2026, 3, 31))) == 1
    assert service.reconcile_sqlite_from_duckdb() == 0  # tekrar: yeni bar yok


def test_market_history_bulk_catalog_and_latest_dates(duck_file):
    con = duckdb.connect(str(duck_file))
    con.execute("INSERT INTO bist_stocks VALUES ('THYAO', 'THY')")
    con.execute("INSERT INTO daily_prices VALUES ('THYAO', '2026-03-02', 1, 2, 1, 1.5, 10)")
    con.close()
    repo = DuckDBMarketHistoryRepository(duck_file)

    assert repo.list_tickers() == ["ASELS", "THYAO"]
    bulk = repo.get_price_series_bulk(["asels.is", "THYAO", "YOKTUR"], date(2026, 3, 1), date(2026, 3, 31))
    assert set(bulk) == {"ASELS", "THYAO"}
    assert [b.close_price for b in bulk["ASELS"]] == [10.5, 11.0]  # NULL kapanışlı bar elenir
    assert repo.get_latest_dates() == {"ASELS": date(2026, 3, 3), "THYAO": date(2026, 3, 2)}
    assert repo.get_price_series_bulk([], date(2026, 3, 1), date(2026, 3, 31)) == {}


def test_sync_finds_partial_invalid_bars_for_repair(duck_file):
    service = MarketDataSyncService(duckdb_path=str(duck_file))

    assert service._find_invalid_bar_start(date(2026, 3, 10)) == date(2026, 3, 4)
    assert service._find_invalid_bar_start(date(2026, 1, 1)) is None  # pencere dışı


def test_bulk_downloader_drops_nan_and_zero_close_rows():
    from src.application.services.market_data.bist_bulk_downloader import BistBulkDownloader

    hist = pd.DataFrame(
        {
            "Open": [1.0, 2.0, 3.0],
            "High": [1.0, 2.0, 3.0],
            "Low": [1.0, 2.0, 3.0],
            "Close": [1.0, float("nan"), 0.0],
            "Volume": [10, None, 5],
        },
        index=pd.to_datetime(["2026-03-02", "2026-03-03", "2026-03-04"]).rename("Date"),
    )

    frame = BistBulkDownloader.normalize_history_frame("ASELS", hist)

    assert list(frame["close_price"]) == [1.0]
    assert BistBulkDownloader.normalize_history_frame("ASELS", hist.iloc[1:]) is None


def test_dca_prefers_market_history_over_sqlite(duck_file):
    class Stock:
        id = 1

    class Stocks:
        def get_stock_by_ticker(self, ticker):
            return Stock()

    class Prices:
        def get_price_series(self, *args):  # SQLite'ta farklı (eski) fiyat var
            return [SimpleNamespace(price_date=date(2026, 3, 2), close_price=Decimal("999"))]

    service = DCABacktestService(Prices(), Stocks(), market_history_repo=DuckDBMarketHistoryRepository(duck_file))

    series = service._build_price_series(["ASELS"], date(2026, 3, 1), date(2026, 3, 31))

    assert series[date(2026, 3, 2)] == {"ASELS": Decimal("10.5")}
    # DuckDB'de olmayan hisse SQLite'a düşer
    fallback = service._build_price_series(["YOKTUR"], date(2026, 3, 1), date(2026, 3, 31))
    assert fallback == {date(2026, 3, 2): {"YOKTUR": Decimal("999")}}


def test_stock_360_reads_overview_and_name_from_market_history(duck_file):
    from unittest.mock import MagicMock

    from src.application.services.analysis.stock_360_service import Stock360Service

    stock_repo = MagicMock()
    stock_repo.get_stock_by_ticker.return_value = None
    service = Stock360Service(MagicMock(), stock_repo, MagicMock(), MagicMock(),
                              market_history_repo=DuckDBMarketHistoryRepository(duck_file))

    overview = service.get_overview("asels.is", today=date(2026, 3, 10))

    assert overview.last_price == Decimal("11.0") and overview.last_price_date == date(2026, 3, 3)
    assert round(overview.daily_change_pct, 2) == round((11.0 - 10.5) / 10.5 * 100, 2)
    assert service.get_company_name("ASELS") == "Aselsan"
