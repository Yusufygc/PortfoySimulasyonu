"""Haber sağlayıcıları: kayıtlı örnek yanıtlarla ayrıştırma ve süzgeçler (ağ yok)."""
from __future__ import annotations

import json
from datetime import timezone

import pytest

from src.domain.models.news_item import NewsTarget, TargetKind
from src.domain.ports.services.i_news_provider import NewsProviderUnavailable
from src.infrastructure.news.feed_parser import clean_text, parse_feed, parse_feed_datetime
from src.infrastructure.news.kap_news_provider import KapDisclosureNewsProvider
from src.infrastructure.news.rss_providers import GoogleNewsRssProvider, RssNewsProvider, YahooRssNewsProvider

RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>Test</title>
<item><title>Dolar rekor kırdı</title><link>https://ex.com/a</link>
<pubDate>Sat, 01 Nov 2026 09:30:00 +0300</pubDate>
<description><![CDATA[<p>Kısa &amp; özet</p>]]></description></item>
<item><title>Tarihsiz haber</title><link>https://ex.com/b</link></item>
<item><title>Altın yükseldi</title><link>https://ex.com/c</link><pubDate>2026-11-01T08:00:00Z</pubDate></item>
</channel></rss>""".encode("utf-8")

ATOM = """<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom haber</title>
<link href="https://ex.com/atom"/><updated>2026-11-01T10:00:00+03:00</updated><summary>özet</summary></entry></feed>
""".encode("utf-8")


class TestFeedParser:
    def test_rss_items_normalized_to_utc(self):
        items = parse_feed(RSS, source_id="rss:x", source_name="Test", language="tr")
        assert [i.title for i in items] == ["Dolar rekor kırdı", "Altın yükseldi"]  # tarihsiz atlanır
        assert items[0].published_at.tzinfo == timezone.utc
        assert items[0].published_at.hour == 6  # +03:00 -> UTC
        assert items[0].summary == "Kısa & özet"

    def test_atom_entry_uses_href(self):
        items = parse_feed(ATOM, source_id="a", source_name="Atom")
        assert items[0].url == "https://ex.com/atom"

    def test_empty_or_broken_feed_raises(self):
        with pytest.raises(NewsProviderUnavailable):
            parse_feed(b"<html><body>404</body></html>", source_id="a", source_name="A")
        with pytest.raises(NewsProviderUnavailable):
            parse_feed(b"not xml at all", source_id="a", source_name="A")

    def test_item_limit(self):
        many = "<rss><channel>" + "".join(
            f"<item><title>t{i}</title><link>https://e/{i}</link><pubDate>2026-11-01T08:00:00Z</pubDate></item>"
            for i in range(10)
        ) + "</channel></rss>"
        assert len(parse_feed(many.encode(), source_id="a", source_name="A", limit=3)) == 3

    def test_datetime_formats(self):
        assert parse_feed_datetime("Sat, 01 Nov 2026 09:30:00 GMT").hour == 9
        assert parse_feed_datetime("2026-11-01T09:30:00").tzinfo == timezone.utc  # saat dilimsiz UTC kabul edilir
        assert parse_feed_datetime("geçersiz") is None
        assert parse_feed_datetime(None) is None

    def test_clean_text_strips_markup_and_truncates(self):
        assert clean_text("<b>a</b>   b") == "a b"
        assert len(clean_text("x" * 500)) == 280


class TestRssProviders:
    def test_generic_rss_ignores_targets(self):
        provider = RssNewsProvider("rss:x", "Test", "https://ex.com/feed", fetcher=lambda url: RSS)
        assert len(provider.fetch([])) == 2

    def test_fetch_error_propagates(self):
        def boom(url):
            raise NewsProviderUnavailable("HTTP 404")

        with pytest.raises(NewsProviderUnavailable):
            RssNewsProvider("rss:x", "Test", "https://ex.com/feed", fetcher=boom).fetch([])

    def test_yahoo_only_queries_non_bist_targets_with_symbol_url(self):
        urls = []
        provider = YahooRssNewsProvider("yahoo_rss", "Yahoo", fetcher=lambda url: urls.append(url) or RSS)
        targets = [
            NewsTarget("THYAO", "Türk Hava Yolları", TargetKind.BIST),
            NewsTarget("GC=F", "Altın", TargetKind.METAL),
            NewsTarget("AAPL", "Apple", TargetKind.US_STOCK),
        ]
        items = provider.fetch(targets)
        assert len(urls) == 2 and "s=GC=F" in urls[0] and "s=AAPL" in urls[1]
        assert {i.related_symbols for i in items} == {("GC=F",), ("AAPL",)}
        assert all(i.language == "en" for i in items)

    def test_google_news_uses_ticker_for_bist_and_name_otherwise(self):
        urls = []
        provider = GoogleNewsRssProvider("google_news", "Google", fetcher=lambda url: urls.append(url) or RSS)
        provider.fetch([
            NewsTarget("THYAO", "Türk Hava Yolları", TargetKind.BIST),
            NewsTarget("BTC-USD", "Bitcoin", TargetKind.CRYPTO),
        ])
        assert "q=THYAO&" in urls[0]
        assert "q=Bitcoin&" in urls[1]

    def test_partial_target_failure_keeps_other_results(self):
        def flaky(url):
            if "AAPL" in url:
                raise NewsProviderUnavailable("HTTP 404")
            return RSS

        provider = YahooRssNewsProvider("yahoo_rss", "Yahoo", fetcher=flaky)
        items = provider.fetch([
            NewsTarget("AAPL", "Apple", TargetKind.US_STOCK),
            NewsTarget("BTC-USD", "Bitcoin", TargetKind.CRYPTO),
        ])
        assert items and all(i.related_symbols == ("BTC-USD",) for i in items)

    def test_all_targets_failing_raises(self):
        def boom(url):
            raise NewsProviderUnavailable("HTTP 404")

        provider = YahooRssNewsProvider("yahoo_rss", "Yahoo", fetcher=boom)
        with pytest.raises(NewsProviderUnavailable):
            provider.fetch([NewsTarget("AAPL", "Apple", TargetKind.US_STOCK)])


def _kap_payload(**overrides):
    base = {
        "publishDate": "01.11.2026 09:30:00", "stockCodes": "THYAO", "relatedStocks": "", "kapTitle": "TÜRK HAVA YOLLARI",
        "subject": "Özel Durum Açıklaması (Genel)", "summary": "Yeni uçak siparişi", "disclosureClass": "ODA",
        "disclosureIndex": 1500000,
    }
    base.update(overrides)
    return base


class TestKapProvider:
    TARGETS = [NewsTarget("THYAO", "THY", TargetKind.BIST), NewsTarget("AAPL", "Apple", TargetKind.US_STOCK)]

    def _provider(self, payloads, **kwargs):
        calls = []

        def poster(url, body, headers):
            calls.append((url, body, headers))
            return json.dumps(payloads).encode("utf-8")

        return KapDisclosureNewsProvider(lambda ticker: f"oid-{ticker}", poster=poster, **kwargs), calls

    def test_request_uses_iso_dates_oids_and_referer(self):
        provider, calls = self._provider([_kap_payload()])
        provider.fetch(self.TARGETS)
        _, body, headers = calls[0]
        assert body["mkkMemberOidList"] == ["oid-THYAO"]  # yalnızca BIST hedefleri
        assert len(body["fromDate"]) == 10 and body["fromDate"][4] == "-"
        assert headers["Referer"].endswith("bildirim-sorgu")

    def test_item_fields_and_istanbul_time_to_utc(self):
        provider, _ = self._provider([_kap_payload()])
        item = provider.fetch(self.TARGETS)[0]
        assert item.url == "https://www.kap.org.tr/tr/Bildirim/1500000"
        assert item.published_at.hour == 6  # 09:30 İstanbul -> 06:30 UTC
        assert item.related_symbols == ("THYAO",)
        assert item.source_id == "kap" and item.badge == "ODA" and item.language == "tr"

    def test_mass_notices_hidden_by_default_and_shown_on_request(self):
        mass = _kap_payload(stockCodes="", relatedStocks=",".join(f"S{i}" for i in range(106)), disclosureIndex=2)
        own = _kap_payload()
        hidden, _ = self._provider([mass, own])
        assert len(hidden.fetch(self.TARGETS)) == 1
        shown, _ = self._provider([mass, own], include_mass_notices=True)
        assert len(shown.fetch(self.TARGETS)) == 2

    def test_small_related_notice_is_kept(self):
        related = _kap_payload(stockCodes="", relatedStocks="THYAO, PGSUS", disclosureIndex=3)
        provider, _ = self._provider([related])
        assert provider.fetch(self.TARGETS)[0].related_symbols == ("THYAO",)

    def test_financial_report_sub_documents_collapsed(self):
        fr = {"disclosureClass": "FR", "publishDate": "01.11.2026 18:00:00"}
        payloads = [
            _kap_payload(subject="Faaliyet Raporu", disclosureIndex=11, **fr),
            _kap_payload(subject="Finansal Rapor", disclosureIndex=12, **fr),
            _kap_payload(subject="Sorumluluk Beyanı (Finansal Tablo)", disclosureIndex=13, **fr),
        ]
        provider, _ = self._provider(payloads)
        items = provider.fetch(self.TARGETS)
        assert [i.title for i in items] == ["Finansal Rapor"]

    def test_sorted_newest_first(self):
        old = _kap_payload(publishDate="30.10.2026 10:00:00", disclosureIndex=21)
        new = _kap_payload(publishDate="01.11.2026 10:00:00", disclosureIndex=22)
        provider, _ = self._provider([old, new])
        assert [i.url[-2:] for i in provider.fetch(self.TARGETS)] == ["22", "21"]

    def test_no_bist_targets_returns_empty_without_request(self):
        provider, calls = self._provider([_kap_payload()])
        assert provider.fetch([NewsTarget("AAPL", "Apple", TargetKind.US_STOCK)]) == []
        assert calls == []

    def test_unresolvable_company_does_not_stop_others_but_all_failing_raises(self):
        def resolve(ticker):
            if ticker == "BAD":
                raise KeyError(ticker)
            return f"oid-{ticker}"

        calls = []
        provider = KapDisclosureNewsProvider(
            resolve, poster=lambda u, b, h: calls.append(b) or json.dumps([_kap_payload()]).encode()
        )
        provider.fetch([NewsTarget("BAD", "x", TargetKind.BIST), NewsTarget("THYAO", "THY", TargetKind.BIST)])
        assert calls[0]["mkkMemberOidList"] == ["oid-THYAO"]
        with pytest.raises(NewsProviderUnavailable):
            provider.fetch([NewsTarget("BAD", "x", TargetKind.BIST)])

    def test_bad_response_raises(self):
        provider = KapDisclosureNewsProvider(lambda t: "oid", poster=lambda u, b, h: b"<html>500</html>")
        with pytest.raises(NewsProviderUnavailable):
            provider.fetch(self.TARGETS)
        provider = KapDisclosureNewsProvider(lambda t: "oid", poster=lambda u, b, h: b'{"error": 1}')
        with pytest.raises(NewsProviderUnavailable):
            provider.fetch(self.TARGETS)
