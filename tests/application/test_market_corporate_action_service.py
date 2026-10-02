"""DuckDB piyasa geçmişi için veri güdümlü sermaye artırımı tespiti, onayı ve düzeltilmiş okuma."""
from datetime import date, timedelta

import duckdb
import pytest

from src.application.services.corporate_actions.market_action_service import (
    MarketCorporateActionService,
    classify_break,
)
from src.domain.models.market_corporate_action import (
    MarketActionSource,
    MarketActionStatus,
    MarketActionType,
    MarketCorporateAction,
    PriceBreak,
    bedelli_factor,
    bedelsiz_factor,
    cumulative_factor,
)
from src.infrastructure.market_data.duckdb_corporate_action_store import DuckDBCorporateActionStore
from src.infrastructure.market_data.duckdb_market_history_repo import DuckDBMarketHistoryRepository

START = date(2026, 1, 5)  # pazartesi
DAYS = [START + timedelta(days=i) for i in range(40) if (START + timedelta(days=i)).weekday() < 5]
SPLIT_DAY = DAYS[10]
SPIKE_DAY = DAYS[15]


@pytest.fixture
def duck_file(tmp_path):
    path = tmp_path / "market.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE bist_stocks (ticker VARCHAR PRIMARY KEY, name VARCHAR)")
    con.execute(
        "CREATE TABLE daily_prices (ticker VARCHAR, price_date DATE, open_price DOUBLE, high_price DOUBLE, "
        "low_price DOUBLE, close_price DOUBLE, volume BIGINT, PRIMARY KEY (ticker, price_date))"
    )
    rows = []
    for index, day in enumerate(DAYS):
        split = 20.0 if day < SPLIT_DAY else 10.0  # %100 bedelsiz benzeri kırılma
        spike = 40.0 if day == SPIKE_DAY else 8.0  # tek barlık veri hatası
        for ticker, price in (("SPLT", split), ("FLAT", 5.0), ("SPKE", spike)):
            rows.append((ticker, day, price, price * 1.02, price * 0.98, price, 1000 + index))
    con.executemany("INSERT INTO daily_prices VALUES (?, ?, ?, ?, ?, ?, ?)", rows)
    for ticker in ("SPLT", "FLAT", "SPKE"):
        con.execute("INSERT INTO bist_stocks VALUES (?, ?)", [ticker, ticker])
    con.close()
    return path


@pytest.fixture
def service(duck_file):
    return MarketCorporateActionService(DuckDBMarketHistoryRepository(duck_file), DuckDBCorporateActionStore(duck_file))


def test_factor_formulas_match_portfolio_flow():
    assert bedelsiz_factor(1.0) == pytest.approx(0.5)
    assert bedelsiz_factor(6.3839) == pytest.approx(0.13544, rel=1e-3)  # MERKO
    assert bedelli_factor(0.5, 10.0, 30.0) == pytest.approx((30 + 0.5 * 10) / (1.5 * 30))
    with pytest.raises(ValueError):
        bedelsiz_factor(0)


def test_cumulative_factor_uses_only_confirmed_later_actions():
    def action(day, factor, status):
        return MarketCorporateAction("X", day, factor, status=status)

    actions = [
        action(date(2026, 3, 1), 0.5, MarketActionStatus.CONFIRMED),
        action(date(2026, 6, 1), 0.8, MarketActionStatus.CONFIRMED),
        action(date(2026, 9, 1), 0.1, MarketActionStatus.CANDIDATE),
        action(date(2026, 4, 1), 0.1, MarketActionStatus.NO_BREAK),
    ]
    assert cumulative_factor(actions, date(2026, 2, 1)) == pytest.approx(0.4)
    assert cumulative_factor(actions, date(2026, 3, 1)) == pytest.approx(0.8)  # etkin gün yeni bazdadır
    assert cumulative_factor(actions, date(2026, 7, 1)) == 1.0


