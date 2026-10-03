"""
Strateji backtest motoru — periyodik yeniden dengeleme ve stop-loss / take-profit simülasyonu (saf hesap).

Ağsız, durumsuz, IO yok (dca_backtest.py ile aynı "saf hesap + orkestrasyon" deseni; DB ve optimizasyon
`strategy_backtest_service.py`'dedir). Her simülasyon aynı başlangıç dağılımıyla "al ve tut" taban çizgisini de
hesaplar; böylece stratejinin getiriye katkısı doğrudan karşılaştırılır.

Varsayımlar (arayüzde de belirtilir):
- İşlemler günlük kapanış fiyatından yapılır; gün içi dalgalanma ve fiyat boşluğu (gap) modellenmez.
- Kesirli lot kullanılır; nakit getirisi sıfırdır.
- `commission_rate` alım ve satım tutarının oranıdır (örn. 0.001 = binde bir), varsayılan 0'dır.
- Tüm hisselerin fiyatı olan ilk işlem günü başlangıç günüdür; ondan önceki barlar yalnızca ağırlık hesabı için geçmiş sağlar.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Callable, Dict, List, Optional, Sequence

import pandas as pd

PriceSeries = Dict[date, Dict[str, Decimal]]
WeightFunction = Callable[[date, pd.DataFrame], Dict[str, float]]

_EPSILON = 1e-9
_MIN_WEIGHT_CHANGE = 0.005  # olay listesine yalnızca %0,5'ten büyük ağırlık değişimleri yazılır


@dataclass(frozen=True)
class StrategyEvent:
    event_date: date
    ticker: str          # genel olaylarda boş
    action: str          # REBALANCE | STOP_LOSS | TAKE_PROFIT | FALLBACK
    detail: str


@dataclass(frozen=True)
class StrategyBacktestResult:
    start_date: Optional[date]
    end_date: Optional[date]
    initial_capital: Decimal
    strategy_series: Dict[date, Decimal]
    baseline_series: Dict[date, Decimal]
    final_value: Decimal
    baseline_final_value: Decimal
    total_return_pct: Optional[float]
    baseline_return_pct: Optional[float]
    max_drawdown_pct: Optional[float]
    baseline_max_drawdown_pct: Optional[float]
    events: List[StrategyEvent]
    rebalance_count: int = 0
    exit_count: int = 0
    skipped_tickers: Sequence[str] = ()


def equal_weight_function(tickers: Sequence[str]) -> WeightFunction:
    weights = {t: 1.0 / len(tickers) for t in tickers} if tickers else {}
    return lambda _as_of, _history: dict(weights)


def build_price_matrix(price_series: PriceSeries, tickers: Sequence[str]) -> tuple[pd.DataFrame, List[str]]:
    """Tarih x ticker fiyat matrisi (eksik günler son bilinen fiyatla doldurulur) ve verisi olmayan tickerlar."""
    rows = {d: {t: float(p) for t, p in prices.items() if t in tickers and p is not None and p > 0}
            for d, prices in price_series.items()}
    frame = pd.DataFrame.from_dict(rows, orient="index").sort_index()
    present = [t for t in tickers if t in frame.columns and frame[t].notna().any()]
    skipped = [t for t in tickers if t not in present]
    return frame[present].ffill(), skipped


def rebalance_dates(trading_dates: Sequence[date], start: date, every_months: int) -> List[date]:
    """Başlangıçtan sonra her `every_months` ayda bir, o ayın ilk işlem günü."""
    if every_months < 1:
        raise ValueError("Yeniden dengeleme aralığı en az 1 ay olmalıdır.")
    start_index = start.year * 12 + start.month
    first_of_month: Dict[int, date] = {}
    for d in sorted(trading_dates):
        if d <= start:
            continue
        first_of_month.setdefault(d.year * 12 + d.month, d)
    return [
        d for index, d in sorted(first_of_month.items())
        if index > start_index and (index - start_index) % every_months == 0
    ]


def max_drawdown_pct(series: Dict[date, Decimal]) -> Optional[float]:
    """Zirveden en büyük düşüş (negatif yüzde); seri boşsa None."""
    if not series:
        return None
    peak = None
    worst = 0.0
    for d in sorted(series):
        value = float(series[d])
        peak = value if peak is None else max(peak, value)
        if peak and peak > 0:
            worst = min(worst, value / peak - 1.0)
    return worst * 100.0


def simulate_rebalancing(
    price_series: PriceSeries,
    tickers: Sequence[str],
    initial_capital: Decimal,
    start_date: date,
    rebalance_every_months: int,
    weight_fn: WeightFunction,
    commission_rate: float = 0.0,
) -> StrategyBacktestResult:
    """Periyodik yeniden dengeleme ile "al ve tut" karşılaştırması."""
    prices, skipped = build_price_matrix(price_series, list(tickers))
    sim_dates = _simulation_dates(prices, start_date)
    if not sim_dates:
        return _empty_result(initial_capital, skipped)

    columns = list(prices.columns)
    start = sim_dates[0]
    capital = float(initial_capital)
    events: List[StrategyEvent] = []

    weights = _target_weights(weight_fn, start, prices, columns, events)
    investable = capital * (1.0 - commission_rate)
    shares = {t: investable * weights[t] / prices.at[start, t] for t in columns if weights[t] > 0}
    baseline_shares = dict(shares)

    rebalance_set = set(rebalance_dates(sim_dates, start, rebalance_every_months))
    strategy_series: Dict[date, Decimal] = {}
    baseline_series: Dict[date, Decimal] = {}
    rebalance_count = 0

    for d in sim_dates:
        if d in rebalance_set:
            new_weights = _target_weights(weight_fn, d, prices, columns, events)
            before = _current_weights(shares, prices.loc[d])
            shares, changed = _rebalance(shares, new_weights, prices.loc[d], commission_rate)
            events.extend(_rebalance_events(d, before, new_weights))
            rebalance_count += 1 if changed else 0
        strategy_series[d] = _money(_market_value(shares, prices.loc[d]))
        baseline_series[d] = _money(_market_value(baseline_shares, prices.loc[d]))

    return _build_result(initial_capital, strategy_series, baseline_series, events, skipped, rebalance_count=rebalance_count)


def simulate_stop_take(
    price_series: PriceSeries,
    tickers: Sequence[str],
    initial_capital: Decimal,
    start_date: date,
    stop_loss_pct: Optional[float],
    take_profit_pct: Optional[float],
    commission_rate: float = 0.0,
) -> StrategyBacktestResult:
    """Eşit ağırlıkla alım; her pozisyon giriş fiyatına göre stop-loss / take-profit eşiğinde satılır ve nakde geçer.

    Satılan pozisyon yeniden alınmaz (tek giriş). Eşik kontrolü günlük kapanış fiyatıyla yapılır.
    """
    if stop_loss_pct is None and take_profit_pct is None:
        raise ValueError("Stop-loss veya take-profit eşiklerinden en az biri verilmelidir.")
    prices, skipped = build_price_matrix(price_series, list(tickers))
    sim_dates = _simulation_dates(prices, start_date)
    if not sim_dates:
        return _empty_result(initial_capital, skipped)

    columns = list(prices.columns)
    start = sim_dates[0]
    investable = float(initial_capital) * (1.0 - commission_rate)
    entry = {t: float(prices.at[start, t]) for t in columns}
    shares = {t: investable / len(columns) / entry[t] for t in columns}
    baseline_shares = dict(shares)
    cash = 0.0
    events: List[StrategyEvent] = []
    strategy_series: Dict[date, Decimal] = {}
    baseline_series: Dict[date, Decimal] = {}
    exit_count = 0

    for d in sim_dates:
        day = prices.loc[d]
        if d != start:
            for ticker in list(shares):
                change = float(day[ticker]) / entry[ticker] - 1.0
                reason = _exit_reason(change, stop_loss_pct, take_profit_pct)
                if reason is None:
                    continue
                cash += shares.pop(ticker) * float(day[ticker]) * (1.0 - commission_rate)
                exit_count += 1
                events.append(StrategyEvent(d, ticker, reason, f"{ticker}: giriş fiyatına göre %{change * 100:+.1f}"))
        strategy_series[d] = _money(cash + _market_value(shares, day))
        baseline_series[d] = _money(_market_value(baseline_shares, day))

    return _build_result(initial_capital, strategy_series, baseline_series, events, skipped, exit_count=exit_count)


# ---------------------------------------------------------------- yardımcılar

def _simulation_dates(prices: pd.DataFrame, start_date: date) -> List[date]:
    """Tüm hisselerin fiyatı olan ilk günden (ve istenen başlangıçtan) itibaren işlem günleri."""
    if prices.empty:
        return []
    complete = prices.dropna()
    dates = [d for d in complete.index if d >= start_date]
    return sorted(dates)


def _target_weights(
    weight_fn: WeightFunction,
    as_of: date,
    prices: pd.DataFrame,
    columns: Sequence[str],
    events: List[StrategyEvent],
) -> Dict[str, float]:
    history = prices.loc[:as_of]
    try:
        raw = weight_fn(as_of, history)
    except ValueError as exc:
        events.append(StrategyEvent(as_of, "", "FALLBACK", f"Ağırlık hesaplanamadı, eşit ağırlık kullanıldı: {exc}"))
        raw = {t: 1.0 for t in columns}
    cleaned = {t: max(float(raw.get(t, 0.0)), 0.0) for t in columns}
    total = sum(cleaned.values())
    if total <= 0:
        cleaned = {t: 1.0 for t in columns}
        total = float(len(columns))
    return {t: w / total for t, w in cleaned.items()}


def _market_value(shares: Dict[str, float], day: pd.Series) -> float:
    return sum(quantity * float(day[ticker]) for ticker, quantity in shares.items())


def _rebalance(
    shares: Dict[str, float],
    weights: Dict[str, float],
    day: pd.Series,
    commission_rate: float,
) -> tuple[Dict[str, float], bool]:
    value = _market_value(shares, day)
    current = {t: shares.get(t, 0.0) * float(day[t]) for t in weights}
    targets = {t: value * w for t, w in weights.items()}
    traded = sum(abs(targets[t] - current[t]) for t in weights)
    net_value = value - traded * commission_rate
    new_shares = {t: net_value * w / float(day[t]) for t, w in weights.items() if w > 0}
    return new_shares, traded > value * 1e-9


def _current_weights(shares: Dict[str, float], day: pd.Series) -> Dict[str, float]:
    value = _market_value(shares, day)
    return {t: quantity * float(day[t]) / value for t, quantity in shares.items()} if value > 0 else {}


def _rebalance_events(d: date, before: Dict[str, float], target: Dict[str, float]) -> List[StrategyEvent]:
    """Dengeleme öncesi (fiyat kaymasıyla oluşmuş) ağırlık ile hedef ağırlık farkı belirgin olan hisseler."""
    events = []
    for ticker, weight in target.items():
        current = before.get(ticker, 0.0)
        if abs(weight - current) > _MIN_WEIGHT_CHANGE:
            events.append(StrategyEvent(
                d, ticker, "REBALANCE", f"{ticker}: ağırlık %{current * 100:.1f} -> %{weight * 100:.1f}",
            ))
    return events


def _exit_reason(change: float, stop_loss_pct: Optional[float], take_profit_pct: Optional[float]) -> Optional[str]:
    # Eşiğe tam denk gelen fiyat kayan nokta hatasıyla kaçmasın diye küçük bir tolerans uygulanır.
    if stop_loss_pct is not None and change <= -stop_loss_pct / 100.0 + _EPSILON:
        return "STOP_LOSS"
    if take_profit_pct is not None and change >= take_profit_pct / 100.0 - _EPSILON:
        return "TAKE_PROFIT"
    return None


def _money(value: float) -> Decimal:
    return Decimal(str(round(value, 2)))


def _return_pct(final: Decimal, initial: Decimal) -> Optional[float]:
    return float((final / initial - 1) * 100) if initial > 0 else None


def _build_result(
    initial_capital: Decimal,
    strategy_series: Dict[date, Decimal],
    baseline_series: Dict[date, Decimal],
    events: List[StrategyEvent],
    skipped: Sequence[str],
    rebalance_count: int = 0,
    exit_count: int = 0,
) -> StrategyBacktestResult:
    last = max(strategy_series)
    final_value, baseline_final = strategy_series[last], baseline_series[last]
    return StrategyBacktestResult(
        start_date=min(strategy_series),
        end_date=last,
        initial_capital=initial_capital,
        strategy_series=strategy_series,
        baseline_series=baseline_series,
        final_value=final_value,
        baseline_final_value=baseline_final,
        total_return_pct=_return_pct(final_value, initial_capital),
        baseline_return_pct=_return_pct(baseline_final, initial_capital),
        max_drawdown_pct=max_drawdown_pct(strategy_series),
        baseline_max_drawdown_pct=max_drawdown_pct(baseline_series),
        events=events,
        rebalance_count=rebalance_count,
        exit_count=exit_count,
        skipped_tickers=list(skipped),
    )


def _empty_result(initial_capital: Decimal, skipped: Sequence[str]) -> StrategyBacktestResult:
    zero = Decimal("0")
    return StrategyBacktestResult(
        start_date=None, end_date=None, initial_capital=initial_capital, strategy_series={}, baseline_series={},
        final_value=zero, baseline_final_value=zero, total_return_pct=None, baseline_return_pct=None,
        max_drawdown_pct=None, baseline_max_drawdown_pct=None, events=[], skipped_tickers=list(skipped),
    )
