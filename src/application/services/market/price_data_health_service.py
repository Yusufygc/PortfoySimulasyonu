from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Sequence

from src.domain.models.daily_price import DailyPrice
from src.domain.models.stock import Stock
from src.domain.ports.repositories.i_model_portfolio_repo import IModelPortfolioRepository
from src.domain.ports.repositories.i_portfolio_repo import IPortfolioRepository
from src.domain.ports.repositories.i_price_repo import IPriceRepository
from src.domain.ports.repositories.i_stock_repo import IStockRepository
from src.domain.ports.services.i_market_data_client import IMarketDataClient


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


class PriceDataHealthService:
    def __init__(
        self,
        stock_repo: IStockRepository,
        price_repo: IPriceRepository,
        market_data_client: IMarketDataClient,
        portfolio_repo: IPortfolioRepository | None = None,
        model_portfolio_repo: IModelPortfolioRepository | None = None,
        default_lookback_days: int = 90,
    ) -> None:
        self._stock_repo = stock_repo
        self._price_repo = price_repo
        self._market_data_client = market_data_client
        self._portfolio_repo = portfolio_repo
        self._model_portfolio_repo = model_portfolio_repo
        self._default_lookback_days = default_lookback_days

    def default_start_date(self, today: date | None = None) -> date:
        today = today or date.today()
        candidate = today - timedelta(days=self._default_lookback_days)
        minimum = self.minimum_start_date()
        return max(candidate, minimum) if minimum else candidate

    def minimum_start_date(self) -> date | None:
        first_dates = self._first_trade_dates_by_stock()
        return min(first_dates.values(), default=None)

    def analyze(self, start_date: date, end_date: date) -> PriceDataHealthReport:
        self._validate_range(start_date, end_date)
        first_trade_dates = self._first_trade_dates_by_stock()
        stocks = self._stocks_in_price_health_scope(first_trade_dates)
        stock_ids = [stock.id for stock in stocks if stock.id is not None]
        business_days = self._business_days(start_date, end_date)
        weekend_days = self._weekend_days(start_date, end_date)
        presence_map = self._price_repo.get_price_presence_map(stock_ids, start_date, end_date)
        latest_dates = self._price_repo.get_latest_price_dates(stock_ids)

        empty_weekdays = [
            point_date
            for point_date in business_days
            if self._active_stock_ids_for_date(stock_ids, first_trade_dates, point_date)
            and not any(
                point_date in presence_map.get(stock_id, set())
                for stock_id in self._active_stock_ids_for_date(stock_ids, first_trade_dates, point_date)
            )
        ]
        holiday_candidates = list(empty_weekdays)
        holiday_candidate_set = set(holiday_candidates)

        rows: List[StockPriceHealthRow] = []
        for stock in stocks:
            if stock.id is None:
                continue
            existing_dates = presence_map.get(stock.id, set())
            active_start_date = max(start_date, first_trade_dates.get(stock.id, start_date))
            missing_dates = [
                point_date
                for point_date in business_days
                if point_date >= active_start_date
                and point_date not in holiday_candidate_set
                and point_date not in existing_dates
            ]
            expected_count = len([point_date for point_date in business_days if point_date >= active_start_date])
            status = self._status_for_missing_count(len(missing_dates), expected_count)
            rows.append(
                StockPriceHealthRow(
                    stock_id=stock.id,
                    ticker=stock.ticker,
                    last_price_date=latest_dates.get(stock.id),
                    missing_dates=missing_dates,
                    first_missing_date=missing_dates[0] if missing_dates else None,
                    last_missing_date=missing_dates[-1] if missing_dates else None,
                    status=status,
                    first_trade_date=first_trade_dates.get(stock.id),
                )
            )

        latest_price_date = max(latest_dates.values(), default=None)
        return PriceDataHealthReport(
            start_date=start_date,
            end_date=end_date,
            total_stock_count=len(stock_ids),
            expected_business_days=business_days,
            weekend_days=weekend_days,
            empty_weekdays=empty_weekdays,
            holiday_candidate_dates=holiday_candidates,
            rows=rows,
            latest_price_date=latest_price_date,
        )

    def update_missing_prices(
        self,
        start_date: date,
        end_date: date,
        stock_ids: Sequence[int] | None = None,
    ) -> PriceDataUpdateResult:
        report = self.analyze(start_date, end_date)
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
        self._validate_range(start_date, end_date)
        first_trade_date = self._first_trade_dates_by_stock().get(stock_id)
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

    def update_from_latest_to_today(self, today: date | None = None) -> PriceDataUpdateResult:
        today = today or date.today()
        first_trade_dates = self._first_trade_dates_by_stock()
        stocks = [stock for stock in self._stocks_in_price_health_scope(first_trade_dates) if stock.id is not None]
        latest_dates = self._price_repo.get_latest_price_dates([stock.id for stock in stocks if stock.id is not None])
        updated_count = 0
        errors: List[str] = []
        prices: Dict[int, Decimal] = {}

        for stock in stocks:
            assert stock.id is not None
            latest_date = latest_dates.get(stock.id)
            start_date = latest_date + timedelta(days=1) if latest_date else self.default_start_date(today)
            if stock.id in first_trade_dates:
                start_date = max(start_date, first_trade_dates[stock.id])
            if start_date > today:
                continue
            result = self._fetch_and_save_stock_range(
                stock=stock,
                start_date=start_date,
                end_date=today,
                allowed_dates=set(self._business_days(start_date, today)),
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

    def delete_range(self, start_date: date, end_date: date) -> int:
        self._validate_range(start_date, end_date)
        return self._price_repo.delete_prices_in_range(start_date, end_date)

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
            fallback_result = self._fetch_and_save_stock_dates(
                stock=stock,
                dates=sorted(allowed_dates) if allowed_dates is not None else self._business_days(start_date, end_date),
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

        prices_to_save: List[DailyPrice] = []
        last_price: Decimal | None = None
        for point_date, close_price in sorted(series.items()):
            if allowed_dates is not None and point_date not in allowed_dates:
                continue
            daily_price = DailyPrice(
                id=None,
                stock_id=stock.id,
                price_date=point_date,
                close_price=close_price,
            )
            prices_to_save.append(daily_price)
            last_price = close_price

        if prices_to_save:
            self._price_repo.upsert_daily_prices_bulk(prices_to_save)

        return PriceDataUpdateResult(
            scanned_stock_count=1,
            updated_count=len(prices_to_save),
            prices={stock.id: last_price} if last_price is not None else {},
        )

    def _fetch_and_save_stock_dates(
        self,
        stock: Stock,
        dates: Sequence[date],
        base_errors: List[str] | None = None,
    ) -> PriceDataUpdateResult:
        if stock.id is None:
            return PriceDataUpdateResult(scanned_stock_count=0, updated_count=0)

        errors = list(base_errors or [])
        prices_to_save: List[DailyPrice] = []
        last_price: Decimal | None = None
        for point_date in dates:
            try:
                close_price = self._market_data_client.get_closing_price(stock.id, stock.ticker, point_date)
            except Exception as exc:
                errors.append(f"{stock.ticker} {point_date:%d.%m.%Y}: {exc}")
                continue
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

    @staticmethod
    def _validate_range(start_date: date, end_date: date) -> None:
        if start_date > end_date:
            raise ValueError("Başlangıç tarihi bitiş tarihinden sonra olamaz.")

    @staticmethod
    def _business_days(start_date: date, end_date: date) -> List[date]:
        return [
            point_date
            for point_date in PriceDataHealthService._date_range(start_date, end_date)
            if point_date.weekday() < 5
        ]

    @staticmethod
    def _weekend_days(start_date: date, end_date: date) -> List[date]:
        return [
            point_date
            for point_date in PriceDataHealthService._date_range(start_date, end_date)
            if point_date.weekday() >= 5
        ]

    @staticmethod
    def _date_range(start_date: date, end_date: date) -> List[date]:
        days: List[date] = []
        current = start_date
        while current <= end_date:
            days.append(current)
            current += timedelta(days=1)
        return days

    @staticmethod
    def _status_for_missing_count(missing_count: int, expected_count: int) -> str:
        if missing_count == 0:
            return "Sağlıklı"
        if expected_count <= 0 or missing_count / expected_count < 0.1:
            return "Eksik Var"
        return "Kritik"

    def _first_trade_dates_by_stock(self) -> Dict[int, date]:
        if self._portfolio_repo is None and self._model_portfolio_repo is None:
            return {}
        result: Dict[int, date] = {}
        for trade in self._price_scope_trades():
            current = result.get(trade.stock_id)
            if current is None or trade.trade_date < current:
                result[trade.stock_id] = trade.trade_date
        return result

    def _stocks_in_price_health_scope(self, first_trade_dates: Dict[int, date]) -> List[Stock]:
        stocks = self._stock_repo.get_all_stocks()
        if self._portfolio_repo is None and self._model_portfolio_repo is None:
            return stocks
        active_stock_ids = set(first_trade_dates)
        return [stock for stock in stocks if stock.id in active_stock_ids]

    def _price_scope_trades(self):
        if self._portfolio_repo is not None:
            yield from self._portfolio_repo.get_all_trades()
        if self._model_portfolio_repo is None:
            return
        for portfolio in self._model_portfolio_repo.get_all_model_portfolios():
            if portfolio.id is None:
                continue
            yield from self._model_portfolio_repo.get_trades_by_portfolio_id(portfolio.id)

    @staticmethod
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
