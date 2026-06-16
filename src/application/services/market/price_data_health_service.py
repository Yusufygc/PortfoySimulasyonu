from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta, time
from decimal import Decimal
from typing import Dict, List, NamedTuple, Protocol, Sequence, Set

from src.domain.models.daily_price import DailyPrice
from src.domain.models.model_portfolio import ModelTradeSide
from src.domain.models.stock import Stock
from src.domain.models.trade import TradeSide
from src.application.services.portfolio.safe_portfolio_builder import build_portfolio_safely
from src.domain.ports.repositories.i_corporate_action_repo import ICorporateActionRepository
from src.domain.ports.repositories.i_model_portfolio_repo import IModelPortfolioRepository
from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository
from src.domain.ports.services.i_market_data_client import IMarketDataClient
from src.application.services.corporate_actions.price_adjustment_service import adjusted_market_price

PRICE_SCOPE_ALL_ACTIVE = "all_active"
PRICE_SCOPE_DASHBOARD = "dashboard"
PRICE_SCOPE_MODEL_PREFIX = "model:"
PRICE_SCOPE_ALL_BIST = "all_bist"  # Phase A2: tüm BIST tickerleri (portföye bakmaksızın)


class MarketHolidayProvider(Protocol):
    def get_holidays(self, start_date: date, end_date: date) -> Set[date]:
        ...


class NoKnownMarketHolidayProvider:
    def get_holidays(self, start_date: date, end_date: date) -> Set[date]:
        return set()


@dataclass(frozen=True)
class StockPriceHealthRow:
    stock_id: int
    ticker: str
    last_price_date: date | None
    missing_dates: List[date]
    first_missing_date: date | None
    last_missing_date: date | None
    status: str
    first_trade_date: date | None = None

    @property
    def missing_count(self) -> int:
        return len(self.missing_dates)


@dataclass(frozen=True)
class PriceDataHealthReport:
    start_date: date
    end_date: date
    total_stock_count: int
    expected_business_days: List[date]
    weekend_days: List[date]
    empty_weekdays: List[date]
    holiday_candidate_dates: List[date]
    rows: List[StockPriceHealthRow]
    latest_price_date: date | None
    known_holiday_dates: List[date] = field(default_factory=list)

    @property
    def expected_business_day_count(self) -> int:
        return len(self.expected_business_days)

    @property
    def total_missing_count(self) -> int:
        return sum(row.missing_count for row in self.rows)

    @property
    def holiday_candidate_count(self) -> int:
        return len(self.holiday_candidate_dates)

    @property
    def known_holiday_count(self) -> int:
        return len(self.known_holiday_dates)

    @property
    def total_excluded_holiday_count(self) -> int:
        return self.known_holiday_count + self.holiday_candidate_count

    @property
    def health_label(self) -> str:
        if self.total_stock_count == 0:
            return "Kayıtlı hisse yok"
        denominator = max(1, self.total_stock_count * max(1, self.expected_business_day_count))
        missing_ratio = self.total_missing_count / denominator
        if self.total_missing_count == 0:
            return "Sağlıklı"
        if missing_ratio < 0.1:
            return "Eksik Var"
        return "Kritik"


