"""SplitApplier: gerçek SQLite repository'leriyle defter + fiyat geçmişi + kurumsal aksiyon kaydı."""
from datetime import date, time, timedelta
from decimal import Decimal as D
from types import SimpleNamespace as NS

import pytest

from src.application.services.corporate_actions.split_applier import SplitApplier, SplitApplierDeps
from src.domain.models.daily_price import DailyPrice
from src.domain.models.market_corporate_action import MarketActionStatus
from src.domain.models.split_event import SplitEventStatus, SplitLedger
from src.domain.models.split_signal import SplitDecision, SplitDecisionKind
from src.domain.ports.services.i_split_signal_provider import SplitTarget
from src.infrastructure.db.db_config import SQLiteConfig
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import (
    ORMCashMovement,
    ORMModelPortfolio,
    ORMModelPortfolioTrade,
    ORMStock,
    ORMTrade,
    TradeSideEnum,
)
from src.infrastructure.db.sqlalchemy.repositories.sa_corporate_action_repository import (
    SQLAlchemyCorporateActionRepository,
)
from src.infrastructure.db.sqlalchemy.repositories.sa_price_repository import SQLAlchemyPriceRepository
from src.infrastructure.db.sqlalchemy.repositories.sa_split_ledger_repository import SQLAlchemySplitLedgerRepository

EX = date(2026, 8, 21)
TARGET = SplitTarget("SDTTR", "SDTTR.IS", stock_id=79)


class FakeMarket:
    def __init__(self, status=MarketActionStatus.CONFIRMED):
        self.status, self.registered, self.ignored = status, [], []

    def register_portfolio_action(self, ticker, action):
        self.registered.append((ticker, action.ex_date, action.price_adjustment_factor))
        return NS(status=self.status, effective_date=action.ex_date)

    def set_status(self, ticker, effective_date, status):
        self.ignored.append((ticker, effective_date, status))
        return True


@pytest.fixture
def provider(tmp_path):
    p = SQLAlchemyEngineProvider(SQLiteConfig(db_path=str(tmp_path / "applier.db")))
    with p.get_session() as s:
        s.add(ORMStock(id=79, ticker="SDTTR"))
        s.add(ORMModelPortfolio(id=9, name="Model"))
        s.commit()
    return p


def _prices(provider, before, after):
    days = [EX + timedelta(days=i) for i in range(-6, 6)]
    rows = [DailyPrice(None, 79, d, D(str(before if d < EX else after))) for d in days]
    SQLAlchemyPriceRepository(provider).upsert_daily_prices_bulk(rows)


def _applier(provider, market=None):
    return SplitApplier(SplitApplierDeps(
        SQLAlchemySplitLedgerRepository(provider), SQLAlchemyPriceRepository(provider),
        SQLAlchemyCorporateActionRepository(provider), market,
    ))


def _decision(multiplier="11"):
    return SplitDecision("SDTTR", EX, D(multiplier), SplitDecisionKind.AUTO, signals=())


def _model_trade(provider, qty=65, price="242"):
    with provider.get_session() as s:
        s.add(ORMModelPortfolioTrade(id=34, portfolio_id=9, stock_id=79, trade_date=date(2026, 8, 7),
                                     trade_time=time(16, 40), side=TradeSideEnum.BUY, quantity=qty, price=D(price)))
        s.commit()


def _close(provider, day):
    return SQLAlchemyPriceRepository(provider).get_price_for_date(79, day).close_price


def test_sdttr_model_trade_and_unadjusted_prices_are_fixed(provider):
    _model_trade(provider)
    _prices(provider, before="253", after="23.9")
    market = FakeMarket()

    event = _applier(provider, market).apply(_decision(), TARGET, auto_applied=True)

    with provider.get_session() as s:
        trade = s.get(ORMModelPortfolioTrade, 34)
        assert (trade.quantity, trade.price) == (715, D("22.0000"))
    assert event.status == SplitEventStatus.APPLIED and event.auto_applied
    assert event.cash_entries == ()                                  # 65 x 11 tam sayı: küsurat yok
    assert event.price_adjusted_before == EX and event.price_adjustment_count == 6
    assert _close(provider, EX - timedelta(days=1)) == D("23")      # 253 / 11
    assert _close(provider, EX) == D("23.9")                        # ex-date sonrası dokunulmaz
    action = SQLAlchemyCorporateActionRepository(provider).get_by_id(event.corporate_action_id)
    assert action.applied and action.ratio == D("10") and action.price_adjustment_count == 6
    assert market.registered and event.market_effective_date == EX


def test_already_consistent_prices_are_not_adjusted_twice(provider):
    _model_trade(provider)
    _prices(provider, before="23", after="23.9")                   # Yahoo geçmişi zaten düzeltmiş

    event = _applier(provider, FakeMarket(MarketActionStatus.NO_BREAK)).apply(_decision(), TARGET, auto_applied=True)

    assert event.price_adjusted_before is None and event.price_adjustment_count == 0
    assert _close(provider, EX - timedelta(days=1)) == D("23")
    assert event.market_effective_date is None


