"""Model portföy sunumu (Qt'siz): özet alanlarını ve pozisyon satırlarını biçimler.

Rakamlar `PositionQueryService` ve `ModelPortfolioService` özetinden gelir (hesap burada yapılmaz); bu modül yalnızca
metne çevirir ve QML'in beklediği sözlük biçimini kurar.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List

from src.domain.models.position_snapshot import PositionSnapshot
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


def _change_text(value) -> str:
    return tr_pct(value, with_sign=True) if value is not None else "-"


def position_row(snapshot: PositionSnapshot) -> Dict[str, Any]:
    """Tek pozisyonun QML satırı; fiyatı olmayan pozisyonda değer ve K/Z alanları 0 gösterilir."""
    priced = snapshot.is_priced
    daily, total = snapshot.daily_change_pct, snapshot.total_change_pct
    return {
        "stockId": snapshot.stock_id,
        "ticker": display_ticker(snapshot.ticker),
        "companyName": snapshot.name,
        "quantity": snapshot.quantity,
        "avgCost": float(snapshot.avg_cost),
        "currentPrice": float(snapshot.price) if priced else 0.0,
        "currentValue": float(snapshot.market_value) if priced else 0.0,
        "totalCost": float(snapshot.total_cost),
        "profitLoss": float(snapshot.unrealized_pl) if priced else 0.0,
        "dailyChangePct": float(daily) if daily is not None else 0.0,
        "totalChangePct": float(total) if total is not None else 0.0,
        "weight": float(snapshot.weight_pct),
        "profitLossFormatted": tr_money(snapshot.unrealized_pl) if priced and snapshot.unrealized_pl else ZERO_MONEY,
        "dailyChangeFormatted": _change_text(daily),
        "totalChangeFormatted": _change_text(total),
    }


class ModelPortfolioValuation:
    def __init__(self, service, query_service) -> None:
        self._service = service
        self._query = query_service

    def resolve_prices(self, stock_ids: list) -> Dict[int, Decimal]:
        return self._query.resolve_prices(stock_ids)

    def price_map(self, portfolio_id: int) -> Dict[int, Decimal]:
        return self._query.model_price_map(portfolio_id)

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

    def position_rows(self, portfolio_id: int, price_map: Dict[int, Decimal]) -> List[Dict[str, Any]]:
        return [position_row(p) for p in self._query.model_positions(portfolio_id, price_map).positions]
