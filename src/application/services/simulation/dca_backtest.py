"""
DCA (Düzenli Katkı) Backtest Motoru — saf simülasyon hesabı.

"Geçmişte her ay X TL hisse alsaydım" senaryosu (bkz. TRANSFORMATION_PLAN.md §3.3).
Ağsız, durumsuz, IO yok — saf fonksiyon. DB erişimi ve ticker/tarih hazırlığı
`dca_backtest_service.py`'dedir (golden_cross.py / technical_analysis_service.py
ile aynı "saf hesap + orkestrasyon" desenine uyar).

v1 kapsamı: sabit periyotta (aylık) sabit tutarlı katkı, sabit ağırlıklarla
dağıtılır (Markowitz/periyodik rebalancing ayrı bir alt-faz — bkz. TRANSFORMATION_PLAN.md §9.12).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional


@dataclass(frozen=True)
class DCABacktestResult:
    """simulate_dca() dönüş değeri — pure veri (DB yok)."""
    portfolio_value_series: Dict[date, Decimal]
    total_invested: Decimal
    final_value: Decimal
    shares_by_ticker: Dict[str, Decimal]
    total_return_pct: Optional[float]
    contribution_count: int


def simulate_dca(
    price_series: Dict[date, Dict[str, Decimal]],
    tickers: List[str],
    weights: Dict[str, float],
    contribution_amount: Decimal,
    contribution_dates: List[date],
) -> DCABacktestResult:
    """
    price_series: trading_date -> {ticker: close_price}. Tüm ticker'lar her günde
        olmak zorunda değil — eksik günler son bilinen fiyatla (carry-forward) doldurulur.
    weights: ticker -> pay (0-1 arası); toplamı 1.0 olmalı (çağıran taraf sorumludur).
    contribution_dates: yeni paranın yatırıldığı tarihler (örn. her ayın ilk işlem günü).

    Dönüş: contribution_dates'in en küçüğünden itibaren, price_series'teki her
    tarih için portföy değeri serisi + özet istatistikler.
    """
    if not price_series or not tickers or not contribution_dates:
        return DCABacktestResult(
            portfolio_value_series={},
            total_invested=Decimal("0"),
            final_value=Decimal("0"),
            shares_by_ticker={t: Decimal("0") for t in tickers},
            total_return_pct=None,
            contribution_count=0,
        )

    sorted_dates = sorted(price_series.keys())
    first_contribution_date = min(contribution_dates)
    contribution_date_set = set(contribution_dates)

    shares: Dict[str, Decimal] = {t: Decimal("0") for t in tickers}
    last_known_price: Dict[str, Decimal] = {}
    value_series: Dict[date, Decimal] = {}
    total_invested = Decimal("0")
    contribution_count = 0

    for current_date in sorted_dates:
        _update_last_known_prices(price_series.get(current_date, {}), tickers, last_known_price)

        if current_date in contribution_date_set:
            invested_today = _apply_contribution(
                tickers, weights, contribution_amount, last_known_price, shares
            )
            if invested_today > 0:
                total_invested += invested_today
                contribution_count += 1

        if current_date >= first_contribution_date:
            value_series[current_date] = _portfolio_value(shares, last_known_price, tickers)

    final_value = value_series[sorted_dates[-1]] if sorted_dates and sorted_dates[-1] in value_series else Decimal("0")
    total_return_pct = (
        float(((final_value - total_invested) / total_invested) * Decimal("100"))
        if total_invested > 0
        else None
    )

    return DCABacktestResult(
        portfolio_value_series=value_series,
        total_invested=total_invested,
        final_value=final_value,
        shares_by_ticker=shares,
        total_return_pct=total_return_pct,
        contribution_count=contribution_count,
    )


def _update_last_known_prices(
    day_prices: Dict[str, Decimal],
    tickers: List[str],
    last_known_price: Dict[str, Decimal],
) -> None:
    for ticker in tickers:
        price = day_prices.get(ticker)
        if price is not None and price > 0:
            last_known_price[ticker] = price


def _apply_contribution(
    tickers: List[str],
    weights: Dict[str, float],
    contribution_amount: Decimal,
    last_known_price: Dict[str, Decimal],
    shares: Dict[str, Decimal],
) -> Decimal:
    invested_today = Decimal("0")
    for ticker in tickers:
        price = last_known_price.get(ticker)
        weight = weights.get(ticker, 0.0)
        if price is None or price <= 0 or weight <= 0:
            continue
        amount_for_ticker = contribution_amount * Decimal(str(weight))
        shares[ticker] = shares.get(ticker, Decimal("0")) + (amount_for_ticker / price)
        invested_today += amount_for_ticker
    return invested_today


def _portfolio_value(
    shares: Dict[str, Decimal],
    last_known_price: Dict[str, Decimal],
    tickers: List[str],
) -> Decimal:
    total = Decimal("0")
    for ticker in tickers:
        price = last_known_price.get(ticker)
        if price is not None:
            total += shares.get(ticker, Decimal("0")) * price
    return total


def equal_weights(tickers: List[str]) -> Dict[str, float]:
    """Basit eşit ağırlık dağılımı — v1 varsayılan strateji."""
    if not tickers:
        return {}
    weight = 1.0 / len(tickers)
    return {ticker: weight for ticker in tickers}


def monthly_contribution_dates(available_dates: List[date]) -> List[date]:
    """Verilen (sıralı olması gerekmeyen) tarih kümesinden, her ay için o aydaki
    en erken tarihi seçer — "ayın ilk işlem günü" kuralı. Veri olmayan aylar atlanır."""
    if not available_dates:
        return []
    earliest_by_month: Dict[tuple, date] = {}
    for d in available_dates:
        key = (d.year, d.month)
        if key not in earliest_by_month or d < earliest_by_month[key]:
            earliest_by_month[key] = d
    return sorted(earliest_by_month.values())
