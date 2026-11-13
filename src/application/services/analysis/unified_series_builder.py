"""Birleşik portföy (BIST + BIST dışı varlıklar + TL/USD nakit havuzu) günlük değer ve TWR serisi.

Her gün sonunda toplam değer TL cinsinden hesaplanır: TL nakit + USD nakit x USDTRY + BIST pozisyonları + varlık
pozisyonları. TWR'yi bozmamak için yalnızca portföye dışarıdan giren/çıkan sermaye "dış akış" sayılır:

- gerçek nakit yatırma/çekme (temettü getiridir, akış değildir),
- nakde bağlı olmayan eski varlık işlemleri (alım giriş, satım çıkış sayılır),
- TL nakdini aşan harcamanın (alım, döviz çevirme) karşılanmayan kısmı (dışarıdan gelen sermaye; nakit 0'da kalır).

Havuz içi hareketler (döviz çevirme, nakde bağlı varlık ve BIST işlemleri) akış değildir. Hiç gerçek nakit hareketi
yoksa nakit izlenmez ve tüm işlemler (BIST ve varlık) dış akış olarak sayılır; bu BIST'e özel serideki davranışla aynıdır.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time, timedelta
from decimal import Decimal
from typing import Dict, List, NamedTuple, Optional

from src.application.services.portfolio.safe_portfolio_builder import build_portfolio_safely
from src.domain.models.asset import Asset
from src.domain.models.asset_position import AssetLedger
from src.domain.models.cash_movement import CashMovementType
from src.domain.models.fx_conversion import FxSide
from src.domain.models.trade import TradeSide

from .portfolio_series_builder import _advance_twr_index

ZERO = Decimal("0")
HUNDRED = Decimal("100")
_KIND_ORDER = {"cash": 0, "fx": 1, "bist": 2, "asset": 3}


@dataclass
class UnifiedSeries:
    values: Dict[date, Decimal] = field(default_factory=dict)       # günlük toplam değer (TL)
    twr: Dict[date, Decimal] = field(default_factory=dict)          # TWR endeksi (taban 100)
    holdings: List[dict] = field(default_factory=list)              # bitiş günü pozisyonları (nakit hariç)
    warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class _Event:
    day: date
    at: time
    kind: str
    item: object

    @property
    def sort_key(self):
        return (self.day, self.at, _KIND_ORDER[self.kind])


class _Carry:
    """Gün gün en son bilinen değeri taşır (hafta sonu/tatil boşlukları son kapanışla dolar)."""

    def __init__(self, by_day: Dict[date, Decimal], last: Optional[Decimal]) -> None:
        self._by_day = by_day
        self._last = last

    def at(self, day: date) -> Optional[Decimal]:
        value = self._by_day.get(day)
        if value is not None:
            self._last = value
        return self._last


@dataclass
class _State:
    tracking: bool
    try_cash: Decimal = ZERO
    usd_cash: Decimal = ZERO
    bist_qty: Dict[int, Decimal] = field(default_factory=dict)
    bist_cost: Dict[int, Decimal] = field(default_factory=dict)          # ortalama maliyet toplamı (fiyat yoksa yedek)
    bist_unpriced: set = field(default_factory=set)                      # yedek fiyatla değerlenen hisse kimlikleri
    asset_qty: Dict[int, Decimal] = field(default_factory=dict)
    asset_trade_price: Dict[int, Decimal] = field(default_factory=dict)   # son işlem TL birim fiyatı (fiyat yoksa yedek)
    fx_hint: Optional[Decimal] = None                                   # son döviz işlemi kuru (kur serisi yoksa yedek)


class _EventApplier:
    """Olayın durum (nakit ve miktarlar) üzerindeki etkisini uygular; dış sermaye akışını (TL) döner."""

    @staticmethod
    def _change_try_cash(state: _State, delta: Decimal) -> Decimal:
        """TL nakdi `delta` kadar değiştirir. Nakdi aşan harcamada nakit 0'da kalır; karşılanmayan kısım
        dışarıdan gelen sermayedir ve dış akış olarak döner (aksi halde getiri gibi görünürdü)."""
        new_cash = state.try_cash + delta
        state.try_cash = max(ZERO, new_cash)
        return max(ZERO, -new_cash)

    @staticmethod
    def _apply_cash(state: _State, movement) -> Decimal:
        if movement.type.adds_cash:
            state.try_cash += movement.amount
            return movement.amount if movement.type.is_external_flow else ZERO
        if movement.type == CashMovementType.WITHDRAW:
            state.try_cash = max(ZERO, state.try_cash - movement.amount)
            return -movement.amount
        return ZERO

    @staticmethod
    def _apply_fx(state: _State, conversion) -> Decimal:
        state.fx_hint = conversion.rate
        if state.tracking:
            state.usd_cash += conversion.usd_effect
            return _EventApplier._change_try_cash(state, conversion.try_effect)
        return ZERO

    @staticmethod
    def _track_bist_cost(state: _State, trade) -> None:
        """Pozisyonun kalan maliyetini (ortalama maliyet yöntemi) izler; kapanış fiyatı yoksa değerleme yedeğidir."""
        held_before = state.bist_qty.get(trade.stock_id, ZERO) - (Decimal(trade.quantity) if trade.side == TradeSide.BUY else -Decimal(trade.quantity))
        cost = state.bist_cost.get(trade.stock_id, ZERO)
        if trade.side == TradeSide.BUY:
            cost += trade.cash_amount
        elif held_before > 0:
            cost -= cost / held_before * Decimal(trade.quantity)
        state.bist_cost[trade.stock_id] = max(ZERO, cost)

    @staticmethod
    def _apply_bist(state: _State, trade) -> Decimal:
        sign = 1 if trade.side == TradeSide.BUY else -1
        state.bist_qty[trade.stock_id] = state.bist_qty.get(trade.stock_id, ZERO) + sign * Decimal(trade.quantity)
        _EventApplier._track_bist_cost(state, trade)
        if state.tracking:
            return _EventApplier._change_try_cash(state, -sign * trade.cash_amount)
        return sign * trade.cash_amount

    @staticmethod
    def _apply_asset(state: _State, trade, asset: Optional[Asset]) -> Decimal:
        sign = 1 if trade.side == TradeSide.BUY else -1
        state.asset_qty[trade.asset_id] = state.asset_qty.get(trade.asset_id, ZERO) + sign * trade.quantity
        value_try = trade.cash_amount * trade.fx_rate_to_try
        if trade.quantity > 0:
            state.asset_trade_price[trade.asset_id] = trade.price * trade.fx_rate_to_try
        if state.tracking and trade.cash_linked and asset is not None:
            if asset.settlement_currency == "USD":
                state.usd_cash -= sign * trade.cash_amount
                return ZERO
            return _EventApplier._change_try_cash(state, -sign * trade.cash_amount)
        return sign * value_try

    @classmethod
    def apply(cls, state: _State, event: _Event, assets: Dict[int, Asset]) -> Decimal:
        if event.kind == "cash":
            return cls._apply_cash(state, event.item)
        if event.kind == "fx":
            return cls._apply_fx(state, event.item)
        if event.kind == "bist":
            return cls._apply_bist(state, event.item)
        return cls._apply_asset(state, event.item, assets.get(event.item.asset_id))


class UnifiedSeriesDeps(NamedTuple):
    portfolio_repo: object        # BIST işlemleri
    price_repo: object            # BIST günlük kapanışları
    stock_repo: object
    cash_repo: object             # GERÇEK nakit hareketleri (havuz görünümü değil)
    asset_repo: object
    asset_trade_repo: object
    asset_price_repo: object
    fx_rate_repo: object
    fx_conversion_repo: object


class _PriceBookLoader:
    """Fiyat/kur serilerini okuyup `_Carry` defterlerine çevirir (değerleme bu defterlerden okur)."""

    def __init__(self, deps: UnifiedSeriesDeps) -> None:
        self._price_repo = deps.price_repo
        self._asset_price_repo = deps.asset_price_repo
        self._fx_rate_repo = deps.fx_rate_repo

    def _fx_carry(self, currency: str, start: date, end: date) -> _Carry:
        rates = {r.rate_date: r.rate for r in self._fx_rate_repo.get_rates(currency, "TRY", start, end)}
        before = self._fx_rate_repo.get_rate_on_or_before(currency, "TRY", start - timedelta(days=1))
        return _Carry(rates, before.rate if before else None)

    def _asset_carry(self, asset_id: int, start: date, end: date) -> _Carry:
        rows = {p.price_date: p.close_price for p in self._asset_price_repo.get_daily_prices(asset_id, start, end)}
        before = self._asset_price_repo.get_last_daily_price(asset_id, on_or_before=start - timedelta(days=1))
        return _Carry(rows, before.close_price if before else None)

    def _bist_carry(self, stock_id: int, start: date, end: date) -> _Carry:
        rows = {p.price_date: p.close_price for p in self._price_repo.get_price_series(stock_id, start, end)}
        before = self._price_repo.get_last_price_before(stock_id, start)
        return _Carry(rows, before.close_price if before else None)

    def load(self, data: dict, start: date, end: date) -> dict:
        """Kur, BIST ve varlık kapanış defterleri (`books`): gün bazlı taşınan son değer."""
        currencies = {"USD"} | {a.quote_currency for a in data["assets"].values() if a.quote_currency != "TRY"}
        stock_ids = {t.stock_id for t in data["bist"].valid_trades}
        asset_ids = {t.asset_id for t in data["asset_trades"]}
        return {
            "fx": {c: self._fx_carry(c, start, end) for c in currencies},
            "bist": {sid: self._bist_carry(sid, start, end) for sid in stock_ids},
            "asset": {aid: self._asset_carry(aid, start, end) for aid in asset_ids},
        }


class UnifiedSeriesBuilder:
    def __init__(self, deps: UnifiedSeriesDeps) -> None:
        self._portfolio_repo = deps.portfolio_repo
        self._stock_repo = deps.stock_repo
        self._cash_repo = deps.cash_repo
        self._asset_repo = deps.asset_repo
        self._asset_trade_repo = deps.asset_trade_repo
        self._fx_conversion_repo = deps.fx_conversion_repo
        self._price_books = _PriceBookLoader(deps)

    # ---- veri ---------------------------------------------------------------------------------------------

    def first_event_date(self) -> Optional[date]:
        days = [t.trade_date for t in self._portfolio_repo.get_all_trades()]
        days += [m.movement_date for m in self._cash_repo.get_all_movements()]
        days += [t.trade_date for t in self._asset_trade_repo.list_trades()]
        return min(days) if days else None

    def _load(self, end: date) -> dict:
        trades = [t for t in self._portfolio_repo.get_all_trades() if t.trade_date <= end]
        movements = [m for m in self._cash_repo.get_all_movements() if m.movement_date <= end]
        asset_trades = [t for t in self._asset_trade_repo.list_trades() if t.trade_date <= end]
        conversions = [c for c in self._fx_conversion_repo.list_all() if c.conversion_date <= end]
        return {
            "bist": build_portfolio_safely(trades),
            "movements": movements,
            "asset_trades": asset_trades,
            "conversions": conversions,
            "assets": {a.id: a for a in self._asset_repo.list_assets(active_only=False)},
        }

    @staticmethod
    def _events(data: dict) -> List[_Event]:
        events = [_Event(m.movement_date, m.movement_time or time.min, "cash", m) for m in data["movements"]]
        events += [_Event(c.conversion_date, c.conversion_time or time.min, "fx", c) for c in data["conversions"]]
        events += [_Event(t.trade_date, t.trade_time or time.min, "bist", t) for t in data["bist"].valid_trades]
        events += [_Event(t.trade_date, t.trade_time or time.min, "asset", t) for t in data["asset_trades"]]
        return sorted(events, key=lambda e: e.sort_key)

    # ---- değerleme ----------------------------------------------------------------------------------------

    @staticmethod
    def _fx_rate(books: dict, state: _State, currency: str, day: date) -> Optional[Decimal]:
        if currency == "TRY":
            return Decimal("1")
        carry = books["fx"].get(currency)
        rate = carry.at(day) if carry is not None else None
        return rate if rate is not None else (state.fx_hint if currency == "USD" else None)

    def _asset_unit_try(self, state: _State, books: dict, asset: Asset, day: date, notes: set) -> Optional[Decimal]:
        quoted = books["asset"][asset.id].at(day)
        rate = self._fx_rate(books, state, asset.quote_currency, day)
        if quoted is not None and rate is not None:
            return asset.unit_price(quoted) * rate
        fallback = state.asset_trade_price.get(asset.id)
        if fallback is not None:
            notes.add(asset.symbol)
        return fallback

    def _cash_value(self, state: _State, books: dict, day: date, notes: set) -> Decimal:
        if not state.tracking:
            return ZERO
        total = state.try_cash
        if state.usd_cash > 0:
            usd_rate = self._fx_rate(books, state, "USD", day)
            if usd_rate is None:
                notes.add("USD")
            else:
                total += state.usd_cash * usd_rate
        return total

    @staticmethod
    def _bist_price(state: _State, books: dict, stock_id: int, day: date) -> Optional[Decimal]:
        """Günlük kapanış; yoksa ortalama maliyet (Portföyüm'deki maliyetle değerleme ile tutarlı)."""
        price = books["bist"][stock_id].at(day)
        quantity = state.bist_qty.get(stock_id, ZERO)
        if price is None and quantity > 0 and stock_id in state.bist_cost:
            price = state.bist_cost[stock_id] / quantity
            state.bist_unpriced.add(stock_id)
        return price

    def _bist_value(self, state: _State, books: dict, day: date) -> Decimal:
        total = ZERO
        for stock_id, quantity in state.bist_qty.items():
            if quantity <= 0:
                continue
            price = self._bist_price(state, books, stock_id, day)
            if price is not None:
                total += quantity * price
        return total

    def _asset_value(self, state: _State, data: dict, books: dict, day: date, notes: set) -> Decimal:
        total = ZERO
        for asset_id, quantity in state.asset_qty.items():
            asset = data["assets"].get(asset_id)
            unit = self._asset_unit_try(state, books, asset, day, notes) if asset is not None and quantity > 0 else None
            if unit is not None:
                total += quantity * unit
        return total

    def _total_value(self, state: _State, data: dict, books: dict, day: date, notes: set) -> Decimal:
        return (self._cash_value(state, books, day, notes) + self._bist_value(state, books, day)
                + self._asset_value(state, data, books, day, notes))

    # ---- ana akış -----------------------------------------------------------------------------------------

    def build(self, start: date, end: date) -> UnifiedSeries:
        data = self._load(end)
        events = self._events(data)
        if not events or start > end:
            return UnifiedSeries()
        state = _State(tracking=bool(data["movements"]))
        index = 0
        while index < len(events) and events[index].day < start:
            _EventApplier.apply(state, events[index], data["assets"])
            index += 1
        books = self._price_books.load(data, start, end)
        result, notes = UnifiedSeries(), set()
        twr_index, previous = Decimal("100"), None
        day = start
        while day <= end:
            flow = ZERO
            while index < len(events) and events[index].day == day:
                flow += _EventApplier.apply(state, events[index], data["assets"])
                index += 1
            total = self._total_value(state, data, books, day, notes)
            twr_index = _advance_twr_index(twr_index, total, previous, flow)
            result.values[day], result.twr[day] = total, twr_index
            previous = total
            day += timedelta(days=1)
        result.holdings = self._holdings(state, data, books, end, notes)
        notes |= self._unpriced_bist_names(state)
        result.warnings = [f"{name} için fiyat/kur bulunamadı; son işlem değeriyle değerlendi." for name in sorted(notes)]
        return result

    # ---- bitiş günü pozisyonları --------------------------------------------------------------------------

    def _bist_holdings(self, state: _State, data: dict, books: dict, end: date) -> List[dict]:
        stock_ids = [sid for sid, qty in state.bist_qty.items() if qty > 0 and sid in data["bist"].portfolio.positions]
        tickers = self._stock_repo.get_ticker_map_for_stock_ids(stock_ids) if stock_ids else {}
        items = []
        for stock_id in stock_ids:
            price = self._bist_price(state, books, stock_id, end)
            if price is None:
                continue
            label = tickers.get(stock_id, str(stock_id))
            label = label[:-3] if label.upper().endswith(".IS") else label
            cost = data["bist"].portfolio.positions[stock_id].total_cost
            items.append(self._item(label, state.bist_qty[stock_id] * price, cost))
        return items

    def _unpriced_bist_names(self, state: _State) -> set:
        """Fiyatı bulunamayıp son işlem fiyatıyla değerlenen BIST hisselerinin kodları (uyarı metni için)."""
        ids = [sid for sid in state.bist_unpriced if state.bist_qty.get(sid, ZERO) > 0]
        tickers = self._stock_repo.get_ticker_map_for_stock_ids(ids) if ids else {}
        return {(tickers.get(sid, str(sid))[:-3] if tickers.get(sid, "").upper().endswith(".IS") else tickers.get(sid, str(sid)))
                for sid in ids}

    def _asset_holdings(self, state: _State, data: dict, books: dict, end: date, notes: set) -> List[dict]:
        items = []
        for position in AssetLedger.from_trades(data["asset_trades"]).open_positions():
            asset = data["assets"].get(position.asset_id)
            unit = self._asset_unit_try(state, books, asset, end, notes) if asset is not None else None
            if unit is not None:
                items.append(self._item(asset.symbol, position.total_quantity * unit, position.total_cost_try))
        return items

    def _holdings(self, state: _State, data: dict, books: dict, end: date, notes: set) -> List[dict]:
        items = self._bist_holdings(state, data, books, end) + self._asset_holdings(state, data, books, end, notes)
        total = sum((item["current_value"] for item in items), ZERO)
        for item in items:
            item["weight"] = float(item["current_value"] / total * HUNDRED) if total > 0 else 0.0
        return items

    @staticmethod
    def _item(label: str, value: Decimal, cost: Decimal) -> dict:
        return_pct = float((value - cost) / cost * HUNDRED) if cost > 0 else 0.0
        return {"label": label, "current_value": value, "cost_value": cost, "weight": 0.0, "return_pct": return_pct}
