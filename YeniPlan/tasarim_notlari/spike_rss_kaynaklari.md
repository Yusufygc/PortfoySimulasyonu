# Spike: Türkçe ve global RSS kaynakları

> Ana sayfa: [../index.md](../index.md) | Günlük: [../log.md](../log.md) | Not dizini: [README.md](README.md)

Durum: **Tamamlandı** (2026-11-01). Sonuç: yeterli sayıda çalışan genel besleme var; tümü `lxml` ile ayrıştırılıyor, yeni paket gerekmiyor.

## 1. Yöntem

[scripts/probe_news_sources.py](../../scripts/probe_news_sources.py) (`rss` ve `symbol` bölümleri): her adrese tarayıcı `User-Agent` ile GET, 20 sn zaman aşımı; `lxml.etree` (recover, varlık çözümleme kapalı) ile `item`/`entry` sayımı ve ilk öğenin başlık/tarihi. Doğrulama tarihi: 2026-11-01. Adreslerin tümü bu yoklamada doğrulandı; uydurulmuş adres yoktur.

## 2. Türkçe ekonomi / piyasa

| Kaynak | Adres | Öğe | En yeni | Not |
|---|---|---|---|---|
| AA Ekonomi | `https://www.aa.com.tr/tr/rss/default?cat=ekonomi` | 30 | gün içi | Ajans haberi, temiz |
| BloombergHT | `https://www.bloomberght.com/rss` | 50 | gün içi | Genel akış (yalnızca ekonomi değil); piyasa odaklı |
| NTV Ekonomi | `https://www.ntv.com.tr/ekonomi.rss` | 20 | 4 gün önce | Seyrek güncelleniyor |
| Habertürk Ekonomi | `https://www.haberturk.com/rss/ekonomi.xml` | 30 | gün içi | |
| CNN Türk Ekonomi | `https://www.cnnturk.com/feed/rss/ekonomi/news` | 35 | gün içi | Yaşam/loto haberleri karışıyor |
| TRT Haber Ekonomi | `https://www.trthaber.com/ekonomi_articles.rss` | 60 | gün içi | |
| Sabah Ekonomi | `https://www.sabah.com.tr/rss/ekonomi.xml` | 10 | gün içi | |
| Milliyet Ekonomi | `https://www.milliyet.com.tr/rss/rssnew/ekonomi.xml` | 50 | gün içi | Büyük içerik (313 KB) |
| Hürriyet Ekonomi | `https://www.hurriyet.com.tr/rss/ekonomi` | 100 | karışık sıra | 768 KB; ilk öğe eski (Haziran), sıralama tarihe göre yapılmalı |
| Ekonomim | `https://www.ekonomim.com/rss` | 25 | gün içi | Genel akış |
| Dünya | `https://www.dunya.com/rss?dunya` | 25 | gün içi | Genel akış |
| Investing TR | `https://tr.investing.com/rss/news.rss` | 10 | gün içi | Küçük, piyasa odaklı |
| Investing TR Hisse | `https://tr.investing.com/rss/news_25.rss` | 10 | gün içi | Hisse haberleri |
| Fortune Türkiye | `https://fortuneturkey.com/feed` | 10 | 2 gün önce | |
| BBC Türkçe | `https://feeds.bbci.co.uk/turkce/rss.xml` | 16 | gün içi | Genel haber |

**Çalışmayanlar:** `dunya.com/rss/finans` (404), `paraanaliz.com/feed/` (404), `borsagundem.com/rss` (bağlantı sıfırlandı), `finance.yahoo.com/news/rssindex` (404), `kap.org.tr/tr/rss/bildirim` (404).

## 3. Global

| Kaynak | Adres | Öğe | Not |
|---|---|---|---|
| BBC Business | `https://feeds.bbci.co.uk/news/business/rss.xml` | 52 | |
| CNBC Top News | `https://www.cnbc.com/id/100003114/device/rss/rss.html` | 30 | |
| MarketWatch | `https://feeds.content.dowjones.io/public/rss/mw_topstories` | 10 | |
| Investing (EN) | `https://www.investing.com/rss/news.rss` | 10 | Genel haber |
| CoinDesk | `https://www.coindesk.com/arc/outboundfeeds/rss/` | 25 | Kripto |
| Cointelegraph | `https://cointelegraph.com/rss` | 30 | Kripto |

`CNBC Finance` (`.../id/10000664/...`) çalışıyor ama en yeni öğe 10 gün eski; önerilmez.

## 4. Gözlemler

- Tarih biçimleri karışık: RFC 822 (`Sun, 01 Nov 2026 18:09:47 +0300`, `... GMT`, `... Z`), ISO 8601 (`2026-10-28T18:49:41+03:00`) ve saat dilimsiz yerel (`2026-11-01 11:36:02`, Investing). Ayrıştırıcı hepsini UTC'ye normalize etmeli; saat dilimsiz değerler kaynağa göre İstanbul/UTC varsayılmalı (Investing TR için İstanbul olduğu varsayılıyor, doğrulanmadı).
- Bazı beslemeler genel haber akışıdır (BloombergHT, Dünya, Ekonomim, CNN Türk); piyasa dışı içerik (spor, loto) karışır. Çözüm: haber paneli için **anahtar sözcük süzgeci** (portföy sembolleri, şirket adları, "borsa", "dolar", "altın", "bitcoin" vb.) veya yalnızca ekonomi kategori beslemeleri.
- Boyut: Hürriyet (768 KB) ve Milliyet (313 KB) beslemeleri büyük; yalnızca ilk N öğe işlenmeli ve önbellek zorunlu.
- İçerik yalnızca başlık + kısa özet + bağlantı olarak kullanılacak; tam metin kopyalanmaz.

## 5. Varsayılan Liste Önerisi

| Panel | Varsayılan kaynaklar |
|---|---|
| Piyasa ve Global (Türkçe) | AA Ekonomi, BloombergHT, Habertürk Ekonomi, TRT Haber Ekonomi, Investing TR |
| Piyasa ve Global (İngilizce) | CNBC Top News, BBC Business |
| Kripto | CoinDesk, Cointelegraph (kripto varlığı varsa) |
| Şirket / varlık | KAP (BIST), Google News (arama), Yahoo sembol RSS (ABD/kripto/emtia) |

Kullanıcı Ayarlar'dan her kaynağı kapatabilir ve özel RSS adresi ekleyebilir ([../06_ayarlar_haber_kaynaklari.md](../06_ayarlar_haber_kaynaklari.md)).
