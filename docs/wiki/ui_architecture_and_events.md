# Kullanıcı Arayüzü (UI) ve Olay (Event) Mimarisi

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, `src/ui/` dizini altındaki PySide6 bileşenleri, `src/qt_compat` uyumluluk katmanı, yönlendirme, asenkron iletişim ve tema mimarisini açıklar.

## 1. PySide6 Thread ve Worker Yapısı

Masaüstü uygulamalarında, API istekleri veya yoğun hesaplamalar Ana Thread'i (Main GUI Thread) kilitlerse arayüz donar. Bunu engellemek için tüm işlemler `QRunnable` ve `QThreadPool` tabanlı `worker.py` mekanizması ile arka planda çalıştırılır.

### Temel Akış
1. Kullanıcı butona basar.
2. UI nesnesi (örn. Buton), Worker nesnesini ilklendirir ve `QThreadPool.globalInstance().start(worker)` çağrılır.
3. Worker, hesaplamayı arka planda yapar ve PySide6 `Signal` nesneleri (`signals`) ile sonucu (`success`, `error` vb.) ana thread'deki UI bileşenine iletir.
4. UI bileşeni sadece gelen sinyali dinleyerek ekrana yansıtır.

### Faz 4 Standardı

- UI tarafındaki uzun işlemler ortak `src/ui/worker.py` içindeki `Worker(QRunnable)` ile çalışır; özel `QThread` sınıfı yalnızca gerekçeli ve testli istisna olarak kabul edilir.
- Qt importları üretim UI kodunda doğrudan PySide6 üzerinden yapılmaz; `src/qt_compat/` modülleri binding sınırı olarak kullanılır.
- `app.py`, `QApplication` oluşmadan önce `src/qt_compat/scaling.py` üzerinden Windows 100% üstü ekran ölçeğini ters `QT_SCALE_FACTOR` ile normalize eder. Bu, PySide6/Qt6 sonrası 125% sistem ölçeğinde sayfa içeriklerinin ve sabit px metriklerinin büyümesini engeller. Gerekirse `PORTFOYSIM_DISABLE_QT_SCALE_NORMALIZATION=1` ile kapatılabilir.
- PySide6 altında QRunnable wrapper ömrü için `Worker` aktif işleri `finished` sinyali dış dinleyicilere teslim edilene kadar referans setinde tutar; internal cleanup ayrı sinyalle, `finished` sonrasında yapılır.
- `Worker.signals.error` mevcut tuple sözleşmesini korur: `(exception_type, exception_value, traceback_text)`.
- AI analizi, Gemini chat/yorum üretimi ve optimizasyon akışları `Worker + QThreadPool` modeline taşınmıştır.
- Async UI sonuçlarında request-id kontrolü kullanılır; eski worker sonucu yeni filtre veya ekran durumunu ezmez.
- Analiz sayfası gibi WebEngine/Plotly içeren ekranlarda gizli tablar ilk sayfa kurulumunda `QWebEngineView` oluşturmaz; grafik view'ları tab aktiflenince lazy init edilir ve eldeki DTO cache'i ile render edilir.

## 2. Global Event Bus (Pub/Sub)

Farklı ekranların birbirini doğrudan bilmeden haberleşmesini sağlamak için `container.event_bus` kullanılır. Bu, modüllerin (coupling) sıkı bağlanmasını önler.

- Örneğin fiyat sağlığı ekranında fiyatlar güncellendiğinde, arka plandaki servis `event_bus.prices_updated.emit()` sinyalini yayar.
- Hem Ana Sayfa (Dashboard teknik modülü) hem de Analiz Ekranı bu sinyali dinler ve eğer güncellenen hisse kendi listelerindeyse UI grafiklerini otomatik olarak yeniler.

### Fiyat Güncelleme Olayı

- Public import yüzeyi `src.application.events.GlobalEventBus` olarak sabitlenmiştir.
- `prices_updated` payload sözleşmesi `dict[int, Decimal]` şeklindedir.
- UI katmanında fiyat güncelleme yayını `src/ui/shared/price_event_publisher.py` içindeki `publish_prices_updated(event_bus, prices)` helper'ı üzerinden yapılır.
- Helper boş payload'u yayınlamaz; dolu payload'u kopyalayarak emit eder ve Decimal fiyat değerlerini dönüştürmez.

