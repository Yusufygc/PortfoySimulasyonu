from datetime import date
from decimal import Decimal as D
from types import SimpleNamespace as NS

import pytest

from src.application.services.corporate_actions.split_automation_service import (
    AUTO_APPLY_SETTING,
    SplitAutomationDeps,
    SplitAutomationService,
)
from src.domain.models.asset import AssetClass
from src.domain.models.corporate_action import ActionType
from src.domain.models.split_event import SplitEventStatus
from src.domain.models.split_signal import SplitSignal, SplitSource
from src.domain.ports.services.i_split_signal_provider import ISplitSignalProvider

EX = date(2026, 8, 21)


class FakeSignals(ISplitSignalProvider):
    def __init__(self, signals):
        self.signals, self.targets = signals, None

    def fetch_signals(self, targets, since):
        self.targets = list(targets)
        return self.signals


class FakeApplier:
    def __init__(self, fail=False):
        self.fail, self.applied = fail, []

    def apply(self, decision, target, auto_applied):
        if self.fail:
            raise ValueError("çakışma")
        self.applied.append((decision.ticker, decision.multiplier, target, auto_applied))
        return NS(ticker=decision.ticker, multiplier=decision.multiplier)


class FakeSettings:
    def __init__(self, value=None):
        self.values = {} if value is None else {AUTO_APPLY_SETTING: value}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value):
        self.values[key] = value


class FakeCandidates:
    def __init__(self):
        self.saved = []

    def upsert_discovered(self, candidates):
        self.saved.extend(candidates)
        return candidates


def _service(signals, **options):
    """options: applier, settings, applied_actions, events, assets."""
    stocks = [NS(id=79, ticker="SDTTR"), NS(id=41, ticker="OBAMS")]
    deps = SplitAutomationDeps(
        signal_source=FakeSignals(signals),
        applier=options.get("applier") or FakeApplier(),
        ledger_repo=NS(list_events=lambda: list(options.get("events", ()))),
        stock_repo=NS(get_all_stocks=lambda: stocks,
                      get_ticker_map_for_stock_ids=lambda ids: {s.id: s.ticker for s in stocks if s.id in ids}),
        corporate_action_repo=NS(get_all=lambda: list(options.get("applied_actions", ()))),
        candidate_repo=FakeCandidates(),
        settings_repo=options.get("settings"),
        portfolio_repo=NS(get_all_stock_ids_in_portfolio=lambda: [41]),
        model_portfolio_repo=NS(get_all_model_portfolios=lambda: [NS(id=9)],
                                get_trades_by_portfolio_id=lambda pid: [NS(stock_id=79)]),
        asset_repo=NS(list_assets=lambda active_only=True: list(options.get("assets", ()))),
    )
    return SplitAutomationService(deps), deps


def _two_source(ticker="SDTTR"):
    return [SplitSignal(ticker, EX, D("11"), SplitSource.PRICE_BREAK),
            SplitSignal(ticker, date(2026, 8, 27), D("11"), SplitSource.YAHOO)]


def test_two_source_split_is_applied_automatically():
    service, deps = _service(_two_source())
    result = service.run(since=date(2026, 1, 1))
    assert [(t, m, target.stock_id, auto) for t, m, target, auto in deps.applier.applied] == [("SDTTR", D("11"), 79, True)]
    assert result.summary == "SDTTR 11:1" and result.candidates == []
    assert {t.key for t in deps.signal_source.targets} == {"SDTTR", "OBAMS"}


def test_single_source_becomes_candidate():
    service, deps = _service([SplitSignal("OBAMS", date(2025, 12, 1), D("6"), SplitSource.YAHOO)])
    result = service.run(since=date(2025, 1, 1))
    assert deps.applier.applied == [] and len(result.candidates) == 1
    [candidate] = deps.candidate_repo.saved
    assert (candidate.ticker, candidate.ratio, candidate.ex_date, candidate.action_type, candidate.source) == (
        "OBAMS", D("5"), date(2025, 12, 1), ActionType.BEDELSIZ, "SPLIT_AUTO")
    assert candidate.stock_id == 41


def test_auto_apply_off_keeps_everything_as_candidate():
    service, deps = _service(_two_source(), settings=FakeSettings("0"))
    assert not service.auto_apply_enabled()
    result = service.run(since=date(2026, 1, 1))
    assert deps.applier.applied == [] and len(result.candidates) == 1


def test_setting_round_trip():
    settings = FakeSettings()
    service, _ = _service([], settings=settings)
    assert service.auto_apply_enabled()
    service.set_auto_apply(False)
    assert settings.values[AUTO_APPLY_SETTING] == "0" and not service.auto_apply_enabled()


def test_apply_failure_falls_back_to_candidate_with_error():
    service, deps = _service(_two_source(), applier=FakeApplier(fail=True))
    result = service.run(since=date(2026, 1, 1))
    assert len(result.candidates) == 1 and result.errors == ["SDTTR 21.08.2026: çakışma"]
    assert len(deps.candidate_repo.saved) == 1


def test_applied_corporate_action_or_split_event_is_skipped():
    action = NS(applied=True, action_type=ActionType.BEDELSIZ, stock_id=79, ex_date=EX, ratio=D("10"))
    service, deps = _service(_two_source(), applied_actions=[action])
    assert service.run(since=date(2026, 1, 1)).already_applied == 1
    event = NS(ticker="SDTTR", ex_date=EX, multiplier=D("11"), status=SplitEventStatus.APPLIED)
    service, deps = _service(_two_source(), events=[event])
    assert service.run(since=date(2026, 1, 1)).already_applied == 1 and deps.applier.applied == []


def test_us_stock_assets_are_scanned():
    aapl = NS(id=3, symbol="aapl", yf_symbol="AAPL", asset_class=AssetClass.US_STOCK)
    btc = NS(id=4, symbol="BTC", yf_symbol="BTC-USD", asset_class=AssetClass.CRYPTO)
    signals = [SplitSignal("AAPL", EX, D("4"), SplitSource.YAHOO)]
    service, deps = _service(signals, assets=[aapl, btc])
    result = service.run(since=date(2026, 1, 1))
    targets = {t.key: t for t in deps.signal_source.targets}
    assert targets["AAPL"].asset_id == 3 and "BTC" not in targets
    assert len(result.candidates) == 1 and deps.candidate_repo.saved == []  # varlık adayı yalnızca raporlanır
