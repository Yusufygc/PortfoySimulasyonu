from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Set

from sqlalchemy import text


@dataclass(frozen=True)
class DuplicateGroup:
    table_name: str
    key_name: str
    key_value: str
    count: int


@dataclass(frozen=True)
class OrphanReference:
    table_name: str
    column_name: str
    referenced_table: str
    missing_id: int
    row_count: int


@dataclass(frozen=True)
class UnusedStock:
    stock_id: int
    ticker: str
    daily_price_count: int
    last_price_date: object | None


@dataclass(frozen=True)
class StockUsageReport:
    dashboard_stock_ids: Set[int] = field(default_factory=set)
    watchlist_stock_ids: Set[int] = field(default_factory=set)
    model_portfolio_stock_ids: Set[int] = field(default_factory=set)

    @property
    def all_stock_ids(self) -> Set[int]:
        return set().union(
            self.dashboard_stock_ids,
            self.watchlist_stock_ids,
            self.model_portfolio_stock_ids,
        )

    @property
    def shared_by_dashboard_and_watchlist(self) -> Set[int]:
        return self.dashboard_stock_ids & self.watchlist_stock_ids

    @property
    def shared_by_dashboard_and_model_portfolio(self) -> Set[int]:
        return self.dashboard_stock_ids & self.model_portfolio_stock_ids

    @property
    def shared_by_watchlist_and_model_portfolio(self) -> Set[int]:
        return self.watchlist_stock_ids & self.model_portfolio_stock_ids


@dataclass(frozen=True)
class DatabaseIntegrityReport:
    table_counts: Dict[str, int]
    duplicate_groups: List[DuplicateGroup]
    orphan_references: List[OrphanReference]
    stock_usage: StockUsageReport
    unused_stocks: List[UnusedStock]

    @property
    def has_issues(self) -> bool:
        return bool(self.duplicate_groups or self.orphan_references or self.unused_stocks)


class DatabaseIntegrityService:
    """
    Salt-okunur DB butunluk raporu uretir.

    Bu servis migration veya duzeltme yapmaz; yalnizca tablo sayilari,
    duplicate gruplar, orphan FK adaylari ve stock kullanim kesitlerini okur.
    """

    TABLES = (
        "stocks",
        "trades",
        "daily_prices",
        "watchlists",
        "watchlist_items",
        "model_portfolios",
        "model_portfolio_trades",
    )

    def __init__(self, db_provider) -> None:
        self._provider = db_provider

    def build_report(self) -> DatabaseIntegrityReport:
        with self._provider.get_session() as session:
            return DatabaseIntegrityReport(
                table_counts=self._table_counts(session),
                duplicate_groups=self._duplicate_groups(session),
                orphan_references=self._orphan_references(session),
                stock_usage=self._stock_usage(session),
                unused_stocks=self._unused_stocks(session),
            )

    def _table_counts(self, session) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for table_name in self.TABLES:
            counts[table_name] = int(session.execute(text(f"SELECT COUNT(*) FROM {table_name}")).scalar() or 0)
        return counts

    def _duplicate_groups(self, session) -> List[DuplicateGroup]:
        checks = [
            (
                "stocks",
                "ticker",
                "UPPER(ticker)",
                "SELECT UPPER(ticker) AS key_value, COUNT(*) AS row_count "
                "FROM stocks GROUP BY UPPER(ticker) HAVING COUNT(*) > 1",
            ),
            (
                "daily_prices",
                "stock_id,price_date",
                "stock_id, price_date",
                "SELECT CONCAT(stock_id, ':', price_date) AS key_value, COUNT(*) AS row_count "
                "FROM daily_prices GROUP BY stock_id, price_date HAVING COUNT(*) > 1",
            ),
            (
                "watchlist_items",
                "watchlist_id,stock_id",
                "watchlist_id, stock_id",
                "SELECT CONCAT(watchlist_id, ':', stock_id) AS key_value, COUNT(*) AS row_count "
                "FROM watchlist_items GROUP BY watchlist_id, stock_id HAVING COUNT(*) > 1",
            ),
        ]
        duplicates: List[DuplicateGroup] = []
        for table_name, key_name, _group_expr, sql in checks:
            for row in session.execute(text(sql)):
                duplicates.append(
                    DuplicateGroup(
                        table_name=table_name,
                        key_name=key_name,
                        key_value=str(row.key_value),
                        count=int(row.row_count),
                    )
                )
        return duplicates

    def _orphan_references(self, session) -> List[OrphanReference]:
        checks = [
            ("trades", "stock_id", "stocks", "id"),
            ("daily_prices", "stock_id", "stocks", "id"),
            ("watchlist_items", "stock_id", "stocks", "id"),
            ("model_portfolio_trades", "stock_id", "stocks", "id"),
            ("watchlist_items", "watchlist_id", "watchlists", "id"),
            ("model_portfolio_trades", "portfolio_id", "model_portfolios", "id"),
        ]
        orphans: List[OrphanReference] = []
        for table_name, column_name, ref_table, ref_column in checks:
            sql = text(
                f"SELECT child.{column_name} AS missing_id, COUNT(*) AS row_count "
                f"FROM {table_name} child "
                f"LEFT JOIN {ref_table} parent ON parent.{ref_column} = child.{column_name} "
                f"WHERE parent.{ref_column} IS NULL "
                f"GROUP BY child.{column_name}"
            )
            for row in session.execute(sql):
                orphans.append(
                    OrphanReference(
                        table_name=table_name,
                        column_name=column_name,
                        referenced_table=ref_table,
                        missing_id=int(row.missing_id),
                        row_count=int(row.row_count),
                    )
                )
        return orphans

    def _stock_usage(self, session) -> StockUsageReport:
        return StockUsageReport(
            dashboard_stock_ids=self._stock_ids(session, "trades"),
            watchlist_stock_ids=self._stock_ids(session, "watchlist_items"),
            model_portfolio_stock_ids=self._stock_ids(session, "model_portfolio_trades"),
        )

    def _unused_stocks(self, session) -> List[UnusedStock]:
        sql = text(
            "SELECT s.id AS stock_id, s.ticker, COUNT(dp.id) AS daily_price_count, "
            "MAX(dp.price_date) AS last_price_date "
            "FROM stocks s "
            "LEFT JOIN trades t ON t.stock_id = s.id "
            "LEFT JOIN watchlist_items wi ON wi.stock_id = s.id "
            "LEFT JOIN model_portfolio_trades mt ON mt.stock_id = s.id "
            "LEFT JOIN daily_prices dp ON dp.stock_id = s.id "
            "WHERE t.id IS NULL AND wi.id IS NULL AND mt.id IS NULL "
            "GROUP BY s.id, s.ticker "
            "ORDER BY s.ticker"
        )
        return [
            UnusedStock(
                stock_id=int(row.stock_id),
                ticker=str(row.ticker),
                daily_price_count=int(row.daily_price_count),
                last_price_date=row.last_price_date,
            )
            for row in session.execute(sql)
        ]

    @staticmethod
    def _stock_ids(session, table_name: str) -> Set[int]:
        rows = session.execute(text(f"SELECT DISTINCT stock_id FROM {table_name} WHERE stock_id IS NOT NULL"))
        return {int(row.stock_id) for row in rows}
