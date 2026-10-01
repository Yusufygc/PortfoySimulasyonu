from datetime import date
from decimal import Decimal
import os
import pytest

from src.domain.models.daily_price import DailyPrice
from src.infrastructure.repositories.duckdb_price_repo import DuckDBPriceRepository


@pytest.fixture
def temp_duckdb(tmp_path):
    db_file = str(tmp_path / "test_market.duckdb")
    repo = DuckDBPriceRepository(db_path=db_file)
    return repo


def test_duckdb_price_repo_crud(temp_duckdb):
    repo = temp_duckdb
    sid = 1
    # Mapping
    repo._ticker_by_id[sid] = "THYAO"
    repo._id_by_ticker["THYAO"] = sid

    # Upsert single
    dp = DailyPrice(
        id=None,
        stock_id=sid,
        price_date=date(2026, 1, 15),
        close_price=Decimal("250.50"),
        currency_code="TRY",
        open_price=Decimal("248.00"),
        high_price=Decimal("252.00"),
        low_price=Decimal("247.50"),
        volume=1500000,
    )
    repo.upsert_daily_price(dp)

    # Read back
    read_p = repo.get_price_for_date(sid, date(2026, 1, 15))
    assert read_p is not None
    assert read_p.close_price == Decimal("250.5")
    assert read_p.volume == 1500000

    # Last price before
    last_p = repo.get_last_price_before(sid, date(2026, 1, 20))
    assert last_p is not None
    assert last_p.price_date == date(2026, 1, 15)

    # Series
    series = repo.get_price_series(sid, date(2026, 1, 1), date(2026, 1, 31))
    assert len(series) == 1
    assert series[0].close_price == Decimal("250.5")

    # Native DataFrame query
    df = repo.get_dataframe("THYAO")
    assert len(df) == 1
    assert df.iloc[0]["close"] == 250.50

    # Bulk upsert
    dp2 = DailyPrice(
        id=None,
        stock_id=sid,
        price_date=date(2026, 1, 16),
        close_price=Decimal("255.00"),
        currency_code="TRY",
        volume=2000000,
    )
    repo.upsert_daily_prices_bulk([dp2])
    series2 = repo.get_price_series(sid, date(2026, 1, 1), date(2026, 1, 31))
    assert len(series2) == 2


def test_duckdb_real_data_read():
    """Mevcut aktarılmış veritabanını test eder (varsa)."""
    real_path = "data/market_history.duckdb"
    if not os.path.exists(real_path):
        pytest.skip("data/market_history.duckdb henüz oluşturulmadı")

    repo = DuckDBPriceRepository(db_path=real_path)
    tickers = repo.get_all_tickers()
    assert len(tickers) >= 100
    assert "THYAO" in tickers
    assert "BIMAS" in tickers

    # Doğrudan DataFrame sorgulama testi
    df = repo.get_dataframe("THYAO")
    assert len(df) > 500
    assert "close" in df.columns
