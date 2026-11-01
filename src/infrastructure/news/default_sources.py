"""İlk çalıştırmada eklenen haber kaynakları (doğrulanmış adresler: YeniPlan spike notları, 2026-11-01)."""
from __future__ import annotations

from typing import List

from src.domain.models.news_item import NewsScope, NewsSourceConfig, NewsSourceKind


def _rss(source_id: str, name: str, url: str, **options):
    """`options`: `language` (varsayılan tr), `enabled` (varsayılan True), `description`."""
    return NewsSourceConfig(
        source_id=f"rss:{source_id}", kind=NewsSourceKind.RSS, name=name, url=url, scope=NewsScope.MARKET, **options
    )


def default_news_sources() -> List[NewsSourceConfig]:
    return [
        NewsSourceConfig("kap", NewsSourceKind.KAP, "KAP bildirimleri", True, "tr", NewsScope.COMPANY,
                         description="BIST şirketlerinin resmî bildirimleri"),
        NewsSourceConfig("yahoo_rss", NewsSourceKind.YAHOO_RSS, "Yahoo Finance", True, "en", NewsScope.COMPANY,
                         description="ABD hissesi, kripto ve emtia haberleri"),
        NewsSourceConfig("google_news", NewsSourceKind.GOOGLE_NEWS, "Google Haberler", True, "tr", NewsScope.COMPANY,
                         description="Şirket ve varlık adına göre Türkçe haber araması"),
        _rss("aa_ekonomi", "AA Ekonomi", "https://www.aa.com.tr/tr/rss/default?cat=ekonomi"),
        _rss("bloomberght", "BloombergHT", "https://www.bloomberght.com/rss"),
        _rss("haberturk_ekonomi", "Habertürk Ekonomi", "https://www.haberturk.com/rss/ekonomi.xml"),
        _rss("trt_ekonomi", "TRT Haber Ekonomi", "https://www.trthaber.com/ekonomi_articles.rss"),
        _rss("investing_tr", "Investing Türkiye", "https://tr.investing.com/rss/news.rss"),
        _rss("cnbc_top", "CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", language="en"),
        _rss("bbc_business", "BBC Business", "https://feeds.bbci.co.uk/news/business/rss.xml", language="en"),
        _rss("coindesk", "CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/", language="en", enabled=False,
             description="Kripto haberleri"),
        _rss("cointelegraph", "Cointelegraph", "https://cointelegraph.com/rss", language="en", enabled=False,
             description="Kripto haberleri"),
    ]
