"""
isyatirim.com.tr Mali Tablo Scraper — v6 (JSON endpoint, ViewState-free)

isyatirim'in resmi JSON API'sını kullanır:
  GET /Data.aspx/MaliTablo?companyCode=FROTO&exchange=TRY&financialGroup=XI_29
      &year1=..&period1=..&year2=..&period2=..&year3=..&period3=..&year4=..&period4=..
  → {"ok":true,"value":[{"itemCode":"1A","itemDescTr":"...","value1":"..","value2":"..","value3":"..","value4":".."},..]}

Avantajlar (v5 ViewState postback'e göre):
  - Duplikasyon yok: her batch tamamen bağımsız, gerçek veriler döner.
  - BeautifulSoup / ASP.NET ViewState postback yok.
  - itemCode prefix → section (HTML colspan parsing gerekmez).
  - ~0.3s/batch → 12 çeyrek = ~1s.
  - Banka hisseleri (AKBNK) için XI_29→UFRS auto-fallback.
  - itemCode canonical key: aynı kalem farklı batch'lerde birleşir (kopya yok).

Çıktı şeması v5 ile özdeş (metrics.py/viz/run değişmez):
{
  "ticker": "FROTO",
  "periods": ["2026/3", "2025/12", ...],   # newest first
  "currency": "TRY",
  "sections": {
    "bilanco":    {"Dönen Varlıklar": {"2026/3": 189695856000.0, ...}},
    "gelir":      {"Satış Gelirleri": {...}},
    "dipnot":     {"Amortisman Giderleri": {...}},
    "nakit_akim": {"Serbest Nakit Akım": {...}}
  }
}

Kullanım:
    python isyatirim_scraper.py                   # FROTO 12 çeyrek TRY
    python isyatirim_scraper.py EREGL 16
    python isyatirim_scraper.py AKBNK 8 USD

Import:
    from isyatirim_scraper import fetch_financial_data
    data = fetch_financial_data("FROTO", n_quarters=12)
"""
from __future__ import annotations

import io
import json
import sys
import time
from itertools import islice
from pathlib import Path
from typing import Iterator

import requests

# ---------------------------------------------------------------------------
# stdout fix
# ---------------------------------------------------------------------------

def _fix_stdout() -> None:
    """Windows cp1254 fix — entry-point'te bir kez çağır."""
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "") != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer") and getattr(sys.stderr, "encoding", "") != "utf-8":
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Sabitler
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

# financialGroup: sanayi=XI_29, banka=UFRS
_GROUPS_PRIORITY = ["XI_29", "UFRS"]

# itemCode prefix → section
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
# Dönem üretici
# ---------------------------------------------------------------------------

def _quarter_before(year: int, period: int) -> tuple[int, int]:
    """(2026,3) → (2025,12)."""
    quarters = [3, 6, 9, 12]
    idx = quarters.index(period)
    if idx == 0:
        return year - 1, 12
    return year, quarters[idx - 1]


def _generate_quarters_from(start_year: int, start_period: int, n: int) -> list[tuple[int, int]]:
    """start'tan geriye n çeyrek, yeni→eski."""
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
    if not s or s in ("-", "—", "null", "None", "0", ""):
        # "0" gerçekten sıfır olabilir ama API boş dönem için "" veya null döner
        if s == "0":
            return 0.0
        return None
    try:
        return float(s.replace(".", "").replace(",", "."))
    except ValueError:
        return None


def _row_has_data(row: dict, value_idx: int = 1) -> bool:
    """value{value_idx} gerçek veri içeriyor mu (null/boş değil)?"""
    v = row.get(f"value{value_idx}")
    if v is None:
        return False
    s = str(v).strip()
    return bool(s) and s not in ("", "null", "None")


# ---------------------------------------------------------------------------
# JSON fetch
# ---------------------------------------------------------------------------

def _fetch_batch(
    session: requests.Session,
    ticker: str,
    quarters4: list[tuple[int, int]],
    currency: str,
    group: str,
) -> list[dict] | None:
    """4 (year,period) için GET → satır listesi veya None."""
    quarters4 = (quarters4 + [quarters4[-1]] * 4)[:4]
    params: dict = {
        "companyCode":    ticker,
        "exchange":       currency.upper(),
        "financialGroup": group,
    }
    for i, (y, p) in enumerate(quarters4, start=1):
        params[f"year{i}"]   = y
        params[f"period{i}"] = p

    try:
        r = session.get(_JSON_URL, params=params, headers=_HEADERS, timeout=20)
        j = r.json()
        if not j.get("ok"):
            return None
        rows = j.get("value") or []
        return rows if rows else None
    except Exception as exc:
        print(f"    [batch hata] {exc}")
        return None