### Otomatik Canli Fiyat Yenileme

- `LivePriceRefreshController`, MainWindow icinde uygulama geneli intraday fiyat yenileme timer'ini yonetir; isleri ortak `Worker + QThreadPool` ile arka planda calistirir.
- Otomatik yenileme BIST islem gunlerinde, acikken ve baska yenileme worker'i kosmuyorken baslar; basarili sonuc once `latest_prices` cache'ine yazilir, sonra `prices_updated` olarak yayilir.
- Periyodik intraday hatalarinda tekil ticker hatalari loglanir, kullanici toast ile rahatsiz edilmez; ard arda genel hata birikirse kisa warning gosterilir.
- `prices_updated` UI degerlemesi icin anlik kaynaktir; tarihsel rapor, backtest ve fiyat sagligi `daily_prices` kapanis sozlesmesini kullanmaya devam eder.

## 3. Tema ve Design Tokens (Tasarım Değişkenleri)

`ThemeManager` ve `tokens.py` kullanılarak gelişmiş ve modüler bir QSS mimarisi kurgulanmıştır:

- **Tokens (`src/ui/styles/tokens.py`):** Uygulamanın tüm renk paleti (Dark/Light modu), font boyutları, yuvarlama yarıçapları (border-radius) tek bir merkezde, Python sözlüğü (dict) olarak tutulur.
- **Modüler QSS:** Büyük bir `.qss` dosyası yerine, farklı bileşenler için (primitives, shared, feature) ayrı `.qss` dosyaları mevcuttur. Uygulama ayağa kalkarken bu dosyalar derlenir ve ilgili "Token" stringleri asıl renk kodlarıyla değiştirilerek arayüze basılır.
- Faz 4 itibarıyla yeni görsel stiller inline `setStyleSheet` yerine `cssClass`/dynamic property ve QSS manifest dosyalarıyla eklenir. Bilinçli istisna olarak tema önizleme swatch'ları runtime renk kullandığı için `AppearancePanel` içinde kalabilir.

## 4. Yönlendirme ve PageFactory

Bütün ekranlar `main_window.py` üzerinde barınır. Ancak kod kalabalığını engellemek adına, her ekran `src/ui/pages/` altındaki kendi dizininden `page_factory.py` aracılığı ile çağrılır. Ana pencere sadece bir QStackedWidget kullanarak sayfalar arası geçişi yönetir.

## 5. Faz 4 UI Refactor Notları

- `DashboardActions` export ve corporate-action sorumluluklarını ayrı handler sınıflarına devreder; public action metotları geriye uyum için korunur.
- `ComparisonDataManager` varlık seçenekleri, filter-state üretimi, uyarı üretimi ve DTO/Series dönüşümünü helper sınıflara böler.
- `StockDetailPage` işlem kaydetme orchestration'ını `StockTradeSubmitter` helper'ına devreder; sayfa layout, state ve wiring sorumluluğunda kalır.

## 6. Faz 5 QA ve Regresyon Kapıları

- UI worker/event akışları `tests/ui/test_worker.py`, `tests/ui/pages/ai_page/test_ai_worker_stale.py` ve `tests/ui/test_refactor_guards.py` ile korunur.
- UI katmanı doğrudan `QThread` sınıfı kullanmaz; yeni async işler `Worker + QThreadPool` standardına uyar.
- Fiyat event yayınları UI tarafında yalnız `publish_prices_updated(event_bus, prices)` helper'ı ile yapılır; application coordinator kendi EventBus orkestrasyonunu korur.
- UI testlerinde event döngüsü boşaltma için ortak `drain_qt_events` fixture'ı kullanılır.
- `pytest.ini` manual/network marker'ları default suite'i canlı dış kaynaklardan ayırır; benchmark canlı veri kontrolü manuel operasyon olarak kalır.
- Dialog davranis guard'i `tests/ui/widgets/test_dialog_behavior.py` ile korunur: context-help `?` butonu kapali, Enter primary aksiyona bagli ve model portfoy tutar alani readonly kalir.

