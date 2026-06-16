"""
tufe_provider.py — TÜFE (CPI) Veri Sağlayıcı

EVDS API'sinden TP.FG.J0 serisi çekerek aylık TÜFE endeksi sağlar.
Basit dosya cache ile gereksiz ağ isteklerini önler.

ENTEGRASYON NOTU:
  Bu modül, asıl sisteme entegrasyon için tasarlanmıştır:
  - src/infrastructure/market_data/evds_client.py → EvdsClient.get_series("TP.FG.J0", ...)
  - src/application/services/analysis/benchmark_service.py → zaten TP.FG.J0 kullanıyor
  - config/settings_loader.py → load_market_settings().evds_api_key
  Lab standalone: bu modülü kullanır.
  Asıl sistem: EvdsClient + DI injection yeterli.

Kullanım:
    from tufe_provider import get_tufe_index, real_growth
    tufe = get_tufe_index(date(2024, 1, 1), date(2026, 3, 31))
    # tufe == {"2024-01": 1402.83, "2024-02": 1468.22, ...}
    reel = real_growth(nominal_pct=80.0, tufe_pct=65.0)  # → 9.09%
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Optional
from urllib.request import Request, urlopen
import urllib.error

logger = logging.getLogger(__name__)

# Proje kökü ve lab data cache dizini
_LAB_DIR   = Path(__file__).parent
_CACHE_DIR = _LAB_DIR / "data" / "_cache"
_CACHE_FILE = _CACHE_DIR / "tufe.json"

# EVDS endpoint (asıl sistemdeki evds_client.py ile aynı)
_EVDS_URL_TPL = (
    "https://evds3.tcmb.gov.tr/igmevdsms-dis/"
    "series=TP.FG.J0&startDate={start}&endDate={end}&type=json"
)
_TUFE_SERIES = "TP.FG.J0"


def _load_env_key() -> str:
    """
    .env dosyasından EVDS_API_KEY okur (python-dotenv olmadan, basit parse).
    Asıl sistemde load_market_settings().evds_api_key kullanılır.
    """
    key = os.environ.get("EVDS_API_KEY", "")
    if key:
        return key

    # Proje kökündeki .env dosyasını dene
    root = _LAB_DIR.parent.parent.parent.parent.parent  # proje kökü
    env_paths = [
        _LAB_DIR.parents[4] / ".env",  # 5 üst dizin
        _LAB_DIR.parents[3] / ".env",
        _LAB_DIR.parents[2] / ".env",
        Path(".env"),
    ]
    for env_path in env_paths:
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("EVDS_API_KEY"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    return ""


def _fetch_from_api(start: date, end: date, api_key: str) -> dict[str, float]:
    """EVDS API'sinden TÜFE verisi çeker. EvdsClient.get_series() ile aynı mantık."""
    url = _EVDS_URL_TPL.format(
        start=start.strftime("%d-%m-%Y"),
        end=end.strftime("%d-%m-%Y"),
    )
    req = Request(
        url,
        headers={"key": api_key, "Accept": "application/json"},
        method="GET",
    )
    try:
        with urlopen(req, timeout=15) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.URLError as e:
        raise RuntimeError(f"EVDS bağlantı hatası: {e}") from e

    items = payload.get("items", [])
    result: dict[str, float] = {}
    for item in items:
        # Tarih formatı "YYYY-MM" veya "DD-MM-YYYY" → normalize et
        raw_date = item.get("Tarih") or item.get("tarih") or ""
        raw_val  = item.get(_TUFE_SERIES) or item.get("TP_FG_J0")
        if not raw_date or raw_val is None:
            continue
        try:
            val = float(str(raw_val).replace(",", "."))
        except ValueError:
            continue
        # Tarih normalleştirme: "01-01-2024" → "2024-01"
        parts = raw_date.split("-")
        if len(parts) == 3:
            if len(parts[2]) == 4:  # DD-MM-YYYY
                month_key = f"{parts[2]}-{parts[1]}"
            else:  # YYYY-MM-DD veya YYYY-MM
                month_key = f"{parts[0]}-{parts[1]}"
        elif len(parts) == 2:
            month_key = f"{parts[0]}-{parts[1]}"
        else:
            continue
        result[month_key] = val

    return result


def _load_cache() -> dict[str, float]:
    if _CACHE_FILE.exists():
        try:
            with open(_CACHE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_cache(data: dict[str, float]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_tufe_index(
    start: date,
    end: date,
    force_refresh: bool = False,
) -> dict[str, float]:
    """
    Aylık TÜFE endeksini döndür: {"YYYY-MM": index_value, ...}.

    Önce cache kontrol edilir. Eksik aylar varsa API'den tamamlanır.
    force_refresh=True → cache'i atla, API'den tazele.

    Returns:
        Boş dict: API key yoksa veya bağlantı yoksa (sessiz hata).
    """
    cache = {} if force_refresh else _load_cache()

    # İstenen ayları belirle
    needed: list[str] = []
    d = date(start.year, start.month, 1)
    while d <= end:
        key = f"{d.year}-{d.month:02d}"
        if key not in cache:
            needed.append(key)
        d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)

    if needed:
        api_key = _load_env_key()
        if not api_key:
            logger.warning("EVDS_API_KEY bulunamadı. TÜFE verisi eksik olacak.")
            return cache  # cache'deki mevcut veriyi döndür

        # Eksik dönemlerin tamamını tek istekle çek
        fetch_start = date(
            int(needed[0].split("-")[0]),
            int(needed[0].split("-")[1]),
            1,
        )
        fetch_end = end
        try:
            fresh = _fetch_from_api(fetch_start, fetch_end, api_key)
            cache.update(fresh)
            _save_cache(cache)
            logger.info("TÜFE verisi güncellendi: %d ay", len(fresh))
        except Exception as e:
            logger.warning("TÜFE API hatası: %s", e)

    # İstenen aralığı filtrele
    start_key = f"{start.year}-{start.month:02d}"
    end_key   = f"{end.year}-{end.month:02d}"
    return {k: v for k, v in cache.items() if start_key <= k <= end_key}


def real_growth(nominal_pct: float, tufe_pct: float) -> float:
    """
    Reel büyüme hesabı (Fisher etkisi):
      reel = (1 + nominal) / (1 + tüfe) - 1

    Args:
        nominal_pct: Nominal büyüme oranı (% cinsinden, ör: 80.0 = %80)
        tufe_pct:    Aynı dönem TÜFE artışı (% cinsinden, ör: 65.0 = %65)

    Returns:
        Reel büyüme oranı (% cinsinden)
    """
    return ((1 + nominal_pct / 100) / (1 + tufe_pct / 100) - 1) * 100


def period_to_month(period: str) -> str:
    """
    isyatirim dönem formatını ay-key'e çevirir.
    "2026/3" → "2026-03"
    "2025/12" → "2025-12"
    """
    y, m = period.split("/")
    return f"{y}-{int(m):02d}"


def get_yoy_tufe(period: str, tufe_index: dict[str, float]) -> Optional[float]:
    """
    Belirtilen dönem için YoY TÜFE artışını hesaplar (%).
    Dönem: "2026/3" → Mart 2026 endeksi vs Mart 2025 endeksi.
    """
    cur_month  = period_to_month(period)
    y, m = cur_month.split("-")
    prev_month = f"{int(y) - 1}-{m}"

    cur_idx  = tufe_index.get(cur_month)
    prev_idx = tufe_index.get(prev_month)

    if cur_idx is None or prev_idx is None or prev_idx == 0:
        return None
    return (cur_idx / prev_idx - 1) * 100
