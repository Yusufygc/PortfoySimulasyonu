from __future__ import annotations

import logging
import re
import socket
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from html import unescape
from typing import Any, Callable, Iterable, Sequence

from src.domain.models.corporate_action import ActionType
from src.domain.models.corporate_action_candidate import CandidateDiscoveryData, CorporateActionCandidate
from src.domain.ports.services.i_corporate_action_provider import (
    CorporateActionProviderUnavailable,
    ICorporateActionProvider,
)


logger = logging.getLogger(__name__)

FetchDisclosures = Callable[[Sequence[str], date | None, date | None], Iterable[dict[str, Any]]]


class KapMkkCorporateActionProvider(ICorporateActionProvider):
    """KAP/MKK disclosure normalizer.

    The fetcher is injectable so tests and offline runs do not depend on live KAP access.
    """

    def __init__(self, fetcher: FetchDisclosures | None = None) -> None:
        self._fetcher = fetcher or _fetch_kap_disclosures

    def fetch_candidates(
        self,
        tickers: Sequence[str],
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> list[CorporateActionCandidate]:
        candidates: list[CorporateActionCandidate] = []
        for payload in self._fetcher(tickers, start_date, end_date):
            candidate = parse_kap_mkk_disclosure(payload)
            if candidate is not None and candidate.ticker in {ticker.upper() for ticker in tickers}:
                candidates.append(candidate)
        return candidates


def _resolve_ticker_from_payload(payload: dict[str, Any], text: str) -> str | None:
    ticker = _first_string(payload, "ticker", "stockCode", "stock_code", "code", "symbol")
    if not ticker:
        ticker = _extract_ticker(text)
    return ticker


def _resolve_source_url(payload: dict[str, Any], disclosure_id: str) -> str | None:
    source_url = _first_string(payload, "sourceUrl", "url", "link")
    if not source_url and disclosure_id:
        source_url = f"https://www.kap.org.tr/tr/Bildirim/{disclosure_id}"
    return source_url


def _resolve_ratio(payload: dict[str, Any], text: str, action_type) -> "Decimal | None":
    ratio = _decimal_from_known_keys(payload, "ratio", "rate", "bonusRatio", "paidRatio")
    if ratio is None:
        ratio = _extract_ratio(text, action_type)
    return ratio


def _resolve_subscription_price(payload: dict[str, Any], text: str, action_type) -> "Decimal | None":
    subscription_price = _decimal_from_known_keys(
        payload, "subscriptionPrice", "subscription_price", "rightIssuePrice", "kullanimFiyati"
    )
    if subscription_price is None and action_type == ActionType.BEDELLI:
        subscription_price = _extract_subscription_price(text)
    return subscription_price


def parse_kap_mkk_disclosure(payload: dict[str, Any]) -> CorporateActionCandidate | None:
    text = _payload_text(payload)
    action_type = _detect_action_type(text)
    if action_type is None:
        return None

    ticker = _resolve_ticker_from_payload(payload, text)
    if not ticker:
        return None

    disclosure_id = _first_string(payload, "disclosureId", "id", "bildirimId", "source_disclosure_id")
    if not disclosure_id:
        disclosure_id = f"{ticker}:{_first_string(payload, 'publishDate', 'date') or hash(text)}"

    source_url = _resolve_source_url(payload, str(disclosure_id))
    ratio = _resolve_ratio(payload, text, action_type)
    subscription_price = _resolve_subscription_price(payload, text, action_type)

    ex_date = _date_from_known_keys(payload, "exDate", "ex_date", "rightsUseDate", "hakKullanimTarihi")
    if ex_date is None:
        ex_date = _extract_date(text)

    announcement_date = _date_from_known_keys(payload, "announcementDate", "publishDate", "date")
    confidence = Decimal("0.90") if ratio is not None and ex_date is not None else Decimal("0.55")

    parse_notes = None
    if _is_cancellation_or_update(text):
        parse_notes = "Bildirim iptal/duzeltme/tarih degisikligi ifadesi iceriyor; manuel inceleme gerekir."

    return CorporateActionCandidate.discovered(
        CandidateDiscoveryData(
            ticker=_normalize_ticker(ticker),
            source="KAP_MKK",
            source_disclosure_id=str(disclosure_id),
            source_url=source_url,
            action_type=action_type,
            ratio=ratio,
            ex_date=ex_date,
            subscription_price=subscription_price,
            announcement_date=announcement_date,
            confidence=confidence,
            raw_payload_json=payload,
            parse_notes=parse_notes,
        )
    )


def _fetch_kap_disclosures(
    tickers: Sequence[str],
    start_date: date | None,
    end_date: date | None,
) -> Iterable[dict[str, Any]]:
    """Best-effort public KAP query.

    KAP's authenticated data publication service requires a separate contract.
    This public fallback reads list/detail pages and degrades cleanly when the
    public site is unavailable or does not expose results in static HTML.
    """

    end_date = end_date or date.today()
    start_date = start_date or (end_date - timedelta(days=45))
    target_tickers = {_normalize_ticker(ticker) for ticker in tickers}
    listing_urls = [
        "https://www.kap.org.tr/tr",
        "https://www.kap.org.tr/tr/bildirim-sorgu",
    ]

    payloads: list[dict[str, Any]] = []
    errors: list[str] = []
    for url in listing_urls:
        try:
            html = _fetch_url_text(url)
        except CorporateActionProviderUnavailable as exc:
            errors.append(str(exc))
            continue
        payloads.extend(_payloads_from_listing_html(html, target_tickers, start_date, end_date))

    if payloads or not errors:
        return _dedupe_payloads(payloads)
    raise CorporateActionProviderUnavailable("; ".join(errors))


def _fetch_url_text(url: str, timeout: int = 15) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "PortfoySim/1.0"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8", errors="replace")
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, socket.timeout, OSError) as exc:
        raise CorporateActionProviderUnavailable(f"KAP public source unavailable: {url} ({exc})") from exc


