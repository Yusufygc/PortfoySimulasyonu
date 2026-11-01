"""KAP şirket bildirimleri (BIST). Resmî olmayan `members/byCriteria` uç noktasını kullanır (bkz. YeniPlan spike notu)."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

from src.domain.market_clock import MARKET_TIMEZONE, market_today
from src.domain.models.news_item import NewsItem, NewsScope, NewsTarget, TargetKind
from src.domain.ports.services.i_news_provider import INewsProvider, NewsProviderUnavailable
from src.infrastructure.news._http import PostFetcher, http_post_json

logger = logging.getLogger(__name__)

SOURCE_ID = "kap"
KAP_BYCRITERIA_URL = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"
KAP_DISCLOSURE_URL = "https://www.kap.org.tr/tr/Bildirim/{index}"
_REFERER = "https://www.kap.org.tr/tr/bildirim-sorgu"

LOOKBACK_DAYS = 14
MAX_COMPANIES = 40
MAX_ITEMS = 60
MAX_RELATED_STOCKS = 5  # bundan çok hisse listeleyen kurum bildirimi "toplu duyuru" sayılır

_RESOLVE_OID = Callable[[str], str]


def _request_body(oids: Sequence[str], start, end) -> Dict[str, Any]:
    return {
        "fromDate": start.isoformat(), "toDate": end.isoformat(), "memberType": "IGS",
        "mkkMemberOidList": list(oids), "inactiveMkkMemberOidList": [], "disclosureClass": "",
        "subjectList": [], "isLate": "", "mainSector": "", "sector": "", "subSector": "", "marketOidList": [],
        "index": "", "bdkReview": "", "bdkMemberOidList": [], "year": "", "term": "", "ruleType": "", "period": "",
        "fromSrc": False, "srcCategory": "", "disclosureIndexList": [],
    }


def _split_codes(raw: Any) -> List[str]:
    return [code.strip().upper() for code in str(raw or "").split(",") if code.strip()]


def _parse_publish_date(text: str) -> Optional[datetime]:
    """`dd.MM.yyyy HH:mm:ss` (İstanbul saati) -> UTC."""
    try:
        local = datetime.strptime(text.strip(), "%d.%m.%Y %H:%M:%S")
    except (ValueError, AttributeError):
        return None
    return local.replace(tzinfo=MARKET_TIMEZONE).astimezone(timezone.utc)


def _is_noise_sub_document(payload: Dict[str, Any]) -> bool:
    return payload.get("disclosureClass") == "FR" and "sorumluluk beyan" in str(payload.get("subject", "")).casefold()


def _is_mass_notice(payload: Dict[str, Any], tracked: set) -> bool:
    """Kendi bildirimi olmayan ve çok sayıda hisseyi listeleyen kurum duyurusu."""
    if _split_codes(payload.get("stockCodes")):
        return False
    related = _split_codes(payload.get("relatedStocks"))
    return len(related) > MAX_RELATED_STOCKS or not (set(related) & tracked)


def _related_symbols(payload: Dict[str, Any], tracked: set) -> tuple:
    codes = _split_codes(payload.get("stockCodes")) or _split_codes(payload.get("relatedStocks"))
    return tuple(code for code in codes if code in tracked) or tuple(codes[:MAX_RELATED_STOCKS])


def _to_news_item(payload: Dict[str, Any], tracked: set) -> Optional[NewsItem]:
    published = _parse_publish_date(str(payload.get("publishDate", "")))
    index = payload.get("disclosureIndex")
    title = str(payload.get("subject") or payload.get("kapTitle") or "").strip()
    if published is None or index is None or not title:
        return None
    return NewsItem(
        title=title,
        url=KAP_DISCLOSURE_URL.format(index=index),
        source_id=SOURCE_ID,
        source_name="KAP",
        published_at=published,
        summary=str(payload.get("summary") or "").strip(),
        related_symbols=_related_symbols(payload, tracked),
        language="tr",
        badge=str(payload.get("disclosureClass") or ""),
    )


def _collapse_financial_reports(payloads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aynı şirketin aynı dakikada yayımlanan birden çok `FR` kaydından yalnızca birini bırakır."""
    kept: List[Dict[str, Any]] = []
    seen: Dict[tuple, int] = {}
    for payload in payloads:
        if payload.get("disclosureClass") != "FR":
            kept.append(payload)
            continue
        key = (str(payload.get("stockCodes")), str(payload.get("publishDate", ""))[:16])
        position = seen.get(key)
        if position is None:
            seen[key] = len(kept)
            kept.append(payload)
        elif "finansal rapor" in str(payload.get("subject", "")).casefold():
            kept[position] = payload
    return kept


class KapDisclosureNewsProvider(INewsProvider):
    def __init__(
        self,
        resolve_oid: _RESOLVE_OID,
        poster: Optional[PostFetcher] = None,
        include_mass_notices: bool = False,
    ) -> None:
        self._resolve_oid = resolve_oid
        self._poster = poster or (lambda url, body, headers: http_post_json(url, body, headers, label="KAP"))
        self._include_mass = include_mass_notices

    @property
    def source_id(self) -> str:
        return SOURCE_ID

    @property
    def display_name(self) -> str:
        return "KAP bildirimleri"

    @property
    def scope(self) -> NewsScope:
        return NewsScope.COMPANY

    def _resolve_oids(self, tickers: Sequence[str]) -> List[str]:
        oids: List[str] = []
        for ticker in tickers:
            try:
                oids.append(self._resolve_oid(ticker))
            except Exception as exc:  # kimliği çözülemeyen tek şirket akışı durdurmaz
                logger.warning("KAP kimliği çözülemedi (%s): %s", ticker, exc)
        if not oids:
            raise NewsProviderUnavailable("KAP: şirket kimlikleri çözülemedi")
        return oids

    def _request(self, oids: Sequence[str]) -> List[Dict[str, Any]]:
        today = market_today()
        body = _request_body(oids, today - timedelta(days=LOOKBACK_DAYS), today)
        headers = {"Accept": "application/json", "Referer": _REFERER, "Origin": "https://www.kap.org.tr"}
        try:
            payloads = json.loads(self._poster(KAP_BYCRITERIA_URL, body, headers))
        except (ValueError, TypeError) as exc:
            raise NewsProviderUnavailable(f"KAP: yanıt ayrıştırılamadı ({exc})") from exc
        if not isinstance(payloads, list):
            raise NewsProviderUnavailable("KAP: beklenen bildirim listesi gelmedi")
        return [p for p in payloads if isinstance(p, dict)]

    def _is_wanted(self, payload: Dict[str, Any], tracked: set) -> bool:
        return not _is_noise_sub_document(payload) and (self._include_mass or not _is_mass_notice(payload, tracked))

    def fetch(self, targets: Sequence[NewsTarget]) -> List[NewsItem]:
        tickers = [t.symbol.upper() for t in targets if t.kind is TargetKind.BIST][:MAX_COMPANIES]
        if not tickers:
            return []
        payloads = self._request(self._resolve_oids(tickers))
        tracked = set(tickers)
        wanted = _collapse_financial_reports([p for p in payloads if self._is_wanted(p, tracked)])
        items = [item for item in (_to_news_item(p, tracked) for p in wanted) if item]
        items.sort(key=lambda item: item.published_at, reverse=True)
        return items[:MAX_ITEMS]
