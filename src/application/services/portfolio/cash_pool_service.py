from __future__ import annotations

from datetime import date, time
from decimal import Decimal
from typing import Dict, Optional, Tuple, Union

from src.domain.models.trade import TradeSide

ZERO = Decimal("0")
SUPPORTED_CURRENCIES = ("TRY", "USD")

AsOf = Union[date, Tuple[date, Optional[time]], None]


def _upto(day: date, at: Optional[time], as_of: AsOf) -> bool:
    if as_of is None:
        return True
    as_date, as_time = (as_of, None) if isinstance(as_of, date) else as_of
    if day != as_date:
        return day < as_date
    return as_time is None or at is None or at <= as_time


class CashPoolService:
    """Ortak nakit havuzu bakiyeleri (TL ve USD); olay kaynaklıdır, bakiye saklanmaz.

    - TL: BIST nakit bakiyesi (`PortfolioService`, havuz deposu sayesinde döviz çevirmeleri ve TL ile ödenen varlık
      işlemlerini de içerir).
    - USD: döviz çevirmelerinin USD bacağı + USD ile ödenen nakde bağlı varlık işlemleri.
    """

    def __init__(self, portfolio_service, fx_repo, asset_trade_repo, asset_repo) -> None:
        self._portfolio_service = portfolio_service
        self._fx_repo = fx_repo
        self._asset_trade_repo = asset_trade_repo
        self._asset_repo = asset_repo

    def try_balance(self, as_of: AsOf = None) -> Decimal:
        return self._portfolio_service.get_cash_balance(as_of=as_of)

    def _usd_events(self, exclude_fx_id: Optional[int] = None, exclude_trade_id: Optional[int] = None) -> list:
        """(gün, saat, etki) — döviz çevirmelerinin USD bacağı ve USD ile ödenen nakde bağlı varlık işlemleri."""
        events = [(c.conversion_date, c.conversion_time, c.usd_effect)
                  for c in self._fx_repo.list_all() if c.id != exclude_fx_id]
        assets = {a.id: a for a in self._asset_repo.list_assets(active_only=False)}
        for trade in self._asset_trade_repo.list_trades():
            asset = assets.get(trade.asset_id)
            if trade.cash_linked and asset is not None and asset.settlement_currency == "USD" and trade.id != exclude_trade_id:
                effect = trade.cash_amount if trade.side == TradeSide.SELL else -trade.cash_amount
                events.append((trade.trade_date, trade.trade_time, effect))
        return events

    def usd_balance(self, as_of: AsOf = None, exclude_trade_id: Optional[int] = None) -> Decimal:
        events = self._usd_events(exclude_trade_id=exclude_trade_id)
        return sum((effect for day, at, effect in events if _upto(day, at, as_of)), ZERO)

    def usd_timeline_valid(self, exclude_fx_id: Optional[int] = None, exclude_trade_id: Optional[int] = None) -> bool:
        """USD hareketleri tarih sırasıyla uygulandığında bakiye hiçbir anda eksiye düşmüyor mu.

        Silmeden önce `exclude_*` ile kaydı çıkarılmış hâlde sorulur. Aynı anda önce girişler uygulanır.
        """
        events = self._usd_events(exclude_fx_id, exclude_trade_id)
        running = ZERO
        for _day, _at, effect in sorted(events, key=lambda e: (e[0], e[1] or time.min, -e[2])):
            running += effect
            if running < 0:
                return False
        return True

    def balance(self, currency: str, as_of: AsOf = None) -> Decimal:
        currency = (currency or "").upper()
        if currency == "TRY":
            return self.try_balance(as_of)
        if currency == "USD":
            return self.usd_balance(as_of)
        raise ValueError(f"Nakit havuzunda {currency} desteklenmiyor; yalnızca TRY ve USD kullanılabilir.")

    def balances(self, as_of: AsOf = None) -> Dict[str, Decimal]:
        return {currency: self.balance(currency, as_of) for currency in SUPPORTED_CURRENCIES}
