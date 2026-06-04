# src/domain/ports/repositories/i_trade_adjustment_repo.py

from abc import ABC, abstractmethod
from typing import List
from src.domain.models.trade_adjustment import TradeAdjustment

class ITradeAdjustmentRepository(ABC):
    @abstractmethod
    def insert(self, adjustment: TradeAdjustment) -> TradeAdjustment:
        pass

    @abstractmethod
    def get_by_trade_id(self, trade_id: int) -> List[TradeAdjustment]:
        pass

    @abstractmethod
    def get_by_corporate_action_id(self, corporate_action_id: int) -> List[TradeAdjustment]:
        pass
