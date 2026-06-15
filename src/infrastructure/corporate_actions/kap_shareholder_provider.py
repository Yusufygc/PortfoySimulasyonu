"""
KAP Ortaklık Yapısı sağlayıcısı.

IShareholderProvider implementasyonu:
  - BIST şirketleri listesinden ticker → mkkMemberOid eşleşmesini çıkar (haftalık TTL).
  - https://kap.org.tr/tr/api/company-detail/get-history/{OID}/{itemKey}/N
    endpoint'inden pay sahipliği tarihçesini çek (en yeni önce).
  - Tüm ağ/parse hataları → ShareholderProviderUnavailable.

Sermayede %5+ pay sahibi itemKey: kpy41_acc5_sermayede_dogrudan
"""
from __future__ import annotations

import json
import logging
import re
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Optional

from src.domain.models.shareholder import ShareholderRow, ShareholderSnapshot
from src.domain.ports.services.i_shareholder_provider import (
    IShareholderProvider,
    ShareholderProviderUnavailable,
)

logger = logging.getLogger(__name__)

_PROJECT_ROOT     = Path(__file__).parent.parent.parent.parent
_CACHE_DIR        = _PROJECT_ROOT / "data" / "_cache" / "kap"
_BIST_CACHE_FILE  = _CACHE_DIR / "bist_companies.json"
_BIST_TTL_HOURS   = 24 * 7  # haftalık refresh

