# src/infrastructure/db/sqlalchemy/orm_models.py

from sqlalchemy import Boolean, Column, Computed, Date, DateTime, Enum, ForeignKey, Index, Integer, JSON, Numeric, String, Text, Time, UniqueConstraint
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class TradeSideEnum(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

class CashMovementTypeEnum(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAW = "WITHDRAW"

class ORMStock(Base):
    __tablename__ = "stocks"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    name = Column(String(100))
    currency_code = Column(String(3), nullable=False, default="TRY", server_default="TRY")
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", name="uq_stocks_ticker"),
    )

    # Relationships (Optional but useful for ORM navigation)
    trades = relationship("ORMTrade", back_populates="stock")
    daily_prices = relationship("ORMDailyPrice", back_populates="stock")

class ORMTrade(Base):
    __tablename__ = "trades"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    stock_id = Column(BIGINT(unsigned=True), ForeignKey("stocks.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    trade_date = Column(Date, nullable=False)
    trade_time = Column(Time, nullable=True)
    side = Column(Enum(TradeSideEnum), nullable=False)
    quantity = Column(BIGINT(unsigned=True), nullable=False)
    price = Column(Numeric(18, 4), nullable=False)
    original_quantity = Column(BIGINT(unsigned=True), nullable=False)
    original_price = Column(Numeric(18, 4), nullable=False)
    total_amount = Column(Numeric(18, 4), Computed("quantity * price", persisted=True))
    notes = Column(String(255))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_trades_stock_date", "stock_id", "trade_date"),
        Index("idx_trades_date", "trade_date"),
    )

    stock = relationship("ORMStock", back_populates="trades")

class ORMCashMovement(Base):
    __tablename__ = "cash_movements"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    movement_date = Column(Date, nullable=False)
    movement_time = Column(Time, nullable=True)
    type = Column(Enum(CashMovementTypeEnum), nullable=False)
    amount = Column(Numeric(18, 4), nullable=False)
    notes = Column(String(255))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_cash_movements_date", "movement_date", "movement_time"),
    )

class ORMDailyPrice(Base):
    __tablename__ = "daily_prices"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    stock_id = Column(BIGINT(unsigned=True), ForeignKey("stocks.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    price_date = Column(Date, nullable=False)
    close_price = Column(Numeric(18, 4), nullable=False)
    currency_code = Column(String(3), nullable=False, default="TRY", server_default="TRY")
    source = Column(String(50), nullable=False, default="yfinance", server_default="yfinance")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("stock_id", "price_date", name="uq_daily_price"),
        Index("idx_daily_prices_date", "price_date"),
    )

    stock = relationship("ORMStock", back_populates="daily_prices")


class ORMLatestPrice(Base):
    __tablename__ = "latest_prices"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    stock_id = Column(BIGINT(unsigned=True), ForeignKey("stocks.id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    price = Column(Numeric(18, 4), nullable=False)
    as_of = Column(DateTime, nullable=False)
    source = Column(String(50), nullable=False)
    provider = Column(String(50), nullable=False)
    fetched_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("stock_id", name="uq_latest_prices_stock"),
        Index("idx_latest_prices_as_of", "as_of"),
    )

    stock = relationship("ORMStock")


class ORMWatchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String(1000))
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    items = relationship("ORMWatchlistItem", back_populates="watchlist", cascade="all, delete")

class ORMWatchlistItem(Base):
    __tablename__ = "watchlist_items"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    watchlist_id = Column(Integer, ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False)
    stock_id = Column(BIGINT(unsigned=True), ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    notes = Column(String(1000))
    added_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("watchlist_id", "stock_id", name="unique_watchlist_stock"),
    )

    watchlist = relationship("ORMWatchlist", back_populates="items")
    stock = relationship("ORMStock")

class ORMModelPortfolio(Base):
    __tablename__ = "model_portfolios"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String(1000))
    initial_cash = Column(Numeric(18, 2), nullable=False, default=100000.00, server_default="100000.00")
    sort_order = Column(Integer, nullable=False, default=0, server_default="0")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    trades = relationship("ORMModelPortfolioTrade", back_populates="model_portfolio", cascade="all, delete")
    cash_movements = relationship(
        "ORMModelPortfolioCashMovement",
        back_populates="model_portfolio",
        cascade="all, delete",
    )

class ORMModelPortfolioTrade(Base):
    __tablename__ = "model_portfolio_trades"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("model_portfolios.id", ondelete="CASCADE"), nullable=False)
    stock_id = Column(BIGINT(unsigned=True), ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False)
    trade_date = Column(Date, nullable=False)
    trade_time = Column(Time, nullable=True)
    side = Column(Enum(TradeSideEnum), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(18, 4), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = (
        Index("idx_model_portfolio_trades_portfolio_date", "portfolio_id", "trade_date"),
        Index("idx_model_portfolio_trades_stock_date", "stock_id", "trade_date"),
    )

    model_portfolio = relationship("ORMModelPortfolio", back_populates="trades")
    stock = relationship("ORMStock")


class ORMModelPortfolioCashMovement(Base):
    __tablename__ = "model_portfolio_cash_movements"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("model_portfolios.id", ondelete="CASCADE"), nullable=False)
    movement_date = Column(Date, nullable=False)
    movement_time = Column(Time, nullable=True)
    type = Column(Enum(CashMovementTypeEnum), nullable=False)
    amount = Column(Numeric(18, 4), nullable=False)
    notes = Column(String(255))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_model_portfolio_cash_movements_portfolio_date", "portfolio_id", "movement_date", "movement_time"),
    )

    model_portfolio = relationship("ORMModelPortfolio", back_populates="cash_movements")