def test_fraction_lot_is_paid_in_cash_at_post_ex_close(provider):
    with provider.get_session() as s:
        s.add(ORMTrade(id=1, stock_id=79, trade_date=date(2026, 8, 1), trade_time=time(10), side=TradeSideEnum.BUY,
                       quantity=65, price=D("15.60"), original_quantity=65, original_price=D("15.60")))
        s.commit()
    _prices(provider, before="15.60", after="2.11")

    event = _applier(provider).apply(_decision("7.3834"), TARGET, auto_applied=True)

    with provider.get_session() as s:
        assert s.get(ORMTrade, 1).quantity == 479
        [cash] = s.query(ORMCashMovement).all()
        # 0,921 lot x 2,11 TL (ex-date sonrası ilk kapanış) = 1,94331 -> 1,94
        assert (cash.type.value, cash.amount) == ("FRACTION", D("1.94"))
    assert [(c.ledger, c.amount) for c in event.cash_entries] == [(SplitLedger.MAIN, D("1.94"))]


def test_revert_restores_trades_prices_and_records(provider):
    _model_trade(provider)
    _prices(provider, before="253", after="23.9")
    market = FakeMarket()
    applier = _applier(provider, market)
    event = applier.apply(_decision(), TARGET, auto_applied=True)

    reverted = applier.revert(event.id)

    assert reverted.status == SplitEventStatus.REVERTED
    with provider.get_session() as s:
        assert (s.get(ORMModelPortfolioTrade, 34).quantity, s.get(ORMModelPortfolioTrade, 34).price) == (65, D("242"))
    assert _close(provider, EX - timedelta(days=1)) == D("253")
    assert SQLAlchemyCorporateActionRepository(provider).get_by_id(event.corporate_action_id) is None
    assert market.ignored == [("SDTTR", EX, MarketActionStatus.IGNORED)]


def test_reverse_split_is_refused(provider):
    with pytest.raises(ValueError):
        _applier(provider).apply(_decision("0.1"), TARGET, auto_applied=True)


def test_price_sync_failure_keeps_trade_changes(provider, caplog):
    _model_trade(provider)
    _prices(provider, before="253", after="23.9")

    class BrokenMarket(FakeMarket):
        def register_portfolio_action(self, ticker, action):
            raise OSError("duckdb kilitli")

    event = _applier(provider, BrokenMarket()).apply(_decision(), TARGET, auto_applied=True)

    with provider.get_session() as s:
        assert s.get(ORMModelPortfolioTrade, 34).quantity == 715
    assert event.status == SplitEventStatus.APPLIED
    assert "fiyat geçmişi eşitlenemedi" in caplog.text
    # fiyat düzeltmesi kayda geçti: geri alma fiyatları da geri çevirir
    assert event.price_adjusted_before == EX and event.price_adjustment_count == 6
    _applier(provider, FakeMarket()).revert(event.id)
    assert _close(provider, EX - timedelta(days=1)) == D("253")


# ----------------------------------------------------------------- kullanıcının kaydettiği bedelsiz


def _corporate_action_service(provider, market=None):
    from src.application.services.corporate_actions.corporate_action_service import CorporateActionService
    from src.application.services.corporate_actions.split_applier import CorporateActionSplitAdapter
    from src.infrastructure.db.sqlalchemy.repositories.sa_portfolio_repository import SQLAlchemyPortfolioRepository
    from src.infrastructure.db.sqlalchemy.repositories.sa_stock_repository import SQLAlchemyStockRepository

    return CorporateActionService(
        action_repo=SQLAlchemyCorporateActionRepository(provider),
        portfolio_repo=SQLAlchemyPortfolioRepository(provider),
        split_applier=CorporateActionSplitAdapter(_applier(provider, market), SQLAlchemyStockRepository(provider)),
    )


def test_manual_bedelsiz_adjusts_main_and_model_portfolios(provider):
    with provider.get_session() as s:
        s.add(ORMTrade(id=1, stock_id=79, trade_date=date(2026, 8, 1), trade_time=time(10), side=TradeSideEnum.BUY,
                       quantity=10, price=D("250"), original_quantity=10, original_price=D("250")))
        s.commit()
    _model_trade(provider)
    _prices(provider, before="253", after="23.9")
    service = _corporate_action_service(provider, FakeMarket())
    action = service.register_bedelsiz(stock_id=79, ex_date=EX, ratio=D("10"))

    result = service.apply_action(action.id, current_price=D("253"))

    assert (result.shares_before, result.new_shares, result.shares_after) == (10, 100, 110)
    assert result.avg_cost_after == D("22.7273")  # 250 / 11, işlem fiyatı 4 haneye yuvarlanır
    assert result.price_adjustment_count == 6
    with provider.get_session() as s:
        assert s.get(ORMModelPortfolioTrade, 34).quantity == 715      # model portföy de düzeltildi
        assert s.get(ORMTrade, 1).original_quantity == 10
    stored = SQLAlchemyCorporateActionRepository(provider).get_by_id(action.id)
    assert stored.applied and stored.prices_adjusted
    assert len(SQLAlchemyCorporateActionRepository(provider).get_all()) == 1  # yeni kayıt açılmadı


def test_manual_bedelsiz_for_model_only_stock_no_longer_refused(provider):
    _model_trade(provider)
    _prices(provider, before="253", after="23.9")
    service = _corporate_action_service(provider)
    action = service.register_bedelsiz(stock_id=79, ex_date=EX, ratio=D("10"))

    result = service.apply_action(action.id)

    assert result.shares_before == 0 and result.shares_after == 0
    with provider.get_session() as s:
        assert s.get(ORMModelPortfolioTrade, 34).quantity == 715


def test_manual_bedelsiz_without_any_trades_is_refused(provider):
    service = _corporate_action_service(provider)
    action = service.register_bedelsiz(stock_id=79, ex_date=EX, ratio=D("10"))
    with pytest.raises(ValueError, match="Portföyde bu hisse bulunmuyor"):
        service.apply_action(action.id)
