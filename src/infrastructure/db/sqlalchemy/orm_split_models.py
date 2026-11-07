"""Bölünme otomasyonu tabloları (split_events, split_trade_changes, split_cash_entries)."""
from sqlalchemy import BigInteger, Boolean, Column, Date, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.sql import func

from src.infrastructure.db.sqlalchemy.exact_numeric import ExactNumeric
from src.infrastructure.db.sqlalchemy.orm_models import Base


class ORMSplitEvent(Base):
    """Otomatik/manuel uygulanmış bölünme olayı; ana, model ve varlık defteri değişikliklerinin üst kaydı."""
    __tablename__ = "split_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(20), nullable=False)
    stock_id = Column(BigInteger, ForeignKey("stocks.id", ondelete="RESTRICT"), nullable=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="RESTRICT"), nullable=True)
    ex_date = Column(Date, nullable=False)
    multiplier = Column(ExactNumeric(18, 8), nullable=False)
    sources = Column(String(100), nullable=False, default="")
    auto_applied = Column(Boolean, nullable=False, default=False, server_default="0")
    status = Column(String(10), nullable=False, default="APPLIED")
    corporate_action_id = Column(BigInteger, ForeignKey("corporate_actions.id", ondelete="SET NULL"), nullable=True)
    applied_at = Column(DateTime, nullable=False, server_default=func.now())
    reverted_at = Column(DateTime, nullable=True)
    note = Column(String(500), nullable=True)
    # SQLite fiyat geçmişi düzeltmesi (geri almada ters faktörle geri çevrilir) ve DuckDB olay günü
    price_adjusted_before = Column(Date, nullable=True)
    price_adjustment_count = Column(Integer, nullable=False, default=0, server_default="0")
    market_effective_date = Column(Date, nullable=True)

    __table_args__ = (Index("idx_split_events_ticker_date", "ticker", "ex_date"),)


class ORMSplitTradeChange(Base):
    """Bölünmenin bir işleme etkisi (önceki/sonraki lot ve fiyat); `trade_id` deftere göre ilgili tabloyu gösterir."""
    __tablename__ = "split_trade_changes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("split_events.id", ondelete="CASCADE"), nullable=False)
    ledger = Column(String(5), nullable=False)  # MAIN | MODEL | ASSET
    trade_id = Column(BigInteger, nullable=False)
    portfolio_id = Column(Integer, nullable=True)
    pre_quantity = Column(ExactNumeric(28, 10), nullable=False)
    post_quantity = Column(ExactNumeric(28, 10), nullable=False)
    pre_price = Column(ExactNumeric(28, 10), nullable=False)
    post_price = Column(ExactNumeric(28, 10), nullable=False)

    __table_args__ = (Index("idx_split_trade_changes_event", "event_id"),)


class ORMSplitCashEntry(Base):
    """Bölünme küsurat nakdi için yazılan nakit hareketinin kaydı (geri almada silinir)."""
    __tablename__ = "split_cash_entries"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("split_events.id", ondelete="CASCADE"), nullable=False)
    ledger = Column(String(5), nullable=False)  # MAIN | MODEL
    portfolio_id = Column(Integer, nullable=True)
    movement_id = Column(BigInteger, nullable=False)
    amount = Column(ExactNumeric(18, 4), nullable=False)
    movement_date = Column(Date, nullable=False)
