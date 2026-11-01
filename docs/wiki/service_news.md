> Ana sayfa: [index.md](index.md) | Sayfalar: [qml_pages_guide.md](qml_pages_guide.md) | Ayarlar: [settings_and_system.md](settings_and_system.md) | Dış kaynaklar: [service_market_data_providers.md](service_market_data_providers.md)

# Haber Akışı

Genel Bakış sayfasındaki haber paneli ve Ayarlar > Haber Kaynakları. Şirket/varlık haberleri (KAP, Yahoo, Google News) ve sembolsüz piyasa/global haberleri (RSS) tek serviste birleşir. Yalnızca başlık, kısa özet ve bağlantı saklanır ve gösterilir; haber tam metni kopyalanmaz.

## 1. Mimari

| Katman | Dosya |
|---|---|
| Domain | `src/domain/models/news_item.py`: `NewsItem`, `NewsTarget`/`TargetKind` (BIST, ABD hissesi, kripto, metal), `NewsSourceConfig` (+ `options`), `NewsSourceStatus`, `NewsFeedResult`, `NewsScope` (COMPANY / MARKET), `NewsSourceKind` |
| Port | `ports/services/i_news_provider.py` (`INewsProvider`, `NewsProviderUnavailable`), `ports/repositories/i_news_source_repo.py` (`INewsSourceRepository`, `INewsCache`) |
| Altyapı | `src/infrastructure/news/`: `_http.py`, `feed_parser.py`, `rss_providers.py` (`RssNewsProvider`, `YahooRssNewsProvider`, `GoogleNewsRssProvider`), `kap_news_provider.py`, `news_file_cache.py`, `default_sources.py`, `provider_factory.py`; `sa_news_source_repository.py` |
| Uygulama | `src/application/services/news/news_service.py` (`NewsService`), `news_target_service.py` (`NewsTargetService`) |
| UI | `controllers/news_controller.py`, `news_settings_controller.py`; `models/news_list_model.py`; `qml/components/NewsPanel.qml`, `SettingsNewsTab.qml` |

