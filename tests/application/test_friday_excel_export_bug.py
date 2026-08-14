"""Cuma günü Excel export bug'unu doğrulayan testler.

İki bağlantılı bug kanıtlanır:
  Bug #1 — Sağlık kontrolü, tüm hisseler için fiyat verisi olmayan hafta içi günleri
            tatil adayı olarak sınıflandırıyor (all_active scope). Bu, bugünün eksik
            verisini gizliyor.
  Bug #2 — Simülasyon + ExcelDataPreparer zinciri, fiyat verisi olmayan işlem günlerini
            Excel'den sessizce çıkarıyor.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from src.application.services.market.price_data_health_service import (
    PriceDataHealthService,
    PriceHealthServiceDeps,
)
from src.application.services.reporting.daily_history_models import (
    DailyPortfolioSnapshot,
    DailyPosition,
    PortfolioStatus,
)
from src.application.services.reporting.excel_data_preparer import ExcelDataPreparer
from src.application.services.simulation.history_simulation_service import (
    HistorySimulationService,
)
from src.domain.models.stock import Stock
from src.domain.models.trade import Trade


# ══════════════════════════════════════════════════════════════════════════════
# Fake repository / client sınıfları  (test_price_data_health_service pattern)
# ══════════════════════════════════════════════════════════════════════════════


class _FakeStockRepo:
    def __init__(self, stocks):
        self._stocks = stocks

    def get_all_stocks(self):
        return list(self._stocks)

    def get_stock_by_id(self, stock_id):
        return next((s for s in self._stocks if s.id == stock_id), None)


class _FakePortfolioRepo:
    def __init__(self, trades):
        self._trades = trades

    def get_all_trades(self):
        return list(self._trades)


class _FakePriceRepo:
    def __init__(self, prices_by_stock):
        self.prices_by_stock = {
            sid: dict(pts) for sid, pts in prices_by_stock.items()
        }

    def get_price_presence_map(self, stock_ids, start_date, end_date):
        return {
            sid: {
                d for d in self.prices_by_stock.get(sid, {})
                if start_date <= d <= end_date
            }
            for sid in stock_ids
        }

    def get_latest_price_dates(self, stock_ids):
        result = {}
        for sid in stock_ids:
            dates = sorted(self.prices_by_stock.get(sid, {}))
            if dates:
                result[sid] = dates[-1]
        return result

    def get_portfolio_value_series(self, stock_ids, start_date, end_date):
        result = {}
        for sid in stock_ids:
            for d, price in self.prices_by_stock.get(sid, {}).items():
                if start_date <= d <= end_date:
                    result.setdefault(d, {})[sid] = price
        return result

    def upsert_daily_prices_bulk(self, prices):
        pass

    def delete_prices_in_range(self, start_date, end_date, stock_ids=None):
        return 0


class _FakeMarketClient:
    def get_price_series(self, ticker, start_date, end_date):
        return {}

    def get_closing_price(self, stock_id, ticker, price_date):
        raise ValueError("no data")


# ────── Yardımcı fabrikalar ──────────────────────────────────────────────────


def _make_health_service(prices_by_stock, trades):
    stocks = [
        Stock(id=1, ticker="AAA.IS", name="AAA"),
        Stock(id=2, ticker="BBB.IS", name="BBB"),
    ]
    return PriceDataHealthService(
        deps=PriceHealthServiceDeps(
            stock_repo=_FakeStockRepo(stocks),
            price_repo=_FakePriceRepo(prices_by_stock),
            market_data_client=_FakeMarketClient(),
            portfolio_repo=_FakePortfolioRepo(trades),
        ),
    )


def _make_simulation_service(trades, prices_by_stock, stocks):
    portfolio_repo = MagicMock()
    portfolio_repo.get_all_trades.return_value = list(trades)
    price_repo = MagicMock()
    stock_repo = MagicMock()
    stock_repo.get_all_stocks.return_value = list(stocks)

    # get_portfolio_value_series → {date: {stock_id: price}}
    series = {}
    for sid, pts in prices_by_stock.items():
        for d, price in pts.items():
            series.setdefault(d, {})[sid] = price
    price_repo.get_portfolio_value_series.return_value = series

    return HistorySimulationService(
        portfolio_repo=portfolio_repo,
        price_repo=price_repo,
        stock_repo=stock_repo,
    )


def _snap(
    d,
    total_value=Decimal("100"),
    status=PortfolioStatus.OPEN,
):
    return DailyPortfolioSnapshot(
        date=d,
        total_cost_basis=Decimal("100"),
        total_value=total_value,
        daily_return_pct=Decimal("0"),
        cumulative_return_pct=Decimal("0"),
        daily_pnl=Decimal("0"),
        cumulative_pnl=Decimal("0"),
        status=status,
    )


def _pos(ticker, d, qty=10):
    return DailyPosition(
        date=d,
        ticker=ticker,
        quantity=qty,
        avg_cost=Decimal("10"),
        cost_basis=Decimal("100"),
        close_price=Decimal("10"),
        position_value=Decimal("100"),
        daily_price_change_pct=None,
        daily_pnl_tl=None,
        unrealized_pnl_tl=Decimal("0"),
        unrealized_pnl_pct=Decimal("0"),
        weight_pct=Decimal("1"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# BUG #1: Sağlık kontrolü bugünü tatil adayı olarak gizliyor
# ══════════════════════════════════════════════════════════════════════════════


class TestHealthCheckHidesTodayAsHolidayCandidate:
    """_holiday_candidates_for_scope, all_active scope'ta tüm boş hafta içi
    günleri tatil adayı yapıyor. Bu, bugünün eksik verisini gizliyor."""

    def test_documents_buggy_behavior_empty_weekday_becomes_holiday_candidate(self):
        """Mevcut (hatalı) davranışı belgeler: boş hafta içi gün = tatil adayı."""
        # Pazartesi 5 Ocak 2026: fiyat var, Salı 6 Ocak: fiyat YOK
        trades = [
            Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 5), quantity=1, price=Decimal("10")),
            Trade.create_buy(stock_id=2, trade_date=date(2026, 1, 5), quantity=1, price=Decimal("20")),
        ]
        service = _make_health_service(
            prices_by_stock={
                1: {date(2026, 1, 5): Decimal("10")},
                2: {date(2026, 1, 5): Decimal("20")},
            },
            trades=trades,
        )

        report = service.analyze(date(2026, 1, 5), date(2026, 1, 6))

        # Mevcut davranış: 6 Ocak tatil adayı, eksik = 0
        assert date(2026, 1, 6) in report.holiday_candidate_dates
        assert report.total_missing_count == 0  # BUG: Gerçekte eksik!

    @pytest.mark.xfail(
        reason="BUG: all_active scope'ta tüm boş hafta içi günleri tatil adayı "
               "sayılıyor, bugünün eksik verisi gizleniyor",
        strict=True,
    )
    def test_unfetched_weekday_should_be_missing_not_holiday_candidate(self):
        """Doğru davranış: fiyat çekilmemiş hafta içi gün eksik olarak raporlanmalı."""
        trades = [
            Trade.create_buy(stock_id=1, trade_date=date(2026, 1, 5), quantity=1, price=Decimal("10")),
            Trade.create_buy(stock_id=2, trade_date=date(2026, 1, 5), quantity=1, price=Decimal("20")),
        ]
        service = _make_health_service(
            prices_by_stock={
                1: {date(2026, 1, 5): Decimal("10")},
                2: {date(2026, 1, 5): Decimal("20")},
            },
            trades=trades,
        )

        report = service.analyze(date(2026, 1, 5), date(2026, 1, 6))

        # 6 Ocak (Salı) bir iş günü — fiyat yok → eksik olmalı
        assert report.total_missing_count > 0, (
            "Fiyat verisi olmayan hafta içi gün eksik olarak raporlanmalı"
        )

    @pytest.mark.xfail(
        reason="BUG: Cuma günü (bugün) fiyat çekilmemişse tatil adayı olarak "
               "gizleniyor, sağlık kontrolü 'Sağlıklı' raporluyor",
        strict=True,
    )
    def test_friday_without_prices_should_be_reported_as_missing(self):
        """Cuma 7 Ağustos 2026 — fiyat çekilmemiş → eksik olmalı."""
        # Pzt-Prş fiyat var, Cuma yok
        mon = date(2026, 8, 3)
        tue = date(2026, 8, 4)
        wed = date(2026, 8, 5)
        thu = date(2026, 8, 6)
        fri = date(2026, 8, 7)

        trades = [
            Trade.create_buy(stock_id=1, trade_date=mon, quantity=1, price=Decimal("10")),
            Trade.create_buy(stock_id=2, trade_date=mon, quantity=1, price=Decimal("20")),
        ]
        service = _make_health_service(
            prices_by_stock={
                1: {mon: Decimal("10"), tue: Decimal("11"), wed: Decimal("11"), thu: Decimal("12")},
                2: {mon: Decimal("20"), tue: Decimal("21"), wed: Decimal("21"), thu: Decimal("22")},
                # Cuma (fri) → hiçbir hissede fiyat yok
            },
            trades=trades,
        )

        report = service.analyze(mon, fri)

        # Cuma, normal iş günü — eksik olmalı
        assert report.total_missing_count > 0, (
            "Cuma günü fiyat verisi yoksa eksik olarak raporlanmalı"
        )
        assert fri not in report.holiday_candidate_dates, (
            "Cuma günü tatil adayı olarak sınıflandırılmamalı"
        )


# ══════════════════════════════════════════════════════════════════════════════
# BUG #2: Excel export, fiyat verisi olmayan günleri atlıyor
# ══════════════════════════════════════════════════════════════════════════════


class TestExcelExportMissesFridayData:
    """Simülasyon + ExcelDataPreparer zinciri, fiyat verisi olmayan işlem
    günlerini Excel'den sessizce çıkarıyor."""

    def test_documents_summary_excludes_no_data_days(self):
        """Mevcut davranış: build_summary_df, NO_DATA status'lü günleri atlıyor."""
        preparer = ExcelDataPreparer()
        mon = date(2026, 8, 3)
        tue = date(2026, 8, 4)
        wed = date(2026, 8, 5)
        thu = date(2026, 8, 6)
        fri = date(2026, 8, 7)

        snapshots = [
            _snap(mon, status=PortfolioStatus.OPEN),
            _snap(tue, status=PortfolioStatus.OPEN),
            _snap(wed, status=PortfolioStatus.OPEN),
            _snap(thu, status=PortfolioStatus.OPEN),
            _snap(fri, status=PortfolioStatus.NO_DATA),  # Fiyat yoktu
        ]

        df = preparer.build_summary_df(snapshots)

        # Mevcut davranış: Cuma atlanır, sadece 4 gün
        assert len(df) == 4
        assert fri not in df["Tarih"].tolist()  # BUG: Cuma sessizce kayıp

    @pytest.mark.xfail(
        reason="BUG: build_summary_df, NO_DATA status'lü işlem günlerini "
               "sessizce atlıyor — Cuma verisi Excel'den kayboluyor",
        strict=True,
    )
    def test_summary_should_include_all_trading_days(self):
        """Doğru davranış: tüm işlem günleri summary'de olmalı."""
        preparer = ExcelDataPreparer()
        mon = date(2026, 8, 3)
        fri = date(2026, 8, 7)

        snapshots = [
            _snap(mon, status=PortfolioStatus.OPEN),
            _snap(date(2026, 8, 4), status=PortfolioStatus.OPEN),
            _snap(date(2026, 8, 5), status=PortfolioStatus.OPEN),
            _snap(date(2026, 8, 6), status=PortfolioStatus.OPEN),
            _snap(fri, status=PortfolioStatus.NO_DATA),
        ]

        df = preparer.build_summary_df(snapshots)

        assert fri in df["Tarih"].tolist(), (
            "Fiyat verisi olmayan işlem günleri de summary'de görünmeli"
        )

    def test_documents_detail_excludes_days_without_positions(self):
        """Mevcut davranış: build_detail_df, pozisyonu olmayan günleri atlar."""
        preparer = ExcelDataPreparer()
        mon = date(2026, 8, 3)
        fri = date(2026, 8, 7)

        # Pzt-Prş pozisyon var, Cuma yok (fiyat olmadığı için)
        positions = [
            _pos("AAA.IS", mon),
            _pos("AAA.IS", date(2026, 8, 4)),
            _pos("AAA.IS", date(2026, 8, 5)),
            _pos("AAA.IS", date(2026, 8, 6)),
            # Cuma → pozisyon yok (simülasyon üretmedi)
        ]
        snapshots = [
            _snap(mon, status=PortfolioStatus.OPEN),
            _snap(date(2026, 8, 4), status=PortfolioStatus.OPEN),
            _snap(date(2026, 8, 5), status=PortfolioStatus.OPEN),
            _snap(date(2026, 8, 6), status=PortfolioStatus.OPEN),
            _snap(fri, status=PortfolioStatus.NO_DATA),
        ]

        df = preparer.build_detail_df(positions, snapshots)

        # Mevcut davranış: Cuma detay tablosunda yok
        unique_dates = df["Tarih"].dropna().unique().tolist()
        assert fri not in unique_dates  # BUG: Cuma sessizce kayıp


