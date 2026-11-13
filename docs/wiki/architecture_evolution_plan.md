> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Yol haritası: [roadmap.md](roadmap.md) | Kalite: [code_quality_guardrails.md](code_quality_guardrails.md)

# Mimari Evrim Planı

Durum: **Taslak** (2026-11-01). Clean Architecture korunur; bu plan yeni mimariye geçiş değil, mevcut yapının aşınan yerlerini düzeltme planıdır.

## 0. Neden ve Çıkış Noktası

2026-11-01 QA denetiminde katman sızıntıları, güvenlik ve hesap hataları düzeltildi (bkz. [log.md](log.md)). Kalan sorunlar yapısaldır:

| Sorun | Ölçüm (2026-11-01) |
|---|---|
| Arayüz metni iki yerde | `src/ui_qml/controllers/` içinde ~900 Türkçe metin satırı; `Strings.qml` dışında, tek yerden yönetilemez |
| Büyük denetleyiciler | 4 sınıf eşik dışı: `StockDetailController` 504, `ModelPortfolioController` 461, `Stock360Controller` 455, `PlanningController` 445 etkin satır |
| Fonksiyon borcu | 73 fonksiyon eşik dışı (E1 sonrası); CI tavanında, yeni iş için pay yok |
| Denetleyicide hesap | Biçimlendirme ve küçük hesaplar denetleyicilerde (ör. model portföy ağırlıkları, KPI metinleri) |
| Bileşim kökü testsiz | `src/ui_qml/app.py` kapsamı %0 idi; E1 ile %79 |
| Brüt K/Z | Komisyon/BSMV modellenmiyor |

**Neden yeni mimari değil:** Tek kullanıcılı, yerel veritabanlı masaüstü uygulaması. Katmanlar, olay kaynaklı defter, port/adapter ve DI doğru seçim. Mikroservis, web arka ucu veya tam CQRS bu boyutta yalnızca karmaşıklık ekler.

## 1. Hedef Yapı

```
QML (görünüm, yalnızca bağlama)
  -> ViewModel / denetleyici (durum + sinyal + servis çağrısı; biçimlendirme yok)
       -> Presenter (saf Python: sayı/tarih biçimi, satır sözlükleri, mesaj anahtarları)
  -> Application (komut servisleri + okuma/sorgu servisleri; tek hesap kaynağı)
  -> Domain (modeller, kurallar, portlar)
  <- Infrastructure (portların gerçekleştirimleri; yalnızca bileşim kökünde bağlanır)
```

Kurallar:

- Denetleyici sayı biçimlendirmez, hesap yapmaz, kullanıcı metni üretmez; presenter fonksiyonlarını çağırır.
- Kullanıcıya görünen her metin tek katalogdadır: QML'de `Strings.qml`, Python'da mesaj anahtarı (QML `Strings` üzerinden çözülür).
- Her ekran rakamı tek bir uygulama servisinden gelir (Portföyüm için `UnifiedPortfolioService` örneği).

## 2. Aşamalar

Sıra bağımlılık sırasıdır. Her aşama ayrı commit dizisi, tam test paketi yeşil ve kalite tavanı düşmüş olarak kapanır.

### E1 — Bileşim kökü ve sayısal güvence testleri (küçük, önce)

- `app.py` için offscreen duman testi: `run_qml_app` kurulumunu (denetleyiciler, `setContextProperty`, sinyal bağlantıları) olay döngüsünü başlatmadan doğrulayacak şekilde kurulum fonksiyonuna ayır (`build_ui(engine, container)`), test et.
- TWR ve risk metrikleri için elle hesaplanmış senaryo testleri (yatırma/çekme, ilk gün, tatil, temettü); `sa_portfolio_repository` kapsamını %80 üstüne çıkar.
- **Kabul:** `app.py` kapsamı > %70; TWR senaryoları elle hesapla eşleşir.

### E2 — Presenter katmanı ve tek metin kataloğu

