"""Üç işlem defterinin (trades, model_portfolio_trades, asset_trades) tek oturumda ortak okuması."""
from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional

from src.domain.models.ledger import LedgerKind, LedgerSnapshot
from src.domain.ports.repositories.i_ledger_reader import ILedgerReader
from src.domain.split_math import LedgerLot
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider
from src.infrastructure.db.sqlalchemy.orm_models import ORMAssetTrade, ORMModelPortfolioTrade, ORMTrade


def _dec(value) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _lot(orm, instrument_id: int) -> LedgerLot:
    is_buy = getattr(orm.side, "value", orm.side) == "BUY"
    return LedgerLot(orm.id, orm.trade_date, orm.trade_time, is_buy, _dec(orm.quantity), _dec(orm.price), instrument_id)


class SQLAlchemyLedgerReader(ILedgerReader):
    def __init__(self, db_provider: SQLAlchemyEngineProvider) -> None:
        self._provider = db_provider

    def snapshot(
        self, stock_id: Optional[int] = None, asset_id: Optional[int] = None, include_assets: bool = False,
    ) -> LedgerSnapshot:
        lots: Dict = {}
        with self._provider.get_session() as session:
            if asset_id is None:
                main = session.query(ORMTrade)
                model = session.query(ORMModelPortfolioTrade)
                if stock_id is not None:
                    main, model = main.filter_by(stock_id=stock_id), model.filter_by(stock_id=stock_id)
                for trade in main.all():
                    lots.setdefault((LedgerKind.MAIN, None), []).append(_lot(trade, trade.stock_id))
                for trade in model.all():
                    lots.setdefault((LedgerKind.MODEL, trade.portfolio_id), []).append(_lot(trade, trade.stock_id))
            if asset_id is not None or (stock_id is None and include_assets):
                assets = session.query(ORMAssetTrade)
                if asset_id is not None:
                    assets = assets.filter_by(asset_id=asset_id)
                for trade in assets.all():
                    lots.setdefault((LedgerKind.ASSET, None), []).append(_lot(trade, trade.asset_id))
        return LedgerSnapshot(lots)