def _batch_is_future(rows: list[dict]) -> bool:
    """
    value1 tüm anahtar satırlarda boşsa bu batch henüz yayınlanmamış
    (gelecek dönem) → atla.
    Kontrol: bilanço ve gelir key row'larına bak.
    """
    key_codes = {"1A", "3C"}
    key_rows = [r for r in rows if r.get("itemCode", "").upper() in key_codes]
    if not key_rows:
        return False  # bilinmeyen yapı, güvenli tarafta kal
    return all(not _row_has_data(r, 1) for r in key_rows)


# ---------------------------------------------------------------------------
# Birleştirme — itemCode canonical key
# ---------------------------------------------------------------------------

class _SectionStore:
    """
    Her itemCode'un kalem adını (suffix'li) sabit tutar.
    Aynı bölümde aynı itemDescTr farklı itemCode'larda tekrarlanırsa suffix atar.
    Farklı batch'lerin aynı itemCode'u aynı kalemin dönem verisini birleştirir.
    """
    def __init__(self) -> None:
        # code → kalem_name
        self._code_map: dict[str, dict[str, str]] = {
            s: {} for s in ("bilanco", "gelir", "dipnot", "nakit_akim")
        }
        # desc → kaç farklı code bu desc'e sahip (suffix sayacı)
        self._desc_count: dict[str, dict[str, int]] = {
            s: {} for s in ("bilanco", "gelir", "dipnot", "nakit_akim")
        }
        # section → kalem → period → float|None
        self.data: dict[str, dict[str, dict[str, float | None]]] = {
            s: {} for s in ("bilanco", "gelir", "dipnot", "nakit_akim")
        }

    def add(self, section: str, code: str, desc: str, period: str, val: float | None) -> None:
        # İlk kez bu code görülüyor → kalem adı ata
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
# Ana API
# ---------------------------------------------------------------------------