class ORMBudget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(7), unique=True, nullable=False)  # 'YYYY-MM'
    savings_target = Column(Numeric(18, 2), default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    items = relationship("ORMBudgetItem", back_populates="budget",
                         cascade="all, delete-orphan", lazy="select")


class ORMBudgetItem(Base):
    __tablename__ = "budget_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    budget_id = Column(Integer, ForeignKey("budgets.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String(10), nullable=False)   # 'income' | 'expense'
    name = Column(String(100), nullable=False)
    amount = Column(Numeric(18, 2), default=0)

    budget = relationship("ORMBudget", back_populates="items")


class ORMBudgetPinnedItem(Base):
    __tablename__ = "budget_pinned_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    item_type = Column(String(10), nullable=False)   # 'income' | 'expense'
    name = Column(String(100), nullable=False)
    default_amount = Column(Numeric(18, 2), default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("item_type", "name", name="uq_budget_pinned_item_type_name"),
    )


class ORMFinancialGoal(Base):
    __tablename__ = "financial_goals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    target_amount = Column(Numeric(18, 2), nullable=False)
    current_amount = Column(Numeric(18, 2), default=0)
    deadline = Column(Date, nullable=True)
    priority = Column(String(50), default="MEDIUM")
    status = Column(String(50), default="ACTIVE")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class ActionTypeEnum(str, enum.Enum):
    BEDELLI = "BEDELLI"
    BEDELSIZ = "BEDELSIZ"