## Dialog Davranis Standardi (2026-06-02)

- Uygulama `QDialog` pencereleri `src/ui/widgets/dialog_behavior.py` icindeki `configure_dialog_behavior(...)` helper'i ile `?` context-help butonunu kapatir.
- Ayni helper Enter/Return tusunu primary aksiyona baglar; `Esc` iptal davranisini, cok satirli metin alanlari ve acik popup girisleri kendi davranisini korur.
- Model portfoy al/sat dialogu lot ve fiyat degisimlerinde readonly `Tutar` alanini canli hesaplar; dialog sonucu ve servis API'si degismez.

## Finansal Input Standardi (2026-06-06)

- TL tutar/fiyat girisleri ortak `CurrencySpinBox` bilesenini kullanir; ticker, not, isim, oran ve lot alanlari bu kapsama dahil degildir.
- Finansal input focus aldiginda `TL` suffix'ini gizler ve binlik ayraclari canli uygular (`1.234,56`); focus disinda Turkce gorunumle formatlanir (`1.234,56 TL`).
- Hesaplama ve servis sonucunda formatli metin parse edilmez; raw deger `value()` veya Decimal icin `decimal_value()` uzerinden okunur.
- Eski `InstantDoubleSpinBox` adi geriye uyumlu olarak `CurrencySpinBox` davranisina baglanmistir.

## Islem Tarihi / Piyasa Seansi Guard (2026-06-06)

- Hisse al/sat kaydi icin secilen tarih ve saat BIST acik seansina denk gelmek zorundadir; hafta sonu, BIST tatili, yarim gun kapanis sonrasi ve normal seans disi saatler kesin blokajdir.
- UI helper'i kapali seansta artik `Yes/No` onayi sormaz; kullaniciya yonlendirici uyari gosterir ve kayit akisina devam etmez.
- `TradeEntryService` ve `ModelPortfolioTradeService` production container'da `BistMarketSessionService` ile guard edilir; UI kontrolu atlansa bile kapali seans trade kaydi olusmaz.
- Sermaye/nakit hareketleri bu kurala dahil degildir; kural yalniz hisse al/sat islemleri icindir.

## Model Portfoy UI State Notu (2026-06-03)

- Model portfoy sayfasi acildiginda son secim bulunamazsa listedeki ilk portfoy otomatik secilir; liste bos ise sag panel temizlenir ve islem butonlari pasif kalir.
- Secili portfoyde acik pozisyon yoksa `Hisse Sat` pasif kalir; `Hisse Al`, `Fiyat Guncelle`, `Rapor Al` ve `Sermaye Yonetimi` secili portfoy kapsaminda aktif olur.
- `Sermaye Yonetimi` dialogu tarih, saat, tutar, islem tipi ve not alanlariyla model portfoy sermaye hareketi olusturur.

## Stock Detail Grafik UX Geliştirmesi (2026-06-06)

- `StockChartWidget` `pyqtgraph` tabanlı, artık tamamen Türkçe lokal:
  - **X-ekseni TR ay**: `DateAxisItem.tickStrings` `L10N.AYLAR_KISA` ile `"15 Oca"` üretir (`%d %b` → "Jan" kalktı). `locale.setlocale` bağımlılığı yok; deterministik map.
  - **Y-ekseni `₺` formatı**: yeni `CurrencyAxisItem` Türkçe binlik/ondalık (`₺ 1.234,56`).
  - **Crosshair + tooltip**: `pg.SignalProxy(scene.sigMouseMoved, rateLimit=60)` ile `vLine/hLine` ve `TextItem` etiketi. Fare gerçek noktalara `bisect` ile snap'lenir. Etiket `L10N.GRAFIK_TOOLTIP_TMPL` (`"15 Oca 2026  ·  ₺ 125,40"`). Viewport sağ kenarında otomatik sol-anchor.
  - **Reference legend konumu**: `pg.LegendItem(offset=(14, 44))` — başlık satırının altına çekildi; başlık/eksen tick'leri ile çakışma yok.
  - **Başlık L10N**: `L10N.FIYAT_GECMISI_TMPL = "{ticker} — Fiyat Geçmişi"` (em-dash).