def test_scan_finds_split_and_ignores_single_bar_glitch(service):
    result = service.scan(min_date=date(2026, 1, 1))

    assert [(c.ticker, c.effective_date) for c in result.new_candidates] == [("SPLT", SPLIT_DAY)]
    candidate = result.new_candidates[0]
    assert candidate.factor == pytest.approx(0.5)
    assert candidate.status == MarketActionStatus.CANDIDATE
    assert candidate.source == MarketActionSource.DETECTED
    assert candidate.observed_ratio == pytest.approx(2.0)
    assert result.glitches == 2  # sıçrama girişi ve çıkışı


def test_candidate_does_not_change_prices_until_confirmed_and_raw_is_never_modified(service, duck_file):
    service.scan(min_date=date(2026, 1, 1))
    repo = DuckDBMarketHistoryRepository(duck_file)
    before = [b.close_price for b in repo.get_price_series("SPLT", DAYS[0], DAYS[-1])]
    assert before[0] == 20.0

    service.confirm("SPLT", SPLIT_DAY)

    adjusted = repo.get_price_series("SPLT", DAYS[0], DAYS[-1])
    raw = repo.get_price_series("SPLT", DAYS[0], DAYS[-1], adjusted=False)
    assert {b.close_price for b in adjusted} == {10.0}  # tüm seri yeni bazda
    assert raw[0].close_price == 20.0 and raw[-1].close_price == 10.0
    assert adjusted[0].high_price == pytest.approx(20.0 * 1.02 * 0.5) and adjusted[0].volume == raw[0].volume
    bulk = repo.get_price_series_bulk(["SPLT", "FLAT"], DAYS[0], DAYS[-1])
    assert {b.close_price for b in bulk["SPLT"]} == {10.0} and {b.close_price for b in bulk["FLAT"]} == {5.0}
    assert repo.get_last_bars("SPLT", 1)[0].close_price == 10.0


def test_rescan_skips_known_events_and_ignored_ones_stay_ignored(service):
    service.scan(min_date=date(2026, 1, 1))
    service.ignore("SPLT", SPLIT_DAY)

    again = service.scan(min_date=date(2026, 1, 1))

    assert again.new_candidates == [] and again.already_known == 1
    assert service._actions.list_actions(ticker="SPLT")[0].status == MarketActionStatus.IGNORED


def test_confirm_allows_factor_override(service):
    service.scan(min_date=date(2026, 1, 1))

    updated = service.confirm("SPLT", SPLIT_DAY, factor=0.49)

    assert updated.factor == 0.49 and updated.status == MarketActionStatus.CONFIRMED
    with pytest.raises(ValueError):
        service.confirm("YOKTUR", SPLIT_DAY)


def test_register_marks_no_break_when_raw_series_already_adjusted(service, duck_file):
    flat_day = DAYS[20]
    action = MarketCorporateAction(
        "FLAT", flat_day, 0.5, action_type=MarketActionType.BEDELSIZ, status=MarketActionStatus.CONFIRMED,
        source=MarketActionSource.PORTFOLIO,
    )

    stored = service.register(action)

    assert stored.status == MarketActionStatus.NO_BREAK
    repo = DuckDBMarketHistoryRepository(duck_file)
    assert {b.close_price for b in repo.get_price_series("FLAT", DAYS[0], DAYS[-1])} == {5.0}  # çift düzeltme yok


def test_register_keeps_confirmed_when_break_is_present(service):
    action = MarketCorporateAction(
        "SPLT", SPLIT_DAY, 0.5, action_type=MarketActionType.BEDELSIZ, status=MarketActionStatus.CONFIRMED,
        source=MarketActionSource.KAP, ex_date=SPLIT_DAY, ratio=1.0,
    )

    stored = service.register(action)

    assert stored.status == MarketActionStatus.CONFIRMED and stored.ratio == 1.0 and stored.ex_date == SPLIT_DAY


def test_classify_break_removes_market_wide_move():
    brk = PriceBreak("ABC", date(2026, 3, 3), date(2026, 3, 2), prev_close=30.0, close=14.0, volume=10,
                     prev_volume=10, next_closes=(14.2, 14.5, 14.1), market_ratio=1.05)

    candidate = classify_break(brk)

    assert candidate.factor == pytest.approx(14.0 / 30.0 * 1.05)
    assert candidate.confidence == pytest.approx(0.9)


