from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from src.domain.models.position_snapshot import HUNDRED, ZERO, PortfolioPositions, PositionSnapshot
from src.domain.ticker import clean_ticker

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Quote:
    """Bir hissenin güncel fiyatı ve günlük değişimi (pozisyon sahibi olunmasa da)."""

    price: Decimal = ZERO
    daily_change_pct: Decimal = ZERO


class PositionQueryService:
    """Pozisyon rakamlarının tek okuma kaynağı: ana portföy, model portföy ve hisse fiyatı.

    Portföyüm (`UnifiedPortfolioService`), Hisse Detay ve Model Portföy ekranları aynı pozisyon için aynı değeri
    buradan alır; fiyat çözümü `CurrentPriceResolver` kuralıyla (canlı fiyat yalnızca geçerliyse, aksi halde son kapanış).
    Ana portföy değerleme `BistHoldingsReader` ile Portföyüm'le aynı koddan geçer.
    """

    def __init__(self, bist_reader, model_portfolio_service, stock_lookup_service, price_resolver) -> None:
        self._bist_reader = bist_reader
        self._model_service = model_portfolio_service
        self._lookup = stock_lookup_service
        self._resolver = price_resolver

    # ---- ana portföy ------------------------------------------------------------------------------

    def main_positions(self) -> PortfolioPositions:
        holdings, cash = self._bist_reader.read()
        total = sum((h.value_try for h in holdings), ZERO) + cash
        positions = tuple(
            PositionSnapshot(
                stock_id=h.ref_id,
                ticker=h.symbol,
                name=h.name,
                quantity=int(h.quantity),
                total_cost=h.cost_try,
                price=h.price_native,
                daily_change_pct=h.daily_change_pct,
                weight_pct=h.value_try / total * HUNDRED if total > 0 else ZERO,
            )
            for h in holdings
        )
        return PortfolioPositions(positions=positions, cash=cash, total_value=total)

    def main_position(self, stock_id: int) -> Optional[PositionSnapshot]:
        return self.main_positions().find(stock_id)

    # ---- model portföy ----------------------------------------------------------------------------

    def resolve_prices(self, stock_ids: Sequence[int]) -> Dict[int, Decimal]:
        """Güncel fiyat: önce çözümleyici (canlı/kapanış), yoksa canlı önbellek, eksikler için son kapanış."""
        stock_ids = list(stock_ids)
        price_map: Dict[int, Decimal] = {}
        if self._resolver is not None:
            price_map.update(self._resolver.price_map(stock_ids))
        elif self._lookup:
            price_map.update(self._lookup.get_latest_price_map(stock_ids))
        if self._lookup:
            for sid in [sid for sid in stock_ids if sid not in price_map]:
                close = self._lookup.get_previous_close(sid)
                if close is not None:
                    price_map[sid] = close
        return price_map

    def model_price_map(self, portfolio_id: int) -> Dict[int, Decimal]:
        """Model portföydeki hisselerin fiyatları; okunamazsa boş harita."""
        try:
            return self.resolve_prices(sorted(self._model_service.get_positions(portfolio_id).keys()))
        except Exception as exc:
            logger.warning("Fiyat haritası yüklenemedi: %s", exc)
            return {}

    def model_positions(self, portfolio_id: int, price_map: Optional[Dict[int, Decimal]] = None) -> PortfolioPositions:
        """Model portföyün pozisyonları; `price_map` verilmezse fiyatlar çözülür."""
        if price_map is None:
            price_map = self.model_price_map(portfolio_id)
        details = self._model_service.get_positions_with_details(portfolio_id, price_map)
        summary = self._model_service.get_portfolio_summary(portfolio_id, price_map)
        total = summary.get("total_value", ZERO)
        previous = self._previous_close_map([d["stock_id"] for d in details if d.get("stock_id")])
        positions = tuple(self._model_snapshot(d, previous, total) for d in details)
        return PortfolioPositions(positions=positions, cash=summary.get("remaining_cash", ZERO), total_value=total)

    def model_position(self, portfolio_id: int, stock_id: int) -> Optional[PositionSnapshot]:
        return self.model_positions(portfolio_id).find(stock_id)

    @staticmethod
    def _model_snapshot(detail: dict, previous: Dict[int, Decimal], total: Decimal) -> PositionSnapshot:
        stock_id = detail["stock_id"]
        price = detail.get("current_price")
        prev_close = previous.get(stock_id)
        daily = (price - prev_close) / prev_close * HUNDRED if price and prev_close and prev_close > 0 else None
        value = detail.get("current_value")
        return PositionSnapshot(
            stock_id=stock_id,
            ticker=detail.get("ticker", ""),
            name=detail.get("name", ""),
            quantity=int(detail.get("quantity", 0)),
            total_cost=detail.get("total_cost") or ZERO,
            price=price,
            previous_close=prev_close,
            daily_change_pct=daily,
            weight_pct=value / total * HUNDRED if value and total and total > 0 else ZERO,
        )

    def _previous_close_map(self, stock_ids: List[int]) -> Dict[int, Decimal]:
        """Hisselerin bir önceki kapanış fiyatları (güncel fiyatın gününden önceki son kapanış)."""
        result: Dict[int, Decimal] = {}
        if not self._lookup:
            return result
        try:
            resolved_map = self._resolver.resolve(stock_ids) if self._resolver is not None else {}
            for sid in stock_ids:
                resolved = resolved_map.get(sid)
                if resolved is not None:
                    previous = self._resolver.previous_close(sid, resolved)
                    if previous is not None:
                        result[sid] = previous
                    continue
                prev_close = self._lookup.get_previous_close(sid)
                if prev_close is not None:
                    result[sid] = prev_close
        except Exception as exc:
            logger.warning("Previous close map hatası: %s", exc)
        return result

    # ---- hisse fiyatı -----------------------------------------------------------------------------

    def quote(self, ticker: str, stock_id: Optional[int] = None) -> Quote:
        """Güncel fiyat ve günlük değişim: çözümleyici, canlı önbellek, DuckDB piyasa geçmişi, SQLite kapanışı sırasıyla."""
        clean = clean_ticker(ticker)
        price = ZERO

        if self._resolver is not None and stock_id:
            try:
                resolved = self._resolver.resolve([stock_id]).get(stock_id)
                if resolved is not None:
                    change = self._resolver.daily_change_pct(stock_id, resolved)
                    return Quote(resolved.price, change if change is not None else ZERO)
            except Exception as exc:
                logger.debug("current_price_resolver başarısız: %s", exc)

        if self._lookup is None:
            return Quote()

        if stock_id:
            live = self._lookup.get_latest_price_map([stock_id]).get(stock_id)
            if live is not None:
                price = live
            if price > 0:
                prev_close = self._lookup.get_previous_close(stock_id)
                if prev_close:
                    return Quote(price, (price - prev_close) / prev_close * HUNDRED)

        bars = self._lookup.get_last_market_bars(clean, 2)
        if bars:
            last = Decimal(str(bars[0].close_price))
            before = Decimal(str(bars[1].close_price)) if len(bars) > 1 else last
            return Quote(price if price > 0 else last, (last - before) / before * HUNDRED if before > 0 else ZERO)

        close = self._lookup.get_previous_close(stock_id) if stock_id else self._lookup.get_latest_close(clean)
        if close:
            return Quote(price if price > 0 else Decimal(str(close)), ZERO)
        return Quote(price, ZERO)