- Mimari kural: UI doğrudan `yfinance` çağırmaz; DB serisi boşsa enjekte edilen `market_client.get_price_series` provider'ı kullanılır (P0'dan korunmuş).
- `optimization_page.py` `_load_sources` artık sessiz `except Exception: pass` yerine `logger.warning` + combo'ya `L10N.MODEL_PORTFOY_YOK` placeholder ekler.

## AI Katmanı Temiz Mimariye Taşındı (2026-06-06)

- Eski `src/ui/pages/ai_page/core/` klasörü (HTTP istemci, Gemini SDK, QSettings sohbet deposu, iş kuralları) UI katmanından çıkarıldı ve kaldırıldı; bu kod doğru katmanlara dağıtıldı:
  - **Domain:** `src/domain/models/ai_analysis.py` (saf modeller, L10N içermez; `ModelOutlook` değerleri `up/down/neutral` semantik) + portlar `src/domain/ports/services/i_ai_analysis_provider.py`, `i_ai_chat_provider.py`, `src/domain/ports/repositories/i_chat_history_repo.py`.
  - **Infrastructure:** `src/infrastructure/ai/` — `ai_core_fastapi_client.py` (`requests` + `FastAPIAnalysisProvider` + `_parse_api_response`), `gemini_chat_provider.py` (`google.genai`), `mock_ai_analysis_provider.py`, `qsettings_chat_history_repo.py`.
  - **Application:** `src/application/services/ai/` — `ai_analysis_service.py` (canlı/demo fallback), `ai_chat_service.py` (`SYSTEM_PROMPT` + güvenlik sarmalama + rol eşleme), `safety_guard.py`.
  - **UI:** kullanıcıya dönük Türkçe etiket/disclaimer `src/ui/pages/ai_page/labels.py` (`outlook_label`), sohbet oturum yönetimi `src/ui/pages/ai_page/right_panel/chat_session_manager.py`.
- DI: `container.ai_analysis_service`, `container.ai_chat_service`, `container.chat_history_repo`. `AIPage` servisleri panellere enjekte eder; tekrarlı `load_ai_settings()` çağrıları kaldırıldı (ayar tek noktada).
- `StockChartWidget` artık `yfinance`'i doğrudan çağırmaz; DB serisi boşken `container.market_client.get_price_series` provider'ı kullanılır (`set_price_series_provider`).
- Regresyon kapısı: `tests/ui/test_refactor_guards.py` — `src/ui` altında `requests`/`yfinance`/`google` importu ve `ai_page/core` klasörü yasak.

## AI Asistanı Sidebar ve Arayüz Güncellemesi (2026-06-04)

- AI Finans Asistanı sayfasındaki "Sohbetler" butonu kaldırılmış ve yüzen (`floating`) bir sidebar aç/kapat ikon butonu (`btn_toggle_sidebar`) eklenmiştir.
- Sidebar uzunluğu chat panelinin sol/üst köşesinden (`x=0, y=0`) tam yükseklikte (`self.height()`) başlayacak şekilde hizalanmıştır.
- Aç/kapat ikon butonu ve sidebar, `QParallelAnimationGroup` ve `QPropertyAnimation` (`geometry` özelliği) kullanılarak 250 ms süreyle smooth bir geçişle eş zamanlı olarak hareket ettirilir.
- Sidebar kapalıyken buton chat panelinin sol üst köşesinde (`x=20, y=14`) "Merhaba" mesajının üstünde yer alır; sidebar açıldığında ise başlıklar arası çakışmayı önlemek için otomatik olarak sidebar'ın sağ üst köşesine (`x=sidebar_width - 46, y=14`) kayar.
- Sidebar içindeki eski "Kapat" butonu kaldırılmış, kapatma işlemi de bu hareketli ikon butonuyla birleştirilmiştir.
- Uygulama başlangıcında son aktif sohbetin otomatik olarak açılması yerine, her zaman yeni ve temiz bir sohbet oturumu açılması sağlanmıştır.