- `src/ui_qml/presenters/` paketi: `money.py`/`percent.py` (tek Türkçe biçimleyici; bugün en az üç kopya var), ekran başına presenter (`portfolio_presenter` örneği zaten var).
- Python mesajları: `src/ui_qml/messages.py` içinde anahtar -> varsayılan metin; denetleyici sinyali anahtar + parametre gönderir, QML `Strings.message(key, args)` ile çözer. Geçiş denetleyici denetleyici yapılır.
- Koruma testi (mandal): denetleyicilerdeki Türkçe metin sayısı her commit'te artamaz, hedef 0 (log mesajları hariç).
- **Kabul:** denetleyicilerde kullanıcı metni 0; biçimleyiciler tek modülde.

### E3 — Büyük denetleyicilerin bölünmesi (E2 ile birlikte)

| Denetleyici | Bölme önerisi |
|---|---|
| `StockDetailController` | `StockDetailViewModel` (okuma), `OrderEntryController` (emir + ön izleme), `StockDetailExportController` (Excel) |
| `ModelPortfolioController` | liste/CRUD, işlem/sermaye, rapor alt denetleyicileri; değerleme `ModelPortfolioQueryService`'e |
| `Stock360Controller` | mevcut yardımcı modüller (`stock_360_*`) üstüne bölüm denetleyicileri (genel bakış, finansal, ortaklık) |
| `PlanningController` | sekme başına denetleyici (bütçe, hedef, DCA, strateji) |

- QML adları (`stockDetailController` vb.) geçiş süresince korunur; alt denetleyiciler özellik olarak açılır.
- **Kabul:** sınıf ihlali 0, fonksiyon ihlali <= 50; CI tavanları buna çekilir.

### E4 — Okuma servisleri (tek hesap kaynağı)

- Model portföy, izleme listesi ve Hisse Detay rakamları için uygulama okuma servisleri (`*QueryService`): değerleme, ağırlık, günlük değişim yalnızca burada.
- Denetleyicilerde `Decimal` aritmetiği kalmaz (koruma testi: `src/ui_qml/controllers` içinde para hesabı deseni).
- **Kabul:** aynı pozisyonun değeri Portföyüm, Hisse Detay ve Excel'de birebir aynı (karakterizasyon testi).

### E5 — Ücretler, ortak nakit havuzu ve gram altın (kararlar 2026-11-02)

Kullanıcı kararları: komisyon ve BSMV ayarlanabilir, varsayılan 0; geçmiş işlemler 0 ücretle kalır; tüm alım-satımlar tek ortak nakit havuzundan yapılır; USD varlık için önce TL ile USD alınır; toplam portföy TL ve USD gösterilir; altın gram bazlı, TL fiyatlı ve TL nakitten; eski varlık işlemleri nakde dokunmaz; yetersiz bakiyede hata verilir (otomatik çevirme yok).

**Alt aşamalar** (her biri ayrı commit dizisi, tam test yeşil):

| Aşama | İçerik | Şema |
|---|---|---|
| E5.1 Ücret | `Trade.fee` ve `AssetTrade.fee` (işlem para biriminde, mutlak tutar, işlem anında ayardan hesaplanıp saklanır). Alımda maliyete eklenir, satışta gelirden düşer. Ayarlar: BIST komisyon %, varlık komisyon %, BSMV % (komisyon üzerinden). Excel, nakit hesabı, emir ön izlemesi, ortalama maliyet ve K/Z ücretli çalışır. | Göç 4: `trades.fee`, `asset_trades.fee` (varsayılan 0) |
| E5.2 Ortak nakit havuzu | Nakit para birimine göre tutulur (TRY, USD). `cash_movements.currency`; `fx_conversions` tablosu (TL <-> USD döviz al/sat, kur, ücret). Varlık alımı varlığın ödeme para biriminden düşer, satışı ekler; bakiye yetmezse "Yetersiz USD nakit, önce Döviz Al" hatası. BIST tarafı TL'de kalır. | Göç 5: `cash_movements.currency`, `fx_conversions`, `asset_trades.cash_linked` (eski kayıtlar 0 = nakde dokunmaz, yenilar 1) |
| E5.3 Gram altın | `Asset.settlement_currency` (ödeme/işlem para birimi; varsayılan fiyat para birimi). Altın: fiyat USD ons (GC=F) -> gram TL = ons x USDTRY / 31,1035, birim GRAM, ödeme TL. Katalogda "Altın (gram)"; eski ons kayıtları olduğu gibi kalır. Gümüş/platin/paladyum aynı yoldan gram yapılabilir. | Göç 5: `assets.settlement_currency` |
| E5.4 Birleşik özet | `UnifiedSummary`: nakit para birimine göre (`cash_by_currency`), toplam değer TL ve USD gösterimi USD nakdi de içerir. | yok |
| E5.5 Arayüz | Ayarlar > Ücretler; Portföyüm nakit kartı (TL/USD bakiyesi), Döviz Al/Sat penceresi, varlık işlem penceresinde ödeme para birimi, bakiye ve ücret ön izlemesi, gram gösterimi. | yok |

