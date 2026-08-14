from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Protocol, Sequence

from src.domain.ports.services.i_market_data_client import IMarketDataClient
from datetime import datetime

from .models import BenchmarkDefinition, BenchmarkSeries

logger = logging.getLogger(__name__)


def _parse_evds_month_date(value: str) -> date:
    val_str = str(value).strip()
    if "-" in val_str:
        parts = val_str.split("-")
        if len(parts) == 2:
            if len(parts[0]) == 4:
                return date(int(parts[0]), int(parts[1]), 1)
            return date(int(parts[1]), int(parts[0]), 1)
        elif len(parts) == 3:
            if len(parts[0]) == 4:
                return date(int(parts[0]), int(parts[1]), 1)
            return date(int(parts[2]), int(parts[1]), 1)
    return datetime.strptime(val_str, "%d-%m-%Y").date().replace(day=1)


class EvdsSeriesProvider(Protocol):
    def get_series(self, series_code: str, start_date: date, end_date: date) -> List[dict]:
        ...


class AnalysisBenchmarkService:
    DEFAULT_BENCHMARK_CODES = ["bist100", "gold", "silver", "usd", "euro", "deposit", "cpi"]
    TROY_OUNCE_GRAMS = Decimal("31.1034768")
    MARKET_BENCHMARK_CANDIDATES: Dict[str, Sequence[str]] = {
        "bist100": ("XU100.IS", "^XU100"),
        "usd": ("TRY=X", "USDTRY=X"),
        "euro": ("EURTRY=X",),
    }
    GOLD_USD_TICKERS: Sequence[str] = ("XAUUSD=X", "GC=F")
    SILVER_USD_TICKERS: Sequence[str] = ("XAGUSD=X", "SI=F")

    def __init__(
        self,
        market_data_client: IMarketDataClient,
        evds_client: EvdsSeriesProvider | None = None,
    ) -> None:
        self._market_data_client = market_data_client
        self._evds_client = evds_client
        self._benchmarks: Dict[str, BenchmarkDefinition] = {
            "bist100": BenchmarkDefinition("bist100", "BIST 100", "market", "XU100.IS"),
            "gold": BenchmarkDefinition("gold", "Gram Altın", "market", "XAUTRY=X"),
            "silver": BenchmarkDefinition("silver", "Gram Gümüş", "market", "XAGTRY=X"),
            "usd": BenchmarkDefinition("usd", "USD/TRY", "market", "TRY=X"),
            "euro": BenchmarkDefinition("euro", "EUR/TRY", "market", "EURTRY=X"),
            "deposit": BenchmarkDefinition("deposit", "Mevduat Faizi", "market", "TP.KTF10"),
            "cpi": BenchmarkDefinition("cpi", "TÜFE", "market", "TP.FG.J0"),
        }

    def get_benchmark_definitions(self) -> List[BenchmarkDefinition]:
        return [self._benchmarks[code] for code in self.DEFAULT_BENCHMARK_CODES]

    def build_benchmark_series(
        self,
        start_date: date,
        end_date: date,
        selected_codes: Sequence[str],
    ) -> tuple[List[BenchmarkSeries], List[str]]:
        results: List[BenchmarkSeries] = []
        warnings: List[str] = []
        for code in selected_codes:
            definition = self._benchmarks.get(code)
            if definition is None:
                continue
            try:
                if definition.code == "deposit":
                    points = self._build_deposit_series(start_date, end_date)
                elif definition.code == "cpi":
                    points = self._build_cpi_series(start_date, end_date)
                elif definition.code == "gold":
                    points = self._build_precious_metal_series("XAUTRY=X", self.GOLD_USD_TICKERS, start_date, end_date)
                elif definition.code == "silver":
                    points = self._build_precious_metal_series("XAGTRY=X", self.SILVER_USD_TICKERS, start_date, end_date)
                else:
                    points = self._build_market_series(definition, start_date, end_date)
            except Exception:
                logger.warning("Benchmark serisi olusturulamadi: %s", definition.code, exc_info=True)
                points = {}
            if not points:
                warnings.append(f"Veri akışı hatası: {definition.label} güncel verisi API'den alınamadı (Sembol değişmiş veya sistemden kaldırılmış olabilir).")
                continue
                
            # Ffill durumunda kullanıcıyı 1 kere bilgilendirmek yeterli
            results.append(BenchmarkSeries(code=definition.code, label=definition.label, points=points))
            
        # Hafta sonu / tatil durumunda geriye dönük arama yapıldığına dair genel bilgi
        warnings.append("Not: Seçilen tarih aralığında hafta sonu veya tatillere denk gelen günler için sistem otomatik olarak en yakın geçmiş işlem gününün (örn: Cuma) fiyatını referans almıştır (Forward Fill).")
        return results, warnings

    def _build_market_series(
        self,
        definition: BenchmarkDefinition,
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        candidates = self._get_market_ticker_candidates(definition)
        points, _ = self._fetch_first_available_market_series(candidates, start_date, end_date)
        return self._ffill_series(points, start_date, end_date)

    def _ffill_series(self, series: Dict[date, Decimal], start_date: date, end_date: date) -> Dict[date, Decimal]:
        if not series:
            return {}
            
        result = {}
        # start_date ve öncesindeki en yakın tarihi bul
        past_dates = [dt for dt in series.keys() if dt <= start_date]
        if past_dates:
            last_val = series[max(past_dates)]
        else:
            # Eğer öncesinde veri yoksa, mecburen elimizdeki en eski tarihi alırız
            last_val = series[min(series.keys())]
            
        current_day = start_date
        while current_day <= end_date:
            if current_day in series:
                last_val = series[current_day]
            result[current_day] = last_val
            current_day += timedelta(days=1)
        return result

    def _build_precious_metal_series(self, try_ticker: str, usd_tickers: Sequence[str], start_date: date, end_date: date) -> Dict[date, Decimal]:
        # Try direct TRY ticker first (e.g., XAUTRY=X or XAGTRY=X)
        points, _ = self._fetch_first_available_market_series([try_ticker], start_date, end_date)
        if points:
            return self._ffill_series(self._convert_ounce_try_to_gram_try(points), start_date, end_date)

        # Fallback to cross rate
        metal_usd_series, _ = self._fetch_first_available_market_series(usd_tickers, start_date, end_date)
        if not metal_usd_series:
            return {}

        usd_definition = self._benchmarks.get("usd")
        usd_candidates = self._get_market_ticker_candidates(usd_definition) if usd_definition is not None else []
        usd_try_series, _ = self._fetch_first_available_market_series(usd_candidates, start_date, end_date)
        if usd_try_series:
            combined = self._combine_series_by_date(metal_usd_series, usd_try_series)
            if combined:
                return self._ffill_series(self._convert_ounce_try_to_gram_try(combined), start_date, end_date)

        return self._ffill_series(self._convert_ounce_try_to_gram_try(metal_usd_series), start_date, end_date)

    def _get_market_ticker_candidates(self, definition: BenchmarkDefinition | None) -> List[str]:
        if definition is None:
            return []

        candidates: List[str] = []
        if definition.ticker:
            candidates.append(definition.ticker)
        for ticker in self.MARKET_BENCHMARK_CANDIDATES.get(definition.code, ()):
            if ticker not in candidates:
                candidates.append(ticker)
        return candidates

    def _fetch_first_available_market_series(
        self,
        candidates: Sequence[str],
        start_date: date,
        end_date: date,
    ) -> tuple[Dict[date, Decimal], Optional[str]]:
        for ticker in candidates:
            try:
                points = self._market_data_client.get_price_series(ticker, start_date, end_date)
            except Exception:
                logger.debug("Benchmark ticker denemesi basarisiz: %s", ticker, exc_info=True)
                points = {}
            if points:
                return points, ticker
        return {}, None

    def _combine_series_by_date(
        self,
        left_series: Dict[date, Decimal],
        right_series: Dict[date, Decimal],
    ) -> Dict[date, Decimal]:
        shared_dates = sorted(set(left_series).intersection(right_series))
        return {
            point_date: left_series[point_date] * right_series[point_date]
            for point_date in shared_dates
        }

    def _convert_ounce_try_to_gram_try(self, series: Dict[date, Decimal]) -> Dict[date, Decimal]:
        return {
            point_date: value / self.TROY_OUNCE_GRAMS
            for point_date, value in series.items()
        }

    def _build_deposit_series(self, start_date: date, end_date: date) -> Dict[date, Decimal]:
        rate_series = self._deposit_rate_series(start_date, end_date)
        if not rate_series:
            return {}
        return self._compound_deposit_index(rate_series, start_date, end_date)

    def _deposit_rate_series(self, start_date: date, end_date: date) -> Dict[date, Decimal]:
        rate_series = self._evds_deposit_rates(start_date, end_date)
        if rate_series:
            return rate_series
        try:
            return self._market_data_client.get_price_series("TCMB_TRY_DEPOSIT_3M", start_date, end_date)
        except Exception as e:
            logger.debug(f"Market data client deposit series failed: {e}")
            return {}

    def _evds_deposit_rates(self, start_date: date, end_date: date) -> Dict[date, Decimal]:
        if not self._evds_client:
            return {}
        try:
            items = self._evds_client.get_series("TP.KTF10", start_date - timedelta(days=90), end_date)
        except Exception as e:
            logger.error(f"EVDS Mevduat verisi cekilemedi: {e}")
            return {}
        return self._parse_evds_daily_series(items, "TP_KTF10")

    @staticmethod
    def _parse_evds_daily_series(items: Sequence[dict], value_key: str) -> Dict[date, Decimal]:
        result: Dict[date, Decimal] = {}
        for item in items:
            dt_str = item.get("Tarih")
            val_str = item.get(value_key)
            if dt_str and val_str is not None:
                try:
                    result[datetime.strptime(dt_str, "%d-%m-%Y").date()] = Decimal(str(val_str))
                except (ValueError, TypeError):
                    continue
        return result

    @staticmethod
    def _compound_deposit_index(
        rate_series: Dict[date, Decimal],
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        value = Decimal("100")
        result: Dict[date, Decimal] = {}
        rate_items = sorted(rate_series.items())
        rate_idx = 0
        current_rate: Decimal | None = None
        current_day = start_date
        while current_day <= end_date:
            while rate_idx < len(rate_items) and rate_items[rate_idx][0] <= current_day:
                current_rate = rate_items[rate_idx][1]
                rate_idx += 1
                
            if current_rate is None and result:
                pass
            elif current_rate is None:
                current_rate = Decimal("30.0") # Fallback
                
            if current_rate is not None:
                result[current_day] = value
                # Basit günlük bilesik getiri
                daily_rate = (current_rate / Decimal("100")) / Decimal("365")
                value = value * (Decimal("1") + daily_rate)
            current_day += timedelta(days=1)
        return result

    def _build_cpi_series(self, start_date: date, end_date: date) -> Dict[date, Decimal]:
        cpi_series = self._evds_cpi_series(start_date, end_date)
        if not cpi_series:
            return {}
        return self._ffill_monthly_index(cpi_series, start_date, end_date)

    def _evds_cpi_series(self, start_date: date, end_date: date) -> Dict[date, Decimal]:
        if not self._evds_client:
            return {}
        try:
            items = self._evds_client.get_series("TP.FG.J0", start_date - timedelta(days=365), end_date)
        except Exception as e:
            logger.error(f"EVDS TUFE verisi cekilemedi: {e}")
            return {}
        return self._parse_evds_monthly_series(items, "TP_FG_J0")

    @staticmethod
    def _parse_evds_monthly_series(items: Sequence[dict], value_key: str) -> Dict[date, Decimal]:
        result: Dict[date, Decimal] = {}
        for item in items:
            dt_str = item.get("Tarih")
            val_str = item.get(value_key)
            if dt_str and val_str is not None:
                try:
                    result[_parse_evds_month_date(dt_str)] = Decimal(str(val_str))
                except (ValueError, TypeError):
                    continue
        return result

    @staticmethod
    def _ffill_monthly_index(
        cpi_series: Dict[date, Decimal],
        start_date: date,
        end_date: date,
    ) -> Dict[date, Decimal]:
        result: Dict[date, Decimal] = {}
        cpi_items = sorted(cpi_series.items())
        cpi_idx = 0
        current_cpi: Decimal | None = None
        
        current_day = start_date
        while current_day <= end_date:
            # Ffill yaklasimi ile son aciklanan ayin verisini al
            while cpi_idx < len(cpi_items) and cpi_items[cpi_idx][0] <= current_day:
                current_cpi = cpi_items[cpi_idx][1]
                cpi_idx += 1
                
            if current_cpi is not None:
                result[current_day] = current_cpi
            current_day += timedelta(days=1)
            
        return result