@dataclass(frozen=True)
class PriceDataUpdateResult:
    scanned_stock_count: int
    updated_count: int
    skipped_holiday_count: int = 0
    errors: List[str] = field(default_factory=list)
    prices: Dict[int, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class PriceDataScopeOption:
    value: str
    label: str


def _normalize_scope(scope: str | None) -> str:
    return scope or PRICE_SCOPE_ALL_ACTIVE


def _model_scope_id(scope: str | None) -> int | None:
    normalized = _normalize_scope(scope)
    if not normalized.startswith(PRICE_SCOPE_MODEL_PREFIX):
        return None
    try:
        return int(normalized.removeprefix(PRICE_SCOPE_MODEL_PREFIX))
    except ValueError:
        return None


def _includes_dashboard(scope: str | None) -> bool:
    normalized = _normalize_scope(scope)
    return normalized in (PRICE_SCOPE_ALL_ACTIVE, PRICE_SCOPE_DASHBOARD)


def _includes_models(scope: str | None) -> bool:
    normalized = _normalize_scope(scope)
    return normalized == PRICE_SCOPE_ALL_ACTIVE or _model_scope_id(normalized) is not None


def _validate_range(start_date: date, end_date: date) -> None:
    if start_date > end_date:
        raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")


def _date_range(start_date: date, end_date: date) -> List[date]:
    days: List[date] = []
    current = start_date
    while current <= end_date:
        days.append(current)
        current += timedelta(days=1)
    return days


def _business_days(
    start_date: date,
    end_date: date,
    known_holidays: Set[date] | None = None,
) -> List[date]:
    excluded = known_holidays or set()
    return [
        point_date
        for point_date in _date_range(start_date, end_date)
        if point_date.weekday() < 5 and point_date not in excluded
    ]


def _weekend_days(start_date: date, end_date: date) -> List[date]:
    return [
        point_date
        for point_date in _date_range(start_date, end_date)
        if point_date.weekday() >= 5
    ]


def _status_for_missing_count(missing_count: int, expected_count: int) -> str:
    if missing_count == 0:
        return "Sağlıklı"
    if expected_count <= 0 or missing_count / expected_count < 0.1:
        return "Eksik Var"
    return "Kritik"


def _active_stock_ids_for_date(
    stock_ids: Sequence[int],
    first_trade_dates: Dict[int, date],
    point_date: date,
) -> List[int]:
    if not first_trade_dates:
        return list(stock_ids)
    return [
        stock_id
        for stock_id in stock_ids
        if first_trade_dates.get(stock_id) is not None and first_trade_dates[stock_id] <= point_date
    ]


class PriceHealthServiceDeps(NamedTuple):
    stock_repo: IStockRepository
    price_repo: IPriceRepository
    market_data_client: IMarketDataClient
    portfolio_repo: "IPortfolioRepository | None" = None
    model_portfolio_repo: "IModelPortfolioRepository | None" = None
    corporate_action_repo: "ICorporateActionRepository | None" = None


class _UpdaterCtx(NamedTuple):
    scope_resolver: "PriceScopeResolver"
    analyzer: "PriceHealthAnalyzer"
    holiday_provider: "MarketHolidayProvider"
    default_start_date_func: object


class _RowBuildCtx(NamedTuple):
    first_trade_dates: "Dict[int, date]"
    presence_map: "Dict[int, Set[date]]"
    latest_dates: "Dict[int, date]"
    holiday_candidate_set: "Set[date]"


class PriceScopeResolver:
    def __init__(
        self,
        stock_repo: IStockRepository,
        portfolio_repo: IPortfolioRepository | None = None,
        model_portfolio_repo: IModelPortfolioRepository | None = None,
    ) -> None:
        self._stock_repo = stock_repo
        self._portfolio_repo = portfolio_repo
        self._model_portfolio_repo = model_portfolio_repo

    def scope_options(self) -> List[PriceDataScopeOption]:
        options = [
            PriceDataScopeOption(PRICE_SCOPE_ALL_ACTIVE, "Tüm aktif portföyler"),
            PriceDataScopeOption(PRICE_SCOPE_DASHBOARD, "Ana Portföy"),
        ]
        if self._model_portfolio_repo is None:
            return options
        for portfolio in self._model_portfolio_repo.get_all_model_portfolios():
            if portfolio.id is None:
                continue
            options.append(
                PriceDataScopeOption(
                    f"{PRICE_SCOPE_MODEL_PREFIX}{portfolio.id}",
                    f"Model Portföy: {portfolio.name}",
                )
            )
        return options

    def first_trade_dates_by_stock(self, scope: str | None = None) -> Dict[int, date]:
        if _normalize_scope(scope) == PRICE_SCOPE_ALL_BIST:
            return {}
        if self._portfolio_repo is None and self._model_portfolio_repo is None:
            return {}
        active_stock_ids = self.active_stock_ids(scope)
        result: Dict[int, date] = {}
        for trade in self.price_scope_trades(scope):
            if trade.stock_id not in active_stock_ids:
                continue
            current = result.get(trade.stock_id)
            if current is None or trade.trade_date < current:
                result[trade.stock_id] = trade.trade_date
        return result

    def stocks_in_scope(self, first_trade_dates: Dict[int, date], scope: str | None = None) -> List[Stock]:
        stocks = self._stock_repo.get_all_stocks()
        if _normalize_scope(scope) == PRICE_SCOPE_ALL_BIST:
            return stocks
        if self._portfolio_repo is None and self._model_portfolio_repo is None:
            return stocks
        active_stock_ids = self.active_stock_ids(scope)
        return [stock for stock in stocks if stock.id in active_stock_ids]

    def active_stock_ids(self, scope: str | None = None) -> set[int]:
        if self._portfolio_repo is None and self._model_portfolio_repo is None:
            return set()

        stock_ids: set[int] = set()
        if self._portfolio_repo is not None and _includes_dashboard(scope):
            portfolio = build_portfolio_safely(self._portfolio_repo.get_all_trades()).portfolio
            stock_ids.update(portfolio.active_positions)

        if self._model_portfolio_repo is not None and _includes_models(scope):
            for portfolio_id in self._model_portfolio_ids(scope):
                stock_ids.update(
                    _open_stock_ids_from_trade_like(
                        self._model_portfolio_repo.get_trades_by_portfolio_id(portfolio_id)
                    )
                )

        return stock_ids

    def price_scope_trades(self, scope: str | None = None):
        if self._portfolio_repo is not None and _includes_dashboard(scope):
            yield from self._portfolio_repo.get_all_trades()
        if self._model_portfolio_repo is None or not _includes_models(scope):
            return
        for portfolio_id in self._model_portfolio_ids(scope):
            yield from self._model_portfolio_repo.get_trades_by_portfolio_id(portfolio_id)

    def _model_portfolio_ids(self, scope: str | None = None) -> List[int]:
        if self._model_portfolio_repo is None:
            return []
        selected_id = _model_scope_id(scope)
        if selected_id is not None:
            return [selected_id]
        if _normalize_scope(scope) != PRICE_SCOPE_ALL_ACTIVE:
            return []
        return [
            portfolio.id
            for portfolio in self._model_portfolio_repo.get_all_model_portfolios()
            if portfolio.id is not None
        ]


def _open_stock_ids_from_trade_like(trades) -> set[int]:
    quantities: Dict[int, int] = {}
    ordered = sorted(
        trades,
        key=lambda trade: (
            trade.trade_date,
            trade.trade_time if getattr(trade, "trade_time", None) is not None else time.min,
            getattr(trade, "id", 0) or 0,
        ),
    )
    for trade in ordered:
        side = trade.side
        if side in (TradeSide.BUY, ModelTradeSide.BUY) or getattr(side, "value", side) == "BUY":
            quantities[trade.stock_id] = quantities.get(trade.stock_id, 0) + trade.quantity
        else:
            quantities[trade.stock_id] = quantities.get(trade.stock_id, 0) - trade.quantity
    return {stock_id for stock_id, quantity in quantities.items() if quantity > 0}


class PriceHealthAnalyzer:
    def __init__(
        self,
        price_repo: IPriceRepository,
        scope_resolver: PriceScopeResolver,
        holiday_provider: MarketHolidayProvider,
    ) -> None:
        self._price_repo = price_repo
        self._scope_resolver = scope_resolver
        self._holiday_provider = holiday_provider

    def analyze(self, start_date: date, end_date: date, scope: str | None = None) -> PriceDataHealthReport:
        _validate_range(start_date, end_date)
        first_trade_dates = self._scope_resolver.first_trade_dates_by_stock(scope)
        stocks = self._scope_resolver.stocks_in_scope(first_trade_dates, scope)
        stock_ids = [stock.id for stock in stocks if stock.id is not None]

        known_holidays = self._holiday_provider.get_holidays(start_date, end_date)
        business_days = _business_days(start_date, end_date, known_holidays)
        weekend_days = _weekend_days(start_date, end_date)

        presence_map = self._price_repo.get_price_presence_map(stock_ids, start_date, end_date)
        latest_dates = self._price_repo.get_latest_price_dates(stock_ids)
        empty_weekdays = self._empty_weekdays(
            stock_ids=stock_ids,
            first_trade_dates=first_trade_dates,
            business_days=business_days,
            presence_map=presence_map,
        )
        holiday_candidates = self._holiday_candidates_for_scope(
            scope=scope,
            empty_weekdays=empty_weekdays,
            start_date=start_date,
            end_date=end_date,
        )

        return PriceDataHealthReport(
            start_date=start_date,
            end_date=end_date,
            total_stock_count=len(stock_ids),
            expected_business_days=business_days,
            weekend_days=weekend_days,
            empty_weekdays=empty_weekdays,
            holiday_candidate_dates=holiday_candidates,
            rows=self._build_rows(
                stocks=stocks,
                start_date=start_date,
                business_days=business_days,
                ctx=_RowBuildCtx(
                    first_trade_dates=first_trade_dates,
                    presence_map=presence_map,
                    latest_dates=latest_dates,
                    holiday_candidate_set=set(holiday_candidates),
                ),
            ),
            latest_price_date=max(latest_dates.values(), default=None),
            known_holiday_dates=sorted(known_holidays),
        )

    def _empty_weekdays(
        self,
        stock_ids: Sequence[int],
        first_trade_dates: Dict[int, date],
        business_days: Sequence[date],
        presence_map: Dict[int, Set[date]],
    ) -> List[date]:
        empty_weekdays: List[date] = []
        for point_date in business_days:
            active_ids = _active_stock_ids_for_date(stock_ids, first_trade_dates, point_date)
            if active_ids and not any(point_date in presence_map.get(stock_id, set()) for stock_id in active_ids):
                empty_weekdays.append(point_date)
        return empty_weekdays

    def _holiday_candidates_for_scope(
        self,
        scope: str | None,
        empty_weekdays: Sequence[date],
        start_date: date,
        end_date: date,
    ) -> List[date]:
        if not empty_weekdays or _normalize_scope(scope) == PRICE_SCOPE_ALL_ACTIVE:
            return list(empty_weekdays)

        all_active_ids = sorted(self._scope_resolver.active_stock_ids(PRICE_SCOPE_ALL_ACTIVE))
        if not all_active_ids:
            return list(empty_weekdays)

        all_first_trade_dates = self._scope_resolver.first_trade_dates_by_stock(PRICE_SCOPE_ALL_ACTIVE)
        all_presence_map = self._price_repo.get_price_presence_map(all_active_ids, start_date, end_date)
        return [
            point_date
            for point_date in empty_weekdays
            if not self._has_market_price_on_date(
                point_date=point_date,
                stock_ids=all_active_ids,
                first_trade_dates=all_first_trade_dates,
                presence_map=all_presence_map,
            )
        ]

    def _has_market_price_on_date(
        self,
        point_date: date,
        stock_ids: Sequence[int],
        first_trade_dates: Dict[int, date],
        presence_map: Dict[int, Set[date]],
    ) -> bool:
        active_ids = _active_stock_ids_for_date(stock_ids, first_trade_dates, point_date)
        return any(point_date in presence_map.get(stock_id, set()) for stock_id in active_ids)

    def _build_rows(
        self,
        stocks: Sequence[Stock],
        start_date: date,
        business_days: Sequence[date],
        ctx: "_RowBuildCtx",
    ) -> List[StockPriceHealthRow]:
        rows: List[StockPriceHealthRow] = []
        for stock in stocks:
            if stock.id is None:
                continue
            missing_dates, expected_count = self._missing_dates_for_stock(
                stock_id=stock.id,
                start_date=start_date,
                business_days=business_days,
                ctx=ctx,
            )
            rows.append(
                StockPriceHealthRow(
                    stock_id=stock.id,
                    ticker=stock.ticker,
                    last_price_date=ctx.latest_dates.get(stock.id),
                    missing_dates=missing_dates,
                    first_missing_date=missing_dates[0] if missing_dates else None,
                    last_missing_date=missing_dates[-1] if missing_dates else None,
                    status=_status_for_missing_count(len(missing_dates), expected_count),
                    first_trade_date=ctx.first_trade_dates.get(stock.id),
                )
            )
        return rows

    def _missing_dates_for_stock(
        self,
        stock_id: int,
        start_date: date,
        business_days: Sequence[date],
        ctx: "_RowBuildCtx",
    ) -> tuple[List[date], int]:
        existing_dates = ctx.presence_map.get(stock_id, set())
        active_start_date = max(start_date, ctx.first_trade_dates.get(stock_id, start_date))
        missing_dates = [
            point_date
            for point_date in business_days
            if point_date >= active_start_date
            and point_date not in ctx.holiday_candidate_set
            and point_date not in existing_dates
        ]
        expected_count = len([point_date for point_date in business_days if point_date >= active_start_date])
        return missing_dates, expected_count


class PriceHealthUpdater:
    def __init__(
        self,
        stock_repo: IStockRepository,
        price_repo: IPriceRepository,
        market_data_client: IMarketDataClient,
        ctx: "_UpdaterCtx",
        corporate_action_repo: "ICorporateActionRepository | None" = None,
    ) -> None:
        self._stock_repo = stock_repo
        self._price_repo = price_repo
        self._market_data_client = market_data_client
        self._scope_resolver = ctx.scope_resolver
        self._analyzer = ctx.analyzer
        self._holiday_provider = ctx.holiday_provider
        self._default_start_date_func = ctx.default_start_date_func
        self._corporate_action_repo = corporate_action_repo

    def update_missing_prices(
        self,
        start_date: date,
        end_date: date,
        stock_ids: Sequence[int] | None = None,
        scope: str | None = None,
    ) -> PriceDataUpdateResult:
        report = self._analyzer.analyze(start_date, end_date, scope)
        selected_ids = set(stock_ids or [])
        rows = [row for row in report.rows if not selected_ids or row.stock_id in selected_ids]
        stocks_by_id = {stock.id: stock for stock in self._stock_repo.get_all_stocks() if stock.id is not None}

        updated_count = 0
        errors: List[str] = []
        prices: Dict[int, Decimal] = {}
        for row in rows:
            if not row.missing_dates:
                continue
            stock = stocks_by_id.get(row.stock_id)
            if stock is None:
                continue
            result = self._fetch_and_save_stock_range(
                stock=stock,
                start_date=row.missing_dates[0],
                end_date=row.missing_dates[-1],
                allowed_dates=set(row.missing_dates),
            )
            updated_count += result.updated_count
            errors.extend(result.errors)
            prices.update(result.prices)

        return PriceDataUpdateResult(
            scanned_stock_count=len(rows),
            updated_count=updated_count,
            skipped_holiday_count=report.holiday_candidate_count,
            errors=errors,
            prices=prices,
        )

    def update_stock_range(self, stock_id: int, start_date: date, end_date: date) -> PriceDataUpdateResult:
        _validate_range(start_date, end_date)
        first_trade_date = self._scope_resolver.first_trade_dates_by_stock().get(stock_id)
        if first_trade_date and start_date < first_trade_date:
            raise ValueError(
                f"Başlangıç tarihi {stock_id} id'li hissenin portföye eklenme tarihinden önce olamaz "
                f"({first_trade_date:%d.%m.%Y})."
            )
        stock = self._stock_repo.get_stock_by_id(stock_id)
        if stock is None:
            return PriceDataUpdateResult(
                scanned_stock_count=0,
                updated_count=0,
                errors=[f"{stock_id} id'li hisse bulunamadı."],
            )
        result = self._fetch_and_save_stock_range(stock=stock, start_date=start_date, end_date=end_date)
        return PriceDataUpdateResult(
            scanned_stock_count=1,
            updated_count=result.updated_count,
            errors=result.errors,
            prices=result.prices,
        )

    def update_from_latest_to_today(self, today: date | None = None, scope: str | None = None) -> PriceDataUpdateResult:
        today = today or date.today()
        first_trade_dates = self._scope_resolver.first_trade_dates_by_stock(scope)
        stocks = [
            stock for stock in self._scope_resolver.stocks_in_scope(first_trade_dates, scope) if stock.id is not None
        ]
        latest_dates = self._price_repo.get_latest_price_dates([stock.id for stock in stocks if stock.id is not None])
        updated_count = 0
        errors: List[str] = []
        prices: Dict[int, Decimal] = {}

        for stock in stocks:
            assert stock.id is not None
            latest_date = latest_dates.get(stock.id)
            start_date = latest_date + timedelta(days=1) if latest_date else self._default_start_date_func(today, scope)
            if stock.id in first_trade_dates:
                start_date = max(start_date, first_trade_dates[stock.id])
            if start_date > today:
                continue
            known_holidays = self._holiday_provider.get_holidays(start_date, today)
            result = self._fetch_and_save_stock_range(
                stock=stock,
                start_date=start_date,
                end_date=today,
                allowed_dates=set(_business_days(start_date, today, known_holidays)),
            )
            updated_count += result.updated_count
            errors.extend(result.errors)
            prices.update(result.prices)

        return PriceDataUpdateResult(
            scanned_stock_count=len(stocks),
            updated_count=updated_count,
            errors=errors,
            prices=prices,
        )

    def _fetch_and_save_stock_range(
        self,
        stock: Stock,
        start_date: date,
        end_date: date,
        allowed_dates: set[date] | None = None,
    ) -> PriceDataUpdateResult:
        if stock.id is None:
            return PriceDataUpdateResult(scanned_stock_count=0, updated_count=0)
        try:
            series = self._market_data_client.get_price_series(stock.ticker, start_date, end_date)
        except Exception as exc:
            series = {}
            fetch_errors = [f"{stock.ticker}: seri alinamadi ({exc})"]
        else:
            fetch_errors = []
        if not series:
            return self._fallback_stock_range(
                stock=stock,
                start_date=start_date,
                end_date=end_date,
                allowed_dates=allowed_dates,
                fetch_errors=fetch_errors,
            )

        prices_to_save, last_price = self._daily_prices_from_series(stock, series, allowed_dates)
        if prices_to_save:
            self._price_repo.upsert_daily_prices_bulk(prices_to_save)
        return PriceDataUpdateResult(
            scanned_stock_count=1,
            updated_count=len(prices_to_save),
            prices={stock.id: last_price} if last_price is not None else {},
        )

    def _fallback_stock_range(
        self,
        stock: Stock,
        start_date: date,
        end_date: date,
        allowed_dates: set[date] | None,
        fetch_errors: List[str],
    ) -> PriceDataUpdateResult:
        fallback_result = self._fetch_and_save_stock_dates(
            stock=stock,
            dates=sorted(allowed_dates) if allowed_dates is not None else _business_days(start_date, end_date),
            base_errors=fetch_errors,
        )
        if fallback_result.updated_count > 0:
            return fallback_result
        return PriceDataUpdateResult(
            scanned_stock_count=1,
            updated_count=0,
            errors=fetch_errors
            + [f"{stock.ticker}: {start_date:%d.%m.%Y} - {end_date:%d.%m.%Y} araliginda fiyat verisi bulunamadi."],
        )

    def _daily_prices_from_series(
        self,
        stock: Stock,
        series: Dict[date, Decimal],
        allowed_dates: set[date] | None,
    ) -> tuple[List[DailyPrice], Decimal | None]:
        prices_to_save: List[DailyPrice] = []
        last_price: Decimal | None = None
        actions = self._actions_for_stock(stock.id)
        from src.application.services.corporate_actions.price_adjustment_service import adjust_downloaded_series
        adjusted_series = adjust_downloaded_series(series, actions)
        for point_date, close_price in sorted(adjusted_series.items()):
            if allowed_dates is not None and point_date not in allowed_dates:
                continue
            prices_to_save.append(DailyPrice(id=None, stock_id=stock.id, price_date=point_date, close_price=close_price))
            last_price = close_price
        return prices_to_save, last_price

    def _actions_for_stock(self, stock_id: int | None):
        if stock_id is None or self._corporate_action_repo is None:
            return []
        return self._corporate_action_repo.get_by_stock(stock_id)

    def _fetch_and_save_stock_dates(
        self,
        stock: Stock,
        dates: Sequence[date],
        base_errors: List[str] | None = None,
    ) -> PriceDataUpdateResult:
        if stock.id is None:
            return PriceDataUpdateResult(scanned_stock_count=0, updated_count=0)

        errors = list(base_errors or [])
        downloaded_series: Dict[date, Decimal] = {}
        for point_date in dates:
            try:
                close_price = self._market_data_client.get_closing_price(stock.id, stock.ticker, point_date)
            except Exception as exc:
                errors.append(f"{stock.ticker} {point_date:%d.%m.%Y}: {exc}")
                continue
            val = close_price if isinstance(close_price, Decimal) else Decimal(str(close_price))
            downloaded_series[point_date] = val

        actions = self._actions_for_stock(stock.id)
        from src.application.services.corporate_actions.price_adjustment_service import adjust_downloaded_series
        adjusted_series = adjust_downloaded_series(downloaded_series, actions)

        prices_to_save: List[DailyPrice] = []
        last_price: Decimal | None = None
        for point_date, close_price in sorted(adjusted_series.items()):
            prices_to_save.append(
                DailyPrice(
                    id=None,
                    stock_id=stock.id,
                    price_date=point_date,
                    close_price=close_price,
                )
            )
            last_price = close_price

        if prices_to_save:
            self._price_repo.upsert_daily_prices_bulk(prices_to_save)

        return PriceDataUpdateResult(
            scanned_stock_count=1,
            updated_count=len(prices_to_save),
            errors=errors,
            prices={stock.id: last_price} if last_price is not None else {},
        )



class PriceDataHealthService:
    def __init__(
        self,
        deps: "PriceHealthServiceDeps",
        holiday_provider: "MarketHolidayProvider | None" = None,
        default_lookback_days: int = 90,
    ) -> None:
        self._stock_repo = deps.stock_repo
        self._price_repo = deps.price_repo
        self._market_data_client = deps.market_data_client
        self._portfolio_repo = deps.portfolio_repo
        self._model_portfolio_repo = deps.model_portfolio_repo
        self._holiday_provider = holiday_provider or NoKnownMarketHolidayProvider()
        self._default_lookback_days = default_lookback_days
        self._scope_resolver = PriceScopeResolver(deps.stock_repo, deps.portfolio_repo, deps.model_portfolio_repo)
        self._analyzer = PriceHealthAnalyzer(
            price_repo=deps.price_repo,
            scope_resolver=self._scope_resolver,
            holiday_provider=self._holiday_provider,
        )
        self._updater = PriceHealthUpdater(
            stock_repo=deps.stock_repo,
            price_repo=deps.price_repo,
            market_data_client=deps.market_data_client,
            ctx=_UpdaterCtx(
                scope_resolver=self._scope_resolver,
                analyzer=self._analyzer,
                holiday_provider=self._holiday_provider,
                default_start_date_func=self.default_start_date,
            ),
            corporate_action_repo=deps.corporate_action_repo,
        )

    def portfolio_scope_options(self) -> List[PriceDataScopeOption]:
        return self._scope_resolver.scope_options()

    def active_stock_ids(self, scope: str | None = None) -> set[int]:
        return self._scope_resolver.active_stock_ids(scope)

    def default_start_date(self, today: date | None = None, scope: str | None = None) -> date:
        today = today or date.today()
        candidate = today - timedelta(days=self._default_lookback_days)
        minimum = self.minimum_start_date(scope)
        return max(candidate, minimum) if minimum else candidate

    def minimum_start_date(self, scope: str | None = None) -> date | None:
        first_dates = self._scope_resolver.first_trade_dates_by_stock(scope)
        return min(first_dates.values(), default=None)

    def analyze(self, start_date: date, end_date: date, scope: str | None = None) -> PriceDataHealthReport:
        return self._analyzer.analyze(start_date, end_date, scope)

    def update_missing_prices(
        self,
        start_date: date,
        end_date: date,
        stock_ids: Sequence[int] | None = None,
        scope: str | None = None,
    ) -> PriceDataUpdateResult:
        return self._updater.update_missing_prices(start_date, end_date, stock_ids, scope)

    def update_stock_range(self, stock_id: int, start_date: date, end_date: date) -> PriceDataUpdateResult:
        return self._updater.update_stock_range(stock_id, start_date, end_date)

    def update_from_latest_to_today(self, today: date | None = None, scope: str | None = None) -> PriceDataUpdateResult:
        return self._updater.update_from_latest_to_today(today, scope)

    def delete_range(self, start_date: date, end_date: date, scope: str | None = None) -> int:
        _validate_range(start_date, end_date)
        if scope is None:
            return self._price_repo.delete_prices_in_range(start_date, end_date)
        stock_ids = sorted(self._scope_resolver.active_stock_ids(scope))
        if not stock_ids:
            return 0
        return self._price_repo.delete_prices_in_range(start_date, end_date, stock_ids)
