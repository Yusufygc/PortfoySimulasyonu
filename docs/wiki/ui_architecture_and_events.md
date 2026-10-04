# Kullanıcı Arayüzü Mimarisi (QML) ve Olay Akışı

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Sayfa rehberi: [qml_pages_guide.md](qml_pages_guide.md)

Arayüz yalnızca **PySide6 + Qt Quick (QML)** ile yazılmıştır (`src/ui_qml`). Eski Qt Widgets arayüzü (`src/ui`) 2026-10-03'te silinmiştir; tarihsel anlatımına git geçmişinden (`git log -- src/ui`) ulaşılır. Bu sayfa kalıcı arayüz kurallarını ve olay akışını açıklar; sayfa ve denetleyici ayrıntıları [qml_pages_guide.md](qml_pages_guide.md) içindedir.

## 1. Katmanlı Yapı: İnce QML + Python Denetleyici

```
QML görünümü (qml/views, qml/components)
   ^ özellik bağlama, sinyal/slot
Python denetleyici (controllers/*.py, QObject)  -- context property olarak kaydedilir (app.py)
   v yalnızca application/domain
Application servisleri
```

- QML yalnızca sunum ve etkileşimden sorumludur; iş mantığı, biçimlendirme ve veri erişimi denetleyicide/servistedir.
- Her denetleyici `QObject` alt sınıfıdır; `Property` (okunur, `notify` sinyalli), `Slot` (QML'den çağrılır) ve `Signal` (bildirim, sonuç) sunar. `app.py` denetleyicileri oluşturur ve `engine.rootContext().setContextProperty("xxxController", ctrl)` ile kaydeder.
- QML bileşenleri denetleyiciye `typeof xxxController !== "undefined"` koruması ile erişir; böylece bileşen denetleyicisiz de (testte) uyarısız derlenir.
- Tablolar için `QAbstractTableModel` tabanlı modeller kullanılır (`PositionsTableModel`, `WatchlistTableModel`); satır güncellemelerinde yeşil/kırmızı yanıp sönme animasyonu uygulanır.

## 2. Ana Pencere ve Gezinme

- `Main.qml`: `ApplicationWindow`, üstte `WindowHeader` (arama, piyasa şeridi, senkron rozeti), solda `Sidebar`, ortada `StackLayout` ile 10 sayfa. Her sayfa **lazy `Loader`** ile ilk açıldığında yüklenir; sonra bellekte kalır.
- `ShellController` etkin sayfa dizinini (`activePage`) ve piyasa seans durumunu tutar; `navigateTo(i)` ile sayfa değişir. Sayfa dizinleri: 0 Genel Bakış, 1 İzleme Listeleri, 2 Model Portföyler, 3 Hisse 360, 4 Karşılaştırma Lab, 5 Hisse Tarayıcı, 6 Finansal Planlama, 7 Optimizasyon, 8 AI Asistan, 9 Ayarlar.
- Pencere dar olduğunda (`width < 1100`) kenar çubuğu otomatik daralır. İçerik asgari ölçünün altına inerse sayfa kaydırılır; sayfalar `minContentWidth`/`minContentHeight` bildirebilir.
- `ToastNotification` ile küresel bildirimler gösterilir (senkron sonucu, açılış işleri); modallar kendi içinde yerel toast taşır.

## 3. Tema, Metin ve İkon Sistemi

`src/ui_qml/qml/theme/` altındaki üç singleton `qmldir` ile kayıtlıdır (`pragma Singleton` kullanan her dosya `qmldir`'e eklenmelidir):

| Singleton | Görev |
|---|---|
| `Theme` | Renk paleti (koyu/açık), yazı tipleri, boşluk ve köşe yarıçapı sabitleri. `Theme.isDark` ile tema değişir; seçim `QSettings` (`ui/isDarkTheme`) ile kalıcıdır (`SettingsController.toggleTheme`). Koyu temanın ana renkleri: zemin `#131722`, kart `#242731`, vurgu mavi. |
| `Strings` | Kullanıcıya görünen **tüm** metinler (`Strings.navDashboard`, `Strings.btnCancel`...). Doğru Türkçe karakterler kullanılır. |
| `Icons` | `src/ui_qml/assets/icons/` altındaki Lucide SVG'lerinin kataloğu; `Icons.get("ad")` veya adla `ModernIcon { name: "banknote" }`. |

Kurallar ([RULES.md](../../RULES.md) §2):
- **Emoji yok.** Simgeler yalnızca SVG ikonlardır (`ModernIcon`, GPU renklendirmeli).
- **Metin kataloğu:** QML'e sabit kullanıcı metni yazılmaz; yeni metin önce `Strings.qml`'e eklenir. `tests/ui_qml/test_strings_catalog.py` tanımsız/yinelenen/kullanılmayan anahtarı ve Türkçe sabit literal'i yakalar. Örnek veri ve bileşen varsayılanları testteki izin listesindedir.
- **Taşma yok:** Butonlar içeriğe göre esner (`ModernButton`); çok öğeli yatay alanlar `Flickable`/`Flow`/`GridLayout` ile sarılır; dar kartlarda ikincil etiketler elide edilir.
- Ortak bileşenler: `ModernCard`, `ModernButton`, `ModernInput`, `ModernComboBox`, `ModernScrollBar`, `ModernIcon`, `MetricCard`, `ConfirmDialog`, `ToastNotification`.

## 4. Grafikler ve Web İçerik

| Alan | Teknoloji |
|---|---|
| Fiyat grafiği (Genel Bakış, hisse detayı, tam ekran) | TradingView Lightweight Charts, `assets/templates/tradingview_chart.html` şablonu; `ChartController` OHLCV, zaman dilimi (`1D/1W/1M`), grafik tipi ve göstergeleri (SMA/EMA, Bollinger, RSI, MACD, Golden/Death Cross okları) sağlar. |
| DCA ve strateji testi değer eğrisi | Lightweight Charts (`lw_chart_html.py`, `PlanningController`). |
| Karşılaştırma Lab, Optimizasyon sınırı | Lightweight Charts ve Chart.js (`assets/js/chart.umd.min.js`); denetleyici HTML üretir, QML `WebEngineView` gösterir ([comparison_lab.md](comparison_lab.md)). |
| Hisse 360 finansal dashboard ve ortaklık yapısı | Plotly HTML (`reporting/html/`); yama uygulanmış yerel Plotly JS'i kullanılır, CDN yoktur. |
| Hisse 360 | Denetleyicinin ürettiği geçici HTML dosyaları (`stock_360_html.py`); uygulama kapanırken temizlenir. |
| Küçük çizimler | QML `Canvas` (varlık dağılımı donut'u, treemap, mini sparkline). |

`QtWebEngineQuick.initialize()` `QApplication`'dan önce çağrılır (`ui_qml/app.py`); `app.py` ayrıca `AA_ShareOpenGLContexts` özniteliğini açar (`tests/test_repo_guards.py` bunu denetler). Uygulama Qt Quick Controls "Basic" stilini kullanır (özelleştirilmiş bileşenler yerel stille ezilmesin diye).

## 5. İş Parçacıkları ve Sinyaller

Ana iş parçacığını bloke eden her iş denetleyicide `ThreadPoolExecutor` ile arka planda çalışır:

1. QML bir `Slot` çağırır (ör. `runScan()`).
2. Denetleyici işi `executor.submit(...)` ile başlatır ve `isRunning` özelliğini `true` yapar.
3. İş bitince **iş parçacığından** özel bir Qt sinyali (`_scanCompleted = Signal(object)`) yayılır; sinyal kuyruklu bağlantıyla ana iş parçacığındaki yuvaya (`_apply_results`) ulaşır.
4. Yuva özellikleri günceller ve `notify` sinyalleri QML bağlamalarını yeniler.

Kurallar: arka plan iş parçacığından QML özelliği doğrudan değiştirilmez, `QTimer.singleShot` çağrılmaz. Test ortamında `ImmediateExecutor` ile işler eşzamanlı çalıştırılır.

## 6. Olay Akışı

| Mekanizma | Kullanım |
|---|---|
| `GlobalEventBus.prices_updated` (`dict[int, Decimal]`) | Fiyat güncellemesi (kapanış tamamlama, Dashboard "Fiyatları Güncelle", açılış işleri). Dashboard ve Model Portföy dinler. Boş yük yayınlanmaz. |
| Denetleyici sinyalleri (`dataSynced`, `pricesUpdated`, `portfolioChanged`, `pricesRefreshed`, `systemReset`) | `app.py` içinde bağlanır: sermaye artırımı, temettü, fiyat güncelleme, açılış tamamlama ve sistem yenileme sonrası Dashboard (`reloadPortfolio`) ve Model Portföy (`refreshData`) yenilenir; piyasa senkronu sonrası fiyat ekranları yenilenir. |
| `QSettings` | Tema, otomatik iş işaretleri, son güncelleme zamanları, sohbet geçmişi. |

Canlı fiyat önceliği: EventBus'tan gelen canlı fiyat, sonra `latest_prices`, en son son kapanış (`CurrentPriceResolver`; bkz. [service_portfolio_and_market.md](service_portfolio_and_market.md)). Tarihsel rapor ve backtest yalnızca `daily_prices` kapanışını kullanır.

## 7. Denetleyici Kuralları

- Denetleyici yalnızca `container.<servis>` üzerinden application servisine bağlanır; repository, `sqlite3`, `duckdb`, `sqlalchemy` ve `src.infrastructure` import edilmez (`tests/ui_qml/test_architecture_guards.py`).
- Hisse ve fiyat okuma: `StockLookupService`. Veritabanı istatistiği/bütünlük/yedek: `DatabaseMaintenanceService`. Piyasa düzeltme listesi: `MarketCorporateActionService`. Gemini sağlayıcısı: container'dan enjekte edilen `chat_provider_factory`.
- Servis bulunamazsa (çevrimdışı mod) denetleyici boş durum gösterir ve çökmez; hata kullanıcıya kısa Türkçe metinle yansıtılır, ayrıntı loga yazılır.
- Kullanıcı girdisi denetleyicide doğrulanır: sayılar `number_input.parse_decimal_text` (`1.234,5`, `50.000`, `1234.5`), tarihler `YYYY-AA-GG` veya `GG.AA.YYYY`.
- İşlem girişi (alım/satım) için BIST seans koruması servis katmanındadır (`TradeEntryService`, `ModelPortfolioTradeService`): hafta sonu, tatil ve seans dışı saatte kayıt oluşmaz. Nakit/sermaye hareketleri bu kurala dahil değildir.

## 8. Ekran Ölçeği

`src/qt_compat/scaling.py`, `QApplication` oluşmadan önce Windows'ta %100 üzerindeki ekran ölçeğini ters `QT_SCALE_FACTOR` ile normalize eder (PySide6/Qt6'da %125 ölçekte içeriğin büyümesini önler). Kapatmak için `PORTFOYSIM_DISABLE_QT_SCALE_NORMALIZATION=1` verilir.

## 9. Yeni Sayfa veya Bileşen Eklerken

1. `controllers/` altında denetleyici yaz; `app.py`'de oluştur ve `setContextProperty` ile kaydet.
2. `qml/views/` veya `qml/components/` altında QML yaz; metinleri `Strings.qml`'e ekle; ikonları `Icons.qml`'e kaydet.
3. Sayfa ise `Main.qml` yükleyicisine ve `Sidebar.qml` listesine ekle.
4. Denetleyici ve QML derleme testi yaz (`tests/ui_qml/`); QML'in uyarısız yüklendiğini doğrula.
5. [qml_pages_guide.md](qml_pages_guide.md) ve [log.md](log.md) güncelle.
