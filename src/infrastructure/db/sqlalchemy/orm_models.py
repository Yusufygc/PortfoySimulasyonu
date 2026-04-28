# src/infrastructure/db/sqlalchemy/orm_models.py

from sqlalchemy import Column, Computed, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Time, UniqueConstraint
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

class TradeSideEnum(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"

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
    total_amount = Column(Numeric(18, 4), Computed("quantity * price", persisted=True))
    notes = Column(String(255))
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("idx_trades_stock_date", "stock_id", "trade_date"),
        Index("idx_trades_date", "trade_date"),
    )

    stock = relationship("ORMStock", back_populates="trades")

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

class ORMWatchlist(Base):
    __tablename__ = "watchlists"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(String(1000))
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
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    trades = relationship("ORMModelPortfolioTrade", back_populates="model_portfolio", cascade="all, delete")

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

class ORMBudget(Base):
    __tablename__ = "budgets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    month = Column(String(7), unique=True, nullable=False) # 'YYYY-MM'
    income_salary = Column(Numeric(18, 2), default=0)
    income_additional = Column(Numeric(18, 2), default=0)
    expense_rent = Column(Numeric(18, 2), default=0)
    expense_bills = Column(Numeric(18, 2), default=0)
    expense_food = Column(Numeric(18, 2), default=0)
    expense_transport = Column(Numeric(18, 2), default=0)
    expense_luxury = Column(Numeric(18, 2), default=0)
    savings_target = Column(Numeric(18, 2), default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

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

class ORMRiskProfile(Base):
    __tablename__ = "risk_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    age = Column(Integer, default=0)
    horizon = Column(String(50), default="medium")
    reaction = Column(String(50), default="hold")
    risk_score = Column(Integer, default=0)
    risk_label = Column(String(50), default="DENGELİ")
    created_at = Column(DateTime, server_default=func.now())
