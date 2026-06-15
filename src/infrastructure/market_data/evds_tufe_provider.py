"""
EVDS TÜFE Provider — IInflationDataProvider implementasyonu.

EvdsClient.get_series("TP.FG.J0") üzerinden aylık TÜFE endeksini çeker.
Dosya cache + TTL ile gereksiz ağ isteklerini önler.

Cache: data/_cache/financials/tufe_index.json
TTL: 24 saat (günlük veri — daha sık yenilemek anlamsız)
"""
from __future__ import annotations

import json
import logging
import time
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from src.domain.ports.services.i_inflation_data_provider import InflationDataUnavailable

logger = logging.getLogger(__name__)

_PROJECT_ROOT   = Path(__file__).parent.parent.parent.parent
_CACHE_DIR      = _PROJECT_ROOT / "data" / "_cache" / "financials"
_CACHE_FILE     = _CACHE_DIR / "tufe_index.json"
CACHE_TTL_HOURS = 24
_TUFE_SERIES    = "TP.FG.J0"


def _is_cache_fresh(path: Path) -> bool:
    if not path.exists():
        return False
    age_h = (time.time() - path.stat().st_mtime) / 3600
    return age_h < CACHE_TTL_HOURS


def _load_cache(path: Path) -> dict[str, float] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _save_cache(path: Path, data: dict[str, float]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_items(items: list[dict[str, Any]]) -> dict[str, float]:
    """EVDS API item listesini {"YYYY-MM": value} formatına çevirir."""
    result: dict[str, float] = {}
    for item in items:
        tarih = item.get("Tarih", "")
        val   = item.get(_TUFE_SERIES)
        if not tarih or val is None:
            continue
        try:
            # tarih: "01-01-2024" → "2024-01"
            parts = tarih.split("-")
            month_key = f"{parts[2]}-{parts[1]}"
            result[month_key] = float(str(val).replace(",", "."))
        except Exception:
            continue
    return result


class EvdsTufeProvider:
    """TÜFE aylık endeks verisi — EvdsClient wrapper + dosya cache."""

    def __init__(self, evds_client: Any) -> None:
        self._client = evds_client

    def get_monthly_tufe(self, start: date, end: date) -> dict[str, float]:
        """
        Aylık TÜFE endeks değerleri. {"YYYY-MM": index_value}
        Cache taze ise ağ çağrısı yapılmaz.
        Cache bayat/yok → EvdsClient üzerinden tazele + cache'e yaz.
        """
        if _is_cache_fresh(_CACHE_FILE):
            cached = _load_cache(_CACHE_FILE)
            if cached is not None:
                return _filter_range(cached, start, end)

        try:
            items = self._client.get_series(_TUFE_SERIES, start, end)
            data  = _parse_items(items)
        except Exception as exc:
            logger.warning("EVDS TÜFE çekme hatası: %s", exc)
            cached = _load_cache(_CACHE_FILE) or {}
            if not cached:
                raise InflationDataUnavailable(str(exc)) from exc
            return _filter_range(cached, start, end)

        existing = _load_cache(_CACHE_FILE) or {}
        existing.update(data)
        _save_cache(_CACHE_FILE, existing)
        return _filter_range(existing, start, end)


def _filter_range(data: dict[str, float], start: date, end: date) -> dict[str, float]:
    start_key = f"{start.year}-{start.month:02d}"
    end_key   = f"{end.year}-{end.month:02d}"
    return {k: v for k, v in data.items() if start_key <= k <= end_key}