class ORMCorporateActionCandidate(Base):
    __tablename__ = "corporate_action_candidates"

    id                   = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    ticker               = Column(String(20), nullable=False)
    stock_id             = Column(BIGINT(unsigned=True), ForeignKey("stocks.id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    source               = Column(String(30), nullable=False)
    source_disclosure_id = Column(String(100), nullable=False)
    source_url           = Column(String(500), nullable=True)
    action_type          = Column(Enum(ActionTypeEnum), nullable=False)
    status               = Column(String(30), nullable=False, default="DISCOVERED", server_default="DISCOVERED")
    ratio                = Column(Numeric(12, 8), nullable=True)
    subscription_price   = Column(Numeric(18, 4), nullable=True)
    announcement_date    = Column(Date, nullable=True)
    ex_date              = Column(Date, nullable=True)
    confidence           = Column(Numeric(5, 4), nullable=False, default=0, server_default="0")
    raw_payload_json     = Column(JSON, nullable=True)
    parse_notes          = Column(String(500), nullable=True)
    created_at           = Column(DateTime, nullable=False, server_default=func.now())
    updated_at           = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint(
            "source",
            "source_disclosure_id",
            "action_type",
            "ticker",
            name="uq_corp_action_candidate_source",
        ),
        Index("idx_corp_action_candidates_ticker_status_exdate", "ticker", "status", "ex_date"),
    )

    stock = relationship("ORMStock")

class ORMCorporateAction(Base):
    """
    Bedelli / bedelsiz sermaye artırımı olaylarını saklar.
    applied=1 → portföye uygulandı, tekrar işlem yapılamaz.
    """
    __tablename__ = "corporate_actions"

    id                 = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    stock_id           = Column(BIGINT(unsigned=True), ForeignKey("stocks.id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    action_type        = Column(Enum(ActionTypeEnum), nullable=False)
    ex_date            = Column(Date, nullable=False)
    ratio              = Column(Numeric(12, 8), nullable=False)
    subscription_price = Column(Numeric(18, 4), nullable=True)
    announcement_date  = Column(Date, nullable=True)
    notes              = Column(String(500), nullable=True)
    applied            = Column(Boolean, nullable=False, default=False, server_default="0")
    applied_at         = Column(DateTime, nullable=True)
    prices_adjusted    = Column(Boolean, nullable=False, default=False, server_default="0")
    prices_adjusted_at = Column(DateTime, nullable=True)
    price_adjustment_factor = Column(Numeric(18, 10), nullable=True)
    price_adjustment_count  = Column(Integer, nullable=False, default=0, server_default="0")
    created_at         = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_corporate_actions_stock_exdate", "stock_id", "ex_date"),
        Index("idx_corporate_actions_exdate", "ex_date"),
    )

    stock = relationship("ORMStock")

class ORMRiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    age = Column(Integer, default=0)
    horizon = Column(String(50), default="medium")
    reaction = Column(String(50), default="hold")
    risk_score = Column(Integer, default=0)
    risk_label = Column(String(50), default="DENGELI")
    questionnaire_version = Column(String(20), default="legacy")
    answers_json = Column(JSON, nullable=True)
    dimension_scores_json = Column(JSON, nullable=True)
    recommended_allocation_json = Column(JSON, nullable=True)
    suitability_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class ORMTradeAdjustment(Base):
    __tablename__ = "trade_adjustments"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    trade_id = Column(BIGINT(unsigned=True), ForeignKey("trades.id", ondelete="CASCADE"), nullable=False)
    corporate_action_id = Column(BIGINT(unsigned=True), ForeignKey("corporate_actions.id", ondelete="RESTRICT"), nullable=False)
    factor = Column(Numeric(18, 10), nullable=False)
    pre_quantity = Column(BIGINT(unsigned=True), nullable=False)
    post_quantity = Column(BIGINT(unsigned=True), nullable=False)
    pre_price = Column(Numeric(18, 4), nullable=False)
    post_price = Column(Numeric(18, 4), nullable=False)
    applied_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_trade_adjustments_trade", "trade_id"),
    )

    trade = relationship("ORMTrade")
    corporate_action = relationship("ORMCorporateAction")


# ---------------------------------------------------------------------------
# KAP Ortaklık Yapısı tabloları (Plan 6)
# ---------------------------------------------------------------------------

class ORMKapCompany(Base):
    """KAP'tan bilinen şirket: ticker → mkkMemberOid eşleşmesi."""
    __tablename__ = "kap_companies"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    mkk_member_oid = Column(String(40), nullable=False)
    title = Column(String(255))
    last_fetched_at = Column(DateTime)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("ticker", name="uq_kap_companies_ticker"),
        Index("idx_kap_companies_oid", "mkk_member_oid"),
    )

    shareholder_snapshots = relationship(
        "ORMKapShareholderSnapshot",
        back_populates="company",
        cascade="all, delete-orphan",
    )


class ORMKapShareholderSnapshot(Base):
    """KAP 'Sermayede %5+ pay sahibi' bildirimi (tek tarih için snapshot)."""
    __tablename__ = "kap_shareholder_snapshots"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    company_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("kap_companies.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    creation_date = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("company_id", "creation_date", name="uq_kap_shareholder_snapshot"),
        Index("idx_kap_shareholder_snap_date", "creation_date"),
    )

    company = relationship("ORMKapCompany", back_populates="shareholder_snapshots")
    rows = relationship(
        "ORMKapShareholderRow",
        back_populates="snapshot",
        cascade="all, delete-orphan",
    )


class ORMKapShareholderRow(Base):
    """Snapshot içindeki tek pay sahibi satırı."""
    __tablename__ = "kap_shareholder_rows"

    id = Column(BIGINT(unsigned=True), primary_key=True, autoincrement=True)
    snapshot_id = Column(
        BIGINT(unsigned=True),
        ForeignKey("kap_shareholder_snapshots.id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    shareholder_name = Column(String(500), nullable=False)
    share_in_capital = Column(Numeric(24, 4))
    ratio_in_capital = Column(Numeric(9, 4))
    voting_right_ratio = Column(Numeric(9, 4))
    is_total = Column(Boolean, nullable=False, default=False, server_default="0")

    __table_args__ = (
        Index("idx_kap_shareholder_rows_snap", "snapshot_id"),
    )

    snapshot = relationship("ORMKapShareholderSnapshot", back_populates="rows")