Sağlayıcı sözleşmesi: `fetch(targets)`; COMPANY kaynaklar hedef sembollere göre, MARKET kaynaklar hedeften bağımsız çalışır. Hata durumunda `NewsProviderUnavailable` fırlatılır, **sessizce boş liste dönülmez** (yfinance'in sessiz boş dönüşü yüzünden). `_http.py` HTTP durumunu açıkça denetler (4xx/5xx, boş gövde, ağ hatası -> `NewsProviderUnavailable`), geçici hatalarda `retry_call` kullanır. Gerçek ağ çağrısı testlerde yapılmaz; sağlayıcılara `fetcher`/`poster` enjekte edilir.

## 2. Kaynaklar

| Kaynak kimliği | Tür | Kapsam | Varsayılan |
|---|---|---|---|
| `kap` | KAP bildirimleri | BIST şirketleri (Türkçe) | açık |
| `yahoo_rss` | Yahoo sembol RSS | ABD hissesi, kripto, emtia (İngilizce) | açık |
| `google_news` | Google News arama RSS | BIST kodu ve varlık adıyla Türkçe arama | açık |
| `rss:aa_ekonomi`, `rss:bloomberght`, `rss:haberturk_ekonomi`, `rss:trt_ekonomi`, `rss:investing_tr` | Türkçe RSS | Piyasa akışı | açık |
| `rss:cnbc_top`, `rss:bbc_business` | İngilizce RSS | Global akış | açık |
| `rss:coindesk`, `rss:cointelegraph` | İngilizce RSS | Kripto | kapalı |
| `rss:custom_<sha1>` | Kullanıcının RSS beslemesi | Piyasa akışı | açık |

### KAP

`POST https://www.kap.org.tr/tr/api/disclosure/members/byCriteria` (resmî olmayan iç API; KAP değiştirebilir). Gövde: ISO tarih (`YYYY-AA-GG`; `GG.AA.YYYY` verilirse 500 döner), `memberType: "IGS"`, `mkkMemberOidList` (tek istekte birden çok şirket), diğer alanlar boş; başlıklar tarayıcı `User-Agent` ve `Referer: https://www.kap.org.tr/tr/bildirim-sorgu`. Son 14 gün, en çok 40 şirket, en çok 60 haber. Şirket kimlikleri `KapShareholderProvider.resolve_member_oid` ile çözülür (Hisse 360 ortaklık yapısıyla ortak harita; `GARAN, TGB` gibi virgüllü borsa kodları ayrıştırılır, önbellek `data/_cache/kap/bist_companies_v2.json`). `publishDate` İstanbul saatidir, UTC'ye çevrilir. Bağlantı: `https://www.kap.org.tr/tr/Bildirim/{disclosureIndex}`.

Gürültü süzgeci: kendi bildirimi olmayan ve 5'ten çok hisseyi listeleyen kurum duyuruları (SPK işlem yasağı, MKK) varsayılan gizlidir (KAP kaynağının `include_mass_notices` seçeneğiyle açılır); "Sorumluluk Beyanı" alt belgeleri elenir; aynı şirketin aynı dakikadaki `FR` kayıtları teke iner ("Finansal Rapor" tercih edilir).

### Yahoo ve Google News

- Yahoo: `https://feeds.finance.yahoo.com/rss/2.0/headline?s={yf_symbol}`; yalnızca ABD hissesi, kripto, metal hedefleri. BIST için kullanılmaz (`THYAO.IS` akışı seyrek ve bayat).
- Google News: `https://news.google.com/rss/search?q=...&hl=tr&gl=TR&ceid=TR:tr`; BIST için hisse kodu, diğerleri için varlık adı. Kişisel okuyucu kullanımına yöneliktir; kaynağın kullanım koşulları geçerlidir (Ayarlar'da not düşülür), kapatılabilir.
- İkisi de hedef başına bir akış çeker (en çok 10 hedef, hedef başına 8 haber); bazı hedefler başarısızsa kalanlar gösterilir, hepsi başarısızsa kaynak hata verir.

### RSS

`RssNewsProvider` RSS 2.0 ve Atom'u `lxml` ile ayrıştırır (`resolve_entities=False`, `no_network=True`, en çok 40 öğe, gövde en çok 4 MB). Tarihler UTC'ye normalize edilir (RFC 822, ISO 8601, saat dilimsiz biçimler UTC kabul edilir); başlıksız, bağlantısız veya tarihsiz öğeler atlanır.

## 3. `NewsService`

- `get_company_news(targets, force)` ve `get_market_news(force)`: ilgili kapsamdaki **etkin** kaynakları paralel çeker (en çok 6 iş parçacığı).
- **Hata yalıtımı:** bir kaynağın hatası (beklenmedik istisna dahil) diğerlerini etkilemez; kaynak başına `NewsSourceStatus` (çekim zamanı, haber sayısı, hata, önbellekten mi) döner.
- **Önbellek:** kaynak + hedef parmak izi başına JSON dosya (`data/_cache/news/`, `JsonFileNewsCache`), TTL 10 dakika. Kaynak hata verirse varsa son başarılı çekim gösterilmeye devam eder ve hata raporlanır (yeniden başlatmada ve çevrimdışıyken de).
- **Tekilleştirme:** URL, yoksa normalize başlık özeti; aynı haberin en yenisi kalır; tarihe göre azalan sıra; en çok 150 haber.
- **Kaynak yönetimi:** `list_sources` (ilk çağrıda varsayılanları tohumlar), `set_source_enabled`, `set_source_option`, `add_rss_source` (ad boş olamaz, yalnızca http/https, aynı adres reddedilir), `remove_source` (yalnızca özel beslemeler), `test_source` / `test_rss_url` (önbelleksiz tek çekim, örnek hedeflerle), `get_status` (oturumdaki son çekim/hata).
- **Hedefler (`NewsTargetService`):** BIST portföyünün açık pozisyonları, varlık defterindeki etkin varlıklar ve izleme listeleri; aynı (tür, sembol) bir kez, portföy önce, en çok 30; bir okuyucunun hatası diğerlerini engellemez.

## 4. Veri

`news_sources` tablosu (`ORMNewsSource`): `source_id` (PK), `kind`, `name`, `enabled`, `language`, `scope`, `url`, `description`, `is_custom`, `options_json`, `sort_order`. Varsayılan kaynaklar ilk `list_sources()` çağrısında eklenir. Yenileme aralığı `QSettings` anahtarı `news/refresh_minutes` (5/10/15/30/60 dk, varsayılan 10).

## 5. Arayüz

- **`NewsController`** (`newsController`): tek işçili `ThreadPoolExecutor` + `Signal`, `QTimer` ile periyodik yenileme (ayardaki aralık), portföy/varlık değişince yenileme (`app.py`), `forceRefresh`, `failedSources` (ulaşılamayan kaynak adları), `openUrl` (yalnızca `http`/`https`, `QDesktopServices`; QML'de `Qt.openUrlExternally` kullanılmaz). Hata durumunda önceki satırlar korunur.
- **`NewsPanel.qml`:** "Portföyüm ve İzleme" (şirket) ve "Piyasa ve Global" sekmeleri; kaynak ve dil rozeti, ilgili semboller, göreli zaman, özet; tıklayınca varsayılan tarayıcı. Genel Bakış'ta ≥1150 px'te grafiğin sağında 380 px, dar pencerede grafiğin altında.
- **Ayarlar > Haber Kaynakları** (`NewsSettingsController`, `SettingsNewsTab.qml`): kaynak başına aç/kapa, KAP toplu bildirim anahtarı, özel RSS ekleme/silme, "Bağlantıyı test et" (arka planda), her kaynak için durum metni, yenileme aralığı. Kapatılan kaynak `sourcesChanged` ile panele hemen yansır.

## 6. Bilinen Sınırlar

- KAP ve Yahoo uçları belgesiz/resmî olmayan adreslerdir; kapanabilir. Sağlayıcı hata verirse yalnızca o kaynak "ulaşılamıyor" olur.
- `yfinance` haber API'si (`finance.yahoo.com/xhr/ncp`) 404 verir ve kütüphane bunu sessizce boş listeye çevirir; bu yüzden kullanılmaz.
- Bazı genel RSS akışları (BloombergHT, Dünya, Ekonomim, CNN Türk) piyasa dışı içerik karıştırır; anahtar sözcük süzgeci yoktur. Hürriyet (768 KB) ve Milliyet beslemeleri büyük olduğu için varsayılan listede değildir.
- Doğrulanmış çalışmayan adresler: `dunya.com/rss/finans`, `paraanaliz.com/feed/`, `borsagundem.com/rss`, `finance.yahoo.com/news/rssindex`, `kap.org.tr/tr/rss/bildirim`.
- Kaynak durumu yalnızca oturum içindedir (yeniden başlatınca "Henüz çekilmedi"); kalıcı hata kaydı yok. KAP toplu bildirim seçeneği bir sonraki çekimde (önbellek süresi dolunca veya yenile ile) etkili olur.
- Haber duyarlılığı analizi, bildirim (push) ve haber-fiyat korelasyonu kapsam dışıdır ([roadmap.md](roadmap.md)).

### Doğrulanmış ek RSS adresleri (2026-11-01)

Varsayılan listede olmayan ama çalıştığı doğrulanan adresler; Ayarlar'dan özel besleme olarak eklenebilir:

| Kaynak | Adres | Not |
|---|---|---|
| NTV Ekonomi | `https://www.ntv.com.tr/ekonomi.rss` | Seyrek güncellenir |
| CNN Türk Ekonomi | `https://www.cnnturk.com/feed/rss/ekonomi/news` | Yaşam/loto haberleri karışır |
| Sabah Ekonomi | `https://www.sabah.com.tr/rss/ekonomi.xml` | |
| Milliyet Ekonomi | `https://www.milliyet.com.tr/rss/rssnew/ekonomi.xml` | 313 KB |
| Hürriyet Ekonomi | `https://www.hurriyet.com.tr/rss/ekonomi` | 768 KB, sıra tarihe göre değil |
| Ekonomim | `https://www.ekonomim.com/rss` | Genel akış |
| Dünya | `https://www.dunya.com/rss?dunya` | Genel akış |
| Investing TR Hisse | `https://tr.investing.com/rss/news_25.rss` | Hisse haberleri |
| Fortune Türkiye | `https://fortuneturkey.com/feed` | |
| BBC Türkçe | `https://feeds.bbci.co.uk/turkce/rss.xml` | Genel haber |
| MarketWatch | `https://feeds.content.dowjones.io/public/rss/mw_topstories` | İngilizce |
| Investing (EN) | `https://www.investing.com/rss/news.rss` | İngilizce, genel |

Kaynaklar değişirse `scripts/probe_news_sources.py` (salt okunur canlı yoklama) yeniden çalıştırılır.

## 7. Testler

`tests/infrastructure/news/` (ayrıştırıcı, sağlayıcılar, depo, önbellek, fabrika), `tests/application/services/news/` (servis, hedefler), `tests/ui_qml/test_news_controller.py`, `test_news_panel_view.py`, `test_news_settings_controller.py`, `tests/application/test_asset_container_wiring.py`.
