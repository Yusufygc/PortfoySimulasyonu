# 05 — Genel Bakış ve Haber Akışı

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md) | Önceki: [04_portfoyum_sayfasi.md](04_portfoyum_sayfasi.md) | Sonraki: [06_ayarlar_haber_kaynaklari.md](06_ayarlar_haber_kaynaklari.md)

Durum: **Taslak** (Aşama 6)

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

| Sağlayıcı | Kaynak | Not |
|---|---|---|
| `KapDisclosureNewsProvider` | KAP bildirimleri (Türkçe) | `kap_shareholder_provider.resolve_member_oid(ticker)` yeniden kullanılır; şirket bazlı uç nokta spike'ta doğrulanır |
| `YFinanceNewsProvider` | `Ticker.get_news`, `Search.news` | `yfinance_lock` altında; haberler çoğunlukla İngilizce; yfinance sonuçları oturumda saklar |
| `RssNewsProvider` | Yapılandırılabilir RSS/Atom listesi | `lxml` ile ayrıştırma; yeni paket gerekirse pinli eklenir |

Hepsi `retry_call` kullanır, geçici hatayı `MarketDataUnavailableError`'a sarar. Gerçek ağ çağrısı testlerde yapılmaz; sağlayıcılara `fetcher` enjekte edilebilir (mevcut `KapMkkCorporateActionProvider(fetcher=...)` kalıbı).

### Application (`src/application/services/news/`)

`NewsService`:

- Etkin kaynakları paralel çeker; bir kaynağın hatası diğerlerini etkilemez (kaynak başına hata durumu raporlanır).
- Tekilleştirme: URL, yoksa normalize başlık hash'i.
- Tarihe göre azalan sıralama.
- Takip sembolleri: portföy (BIST + varlık defteri) + izleme listesi; servisler üzerinden alınır.
- Önbellek: `data/_cache/news/` altında TTL'li JSON (yaklaşık 10 dakika); yfinance oturum önbelleği nedeniyle zorunlu.
- Yalnızca başlık, özet ve bağlantı saklanır; haber tam metni saklanmaz.
- İki akış: **şirket haberleri** (takip sembollerine bağlı) ve **piyasa/global haberleri** (sembolsüz genel akış).

### Tercih Deposu

SQLite `news_source_settings(source_id PK, enabled, config_json)` + infrastructure repository. Özel RSS beslemeleri `config_json` içinde tutulur (bkz. [06](06_ayarlar_haber_kaynaklari.md)).

### UI (`src/ui_qml/`)

- `controllers/news_controller.py`: `MarketTickerController` kalıbı — tek işçili `ThreadPoolExecutor`, `_loading` bayrağı, `Signal` ile ana thread'e dönüş, `QTimer` ile periyodik yenileme; `openUrl(url)` slotu `QDesktopServices.openUrl` kullanır (örnek: `corporate_action_controller.py`). QML'de `Qt.openUrlExternally` kullanılmaz.
- `models/news_list_model.py`: `ListTableModel` tabanlı.
- `qml/components/NewsPanel.qml`: iki sekme — "Portföyüm ve İzleme" (şirket) / "Piyasa ve Global". Her satırda kaynak rozeti, dil rozeti, göreli zaman; tıklayınca varsayılan tarayıcı açılır. Boş durum, yükleniyor ve hata durumları metinleri `Strings.qml`'de.

## 3. Spike (kod öncesi)

Aşama 6 kodlamasından önce yapılır; sonuçlar [tasarim_notlari/](tasarim_notlari/) altına yazılır:

1. **KAP:** Şirket bazlı bildirim listesi uç noktası depoda doğrulanmadı. `scripts/` altında canlı yoklama betiği yazılır; çalışırsa `@pytest.mark.network` testi eklenir. Çalışmazsa mevcut `kap_mkk_provider` HTML yolu "best-effort" kullanılır veya KAP haberi kapsam dışı bırakılıp kullanıcıya bildirilir.
2. **yfinance:** `.IS` hisseleri için haber kapsamı ve yanıt alanları (başlık, yayıncı, zaman, bağlantı) denenir.
3. **RSS:** Aday Türkçe ekonomi/piyasa kaynakları denenir. Gerçek besleme adresleri bu adımda doğrulanır; doğrulanmamış adres koda yazılmaz.

## 4. Sınırlar

- Haber içeriğinin telif sınırları nedeniyle yalnızca başlık, kısa özet ve bağlantı gösterilir.
- Haber duyarlılığı analizi, bildirim (push) ve haber–fiyat korelasyonu v1 dışıdır.

## 5. Testler

- `NewsService`: sahte sağlayıcılar; kaynak hata yalıtımı; tekilleştirme; sıralama; önbellek TTL; aç/kapa.
- Sağlayıcılar: kayıtlı örnek yanıtlarla ayrıştırma (saf fonksiyon testleri).
- `NewsController`: sinyal sırası, yükleniyor bayrağı, `openUrl` çağrısı (monkeypatch).
- QML: `NewsPanel` boş/dolu/hata durumu uyarısız yükleme.
