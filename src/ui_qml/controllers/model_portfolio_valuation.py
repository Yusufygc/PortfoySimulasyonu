"""Model portföy değerleme (Qt'siz): fiyat haritası, önceki kapanış, özet alanları ve pozisyon satırları.

`ModelPortfolioController` yalnızca durumu tutar ve sinyal yayar; sayılar ve biçimleme burada üretilir.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List

from src.ui_qml.presenters.formatting import tr_money, tr_pct

logger = logging.getLogger(__name__)

ZERO_MONEY = "₺0,00"


def display_ticker(ticker: str) -> str:
    text = (ticker or "").strip()
    return text[:-3] if text.upper().endswith(".IS") else text


def profit_loss_state(profit_loss: Decimal) -> str:
    rounded = round(profit_loss, 2)
    if rounded > 0:
        return "positive"
    return "negative" if rounded < 0 else "neutral"


def empty_summary() -> Dict[str, Any]:
    return {
        "net_capital": ZERO_MONEY, "remaining_cash": ZERO_MONEY, "remaining_cash_raw": Decimal("0"),
        "total_value": ZERO_MONEY, "profit_loss": ZERO_MONEY, "profit_loss_pct": 0.0, "state": "neutral",
    }


class ModelPortfolioValuation:
    def __init__(self, service, lookup, container=None) -> None:
        self._service = service
        self._lookup = lookup
        self._container = container

    def _resolver(self):
        return getattr(self._container, "current_price_resolver", None) if self._container else None

    def resolve_prices(self, stock_ids: list) -> Dict[int, Decimal]:
        """Güncel fiyat: önce çözümleyici (canlı/kapanış), yoksa canlı önbellek, eksikler için son kapanış."""
        price_map: Dict[int, Decimal] = {}
        resolver = self._resolver()
        if resolver is not None:
            price_map.update(resolver.price_map(stock_ids))
        elif self._lookup:
            price_map.update(self._lookup.get_latest_price_map(stock_ids))
        if self._lookup:
            for sid in [sid for sid in stock_ids if sid not in price_map]:
                close = self._lookup.get_previous_close(sid)
                if close is not None:
                    price_map[sid] = close
        return price_map

    def price_map(self, portfolio_id: int) -> Dict[int, Decimal]:
        """Portföydeki hisselerin fiyatları; okunamazsa boş harita."""
        try:
            return self.resolve_prices(sorted(self._service.get_positions(portfolio_id).keys()))
        except Exception as exc:
            logger.warning("Fiyat haritası yüklenemedi: %s", exc)
            return {}

    def previous_close_map(self, positions: list) -> Dict[int, Decimal]:
        """Pozisyondaki hisselerin bir önceki kapanış fiyatları."""
        result: Dict[int, Decimal] = {}
        if not self._lookup:
            return result
        try:
            stock_ids = [pos.get("stock_id") for pos in positions if pos.get("stock_id")]
            resolver = self._resolver()
            resolved_map = resolver.resolve(stock_ids) if resolver is not None else {}
            for sid in stock_ids:
                resolved = resolved_map.get(sid)
                if resolved is not None:
                    # Önceki kapanış, güncel fiyatın gününden önceki son kapanıştır
                    previous = resolver.previous_close(sid, resolved)
                    if previous is not None:
                        result[sid] = previous
                    continue
                prev_close = self._lookup.get_previous_close(sid)
                if prev_close is not None:
                    result[sid] = prev_close
        except Exception as exc:
            logger.warning("Previous close map hatası: %s", exc)
        return result

    def summary(self, portfolio_id: int, price_map: Dict[int, Decimal]) -> Dict[str, Any]:
        raw = self._service.get_portfolio_summary(portfolio_id, price_map)
        remaining_cash = raw.get("remaining_cash", Decimal("0"))
        profit_loss = raw.get("profit_loss", Decimal("0"))
        return {
            "net_capital": tr_money(raw.get("net_capital", raw.get("initial_cash", Decimal("0")))),
            "remaining_cash": tr_money(remaining_cash),
            "remaining_cash_raw": remaining_cash,
            "total_value": tr_money(raw.get("total_value", Decimal("0"))),
            "profit_loss": tr_money(profit_loss),
            "profit_loss_pct": float(raw.get("profit_loss_pct", Decimal("0"))),
            "state": profit_loss_state(profit_loss),
        }

    def _total_value(self, portfolio_id: int, price_map: Dict[int, Decimal]) -> Decimal:
        # Ağırlık paydası bir kez hesaplanır (eskiden her pozisyonda yeniden: O(N²))
        try:
            return self._service.get_portfolio_summary(portfolio_id, price_map).get("total_value", Decimal("0"))
        except Exception:
            logger.warning("Model portföy toplam değeri hesaplanamadı; ağırlık 0 gösterilecek.", exc_info=True)
            return Decimal("0")

    def position_rows(self, portfolio_id: int, price_map: Dict[int, Decimal]) -> List[Dict[str, Any]]:
        positions = self._service.get_positions_with_details(portfolio_id, price_map)
        prev_close_map = self.previous_close_map(positions)
        total_val = self._total_value(portfolio_id, price_map)
        return [self._row(pos, prev_close_map, total_val) for pos in positions]

    @staticmethod
    def _row(pos: Dict[str, Any], prev_close_map: Dict[int, Decimal], total_val: Decimal) -> Dict[str, Any]:
        stock_id = pos.get("stock_id")
        current_price = pos.get("current_price")
        avg_cost = pos.get("avg_cost")
        current_value = pos.get("current_value")
        total_cost = pos.get("total_cost")
        profit_loss = pos.get("profit_loss")

        prev_close = prev_close_map.get(stock_id)
        daily_change_pct = None
        if current_price and prev_close and prev_close > 0:
            daily_change_pct = float(((current_price - prev_close) / prev_close) * 100)
        total_change_pct = None
        if current_price and avg_cost and avg_cost > 0:
            total_change_pct = float(((current_price - avg_cost) / avg_cost) * 100)
        weight = float((current_value / total_val) * 100) if current_value and total_val and total_val > 0 else 0.0

        return {
            "stockId": stock_id,
            "ticker": display_ticker(pos.get("ticker", "")),
            "companyName": pos.get("name", ""),
            "quantity": pos.get("quantity", 0),
            "avgCost": float(avg_cost) if avg_cost else 0.0,
            "currentPrice": float(current_price) if current_price else 0.0,
            "currentValue": float(current_value) if current_value else 0.0,
            "totalCost": float(total_cost) if total_cost else 0.0,
            "profitLoss": float(profit_loss) if profit_loss else 0.0,
            "dailyChangePct": daily_change_pct if daily_change_pct is not None else 0.0,
            "totalChangePct": total_change_pct if total_change_pct is not None else 0.0,
            "weight": weight,
            "profitLossFormatted": tr_money(profit_loss) if profit_loss else ZERO_MONEY,
            "dailyChangeFormatted": _change_text(daily_change_pct),
            "totalChangeFormatted": _change_text(total_change_pct),
        }


def _change_text(value) -> str:
    return tr_pct(Decimal(str(value)), with_sign=True) if value is not None else "-"