_BIST_URL = "https://www.kap.org.tr/tr/bist-sirketler"
_ITEM_KEY_SHAREHOLDER = "kpy41_acc5_sermayede_dogrudan"
_HISTORY_URL = "https://kap.org.tr/tr/api/company-detail/get-history/{oid}/{key}/N"

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/html, */*",
    "Accept-Language": "tr-TR,tr;q=0.9",
}


class KapShareholderProvider(IShareholderProvider):
    """KAP HTTP + dosya cache tabanlı pay sahipliği sağlayıcısı."""

    def __init__(self) -> None:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_shareholder_history(self, ticker: str) -> list[ShareholderSnapshot]:
        ticker = ticker.strip().upper()
        oid = self._resolve_oid(ticker)
        raw = self._fetch_history(oid, _ITEM_KEY_SHAREHOLDER)
        return _parse_history(raw)

    def resolve_member_oid(self, ticker: str) -> tuple[str, Optional[str]]:
        """Ticker → (mkkMemberOid, title). Cache miss'te ağdan çeker."""
        ticker = ticker.strip().upper()
        comp_map = self._load_bist_map()
        rec = comp_map.get(ticker)
        if not rec:
            raise ShareholderProviderUnavailable(
                f"{ticker}: KAP'ta bulunamadı (BIST listesi haritası)"
            )
        return rec["mkkMemberOid"], rec.get("kapMemberTitle")

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _resolve_oid(self, ticker: str) -> str:
        oid, _ = self.resolve_member_oid(ticker)
        return oid

    def _load_bist_map(self) -> dict:
        if self._cache_fresh(_BIST_CACHE_FILE, _BIST_TTL_HOURS):
            try:
                return json.loads(_BIST_CACHE_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("BIST cache parse hatası, yeniden çekilecek: %s", exc)
        return self._refresh_bist_map()

    def _refresh_bist_map(self) -> dict:
        try:
            html = self._http_get(_BIST_URL)
        except Exception as exc:
            raise ShareholderProviderUnavailable(f"KAP BIST listesi alınamadı: {exc}") from exc
        comp_map = _parse_bist_companies(html)
        if not comp_map:
            raise ShareholderProviderUnavailable("KAP BIST listesi boş döndü")
        try:
            _BIST_CACHE_FILE.write_text(json.dumps(comp_map, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.warning("BIST cache yazılamadı: %s", exc)
        return comp_map

    def _fetch_history(self, oid: str, item_key: str) -> list[dict]:
        url = _HISTORY_URL.format(oid=oid, key=item_key)
        try:
            body = self._http_get(url)
            data = json.loads(body)
        except Exception as exc:
            raise ShareholderProviderUnavailable(
                f"KAP tarihçe alınamadı [{oid}/{item_key}]: {exc}"
            ) from exc
        if not isinstance(data, list):
            raise ShareholderProviderUnavailable(
                f"KAP tarihçe beklenen JSON listesi değil: {type(data).__name__}"
            )
        return data

    def _http_get(self, url: str, timeout: int = 20) -> str:
        req = urllib.request.Request(url, headers=_HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")

    @staticmethod
    def _cache_fresh(path: Path, ttl_hours: int) -> bool:
        if not path.exists():
            return False
        age = datetime.now() - datetime.fromtimestamp(path.stat().st_mtime)
        return age < timedelta(hours=ttl_hours)


# ---------------------------------------------------------------------------
# Parsers — saf fonksiyonlar (test edilebilir)
# ---------------------------------------------------------------------------

_OBJ_PATTERN  = re.compile(r"\{[^{}]*?\"mkkMemberOid\"[^{}]*?\}")
_OID_PATTERN  = re.compile(r'"mkkMemberOid":"([0-9a-fA-F]{32})"')
_TICK_PATTERN = re.compile(r'"stockCode":"([A-Z0-9]+)"')
_TITLE_PATTERN = re.compile(r'"kapMemberTitle":"([^"]+)"')


def _parse_bist_companies(html: str) -> dict[str, dict]:
    """KAP BIST sayfasından ticker → company info map çıkar (alan sırasından bağımsız)."""
    out: dict[str, dict] = {}
    for obj_match in _OBJ_PATTERN.finditer(html):
        obj = obj_match.group(0)
        oid_m   = _OID_PATTERN.search(obj)
        tick_m  = _TICK_PATTERN.search(obj)
        title_m = _TITLE_PATTERN.search(obj)
        if not oid_m or not tick_m:
            continue
        ticker = tick_m.group(1)
        if ticker in out:
            continue
        out[ticker] = {
            "mkkMemberOid":   oid_m.group(1),
            "stockCode":      ticker,
            "kapMemberTitle": title_m.group(1) if title_m else None,
        }
    return out


def _parse_history(raw: list[dict]) -> list[ShareholderSnapshot]:
    """KAP get-history yanıtını ShareholderSnapshot listesine çevir (en yeni önce)."""
    snapshots: list[ShareholderSnapshot] = []
    for entry in raw:
        date_str = entry.get("creationDate", "")
        snap_date = _parse_creation_date(date_str)
        if snap_date is None:
            continue
        rows_raw = entry.get("value") or []
        if not isinstance(rows_raw, list):
            continue
        rows: list[ShareholderRow] = []
        for r in rows_raw:
            name = str(r.get("shareholder", "")).strip()
            if not name:
                continue
            rows.append(ShareholderRow(
                shareholder_name=name,
                share_in_capital=_parse_decimal(r.get("shareInCapital")),
                ratio_in_capital=_parse_decimal(r.get("ratioInCapital")),
                voting_right_ratio=_parse_decimal(r.get("votingRightRatio")),
                is_total=name.strip().upper() in {"TOTAL", "TOPLAM"},
            ))
        if rows:
            snapshots.append(ShareholderSnapshot(creation_date=snap_date, rows=tuple(rows)))
    snapshots.sort(key=lambda s: s.creation_date, reverse=True)
    return snapshots


def _parse_creation_date(value: str) -> Optional[date]:
    """KAP 'DD/MM/YYYY' veya 'DD/MM/YYYY HH:MM:SS' formatlarını parse et."""
    if not value:
        return None
    head = value.strip().split()[0]
    try:
        return datetime.strptime(head, "%d/%m/%Y").date()
    except ValueError:
        return None


def _parse_decimal(value) -> Optional[Decimal]:
    """KAP TR-locale sayı stringi: '69.600.000' (TL) ya da '19,33' (%) → Decimal."""
    if value is None:
        return None
    s = str(value).strip()
    if not s or s.lower() in {"-", "n/a"}:
        return None
    # Binlik ayırıcı '.', ondalık ',': '69.600.000,12' → '69600000.12'
    if "," in s:
        s = s.replace(".", "").replace(",", ".")
    else:
        # Sadece nokta varsa ve >1 nokta varsa binlik; tek nokta → ondalık
        if s.count(".") > 1:
            s = s.replace(".", "")
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None
