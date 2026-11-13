"""NewsTargetService: portföy + varlık defteri + izleme listesi hedeflerini birleştirir."""
from __future__ import annotations

from types import SimpleNamespace

from src.application.services.news.news_target_service import MAX_TARGETS, NewsTargetService
from src.domain.models.asset import AssetClass
from src.domain.models.news_item import TargetKind


def _service(active=None, stocks=None, assets=(), watchlists=None):
    portfolio = SimpleNamespace(get_current_portfolio=lambda: SimpleNamespace(active_positions=active or {}))
    lookup = SimpleNamespace(get_stocks=lambda ids: {i: stocks[i] for i in ids if i in (stocks or {})})
    ledger = SimpleNamespace(list_assets=lambda active_only=True: list(assets))
    lists = watchlists or {}
    watch = SimpleNamespace(
        get_all_watchlists=lambda: [SimpleNamespace(id=i) for i in lists],
        get_watchlist_stocks=lambda wid: lists[wid],
    )
    return NewsTargetService(portfolio, lookup, ledger, watch)


def _stock(ticker, name):
    return SimpleNamespace(ticker=ticker, name=name)


def _asset(yf_symbol, name, cls):
    return SimpleNamespace(yf_symbol=yf_symbol, name=name, asset_class=cls)


def _entry(ticker, name="x", stock=True):
    return {"ticker": ticker, "name": name, "stock": object() if stock else None}


def test_collects_all_three_sources_with_kinds():
    service = _service(
        active={1: object()}, stocks={1: _stock("THYAO.IS", "Türk Hava Yolları")},
        assets=[_asset("GC=F", "Altın", AssetClass.PRECIOUS_METAL), _asset("BTC-USD", "Bitcoin", AssetClass.CRYPTO),
                _asset("AAPL", "Apple", AssetClass.US_STOCK)],
        watchlists={1: [_entry("ASELS", "Aselsan")]},
    )
    targets = service.get_targets()
    assert [(t.symbol, t.kind) for t in targets] == [
        ("THYAO", TargetKind.BIST), ("GC=F", TargetKind.METAL), ("BTC-USD", TargetKind.CRYPTO),
        ("AAPL", TargetKind.US_STOCK), ("ASELS", TargetKind.BIST),
    ]


def test_duplicate_between_portfolio_and_watchlist_kept_once_portfolio_first():
    service = _service(
        active={1: object()}, stocks={1: _stock("THYAO", "THY")},
        watchlists={1: [_entry("THYAO", "THY izleme"), _entry("GARAN", "Garanti")]},
    )
    targets = service.get_targets()
    assert [t.symbol for t in targets] == ["THYAO", "GARAN"]
    assert targets[0].name == "THY"


def test_unknown_watchlist_stock_skipped_and_limit_applied():
    entries = [_entry(f"T{i:02d}") for i in range(MAX_TARGETS + 10)] + [_entry("YOK", stock=False)]
    targets = _service(watchlists={1: entries}).get_targets()
    assert len(targets) == MAX_TARGETS and "YOK" not in {t.symbol for t in targets}


def test_one_failing_reader_does_not_hide_others():
    service = _service(assets=[_asset("AAPL", "Apple", AssetClass.US_STOCK)])
    service._portfolio = SimpleNamespace(get_current_portfolio=lambda: (_ for _ in ()).throw(RuntimeError("db")))
    assert [t.symbol for t in service.get_targets()] == ["AAPL"]
