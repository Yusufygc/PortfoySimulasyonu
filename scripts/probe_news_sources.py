"""Haber kaynaklarının canlı yoklaması (salt okunur HTTP GET/POST; veritabanına yazmaz).

Haber akışı tasarımının dayandığı kaynakların hâlâ çalışıp çalışmadığını doğrular: KAP şirket bazlı bildirim uç noktası,
Türkçe/global RSS adayları, Yahoo ve Google News sembol bazlı RSS. Kaynaklar zamanla değişir; haber sağlayıcıları
yazılırken veya bir kaynak bozulduğunda yeniden çalıştırın. Bulgular: YeniPlan/tasarim_notlari/spike_*.md.

Kullanım (depo kökünden):

    .\\venv\\Scripts\\python.exe scripts\\probe_news_sources.py            # hepsi
    .\\venv\\Scripts\\python.exe scripts\\probe_news_sources.py kap rss    # seçili bölümler (kap, rss, symbol)
"""
from __future__ import annotations

import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.stdout.reconfigure(encoding="utf-8")

import requests
from lxml import etree

UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
    "Accept-Language": "tr-TR,tr;q=0.9",
}
TIMEOUT = 20

RSS_CANDIDATES = {
    "AA Ekonomi": "https://www.aa.com.tr/tr/rss/default?cat=ekonomi",
    "BloombergHT": "https://www.bloomberght.com/rss",
    "NTV Ekonomi": "https://www.ntv.com.tr/ekonomi.rss",
    "Dünya": "https://www.dunya.com/rss?dunya",
    "Hürriyet Ekonomi": "https://www.hurriyet.com.tr/rss/ekonomi",
    "Habertürk Ekonomi": "https://www.haberturk.com/rss/ekonomi.xml",
    "CNN Türk Ekonomi": "https://www.cnnturk.com/feed/rss/ekonomi/news",
    "TRT Haber Ekonomi": "https://www.trthaber.com/ekonomi_articles.rss",
    "Sabah Ekonomi": "https://www.sabah.com.tr/rss/ekonomi.xml",
    "Milliyet Ekonomi": "https://www.milliyet.com.tr/rss/rssnew/ekonomi.xml",
    "Investing TR": "https://tr.investing.com/rss/news.rss",
    "Investing TR Hisse": "https://tr.investing.com/rss/news_25.rss",
    "BBC Türkçe": "https://feeds.bbci.co.uk/turkce/rss.xml",
    "Ekonomim": "https://www.ekonomim.com/rss",
    "Fortune TR": "https://fortuneturkey.com/feed",
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "CNBC Top": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "MarketWatch": "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "Investing EN": "https://www.investing.com/rss/news.rss",
    "Coindesk": "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "Cointelegraph": "https://cointelegraph.com/rss",
}

SYMBOL_FEEDS = {
    "Yahoo RSS AAPL": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL&region=US&lang=en-US",
    "Yahoo RSS THYAO.IS": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=THYAO.IS&region=TR&lang=tr-TR",
    "Yahoo RSS BTC-USD": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=BTC-USD&region=US&lang=en-US",
    "Yahoo RSS GC=F": "https://feeds.finance.yahoo.com/rss/2.0/headline?s=GC=F&region=US&lang=en-US",
    "Google News THYAO": "https://news.google.com/rss/search?q=THYAO&hl=tr&gl=TR&ceid=TR:tr",
    "Google News altın": "https://news.google.com/rss/search?q=gram+alt%C4%B1n&hl=tr&gl=TR&ceid=TR:tr",
    "Google News bitcoin": "https://news.google.com/rss/search?q=bitcoin&hl=tr&gl=TR&ceid=TR:tr",
}

KAP_URL = "https://www.kap.org.tr/tr/api/disclosure/members/byCriteria"


def _first_entry_fields(entries):
    """İlk öğenin (başlık, tarih) metni; yoksa boş."""
    title = date_text = ""
    for child in (entries[0] if entries else []):
        tag = etree.QName(child).localname
        if tag == "title" and not title:
            title = (child.text or "").strip()
        if tag in ("pubDate", "published", "updated", "date") and not date_text:
            date_text = (child.text or "").strip()
    return title, date_text


def probe_feed(item):
    name, url = item
    try:
        response = requests.get(url, headers=UA, timeout=TIMEOUT)
    except Exception as exc:  # noqa: BLE001 - yoklama betiği: hata metni raporlanır
        return name, f"HATA {type(exc).__name__}"
    info = f"{response.status_code} {len(response.content)}B"
    if response.status_code != 200:
        return name, info
    root = etree.fromstring(response.content, parser=etree.XMLParser(recover=True, resolve_entities=False))
    entries = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
    title, date_text = _first_entry_fields(entries)
    return name, f"{info} | {len(entries)} öğe | {date_text[:31]} | {title[:60]}"


def run_feeds(title, feeds):
    print(f"\n== {title}")
    with ThreadPoolExecutor(max_workers=8) as pool:
        for name, info in pool.map(probe_feed, feeds.items()):
            print(f"{name:22} {info}")


def run_kap():
    from src.infrastructure.corporate_actions.kap_shareholder_provider import KapShareholderProvider

    print("\n== KAP şirket bazlı bildirimler (POST members/byCriteria)")
    provider = KapShareholderProvider()
    tickers = ("THYAO", "AKBNK", "ASELS")
    oids = {}
    for ticker in tickers:
        try:
            oids[ticker] = provider.resolve_member_oid(ticker)[0]
        except Exception as exc:  # noqa: BLE001
            print(f"  {ticker}: KAP kimliği çözülemedi ({exc})")
    if not oids:
        return
    today = date.today()
    body = {
        "fromDate": (today - timedelta(days=14)).isoformat(), "toDate": today.isoformat(), "memberType": "IGS",
        "mkkMemberOidList": list(oids.values()), "inactiveMkkMemberOidList": [], "disclosureClass": "",
        "subjectList": [], "isLate": "", "mainSector": "", "sector": "", "subSector": "", "marketOidList": [],
        "index": "", "bdkReview": "", "bdkMemberOidList": [], "year": "", "term": "", "ruleType": "", "period": "",
        "fromSrc": False, "srcCategory": "", "disclosureIndexList": [],
    }
    headers = {**UA, "Accept": "application/json", "Referer": "https://www.kap.org.tr/tr/bildirim-sorgu",
               "Origin": "https://www.kap.org.tr"}
    started = time.time()
    response = requests.post(KAP_URL, json=body, headers=headers, timeout=TIMEOUT)
    elapsed = time.time() - started
    print(f"  durum {response.status_code}, {elapsed:.2f} sn, {len(response.content)} B")
    if response.status_code != 200:
        print("  ", response.text[:200])
        return
    items = response.json()
    own = [i for i in items if i.get("stockCodes")]
    print(f"  {len(items)} bildirim; kendi bildirimi {len(own)}, ortak/kurum bildirimi {len(items) - len(own)}")
    print("  sınıflar:", dict(Counter(i.get("disclosureClass") for i in items)))
    for item in own[:5]:
        print("   ", item["publishDate"], "|", item["stockCodes"], "|", (item.get("subject") or "")[:55],
              "| https://www.kap.org.tr/tr/Bildirim/" + str(item["disclosureIndex"]))


def main(argv: list[str]) -> int:
    sections = set(argv) or {"kap", "rss", "symbol"}
    if "rss" in sections:
        run_feeds("Genel RSS adayları", RSS_CANDIDATES)
    if "symbol" in sections:
        run_feeds("Sembol / konu bazlı RSS", SYMBOL_FEEDS)
    if "kap" in sections:
        run_kap()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
