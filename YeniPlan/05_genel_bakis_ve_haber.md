# 05 — Genel Bakış ve Haber Akışı

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md) | Önceki: [04_portfoyum_sayfasi.md](04_portfoyum_sayfasi.md) | Sonraki: [06_ayarlar_haber_kaynaklari.md](06_ayarlar_haber_kaynaklari.md)

Durum: **Uygulandı** (Aşama 6; Ayarlar sekmesi Aşama 7'de). Spike sonuçları aşağıda ve [tasarim_notlari/](tasarim_notlari/) altında

## 1. Sayfa Yerleşimi

Genel Bakış (indeks 0) şu yapıya iner:

1. Başlık ve `PriceStatusChip`.
2. Grafik alanı: `TradingViewToolbar`, hızlı sembol seçici (portföy BIST hisseleri + portföy varlıkları + izleme listesi), `TradingViewChart`.
3. Haber paneli (`NewsPanel.qml`): grafiğin yanında veya altında; dar pencerede alta iner.

Grafik şu an yalnızca BIST çizer (`ChartController._load_candles`: DuckDB → SQLite → demo). Global sembol için sınıf bazlı ikinci veri yolu eklenir: sembol varlık defterinde bulunuyorsa `asset_prices` / yfinance geçmişi kullanılır, aksi halde mevcut BIST yolu. BIST yolu değişmez; mevcut `test_chart_*` karakterizasyon testleri korunur.

## 2. Haber Mimarisi

### Domain (`src/domain/`)

- `models/news_item.py`: `NewsItem(id, title, summary, source_id, published_at, url, related_symbols, language)`.
- `ports/services/i_news_provider.py`: `INewsProvider` — `source_id`, `display_name`, `fetch(symbols: list[str] | None) -> list[NewsItem]`.
- `ports/repositories/i_news_source_preferences.py`: kaynak aç/kapa tercihleri.

### Infrastructure (`src/infrastructure/news/`)

Spike sonrası kesinleşen sağlayıcılar:

| Sağlayıcı | Kaynak | Kapsam | Not |
|---|---|---|---|
| `KapDisclosureNewsProvider` | `POST https://www.kap.org.tr/tr/api/disclosure/members/byCriteria` | BIST şirket bildirimleri (Türkçe) | Tek istekte çoklu şirket; ISO tarih; ortak/kurum bildirimi ve alt belge gürültüsü süzülür ([spike_kap_bildirim.md](tasarim_notlari/spike_kap_bildirim.md)). Ön koşul: KAP kimlik haritası hatasının düzeltilmesi |
| `YahooRssNewsProvider` | `https://feeds.finance.yahoo.com/rss/2.0/headline?s={yf_symbol}` | ABD hissesi, kripto, emtia (İngilizce) | `YFinanceNewsProvider` **iptal**: `yfinance` haber API'si 404 veriyor ([spike_yfinance_haber.md](tasarim_notlari/spike_yfinance_haber.md)) |
| `GoogleNewsRssProvider` | `https://news.google.com/rss/search?q=...&hl=tr&gl=TR&ceid=TR:tr` | BIST şirketleri ve varlık adları (Türkçe) | Kullanım koşulu notu; varsayılan açık/kapalı kararı kullanıcıda |
| `RssNewsProvider` | Yapılandırılabilir RSS/Atom listesi | Piyasa ve global genel akış | `lxml`; doğrulanmış varsayılan liste [spike_rss_kaynaklari.md](tasarim_notlari/spike_rss_kaynaklari.md) §5 |

Hepsi `retry_call` kullanır ve **HTTP durumunu açıkça denetler**: 4xx/5xx, boş gövde veya ayrıştırılamayan yanıt `MarketDataUnavailableError` olur (`yfinance`'in sessiz boş dönüşü tekrarlanmaz). Gerçek ağ çağrısı testlerde yapılmaz; sağlayıcılara `fetcher` enjekte edilir (mevcut `KapMkkCorporateActionProvider(fetcher=...)` kalıbı).

Ortak ayrıştırma ilkeleri: tarihler UTC'ye normalize edilir (RFC 822, ISO 8601 ve saat dilimsiz biçimler); yalnızca ilk N öğe işlenir (Hürriyet 768 KB); genel akışlarda piyasa dışı içerik anahtar sözcük süzgeciyle elenebilir.

### Application (`src/application/services/news/`)

`NewsService`:

- Etkin kaynakları paralel çeker; bir kaynağın hatası diğerlerini etkilemez (kaynak başına hata durumu raporlanır).
- Tekilleştirme: URL, yoksa normalize başlık hash'i.
- Tarihe göre azalan sıralama.
- Takip sembolleri: portföy (BIST + varlık defteri) + izleme listesi; servisler üzerinden alınır.
- Önbellek: `data/_cache/news/` altında TTL'li JSON (yaklaşık 10 dakika); sık yenilemede kaynakları gereksiz yüklememek için zorunlu.
- Yalnızca başlık, özet ve bağlantı saklanır; haber tam metni saklanmaz.
- İki akış: **şirket haberleri** (takip sembollerine bağlı) ve **piyasa/global haberleri** (sembolsüz genel akış).

### Tercih Deposu

SQLite `news_source_settings(source_id PK, enabled, config_json)` + infrastructure repository. Özel RSS beslemeleri `config_json` içinde tutulur (bkz. [06](06_ayarlar_haber_kaynaklari.md)).

### UI (`src/ui_qml/`)

- `controllers/news_controller.py`: `MarketTickerController` kalıbı — tek işçili `ThreadPoolExecutor`, `_loading` bayrağı, `Signal` ile ana thread'e dönüş, `QTimer` ile periyodik yenileme; `openUrl(url)` slotu `QDesktopServices.openUrl` kullanır (örnek: `corporate_action_controller.py`). QML'de `Qt.openUrlExternally` kullanılmaz.
- `models/news_list_model.py`: `ListTableModel` tabanlı.
- `qml/components/NewsPanel.qml`: iki sekme — "Portföyüm ve İzleme" (şirket) / "Piyasa ve Global". Her satırda kaynak rozeti, dil rozeti, göreli zaman; tıklayınca varsayılan tarayıcı açılır. Boş durum, yükleniyor ve hata durumları metinleri `Strings.qml`'de.

## 2b. Uygulama Notları (Aşama 6)

Plandan sapmalar ve gerçek dosya yolları:

| Konu | Uygulama |
|---|---|
| Domain | `src/domain/models/news_item.py` (`NewsItem`, `NewsTarget`/`TargetKind`, `NewsSourceConfig` + `options`, `NewsSourceStatus`, `NewsFeedResult`); portlar `ports/services/i_news_provider.py` (`NewsProviderUnavailable`), `ports/repositories/i_news_source_repo.py` (`INewsSourceRepository`, `INewsCache`) |
| Sağlayıcı arayüzü | `fetch(targets)`; `scope` ile COMPANY (KAP, Yahoo, Google; hedef gerekir) / MARKET (RSS; hedefsiz) ayrımı. Plandaki `fetch(symbols \| None)` yerine hedefe tür bilgisi taşıyan `NewsTarget` kullanıldı |
| Altyapı | `src/infrastructure/news/`: `_http.py` (durum denetimi + `retry_call`), `feed_parser.py` (UTC'ye normalize), `rss_providers.py` (RSS, Yahoo, Google), `kap_news_provider.py`, `news_file_cache.py`, `default_sources.py`, `provider_factory.py` |
| KAP süzgeci | Çok hisseli kurum bildirimleri varsayılan gizli (`include_mass_notices` seçeneği), "Sorumluluk Beyanı" alt belgeleri elenir, aynı dakikadaki `FR` kayıtları teke iner |
| Servis | `services/news/news_service.py`: kaynak başına hata yalıtımı, URL/başlık tekilleştirme, TTL 10 dk, hatada eski önbelleğe düşme (durumda hata raporlanır), en çok 150 haber. `news_target_service.py`: portföy → varlık defteri → izleme listesi, en çok 30 hedef |
| Önbellek | Kaynak + hedef parmak izi başına JSON dosya (`data/_cache/news/`); yeniden başlatmada ve çevrimdışıyken son çekim gösterilir |
| UI | `NewsController` (tek işçi, 10 dk yenileme, `forceRefresh`, `failedSources`, yalnızca http/https `openUrl`), `NewsListModel`, `NewsPanel.qml`; Genel Bakış ≥1150 px'te grafik + 380 px panel, dar pencerede panel altta |
| Grafik | `AssetChartService` + `chart_candle_sources.load_asset_candles`: sembol BIST'te yoksa varlık defterindeki kapanışlar çizilir (OHLC kapanıştan türetilir, hacim yok); son fiyat varlığın para birimiyle; hızlı seçici `chartController.quickAssets` ile varlıkları da listeler |

Canlı doğrulama (2026-11-01, geçici veritabanı): 7 genel RSS kaynağı 0,4 sn'de 150 haber; KAP + Yahoo + Google 5 hedef için 3,1 sn'de 81 haber (GARAN dahil KAP bildirimi geldi).

Bilinen sınırlar: 1H/1W/1M yeniden örnekleme 2 ondalıkta yuvarlar (çok düşük fiyatlı varlıkta haftalık/aylık mumlar kaba kalır); varlık grafiğinde hacim ve gerçek OHLC yok; Yahoo sembol akışı BIST için kullanılmaz (bayat).

## 3. Spike Sonuçları (2026-11-01)

Ayrıntılar `tasarim_notlari/` altındadır; yoklama betiği [scripts/probe_news_sources.py](../scripts/probe_news_sources.py) kaynaklar değişirse yeniden çalıştırılır.

1. **KAP: kullanılabilir.** `POST .../tr/api/disclosure/members/byCriteria` şirket bazlı bildirim listesini döndürüyor (0,2-1,2 sn). İki ön koşul: (a) mevcut KAP kimlik haritası, birden fazla borsa kodu olan 45 şirketi (GARAN dahil) atlıyor; düzeltilmeli. (b) Sonuçların ~üçte biri çok hisseli kurum bildirimi / alt belge gürültüsü; süzgeç gerekli. Bkz. [spike_kap_bildirim.md](tasarim_notlari/spike_kap_bildirim.md).
2. **yfinance haberi: çalışmıyor.** Yahoo uç noktası 404, kütüphane sessizce boş liste döndürüyor. Yerine Yahoo sembol RSS (ABD, kripto, emtia) ve Google News RSS (Türkçe, BIST). Bkz. [spike_yfinance_haber.md](tasarim_notlari/spike_yfinance_haber.md).
3. **RSS: 15 Türkçe + 6 global besleme doğrulandı**, 5 adres çalışmıyor. Bkz. [spike_rss_kaynaklari.md](tasarim_notlari/spike_rss_kaynaklari.md).

## 4. Sınırlar

- Haber içeriğinin telif sınırları nedeniyle yalnızca başlık, kısa özet ve bağlantı gösterilir.
- Haber duyarlılığı analizi, bildirim (push) ve haber–fiyat korelasyonu v1 dışıdır.

## 5. Testler

- `NewsService`: sahte sağlayıcılar; kaynak hata yalıtımı; tekilleştirme; sıralama; önbellek TTL; aç/kapa.
- Sağlayıcılar: kayıtlı örnek yanıtlarla ayrıştırma (saf fonksiyon testleri).
- `NewsController`: sinyal sırası, yükleniyor bayrağı, `openUrl` çağrısı (monkeypatch).
- QML: `NewsPanel` boş/dolu/hata durumu uyarısız yükleme.
