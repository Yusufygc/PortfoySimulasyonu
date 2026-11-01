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

### E5 — Alan eksikleri

- İşlem komisyonu ve BSMV: `Trade`/`AssetTrade` ücret alanı, maliyete ekleme, Excel ve TWR'ye yansıtma; `schema_migrations.py` göç 4 (otomatik yedekli).
- [roadmap.md](roadmap.md) §2.8 maddeleri (birleşik TWR, varlıkların optimizasyona girmesi, varlık nakdi) bu aşamadan sonra ele alınır.
- **Kabul:** komisyonlu alım/satım ortalama maliyet ve K/Z'yi elle hesapla eşleşir; eski veritabanı göçle kayıpsız açılır.

### E6 — Özellik modülleri (isteğe bağlı, son)

- `src/application/services/` ve `src/ui_qml/controllers/` altında özellik dilimleri: `portfolio/`, `assets/`, `news/`, `planning/`, `analysis/`, `market/`. Katman kuralları dilim içinde de geçerli; dilimler arası yalnızca uygulama servisi üzerinden.
- Yalnızca E2-E4 bittikten sonra ve kod hareketinin getirisi açıksa yapılır (salt taşıma refaktörü değer şartını sağlamalı, bkz. [code_quality_guardrails.md](code_quality_guardrails.md) §8).

### E2 uygulama notları (2026-11-02)

- **Sapma:** plan, Python mesajlarının QML'de `Strings.message(key, args)` ile çözülmesini öngörüyordu. Bunun için her tüketici QML ve testindeki metin beklentisi değişecekti. Bunun yerine anahtar Python'da çözülür (`msg()`), sinyaller eskisi gibi hazır metin taşır; metin yine tek dosyadadır (`src/ui_qml/messages.py`). Dil değişimi gerekirse çözüm noktası tek yerde (`msg`) kalır.
- **Muaf tutulanlar (67 satır, `# metin-muaf: neden`):** yapay zeka sistem istemleri ve kullanıcı istemi parçaları, HTML/JS grafik şablonları, servis durum değerleri ve eşleme anahtarları (öncelik, dönem kimliği, bilanço kalem adı, ortaklık adı), sorgu niyet desenleri, servis yokken kullanılan demo yedek verisi (`stock_360_fallback`, izleme listesi). Yedek (demo) verinin üretimde gerçekten gerekli olup olmadığı ayrı bir temizlik konusudur.
- **Sayılamayanlar:** mandal Türkçe harf içeren sabitleri sayar; harf içermeyen kullanıcı metni ("Evet", "Metrik", "ORTA" gibi) tespit edilemez, rastlananlar elle kataloğa alındı.
- **Biçim ailesi farkı bilerek korundu:** Hisse 360 (`₺1,234.50 Mr`) ve Portföyüm (`₺1,234.56`) İngilizce ayraçlı kompakt biçim kullanır, `strategy_backtest` ve ana sayfa getirisi `%+1,23` işaretini yüzdeden sonra yazar. Çıktıyı değiştirmemek için `tr_*` ailesine alınmadı; birleştirme ayrı bir görünür-değişiklik kararıdır.
- **Kalan (E2 kapsamı dışı):** `Strings.qml` ile `messages.py` arasında aynı metnin iki yerde bulunmadığını denetleyen test yok.

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
| E2 | Uygulandı (2026-11-02): `presenters/formatting.py` (tek Türkçe biçimleyici, 9 kopya kalktı), `messages.py` (Python metin kataloğu), mandal tavanı 538 -> 0 (67 satır `metin-muaf`). Sapma ve kalanlar aşağıda |
| E3 | Açık |
| E4 | Açık |
| E5 | Açık |
| E6 | Açık (isteğe bağlı) |