def fetch_financial_data(
    ticker: str,
    n_quarters: int = 12,
    currency: str = "TRY",
    verbose: bool = True,
) -> dict:
    """
    İş Yatırım JSON API'sından ticker için finansal veri çeker.

    Dönen dict şeması (metrics.py/viz_prototype.py/run.py ile uyumlu):
    {
      "ticker": str,
      "periods": list[str],        # newest first: ["2026/3", "2025/12", ...]
      "currency": str,
      "sections": {
        "bilanco":    {kalem: {period: float|None}},
        "gelir":      {kalem: {period: float|None}},
        "dipnot":     {kalem: {period: float|None}},
        "nakit_akim": {kalem: {period: float|None}},
      }
    }
    """
    ticker   = ticker.upper().strip()
    currency = currency.upper().strip()

    if verbose:
        print(f"\n[Scraper] {ticker} — en fazla {n_quarters} çeyrek, {currency}")

    session = requests.Session()

    # --- financialGroup auto-detect + ilk gerçek dönem bul ---
    # Bu yılın tüm çeyreklerini + önceki yılı dene; en yeni gerçek verili dönemi bul.
    import datetime
    now = datetime.date.today()
    candidates: list[tuple[int, int]] = []
    for y in [now.year, now.year - 1]:
        for p in [12, 9, 6, 3]:
            candidates.append((y, p))

    chosen_group:    str | None = None
    first_real_year: int | None = None
    first_real_period: int | None = None
    probe_rows:      list[dict] | None = None

    # Probe: ilk 4 aday → batch olarak gönder.
    # Batch içinde value1..value4 sırasıyla en yeni→eski çeyrek.
    # En yeni value_idx'i (1=en yeni) bul; değer varsa o dönem gerçek.
    probe_batch = candidates[:4]  # [(yıl,12),(yıl,9),(yıl,6),(yıl,3)]
    key_codes = {"1A", "3C"}

    for grp in _GROUPS_PRIORITY:
        rows = _fetch_batch(session, ticker, probe_batch, currency, grp)
        if not rows:
            continue
        key_rows = [r for r in rows if r.get("itemCode", "").upper() in key_codes]
        if not key_rows:
            continue
        # En küçük value_idx (= en yeni dönem) gerçek veri içeriyor mu?
        for vi in range(1, 5):
            if any(_row_has_data(r, vi) for r in key_rows):
                chosen_group = grp
                first_real_year, first_real_period = probe_batch[vi - 1]
                probe_rows = rows
                break
        if chosen_group:
            break

    if not chosen_group:
        # Fallback: önceki yıl batch
        probe_batch2 = candidates[4:8]
        for grp in _GROUPS_PRIORITY:
            rows = _fetch_batch(session, ticker, probe_batch2, currency, grp)
            if rows:
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
        raise RuntimeError(f"{ticker}: veri bulunamadı (tüm financialGroup denemesi başarısız)")

    if verbose:
        print(f"  financialGroup: {chosen_group}")
        print(f"  Başlangıç dönemi: {_period_label(first_real_year, first_real_period)}")

    # --- Çeyrek listesi oluştur ---
    all_quarters = _generate_quarters_from(first_real_year, first_real_period, n_quarters + 4)
    batches = list(_batched(all_quarters, 4))

    store = _SectionStore()
    collected_periods: list[str] = []
    real_batches = 0

    # probe_batch == batches[0] ise probe_rows yeniden kullanılabilir.
    # Değilse (örn. probe_batch=[2026/12..2026/3] ama batches[0]=[2026/3..2025/6])
    # ilk batch ayrıca çekilir.
    probe_batch_labels = [_period_label(y, p) for y, p in (probe_batch or [])]
    first_batch_labels = [_period_label(y, p) for y, p in batches[0]] if batches else []
    _probe_cache = probe_rows if probe_batch_labels == first_batch_labels else None

    for idx, batch in enumerate(batches):
        if len(collected_periods) >= n_quarters:
            break

        if idx == 0 and _probe_cache is not None:
            rows = _probe_cache
        else:
            if idx > 0:
                time.sleep(0.3)
            rows = _fetch_batch(session, ticker, batch, currency, chosen_group)

        if not rows:
            if verbose:
                print(f"  Batch {idx+1}: boş/hata (atlandı)")
            continue

        if _batch_is_future(rows):
            if verbose:
                print(f"  Batch {idx+1}: gelecek dönem (atlandı)")
            continue

        batch_added = 0
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
                val   = _parse_value(row.get(f"value{i}"))
                store.add(section, code, desc, label, val)
                if i == 1:
                    batch_added += 1  # sadece ilk period için say

        real_batches += 1
        for y, p in batch:
            label = _period_label(y, p)
            if label not in collected_periods:
                collected_periods.append(label)

        if verbose:
            labels = [_period_label(y, p) for y, p in batch]
            row_count = sum(len(store.data[s]) for s in store.data)
            print(f"  Batch {idx+1}/{len(batches)}: {labels[0]}..{labels[-1]}  → {batch_added} satır, {row_count} toplam kalem")

    final_periods = collected_periods[:n_quarters]

    if verbose:
        print(f"  Toplam {len(final_periods)} dönem, {real_batches} batch")
        for s in ("bilanco", "gelir", "dipnot", "nakit_akim"):
            print(f"    {s}={len(store.data[s])} kalem")

    return {
        "ticker":   ticker,
        "periods":  final_periods,
        "currency": currency,
        "sections": store.data,
    }


# ---------------------------------------------------------------------------
# Kaydetme
# ---------------------------------------------------------------------------

def _save(data: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    ticker   = data["ticker"]
    currency = data["currency"].lower()
    path     = out_dir / f"{ticker.lower()}_{currency}_finansal.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    _fix_stdout()

    ticker   = sys.argv[1] if len(sys.argv) > 1 else "FROTO"
    n_qrtrs  = int(sys.argv[2]) if len(sys.argv) > 2 else 12
    currency = sys.argv[3].upper() if len(sys.argv) > 3 else "TRY"

    data     = fetch_financial_data(ticker, n_quarters=n_qrtrs, currency=currency)
    lab_dir  = Path(__file__).parent
    out_file = _save(data, lab_dir / "data" / ticker)
    print(f"\n  Kaydedildi: {out_file}")

    # Duplikasyon kontrol
    print("\n  === Satış Gelirleri (benzersizlik testi) ===")
    satis = data["sections"]["gelir"].get("Satış Gelirleri", {})
    for p in data["periods"]:
        v = satis.get(p)
        print(f"  {p:>9}  {v:>22,.0f}" if v else f"  {p:>9}  —")

    # Bilanço (son dönem)
    print("\n  === Bilanço (son dönem) ===")
    p0 = data["periods"][0] if data["periods"] else "?"
    for k in list(data["sections"]["bilanco"].keys())[:10]:
        v = data["sections"]["bilanco"][k].get(p0)
        if v:
            print(f"  {k:<52} {v:>22,.0f}")
