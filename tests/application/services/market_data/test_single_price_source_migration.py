from datetime import date, timedelta
from types import SimpleNamespace as NS

from src.application.services.market_data.single_price_source_migration import (
    DONE_SETTING,
    MigrationDeps,
    SinglePriceSourceMigration,
    factor_trace,
)

DAYS = [date(2026, 1, 5) + timedelta(days=i) for i in range(20)]


def test_factor_trace_separates_factor_from_dividend_noise():
    reference = {d: 10.0 for d in DAYS}
    factor = {d: (7.6 if i < 15 else 10.0) for i, d in enumerate(DAYS)}       # %75'i 0,76 farklı
    dividend = {d: (9.9 if i < 15 else 10.0) for i, d in enumerate(DAYS)}     # %1 fark: temettü karışımı
    isolated = {d: (9.0 if i == 3 else 10.0) for i, d in enumerate(DAYS)}    # tek gün sapma
    assert round(factor_trace(factor, reference), 2) == 0.76
    assert factor_trace(dividend, reference) is None
    assert factor_trace(isolated, reference) is None


class FakeSettings(dict):
    def set(self, key, value):
        self[key] = value


def _migration(stored_by_id, imported, settings=None):
    calls = {"import": [], "project": 0}
    stocks = NS(get_all_stocks=lambda: [NS(id=1, ticker="RUZYE.IS"), NS(id=2, ticker="ASELS")])
    prices = NS(get_price_series=lambda sid, s, e: [NS(price_date=d, close_price=v) for d, v in stored_by_id.get(sid, {}).items()])
    history = NS(get_price_series=lambda t, s, e, adjusted=True: [NS(price_date=d, close_price=10.0) for d in DAYS])

    def import_actions(ticker, closes):
        calls["import"].append(ticker)
        return imported.get(ticker, [])

    def project():
        calls["project"] += 1
        return NS(written_count=7)

    migration = SinglePriceSourceMigration(MigrationDeps(
        stock_repo=stocks, price_repo=prices, history_repo=history,
        market_action_service=NS(import_actions_from_adjusted_history=import_actions),
        projection=NS(project=project), settings_repo=settings,
    ))
    return migration, calls


def test_migration_imports_factor_then_projects_once():
    stored = {1: {d: 7.6 for d in DAYS}, 2: {d: 10.0 for d in DAYS}}
    settings = FakeSettings()
    migration, calls = _migration(stored, {"RUZYE": [object()]}, settings)

    report = migration.run_once()

    assert calls["import"] == ["RUZYE"] and report.factor_stocks == ["RUZYE"] and report.unresolved == []
    assert calls["project"] == 1 and report.projected_rows == 7 and settings[DONE_SETTING] == "1"
    assert migration.run_once().skipped and calls["project"] == 1


def test_unverifiable_factor_is_reported_and_duckdb_wins():
    migration, calls = _migration({1: {d: 7.6 for d in DAYS}}, {})
    report = migration.run()
    assert report.unresolved == ["RUZYE"] and calls["project"] == 1