def _payloads_from_listing_html(
    html: str,
    target_tickers: set[str],
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    payloads: list[dict[str, Any]] = []
    for disclosure_id, source_url, context in _extract_disclosure_links(html):
        context_text = _html_to_text(context)
        if not _context_matches_targets(context_text, target_tickers):
            continue
        if _extract_date(context_text) is not None:
            point_date = _extract_date(context_text)
            if point_date is not None and not (start_date <= point_date <= end_date):
                continue
        detail_payload = _fetch_detail_payload(disclosure_id, source_url, context_text, target_tickers)
        if detail_payload is not None:
            payloads.append(detail_payload)
    return payloads


def _extract_disclosure_links(html: str) -> list[tuple[str, str, str]]:
    decoded = unescape(html)
    pattern = re.compile(r"(?:https://(?:www\.)?kap\.org\.tr)?/(?:tr|en)/Bildirim/(\d+)")
    links: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for match in pattern.finditer(decoded):
        disclosure_id = match.group(1)
        if disclosure_id in seen:
            continue
        seen.add(disclosure_id)
        source_url = f"https://www.kap.org.tr/tr/Bildirim/{disclosure_id}"
        start = max(0, match.start() - 800)
        end = min(len(decoded), match.end() + 1600)
        links.append((disclosure_id, source_url, decoded[start:end]))
    return links


def _context_matches_targets(text: str, target_tickers: set[str]) -> bool:
    normalized_text = text.upper()
    if not any(ticker.replace(".IS", "") in normalized_text or ticker in normalized_text for ticker in target_tickers):
        return False
    lower = _ascii_lower(text)
    return any(token in lower for token in ("bedelsiz", "bedelli", "sermaye art", "bonus issue", "rights issue"))


def _fetch_detail_payload(
    disclosure_id: str,
    source_url: str,
    context_text: str,
    target_tickers: set[str],
) -> dict[str, Any] | None:
    detail_urls = [
        f"https://www.kap.org.tr/tr/api/BildirimPdf/{disclosure_id}",
        source_url,
    ]
    detail_text = context_text
    for detail_url in detail_urls:
        try:
            detail_text = _html_to_text(_fetch_url_text(detail_url))
            break
        except CorporateActionProviderUnavailable:
            continue
    if not detail_text:
        return None
    return {
        "id": disclosure_id,
        "ticker": _ticker_from_targets(f"{context_text} {detail_text}", target_tickers),
        "sourceUrl": source_url,
        "title": _first_line(detail_text),
        "summary": detail_text,
    }


def _ticker_from_targets(text: str, target_tickers: set[str]) -> str | None:
    normalized_text = text.upper()
    for ticker in sorted(target_tickers):
        base = ticker.replace(".IS", "")
        if ticker in normalized_text or base in normalized_text:
            return ticker
    return None


def _dedupe_payloads(payloads: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for payload in payloads:
        disclosure_id = str(payload.get("id") or payload.get("disclosureId") or "")
        if disclosure_id and disclosure_id in seen:
            continue
        if disclosure_id:
            seen.add(disclosure_id)
        result.append(payload)
    return result


def _html_to_text(html: str) -> str:
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _first_line(text: str) -> str:
    return text.strip().splitlines()[0][:200] if text.strip() else ""


def _payload_text(payload: dict[str, Any]) -> str:
    parts = []
    for key, value in payload.items():
        if isinstance(value, (str, int, float)):
            parts.append(f"{key}: {value}")
        elif isinstance(value, list):
            parts.append(" ".join(str(item) for item in value if isinstance(item, (str, int, float))))
        elif isinstance(value, dict):
            parts.append(_payload_text(value))
    return " ".join(parts)


def _detect_action_type(text: str) -> ActionType | None:
    lower = _ascii_lower(text)
    if "bedelsiz" in lower or "bonus issue" in lower:
        return ActionType.BEDELSIZ
    if "bedelli" in lower or "rights issue" in lower or "ruchan" in lower:
        return ActionType.BEDELLI
    return None


def _extract_ticker(text: str) -> str | None:
    match = re.search(r"\b([A-Z]{3,6})(?:\.IS)?\b", text.upper())
    return match.group(1) if match else None


def _normalize_ticker(ticker: str) -> str:
    ticker = ticker.strip().upper()
    return ticker if ticker.endswith(".IS") else f"{ticker}.IS"


def _extract_ratio(text: str, action_type: ActionType) -> Decimal | None:
    labels = ["bedelsiz", "bonus"] if action_type == ActionType.BEDELSIZ else ["bedelli", "rights"]
    for label in labels:
        match = re.search(rf"{label}.{{0,80}}?%?\s*([0-9]+(?:[.,][0-9]+)?)", _ascii_lower(text))
        if match:
            return _percent_to_ratio(match.group(1))
    match = re.search(r"%\s*([0-9]+(?:[.,][0-9]+)?)", text)
    return _percent_to_ratio(match.group(1)) if match else None


def _extract_subscription_price(text: str) -> Decimal | None:
    lower = _ascii_lower(text)
    patterns = [
        r"kullanim\s+fiyati.{0,40}?([0-9]+(?:[.,][0-9]+)?)",
        r"ruchan.{0,40}?fiyat.{0,40}?([0-9]+(?:[.,][0-9]+)?)",
        r"subscription.{0,40}?price.{0,40}?([0-9]+(?:[.,][0-9]+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, lower)
        if match:
            return _decimal(match.group(1))
    return None


def _extract_date(text: str) -> date | None:
    match = re.search(r"\b([0-3]?\d[./-][01]?\d[./-]20\d{2})\b", text)
    if not match:
        match = re.search(r"\b(20\d{2}-[01]?\d-[0-3]?\d)\b", text)
    return _parse_date(match.group(1)) if match else None


def _date_from_known_keys(payload: dict[str, Any], *keys: str) -> date | None:
    for key in keys:
        value = _deep_get(payload, key)
        if value is not None:
            parsed = _parse_date(str(value))
            if parsed is not None:
                return parsed
    return None


def _decimal_from_known_keys(payload: dict[str, Any], *keys: str) -> Decimal | None:
    for key in keys:
        value = _deep_get(payload, key)
        parsed = _decimal(str(value)) if value is not None else None
        if parsed is not None:
            if parsed > Decimal("1"):
                return parsed / Decimal("100")
            return parsed
    return None


def _first_string(payload: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _deep_get(payload, key)
        if value not in (None, ""):
            return str(value)
    return None


def _deep_get(payload: dict[str, Any], key: str) -> Any:
    if key in payload:
        return payload[key]
    for value in payload.values():
        if isinstance(value, dict):
            found = _deep_get(value, key)
            if found is not None:
                return found
    return None


def _percent_to_ratio(value: str) -> Decimal | None:
    parsed = _decimal(value)
    return parsed / Decimal("100") if parsed is not None else None


def _decimal(value: str) -> Decimal | None:
    normalized = value.strip().replace("%", "")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except (InvalidOperation, ValueError):
        return None


def _parse_date(value: str) -> date | None:
    value = value.strip()[:10]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _is_cancellation_or_update(text: str) -> bool:
    lower = _ascii_lower(text)
    return any(token in lower for token in ("iptal", "duzeltme", "tarih degisikligi", "cancel"))


def _ascii_lower(text: str) -> str:
    return (
        text.lower()
        .replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )
