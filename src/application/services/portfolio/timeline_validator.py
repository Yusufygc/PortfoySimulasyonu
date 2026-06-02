from collections import defaultdict
from datetime import date, time as dt_time
from decimal import Decimal
from typing import Iterable, List, Optional, Tuple

from src.domain.models.cash_movement import CashMovementType
from src.domain.models.trade import Trade, TradeSide

class PortfolioTimelineValidator:
    """
    Geçmişe dönük işlem girişlerinde zaman çizelgesinin bozulup bozulmadığını
    kontrol eden SRP odaklı doğrulayıcı servis.
    """
    
    @classmethod
    def validate_candidate_timeline(
        cls, 
        candidate: Trade, 
        existing_trades: list[Trade], 
        cash_movements: list[tuple[date, dt_time, int, int, object, Decimal]]
    ) -> None:
        baseline_violations = {
            marker for marker, _reason in cls._timeline_violations(existing_trades, cash_movements)
        }
        candidate_marker = ("candidate", id(candidate))
        candidate_violations = cls._timeline_violations(
            list(existing_trades) + [candidate],
            cash_movements,
            candidate_marker=candidate_marker,
        )

        for marker, reason in candidate_violations:
            if marker == candidate_marker:
                raise ValueError(reason)
            if marker not in baseline_violations:
                raise ValueError(
                    "Bu tarih/saat ile işlem, sonraki nakit veya lot akışını geçersiz hale getiriyor."
                )

    @classmethod
    def _timeline_violations(
        cls,
        trades: list[Trade],
        cash_movements: list[tuple[date, dt_time, int, int, object, Decimal]],
        candidate_marker: tuple | None = None,
    ) -> list[tuple[object, str]]:
        cash = Decimal("0")
        positions: dict[int, int] = defaultdict(int)
        violations: list[tuple[object, str]] = []
        events = cls._timeline_events(trades, cash_movements, candidate_marker)

        for _event_date, _event_time, _event_order, event_id, event_type, payload, marker in events:
            cash = cls._apply_event(event_id, event_type, payload, marker, cash, positions, violations)
        return violations

    @classmethod
    def _timeline_events(
        cls,
        trades: list[Trade],
        cash_movements: list[tuple[date, dt_time, int, int, object, Decimal]],
        candidate_marker: tuple | None = None,
    ) -> list[tuple[date, dt_time, int, int, object, object, object]]:
        events: list[tuple[date, dt_time, int, int, object, object, object]] = []
        for event_date, event_time, event_order, event_id, event_type, amount in cash_movements:
            events.append((event_date, event_time, event_order, event_id, event_type, amount, None))

        for index, trade in enumerate(trades):
            marker = candidate_marker if candidate_marker is not None and index == len(trades) - 1 else cls._trade_marker(trade)
            events.append(
                (
                    trade.trade_date,
                    trade.trade_time or dt_time.min,
                    20,
                    int(trade.id or (10**12 if marker == candidate_marker else 0)),
                    "TRADE",
                    trade,
                    marker,
                )
            )

        events.sort(key=lambda event: (event[0], event[1], event[2], event[3]))
        return events

    @classmethod
    def _apply_event(cls, event_id, event_type, payload, marker, cash, positions, violations) -> Decimal:
        if event_type == CashMovementType.DEPOSIT:
            return cash + payload
        if event_type == CashMovementType.WITHDRAW:
            return cls._apply_withdraw(event_id, payload, marker, cash, violations)
        return cls._apply_trade_event(payload, marker, cash, positions, violations)

    @staticmethod
    def _apply_withdraw(event_id, amount: Decimal, marker, cash: Decimal, violations) -> Decimal:
        if amount > cash:
            violations.append((marker or ("cash", event_id), "Yetersiz nakit. Nakit çekimi bakiyeyi aşıyor."))
            return Decimal("0")
        return cash - amount

    @classmethod
    def _apply_trade_event(cls, trade: Trade, marker, cash: Decimal, positions, violations) -> Decimal:
        if trade.side == TradeSide.BUY:
            return cls._apply_buy_trade(trade, marker, cash, positions, violations)
        available = positions[trade.stock_id]
        if trade.quantity > available:
            violations.append((marker, f"Yetersiz pozisyon. Satmak istediğiniz: {trade.quantity}, Mevcut: {available}"))
            return cash
        positions[trade.stock_id] -= trade.quantity
        return cash + trade.total_amount

    @staticmethod
    def _apply_buy_trade(trade: Trade, marker, cash: Decimal, positions, violations) -> Decimal:
        if trade.total_amount > cash:
            violations.append((marker, f"Yetersiz nakit. Gerekli: {trade.total_amount:.2f} TL, Mevcut: {cash:.2f} TL"))
            cash = Decimal("0")
        else:
            cash -= trade.total_amount
        positions[trade.stock_id] += trade.quantity
        return cash

    @staticmethod
    def _trade_marker(trade: Trade) -> object:
        return ("trade", int(trade.id)) if trade.id is not None else ("trade_object", id(trade))
