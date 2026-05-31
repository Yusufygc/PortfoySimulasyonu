from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402
load_dotenv(PROJECT_ROOT / ".env")

from src.application.services.analysis.benchmark_service import AnalysisBenchmarkService
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient


DEFAULT_CODES = ("bist100", "gold", "usd", "deposit")


@dataclass(frozen=True)
class SourceEvent:
    kind: str
    detail: str


class TracingMarketDataClient(YFinanceMarketDataClient):
    """Projede kullanılan benchmark kaynaklarını çağrı bazında kaydeder."""

    def __init__(self, timeout: int) -> None:
        super().__init__(timeout=timeout)
        self.events: list[SourceEvent] = []
        self.raw_post_responses: list[tuple[str, object]] = []

        _orig_request_text = self._scraped_provider._request_text
        def _traced_request_text(url):
            self.events.append(SourceEvent("scraped", url))
            return _orig_request_text(url)
        self._scraped_provider._request_text = _traced_request_text

        _orig_request_json = self._scraped_provider._request_json
        def _traced_request_json(url):
            self.events.append(SourceEvent("scraped-json", url))
            return _orig_request_json(url)
        self._scraped_provider._request_json = _traced_request_json

        _orig_request_json_post = self._scraped_provider._evds_client.request_json_post
        def _traced_request_json_post(url, payload):
            series = payload.get("series", "")
            start_date = payload.get("startDate", "")
            end_date = payload.get("endDate", "")
            self.events.append(SourceEvent("tcmb-evds", f"{url} series={series} start={start_date} end={end_date}"))
            response = _orig_request_json_post(url, payload)
            self.raw_post_responses.append((url, response))
            return response
        self._scraped_provider._evds_client.request_json_post = _traced_request_json_post

        _orig_request_json_post_path = self._scraped_provider._evds_client.request_json_post_path
        def _traced_request_json_post_path(path, payload):
            self.events.append(SourceEvent("tcmb-evds", f"{path} {payload}"))
            response = _orig_request_json_post_path(path, payload)
            self.raw_post_responses.append((path, response))
            return response
        self._scraped_provider._evds_client.request_json_post_path = _traced_request_json_post_path

        _orig_request_to_investing = self._investing_client._request_to_investing
        def _traced_request_to_investing(endpoint, params):
            self.events.append(SourceEvent("investing", f"{endpoint} {params}"))
            return _orig_request_to_investing(endpoint, params)
        self._investing_client._request_to_investing = _traced_request_to_investing

    def consume_events(self) -> list[SourceEvent]:
        events = list(self.events)
        self.events.clear()
        return events

    def _download_dataframe(self, tickers, start: date, end: date):
        self.events.append(SourceEvent("yfinance", f"tickers={tickers}, start={start}, end={end}"))
        return super()._download_dataframe(tickers, start, end)


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("Tarih YYYY-AA-GG formatında olmalı.") from exc


def _fmt_decimal(value: Decimal) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def _print(text: str = "") -> None:
    print(text, flush=True)


def _print_sources(events: Iterable[SourceEvent]) -> None:
    grouped: dict[str, list[str]] = {}
    for event in events:
        grouped.setdefault(event.kind, [])
        if event.detail not in grouped[event.kind]:
            grouped[event.kind].append(event.detail)

    if not grouped:
        _print("Kullanılan kaynak: cache veya veri yok")
        return

    _print("Kullanılan proje kaynakları:")
    for kind, details in grouped.items():
        _print(f"  - {kind}")
        for detail in details:
            _print(f"    {detail}")


def _print_series(label: str, code: str, points: dict[date, Decimal], limit: int | None) -> None:
    rows = sorted(points.items())
    visible_rows = rows if limit is None else rows[-limit:]

    _print(f"{label} ({code}) - {len(rows)} nokta")
    _print("Tarih       Değer")
    for point_date, value in visible_rows:
        _print(f"{point_date.isoformat()}  {_fmt_decimal(value)}")
    if limit is not None and len(rows) > limit:
        _print(f"... toplam {len(rows)} noktanın son {limit} satırı gösterildi")


