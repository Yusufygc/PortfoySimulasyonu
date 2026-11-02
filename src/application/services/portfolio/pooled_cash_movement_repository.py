from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Iterable, List, Optional

from src.domain.models.cash_movement import CashMovement, CashMovementType
from src.domain.models.trade import TradeSide
from src.domain.ports.repositories.i_cash_movement_repo import ICashMovementRepository

# Sentetik hareket kimlikleri negatiftir; gerçek kayıtlarla çakışmaz ve silme/güncelleme gerçek depoda bulunmaz.
FX_ID_OFFSET = -1_000_000_000
ASSET_TRADE_ID_OFFSET = -2_000_000_000


def _sort_key(movement: CashMovement):
    return (movement.movement_date, movement.movement_time or time.min, movement.id or 0)


class PooledCashMovementRepository(ICashMovementRepository):
    """TL nakit görünümü: gerçek nakit hareketleri + ortak havuzdan TL çıkış/girişleri.

    Döviz çevirmelerinin TL bacağı ve TL ile ödenen (nakde bağlı) varlık işlemleri, BIST portföyünün gözünde TL
    çıkışı (WITHDRAW) ya da girişi (DEPOSIT) olarak görünür. Böylece BIST alım gücü, nakit bakiyesi ve TWR (dış akış
    olarak ayrılır) ortak havuzla tutarlı kalır. Yazma işlemleri gerçek depoya gider.
    """

    def __init__(self, real_repo: ICashMovementRepository, fx_repo, asset_trade_repo, asset_repo) -> None:
        self._real = real_repo
        self._fx_repo = fx_repo
        self._asset_trade_repo = asset_trade_repo
        self._asset_repo = asset_repo

    # ---- sentetik hareketler ----------------------------------------------------------------------

    def _synthetic(self) -> List[CashMovement]:
        movements = [self._from_effect(FX_ID_OFFSET - c.id, c.conversion_date, c.conversion_time, c.try_effect,
                                       "Döviz alımı (USD)" if c.usd_effect > 0 else "Döviz satımı (USD)")
                     for c in self._fx_repo.list_all()]
        assets = {a.id: a for a in self._asset_repo.list_assets(active_only=False)}
        for trade in self._asset_trade_repo.list_trades():
            asset = assets.get(trade.asset_id)
            if not trade.cash_linked or asset is None or asset.settlement_currency != "TRY":
                continue
            effect = trade.cash_amount if trade.side == TradeSide.SELL else -trade.cash_amount
            label = f"{asset.symbol} {'satımı' if trade.side == TradeSide.SELL else 'alımı'}"
            movements.append(self._from_effect(ASSET_TRADE_ID_OFFSET - trade.id, trade.trade_date, trade.trade_time, effect, label))
        return movements

    @staticmethod
    def _from_effect(movement_id: int, day: date, at: Optional[time], effect: Decimal, label: str) -> CashMovement:
        kind = CashMovementType.DEPOSIT if effect > 0 else CashMovementType.WITHDRAW
        return CashMovement(id=movement_id, movement_date=day, movement_time=at, type=kind, amount=abs(effect), notes=label)

    # ---- okuma ------------------------------------------------------------------------------------

    def get_all_movements(self) -> List[CashMovement]:
        return sorted(self._real.get_all_movements() + self._synthetic(), key=_sort_key)

    def get_movements_until(self, movement_date: date, movement_time: Optional[time] = None) -> List[CashMovement]:
        synthetic = [
            m for m in self._synthetic()
            if m.movement_date < movement_date
            or (m.movement_date == movement_date and (movement_time is None or m.movement_time is None or m.movement_time <= movement_time))
        ]
        return sorted(self._real.get_movements_until(movement_date, movement_time) + synthetic, key=_sort_key)

    def get_movements_by_type(self, movement_type: CashMovementType, stock_id: Optional[int] = None) -> List[CashMovement]:
        return self._real.get_movements_by_type(movement_type, stock_id)

    def get_movement(self, movement_id: int) -> Optional[CashMovement]:
        return self._real.get_movement(movement_id)

    # ---- yazma (gerçek depoya) -------------------------------------------------------------------

    def insert_movement(self, movement: CashMovement) -> CashMovement:
        return self._real.insert_movement(movement)

    def insert_movements_bulk(self, movements: Iterable[CashMovement]) -> None:
        self._real.insert_movements_bulk(movements)

    def delete_movement(self, movement_id: int) -> None:
        self._real.delete_movement(movement_id)

    def delete_all_movements(self) -> None:
        self._real.delete_all_movements()