def test_reverse_split_candidate_has_factor_above_one():
    brk = PriceBreak("ABC", date(2026, 3, 3), date(2026, 3, 2), prev_close=2.0, close=20.0, volume=10,
                     prev_volume=10, next_closes=(20.5, 19.8, 21.0))

    candidate = classify_break(brk)

    assert candidate.action_type == MarketActionType.REVERSE_SPLIT and candidate.factor == pytest.approx(10.0)


def test_readers_work_without_corporate_action_table(tmp_path):
    path = tmp_path / "bos.duckdb"
    con = duckdb.connect(str(path))
    con.execute("CREATE TABLE bist_stocks (ticker VARCHAR PRIMARY KEY, name VARCHAR)")
    con.execute(
        "CREATE TABLE daily_prices (ticker VARCHAR, price_date DATE, open_price DOUBLE, high_price DOUBLE, "
        "low_price DOUBLE, close_price DOUBLE, volume BIGINT, PRIMARY KEY (ticker, price_date))"
    )
    con.execute("INSERT INTO daily_prices VALUES ('A', '2026-03-02', 1, 1, 1, 1, 1)")
    con.close()

    repo = DuckDBMarketHistoryRepository(path)

    assert [b.close_price for b in repo.get_price_series("A", date(2026, 3, 1), date(2026, 3, 31))] == [1.0]
    assert DuckDBCorporateActionStore(path).list_actions() == []


def _portfolio_action(ex_date, factor, stock_id=1):
    from decimal import Decimal

    from src.domain.models.corporate_action import ActionType, CorporateAction

    return CorporateAction(
        id=1, stock_id=stock_id, action_type=ActionType.BEDELSIZ, ex_date=ex_date, ratio=Decimal("1"),
        subscription_price=None, announcement_date=None, notes=None, applied=True, prices_adjusted=True,
        price_adjustment_factor=Decimal(str(factor)), price_adjustment_count=5,
    )


def test_portfolio_action_is_imported_with_effective_date_found_from_raw_data(service, duck_file):
    # KAP ex-date kırılmadan 2 gün sonra kayıtlı (MERKO'da olduğu gibi): etkin gün veriden bulunur
    stored = service.register_portfolio_action("SPLT.IS", _portfolio_action(SPLIT_DAY + timedelta(days=2), 0.5))

    assert stored.effective_date == SPLIT_DAY and stored.status == MarketActionStatus.CONFIRMED
    assert stored.source == MarketActionSource.PORTFOLIO and stored.ex_date == SPLIT_DAY + timedelta(days=2)
    repo = DuckDBMarketHistoryRepository(duck_file)
    assert {b.close_price for b in repo.get_price_series("SPLT", DAYS[0], DAYS[-1])} == {10.0}


def test_portfolio_action_without_break_in_raw_data_does_not_adjust(service, duck_file):
    stored = service.register_portfolio_action("FLAT", _portfolio_action(DAYS[20], 0.5))

    assert stored.status == MarketActionStatus.NO_BREAK
    repo = DuckDBMarketHistoryRepository(duck_file)
    assert {b.close_price for b in repo.get_price_series("FLAT", DAYS[0], DAYS[-1])} == {5.0}


def test_sync_service_refresh_imports_portfolio_actions_and_is_safe_without_service(duck_file):
    from types import SimpleNamespace

    from src.application.services.market_data.market_data_sync_service import MarketDataSyncService

    store = DuckDBCorporateActionStore(duck_file)
    market = MarketCorporateActionService(DuckDBMarketHistoryRepository(duck_file), store)
    stock_repo = SimpleNamespace(get_all_stocks=lambda: [SimpleNamespace(id=1, ticker="SPLT.IS")])
    action_repo = SimpleNamespace(get_all=lambda: [_portfolio_action(SPLIT_DAY, 0.5)])

    MarketDataSyncService(str(duck_file)).refresh_corporate_actions()  # servis yok: sessizce çıkar
    assert store.list_actions() == []

    MarketDataSyncService(
        str(duck_file), stock_repo=stock_repo, market_action_service=market, portfolio_action_repo=action_repo
    ).refresh_corporate_actions()

    assert [(a.ticker, a.status) for a in store.list_actions()] == [("SPLT", MarketActionStatus.CONFIRMED)]