def _build_parser() -> argparse.ArgumentParser:
    today = date.today()
    default_end = today - timedelta(days=1)
    default_start = default_end - timedelta(days=14)

    parser = argparse.ArgumentParser(
        description=(
            "Projede kullanılan benchmark veri akışını canlı çalıştırır ve çekilen "
            "güncel verileri konsola yazdırır."
        )
    )
    parser.add_argument(
        "--start",
        type=_parse_date,
        default=default_start,
        help=f"Başlangıç tarihi, YYYY-AA-GG. Varsayılan: {default_start}",
    )
    parser.add_argument(
        "--end",
        type=_parse_date,
        default=default_end,
        help=f"Bitiş tarihi, YYYY-AA-GG. Varsayılan: {default_end}",
    )
    parser.add_argument(
        "--codes",
        default=",".join(DEFAULT_CODES),
        help="Virgülle ayrılmış benchmark kodları. Varsayılan: bist100,gold,usd,deposit",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="HTTP/yfinance zaman aşımı saniyesi. Varsayılan: 20",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Her seri için gösterilecek son satır sayısı. Tümünü göstermek için 0.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        default=False,
        help="Ham API yanıtlarını (JSON) ekrana yaz — parse sorunu debug için.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    if args.start > args.end:
        _print("Hata: --start tarihi --end tarihinden büyük olamaz.")
        return 2

    selected_codes = [code.strip() for code in args.codes.split(",") if code.strip()]
    if not selected_codes:
        _print("Hata: En az bir benchmark kodu verilmeli.")
        return 2

    limit = None if args.limit == 0 else max(args.limit, 1)
    _print("=" * 96)
    _print(f"Benchmark canlı veri kontrolü: {args.start.isoformat()} - {args.end.isoformat()}")
    _print(f"Benchmark kodları: {', '.join(selected_codes)}")
    _print("Veri yolu: AnalysisBenchmarkService -> YFinanceMarketDataClient")
    _print("=" * 96)

    series_list = []
    warnings: list[str] = []
    source_events_by_code: dict[str, list[SourceEvent]] = {}
    raw_responses_by_code: dict[str, list[tuple[str, object]]] = {}
    for code in selected_codes:
        client = TracingMarketDataClient(timeout=args.timeout)
        service = AnalysisBenchmarkService(market_data_client=client)
        code_series, code_warnings = service.build_benchmark_series(args.start, args.end, [code])
        source_events_by_code[code] = client.consume_events()
        raw_responses_by_code[code] = list(client.raw_post_responses)
        series_list.extend(code_series)
        warnings.extend(code_warnings)

    for benchmark in series_list:
        _print_series(benchmark.label, benchmark.code, benchmark.points, limit)
        _print_sources(source_events_by_code.get(benchmark.code, []))
        if args.raw:
            for url, resp in raw_responses_by_code.get(benchmark.code, []):
                _print(f"  [HAM YANIT] {url}")
                _print(f"  {json.dumps(resp, ensure_ascii=False, indent=2)[:2000]}")
        _print("-" * 96)

    missing_codes = sorted(set(selected_codes) - {series.code for series in series_list})
    if missing_codes:
        _print(f"Veri üretilemeyen benchmark kodları: {', '.join(missing_codes)}")
        for code in missing_codes:
            _print(f"{code} için denenen kaynaklar:")
            _print_sources(source_events_by_code.get(code, []))
            if args.raw:
                for url, resp in raw_responses_by_code.get(code, []):
                    _print(f"  [HAM YANIT] {url}")
                    _print(f"  {json.dumps(resp, ensure_ascii=False, indent=2)[:2000]}")

    if warnings:
        _print("Uyarılar:")
        for warning in warnings:
            _print(f"  - {warning}")

    if missing_codes:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
