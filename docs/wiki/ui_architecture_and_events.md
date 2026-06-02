# Kullanıcı Arayüzü (UI) ve Olay (Event) Mimarisi

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, `src/ui/` dizini altındaki PyQt5 bileşenleri, yönlendirme, asenkron iletişim ve tema mimarisini açıklar.

## 1. PyQt5 Thread ve Worker Yapısı

Masaüstü uygulamalarında, API istekleri veya yoğun hesaplamalar Ana Thread'i (Main GUI Thread) kilitlerse arayüz donar. Bunu engellemek için tüm işlemler `QRunnable` ve `QThreadPool` tabanlı `worker.py` mekanizması ile arka planda çalıştırılır.

### Temel Akış
1. Kullanıcı butona basar.
2. UI nesnesi (örn. Buton), Worker nesnesini ilklendirir ve `QThreadPool.globalInstance().start(worker)` çağrılır.
3. Worker, hesaplamayı arka planda yapar ve PyQt Sinyalleri (`signals`) ile sonucu (`success`, `error` vb.) ana thread'deki UI bileşenine iletir.
4. UI bileşeni sadece gelen sinyali dinleyerek ekrana yansıtır.

### Faz 4 Standardı

- UI tarafındaki uzun işlemler ortak `src/ui/worker.py` içindeki `Worker(QRunnable)` ile çalışır; özel `QThread` sınıfı yalnızca gerekçeli ve testli istisna olarak kabul edilir.
- `Worker.signals.error` mevcut tuple sözleşmesini korur: `(exception_type, exception_value, traceback_text)`.
- AI analizi, Gemini chat/yorum üretimi ve optimizasyon akışları `Worker + QThreadPool` modeline taşınmıştır.
- Async UI sonuçlarında request-id kontrolü kullanılır; eski worker sonucu yeni filtre veya ekran durumunu ezmez.

## 2. Global Event Bus (Pub/Sub)

Farklı ekranların birbirini doğrudan bilmeden haberleşmesini sağlamak için `container.event_bus` kullanılır. Bu, modüllerin (coupling) sıkı bağlanmasını önler.

- Örneğin fiyat sağlığı ekranında fiyatlar güncellendiğinde, arka plandaki servis `event_bus.prices_updated.emit()` sinyalini yayar.
- Hem Portföy Dashboard'u hem de Analiz Ekranı bu sinyali dinler ve eğer güncellenen hisse kendi listelerindeyse UI grafiklerini otomatik olarak yeniler.

### Fiyat Güncelleme Olayı

- Public import yüzeyi `src.application.events.GlobalEventBus` olarak sabitlenmiştir.
- `prices_updated` payload sözleşmesi `dict[int, Decimal]` şeklindedir.
- UI katmanında fiyat güncelleme yayını `src/ui/shared/price_event_publisher.py` içindeki `publish_prices_updated(event_bus, prices)` helper'ı üzerinden yapılır.
- Helper boş payload'u yayınlamaz; dolu payload'u kopyalayarak emit eder ve Decimal fiyat değerlerini dönüştürmez.

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
