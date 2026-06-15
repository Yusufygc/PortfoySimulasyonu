"""
isyatirim.com.tr Mali Tablo Provider — Clean Architecture adapter.

IFinancialStatementProvider implementasyonu:
  - isyatirim JSON API'sından BIST hisse mali tablolarını çeker.
  - Dosya cache + TTL ile gereksiz ağ isteklerini önler.
  - Tüm ağ/parse hataları → FinancialStatementProviderUnavailable.

Cache konumu: data/_cache/financials/{TICKER}_{CURRENCY}.json
TTL: 12 saat (CACHE_TTL_HOURS).
"""
from __future__ import annotations

import json
import logging
import time
from datetime import timedelta
from itertools import islice
from pathlib import Path
from typing import Iterator

import requests

from src.domain.ports.services.i_financial_statement_provider import (
    FinancialStatementProviderUnavailable,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Cache ayarları
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
_CACHE_DIR    = _PROJECT_ROOT / "data" / "_cache" / "financials"
CACHE_TTL_HOURS = 12

# ---------------------------------------------------------------------------
# isyatirim API sabitleri
# ---------------------------------------------------------------------------

_JSON_URL = (
    "https://www.isyatirim.com.tr"
    "/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo"
)
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, */*",
    "Accept-Language": "tr-TR,tr;q=0.9",
    "Referer": "https://www.isyatirim.com.tr/",
}
_GROUPS_PRIORITY = ["XI_29", "UFRS"]

_SECTION_BY_PREFIX: list[tuple[str, str]] = [
    ("1",  "bilanco"),
    ("2",  "bilanco"),
    ("3",  "gelir"),
    ("4B", "dipnot"),
    ("4C", "nakit_akim"),
]


def _code_to_section(item_code: str) -> str | None:
    c = item_code.upper()
    for prefix, section in _SECTION_BY_PREFIX:
        if c.startswith(prefix):
            return section
    return None


# ---------------------------------------------------------------------------
# Dönem yardımcıları
# ---------------------------------------------------------------------------

def _quarter_before(year: int, period: int) -> tuple[int, int]:
    quarters = [3, 6, 9, 12]
    idx = quarters.index(period)
    return (year - 1, 12) if idx == 0 else (year, quarters[idx - 1])


def _generate_quarters(start_year: int, start_period: int, n: int) -> list[tuple[int, int]]:
    result = [(start_year, start_period)]
    y, p = start_year, start_period
    for _ in range(n - 1):
        y, p = _quarter_before(y, p)
        result.append((y, p))
    return result


def _batched(lst: list, n: int) -> Iterator[list]:
    it = iter(lst)
    while True:
        chunk = list(islice(it, n))
        if not chunk:
            break
        yield chunk


def _period_label(year: int, period: int) -> str:
    return f"{year}/{period}"


# ---------------------------------------------------------------------------
# Sayı çözümleme
# ---------------------------------------------------------------------------

def _parse_value(v: object) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in ("-", "—", "null", "None", ""):
        return None
    if s == "0":
        return 0.0
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _row_has_data(row: dict, value_idx: int = 1) -> bool:
    v = row.get(f"value{value_idx}")
    if v is None:
        return False
    s = str(v).strip()
    return bool(s) and s not in ("", "null", "None")


# ---------------------------------------------------------------------------
# Birleştirici (itemCode canonical)
# ---------------------------------------------------------------------------

class _SectionStore:
    def __init__(self) -> None:
        self._code_map:   dict[str, dict[str, str]]       = {s: {} for s in ("bilanco", "gelir", "dipnot", "nakit_akim")}
        self._desc_count: dict[str, dict[str, int]]       = {s: {} for s in ("bilanco", "gelir", "dipnot", "nakit_akim")}
        self.data:        dict[str, dict[str, dict]]      = {s: {} for s in ("bilanco", "gelir", "dipnot", "nakit_akim")}

    def add(self, section: str, code: str, desc: str, period: str, val: float | None) -> None:
        if code not in self._code_map[section]:
            dc = self._desc_count[section]
            dc[desc] = dc.get(desc, 0) + 1
            n = dc[desc]
            kalem = desc if n == 1 else f"{desc} ({n})"
            self._code_map[section][code] = kalem
            self.data[section][kalem] = {}
        else:
            kalem = self._code_map[section][code]
        self.data[section][kalem][period] = val


# ---------------------------------------------------------------------------
# Batch fetch
# ---------------------------------------------------------------------------

def _fetch_batch(
    session: requests.Session,
    ticker: str,
    quarters4: list[tuple[int, int]],
    currency: str,
    group: str,
) -> list[dict] | None:
    quarters4 = (quarters4 + [quarters4[-1]] * 4)[:4]
    params: dict = {"companyCode": ticker, "exchange": currency.upper(), "financialGroup": group}
    for i, (y, p) in enumerate(quarters4, start=1):
        params[f"year{i}"]   = y
        params[f"period{i}"] = p
    try:
        r = session.get(_JSON_URL, params=params, headers=_HEADERS, timeout=20)
        j = r.json()
        if not j.get("ok"):
            return None
        rows = j.get("value") or []
        return rows or None
    except Exception as exc:
        logger.debug("isyatirim batch hata [%s]: %s", ticker, exc)
        return None


def _batch_is_future(rows: list[dict]) -> bool:
    key_rows = [r for r in rows if r.get("itemCode", "").upper() in {"1A", "3C"}]
    if not key_rows:
        return False
    return all(not _row_has_data(r, 1) for r in key_rows)


# ---------------------------------------------------------------------------
# Cache yardımcıları
# ---------------------------------------------------------------------------

def _cache_path(ticker: str, currency: str) -> Path:
    return _CACHE_DIR / f"{ticker.upper()}_{currency.upper()}.json"


def _is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age = time.time() - path.stat().st_mtime
    return age < CACHE_TTL_HOURS * 3600


def _load_cache(path: Path) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _save_cache(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ---------------------------------------------------------------------------
# Scraping mantığı (lab isyatirim_scraper.py'den taşındı)
# ---------------------------------------------------------------------------

def _scrape(ticker: str, n_quarters: int, currency: str) -> dict:
    """isyatirim JSON API'sından veri çek. Hata → FinancialStatementProviderUnavailable."""
    import datetime

    session  = requests.Session()
    now      = datetime.date.today()

    candidates: list[tuple[int, int]] = []
    for y in [now.year, now.year - 1]:
        for p in [12, 9, 6, 3]:
            candidates.append((y, p))

    chosen_group: str | None    = None
    first_real_year: int | None = None
    first_real_period: int | None = None
    probe_rows: list[dict] | None = None
    probe_batch = candidates[:4]
    key_codes = {"1A", "3C"}

    for grp in _GROUPS_PRIORITY:
        rows = _fetch_batch(session, ticker, probe_batch, currency, grp)
        if not rows:
            continue
        key_rows = [r for r in rows if r.get("itemCode", "").upper() in key_codes]
        if not key_rows:
            continue
        for vi in range(1, 5):
            if any(_row_has_data(r, vi) for r in key_rows):
                chosen_group = grp
                first_real_year, first_real_period = probe_batch[vi - 1]
                probe_rows = rows
                break
        if chosen_group:
            break

    if not chosen_group:
        probe_batch2 = candidates[4:8]
        for grp in _GROUPS_PRIORITY:
            rows = _fetch_batch(session, ticker, probe_batch2, currency, grp)
            if not rows:
                continue
            key_rows = [r for r in rows if r.get("itemCode", "").upper() in key_codes]
            for vi in range(1, 5):
                if key_rows and any(_row_has_data(r, vi) for r in key_rows):
                    chosen_group = grp
                    first_real_year, first_real_period = probe_batch2[vi - 1]
                    probe_rows = rows
                    break
            if chosen_group:
                break

    if not chosen_group or first_real_year is None:
        raise FinancialStatementProviderUnavailable(
            f"{ticker}: isyatirim'den veri bulunamadı (tüm financialGroup denemesi başarısız)"
        )

    all_quarters = _generate_quarters(first_real_year, first_real_period, n_quarters + 4)
    batches      = list(_batched(all_quarters, 4))

    store             = _SectionStore()
    collected_periods: list[str] = []

    probe_labels = [_period_label(y, p) for y, p in probe_batch]
    first_labels = [_period_label(y, p) for y, p in batches[0]] if batches else []
    probe_cache  = probe_rows if probe_labels == first_labels else None

    for idx, batch in enumerate(batches):
        if len(collected_periods) >= n_quarters:
            break

        if idx == 0 and probe_cache is not None:
            rows = probe_cache
        else:
            if idx > 0:
                time.sleep(0.3)
            rows = _fetch_batch(session, ticker, batch, currency, chosen_group)

        if not rows or _batch_is_future(rows):
            continue

        for y, p in batch:
            label = _period_label(y, p)
            if label not in collected_periods:
                collected_periods.append(label)

        for row in rows:
            code    = row.get("itemCode", "")
            section = _code_to_section(code)
            if section is None:
                continue
            desc = (row.get("itemDescTr") or "").strip()
            if not desc:
                continue
            for i, (y, p) in enumerate(batch, start=1):
                label = _period_label(y, p)
                store.add(section, code, desc, label, _parse_value(row.get(f"value{i}")))

    final_periods = collected_periods[:n_quarters]
    if not final_periods:
        raise FinancialStatementProviderUnavailable(
            f"{ticker}: isyatirim'den geçerli dönem verisi alınamadı"
        )

    return {
        "ticker":   ticker,
        "periods":  final_periods,
        "currency": currency,
        "sections": store.data,
    }


# ---------------------------------------------------------------------------
# Public provider sınıfı
# ---------------------------------------------------------------------------

class IsyatirimProvider:
    """
    IFinancialStatementProvider implementasyonu.
    Cache geçerliyse ağa gitmez; geçersizse scrape eder ve cache'e yazar.
    """

    def get_financial_data(
        self,
        ticker: str,
        n_quarters: int = 12,
        currency: str = "TRY",
    ) -> dict:
        ticker   = ticker.upper().strip()
        currency = currency.upper().strip()

        path = _cache_path(ticker, currency)
        if _is_cache_fresh(path):
            cached = _load_cache(path)
            if cached:
                logger.debug("isyatirim cache hit: %s_%s", ticker, currency)
                return cached

        logger.info("isyatirim scrape: %s (%s, %dQ)", ticker, currency, n_quarters)
        try:
            data = _scrape(ticker, n_quarters, currency)
        except FinancialStatementProviderUnavailable:
            raise
        except Exception as exc:
            raise FinancialStatementProviderUnavailable(
                f"isyatirim veri çekme hatası [{ticker}]: {exc}"
            ) from exc

        try:
            _save_cache(path, data)
        except Exception as exc:
            logger.warning("isyatirim cache yazılamadı [%s]: %s", ticker, exc)

        return data