# ══════════════════════════════════════════════════════════════════════════════
# ENTEGRASYON: Simülasyon → Data Preparer zinciri
# ══════════════════════════════════════════════════════════════════════════════


class TestSimulationToExcelChainFridayMissing:
    """Tam simülasyon → data preparer zincirinde Cuma'nın kaybolmasını belgeler."""

    def _setup_friday_scenario(self):
        """Pzt-Prş fiyat var, Cuma yok senaryosu."""

        class DummyStock:
            def __init__(self, stock_id, ticker):
                self.id = stock_id
                self.ticker = ticker

        mon = date(2026, 8, 3)
        fri = date(2026, 8, 7)

        stocks = [DummyStock(1, "AAA.IS")]
        trades = [
            Trade.create_buy(stock_id=1, trade_date=mon, quantity=10, price=Decimal("10")),
        ]
        prices = {
            1: {
                mon: Decimal("10"),
                date(2026, 8, 4): Decimal("11"),
                date(2026, 8, 5): Decimal("11.5"),
                date(2026, 8, 6): Decimal("12"),
                # Cuma → fiyat yok
            },
        }

        service = _make_simulation_service(trades, prices, stocks)
        return service, mon, fri

    def test_simulation_produces_no_data_for_friday(self):
        """Simülasyon Cuma'yı NO_DATA olarak işaretler."""
        service, mon, fri = self._setup_friday_scenario()

        positions, snapshots = service.simulate_history(mon, fri)

        friday_snapshots = [s for s in snapshots if s.date == fri]
        assert len(friday_snapshots) == 1
        assert friday_snapshots[0].status == PortfolioStatus.NO_DATA

        friday_positions = [p for p in positions if p.date == fri]
        assert len(friday_positions) == 0  # Pozisyon üretilmedi

    def test_full_chain_friday_missing_from_summary(self):
        """Simülasyon + build_summary_df → Cuma summary'de yok."""
        service, mon, fri = self._setup_friday_scenario()
        preparer = ExcelDataPreparer()

        _, snapshots = service.simulate_history(mon, fri)
        df = preparer.build_summary_df(snapshots)

        dates_in_summary = df["Tarih"].tolist()
        # Cuma NO_DATA olduğu için atlandı
        assert fri not in dates_in_summary, "Cuma summary'de olmamalı (mevcut davranış)"
        # Pzt-Prş mevcut
        assert mon in dates_in_summary

    def test_full_chain_friday_missing_from_detail(self):
        """Simülasyon + build_detail_df → Cuma detayda yok."""
        service, mon, fri = self._setup_friday_scenario()
        preparer = ExcelDataPreparer()

        positions, snapshots = service.simulate_history(mon, fri)
        df = preparer.build_detail_df(positions, snapshots)

        unique_dates = df["Tarih"].dropna().unique().tolist()
        assert fri not in unique_dates, "Cuma detay tablosunda olmamalı (mevcut davranış)"
        assert mon in unique_dates

    @pytest.mark.xfail(
        reason="BUG: Tam zincirde (simülasyon → data preparer → Excel), fiyat "
               "verisi olmayan Cuma günü tamamen kayboluyor",
        strict=True,
    )
    def test_full_chain_friday_should_appear_somewhere_in_output(self):
        """Doğru davranış: Cuma Excel çıktısında bir şekilde görünmeli."""
        service, mon, fri = self._setup_friday_scenario()
        preparer = ExcelDataPreparer()

        positions, snapshots = service.simulate_history(mon, fri)
        summary_df = preparer.build_summary_df(snapshots)
        detail_df = preparer.build_detail_df(positions, snapshots)

        summary_dates = set(summary_df["Tarih"].tolist())
        detail_dates = set(detail_df["Tarih"].dropna().unique().tolist())
        all_dates = summary_dates | detail_dates

        assert fri in all_dates, (
            "Cuma günü, fiyat verisi olmasa bile, Excel çıktısında "
            "bir şekilde görünmeli (summary veya detail)"
        )