**Kurallar:**

- Ücret geçmişi yeniden yazmaz: işlem anındaki oran `fee` olarak saklanır; ayar sonradan değişse eski işlem aynı kalır.
- Nakit bakiyesi olay kaynaklıdır: para birimi başına `hareketler + döviz çevirmeleri + nakde bağlı işlemler`; türev değer saklanmaz.
- Döviz çevirme iç transferdir (dış sermaye akışı sayılmaz, TWR'yi etkilemez); USD nakdin kur kazancı bu aşamada ayrı izlenmez, yalnızca toplam değerde görünür.
- Birleşik TWR, risk ve optimizasyon varlıkları hâlâ kapsamaz ([roadmap.md](roadmap.md) §2.8).
- Göçler otomatik yedekli ve idempotent; eski veritabanıyla göç testi zorunlu.

**Kabul:** komisyonlu alım/satım ortalama maliyet, nakit ve K/Z elle hesapla eşleşir; TL ile USD alıp USD varlık alınca iki para biriminin bakiyesi doğru düşer; yetersiz bakiye hata verir; gram altın TL fiyatı ons x kur / 31,1035 ile elle eşleşir; eski veritabanı göçle kayıpsız açılır.

### E6 — Özellik modülleri (isteğe bağlı, son)

- `src/application/services/` ve `src/ui_qml/controllers/` altında özellik dilimleri: `portfolio/`, `assets/`, `news/`, `planning/`, `analysis/`, `market/`. Katman kuralları dilim içinde de geçerli; dilimler arası yalnızca uygulama servisi üzerinden.
- Yalnızca E2-E4 bittikten sonra ve kod hareketinin getirisi açıksa yapılır (salt taşıma refaktörü değer şartını sağlamalı, bkz. [code_quality_guardrails.md](code_quality_guardrails.md) §8).

### E2 uygulama notları (2026-11-02)

- **Sapma:** plan, Python mesajlarının QML'de `Strings.message(key, args)` ile çözülmesini öngörüyordu. Bunun için her tüketici QML ve testindeki metin beklentisi değişecekti. Bunun yerine anahtar Python'da çözülür (`msg()`), sinyaller eskisi gibi hazır metin taşır; metin yine tek dosyadadır (`src/ui_qml/messages.py`). Dil değişimi gerekirse çözüm noktası tek yerde (`msg`) kalır.
- **Muaf tutulanlar (67 satır, `# metin-muaf: neden`):** yapay zeka sistem istemleri ve kullanıcı istemi parçaları, HTML/JS grafik şablonları, servis durum değerleri ve eşleme anahtarları (öncelik, dönem kimliği, bilanço kalem adı, ortaklık adı), sorgu niyet desenleri, servis yokken kullanılan demo yedek verisi (`stock_360_fallback`, izleme listesi). Yedek (demo) verinin üretimde gerçekten gerekli olup olmadığı ayrı bir temizlik konusudur.
- **Sayılamayanlar:** mandal Türkçe harf içeren sabitleri sayar; harf içermeyen kullanıcı metni ("Evet", "Metrik", "ORTA" gibi) tespit edilemez, rastlananlar elle kataloğa alındı.
- **Biçim ailesi farkı bilerek korundu:** Hisse 360 (`₺1,234.50 Mr`) ve Portföyüm (`₺1,234.56`) İngilizce ayraçlı kompakt biçim kullanır, `strategy_backtest` ve ana sayfa getirisi `%+1,23` işaretini yüzdeden sonra yazar. Çıktıyı değiştirmemek için `tr_*` ailesine alınmadı; birleştirme ayrı bir görünür-değişiklik kararıdır.
- **Kalan (E2 kapsamı dışı):** `Strings.qml` ile `messages.py` arasında aynı metnin iki yerde bulunmadığını denetleyen test yok.

### E3 uygulama notları (2026-11-02)

- **Sapma:** plan alt denetleyicileri QML'e ayrı bağlam adıyla açmayı öngörüyordu. Bunun yerine QML adları ve bağlama yüzeyi değişmeden, iş mantığı Qt'siz modüllere ve mixin sınıflarına ayrıldı: `model_portfolio_valuation`/`model_portfolio_export` (Qt'siz sınıf ve fonksiyonlar), `planning_dca_chart`/`planning_months` (fonksiyon), `stock_360_state` ve `stock_detail_loader`/`stock_detail_actions` (durum ve arka plan işini taşıyan mixin; sinyaller denetleyicide kalır). Sebep: bağlam adı değişimi her QML tüketicisini ve testi etkilerdi, kazanç yalnızca isimdi.
- **Ölçüm kuralı:** `measure_code_quality.py` `@Property` getter'larını sayımdan düşer; getter'ları lambda'ya çevirmek metriği düşürmez, denendi ve geri alındı.
- **Mixin sınırı:** mixin içindeki metotlar `self` üzerinden denetleyici durumuna bağlıdır (`_container`, `_ticker`...). Bu yüzden tam bağımsız birim değildir; bağımsız test edilebilir olanlar (değerleme, dışa aktarım, bütçe ayları, DCA grafiği) fonksiyon/sınıf olarak ayrıldı (`tests/ui_qml/test_controller_helpers.py`). Mixin'lerin Qt'siz bir hizmete dönüştürülmesi E4 ile birlikte ele alınır.
- **Fonksiyon borcu:** hedef olan <= 50 bu aşamada sağlanmadı (72); borç `stock_detail_loader`'a (`_load_main_position_data` 85 satır) ve diğer büyük fonksiyonlara dağıldı. E4'te okuma servisleriyle birlikte erir.

### E4 uygulama notları (2026-11-02)

- **Kapsam:** plan `*QueryService` ailesi öngörüyordu; tek `PositionQueryService` yeterli çıktı (ana portföy, model portföy, fiyat). Hisse Detay pozisyon rakamları, Model Portföy satırları ve emir ön izlemesi buraya/domain'e taşındı; `watchlist_pricing` saf fonksiyonları `src/application/services/market/`a taşındı (denetleyiciden hesap çıktı, davranış aynı).
- **Düzelen hata:** Hisse Detay model portföy bağlamında portföy ağırlığı, özet fiyat haritası verilmeden alındığından yalnızca nakde bölünüyordu.
- **Kabul:** aynı pozisyonun değeri Portföyüm, Hisse Detay ve Excel geçmişinde birebir aynı (`test_same_position_value_in_portfolio_page_detail_and_excel_history`). Excel'in günlük geçmişi gün gün kapanışla çalışır; bugünkü satırı aynı `Position.market_value` ile hesapladığı için eşleşir.
- **Mandal:** `test_controller_money_math_ratchet.py` denetleyicilerdeki `Decimal` aritmetiği ve `* 100` / `/ 100` satırlarını sayar (tavan 34, artamaz). Kalanlar bilinçli ertelendi: Hisse 360 hesap modülleri, optimizasyon yüzde gösterimi, kurumsal aksiyon ve grafik yardımcıları. Bu dosyalar kendi ekranlarının sunum dönüşümüdür; ortak pozisyon rakamı üretmez.
- **Kalan:** mixin'lerin (`stock_detail_loader` vb.) Qt'siz hizmete dönüşümü yapılmadı; izleme listesi canlı fiyat bindirmesi hâlâ denetleyicide karar veriyor (`watchlist_controller`, çözümleyici kuralını çağırır).

## 3. Riskler

| Risk | Önlem |
|---|---|
| Büyük bölmelerde davranış kayması | Karakterizasyon testi önce (JSON/SHA-256), görsel anlık görüntü (`scripts/qml_visual_snapshot.py compare`) |
| QML adlarının değişmesi | Geçiş süresince eski bağlam adları korunur |
| Mesaj anahtarına geçişte eksik metin | Koruma testi: tanımsız anahtar yok, kullanılmayan anahtar yok |
| Komisyon göçü | Otomatik yedek, idempotent göç, eski veriyle göç testi |

## 4. Durum Takibi

| Aşama | Durum |
|---|---|
| E1 | Uygulandı (2026-11-01): `create_controllers` / `wire_controllers` / `build_ui`, `test_app_composition.py` (app.py %79), `test_twr_scenarios.py`, `test_portfolio_repository.py` (%100) |
| E2 | Uygulandı (2026-11-02): `presenters/formatting.py` (tek Türkçe biçimleyici, 9 kopya kalktı), `messages.py` (Python metin kataloğu; B4'te `messages/` paketi), mandal tavanı 538 -> 0 (67 satır `metin-muaf`). Sapma ve kalanlar aşağıda |
| E3 | Uygulandı (2026-11-02): sınıf ihlali 4 -> 0, fonksiyon 73 -> 72; CI tavanı 0 / 72. Sapma ve kalanlar aşağıda |
| E4 | Uygulandı (2026-11-02): `PositionQueryService`, `PositionSnapshot`, `preview_order`; karakterizasyon testi Portföyüm = Hisse Detay = Excel; denetleyici para aritmetiği mandalı (36 -> 34 satır). Sapma ve kalanlar aşağıda |
| E5 | Uygulandı (2026-11-03). E5.1 Uygulandı (2026-11-02): ücret alanları, göç 4, `FeeSettingsService`, Ayarlar > Ücretler, ücretli nakit/maliyet/K/Z/TWR/ön izleme. E5.2 backend Uygulandı: `FxConversion`, `CashPoolService`, `PooledCashMovementRepository`, göç 5. E5.3 Uygulandı: `Asset.trade_currency`, gram altın TL, göç 6. E5.4 (birleşik özette USD nakit) ve E5.5 (Döviz Al/Sat penceresi, nakit kartı, varlık işleminde nakit ve ücret) Uygulandı |
| E6 | Açık (isteğe bağlı) |
| B1 | Uygulandı (2026-11-07): özellik başına servis kaydı (`container_parts/features/`, `ServiceRegistry`), denetleyici kaydı (`controllers/registry.py`) ve bildirilmiş bağımlılıklar (`REQUIRES` + `ServiceView`; 6 denetleyici geçti, kalanlar doğrudan erişim tavanıyla aşamalı) |
| B2 | Uygulandı (2026-11-07): DuckDB tek fiyat yazıcısı, SQLite yansıması (`PriceProjectionService`, `MarketPriceRefresher`, `SinglePriceSourceMigration`), tek yazıcı koruma testi |
| B3 | Uygulandı (2026-11-07): ortak defter okuma noktası `ILedgerReader` / `LedgerSnapshot`; bölünme, aday keşfi ve fiyat sağlığı kapsamı geçti |
| B4 | Uygulandı (2026-11-07): `src/ui_qml/messages/` paketi (anahtar önekine göre 7 modül, yinelenen anahtar hata); `Strings.qml` bilerek bölünmedi |
| B5 | Uygulandı (2026-11-07): `scripts/measure_change_footprint.py`, hedef ve ölçüm [code_quality_guardrails.md](code_quality_guardrails.md) §9 |
