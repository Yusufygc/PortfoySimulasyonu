# Mimari Belgesi

> Ana sayfa: [index.md](index.md) | Değişiklik günlüğü: [log.md](log.md)

## Genel Bakış

Proje **Clean Architecture** ile yapılandırılmıştır. Bağımlılıklar yalnızca içe doğru akar:

```
┌──────────────────────────────────────────────┐
│  UI  (PyQt5, QSS, pyqtgraph)                │
│    └── Application (Services, DI, EventBus) │
│          └── Infrastructure (SQLAlchemy,    │
│                               YFinance)     │
│                └── Domain (Entities, Ports) │
└──────────────────────────────────────────────┘
```

Hiçbir katman kendisinin üzerindeki katmana doğrudan bağımlı değildir.

---

## Katmanlar

### 1. Domain (`src/domain/`)

Dış bağımlılığı olmayan saf iş mantığı katmanı.

**Modeller (`src/domain/models/`):**

| Model | Sorumluluk |
|-------|-----------|
| `Portfolio` | İşlemlerden pozisyon ve P&L hesaplama (event-sourced) |
| `Trade` | Al/Sat işlem kaydı |
| `Position` | Tek hisse için mevcut durum (miktar, maliyet, piyasa değeri) |
| `Stock` | Hisse kimlik bilgisi (ticker, isim, para birimi) |
| `DailyPrice` | Günlük kapanış fiyatı kaydı |
| `RiskProfile` | Risk anketi sonuçları ve skoru |
| `ModelPortfolio` | Sanal portföy tanımı |
| `OptimizationResult` | Markowitz çıktısı (ağırlıklar, beklenen getiri, risk) |
| `Budget` | Aylık birikim hedefi |
| `Watchlist` | Kullanıcı izleme listesi |
| `CorporateAction` | Sermaye artırımı, temettü gibi kurumsal aksiyonlar |

**Port Arayüzleri (`src/domain/ports/`):**
- `repositories/`: Repository sözleşmeleri (ABC) — Infrastructure bunu uygular
- `services/`: Dış servis sözleşmeleri (piyasa verisi istemcisi vb.)

---

### 2. Application (`src/application/`)

Use case orkestrasyon katmanı. Domain ve Infrastructure'ı bir araya getirir.

**DI Container (`container.py`):**  
Tüm bağımlılıkları tek noktada bağlar. UI ve servisler container üzerinden dependency injection ile erişir.

**Event Bus (`events/event_bus.py`):**  
`GlobalEventBus` — PyQt5 `QObject` sinyalleri üzerine kurulu Pub/Sub sistemi. Arka plan iş parçacıklarından UI'a thread-safe veri iletimi sağlar.

```
Sinyal örnekleri:
  prices_updated   → fiyat güncellemesi (dict: stock_id → Decimal)
  portfolio_changed → portföy değişimi
  trade_added      → yeni işlem eklendi
```

**Servis Modülleri (`services/`):**

| Modül | Sorumluluk |
|-------|-----------|
| `portfolio/` | İşlem girişi, portföy koordinatörü, fiyat güncelleme zincirleme |
| `market/` | Fiyat sorgulama, veri sağlığı kontrolü |
| `analysis/` | Portföy analizi, benchmark karşılaştırması, metrikler |
| `planning/` | Model portföy, optimizasyon, finansal planlama, risk profili |
| `simulation/` | Geçmiş veri backfill, tarihsel simülasyon |
| `reporting/` | Excel dışa aktarma (openpyxl, biçimlendirilmiş çıktı) |
| `corporate_actions/` | Bedelli/bedelsiz sermaye artırımı işlemleri |
| `database/` | Veritabanı yönetim servisleri |
| `watchlist/` | İzleme listesi CRUD |

---

### 3. Infrastructure (`src/infrastructure/`)

Dış dünyayla iletişim katmanı.

**Veritabanı (`db/sqlalchemy/`):**
- `orm_models.py` — SQLAlchemy tablo tanımları
- `repositories/` — Domain port arayüzlerinin SQLAlchemy implementasyonları
- Bağlantı havuzu (connection pool) `.env` üzerinden yapılandırılır

**Temel Tablolar:**

| Tablo | Açıklama |
|-------|----------|
| `stocks` | Ticker, isim, para birimi |
| `trades` | Al/Sat işlemleri (BUY/SELL, miktar, fiyat) |
| `daily_prices` | Günlük kapanış fiyatları |
| `watchlists` / `watchlist_items` | İzleme listeleri |
| `model_portfolios` / `model_trades` | Sanal portföy simülasyonu |
| `budgets` | Aylık birikim hedefleri |
| `risk_profiles` | Risk anketi sonuçları |
| `corporate_actions` | Sermaye artırımı ve temettü kayıtları |

**Piyasa Verisi (`market_data/yfinance_client.py`):**  
YFinance API sarmalayıcısı. BIST tatil takvimi (`calendar/`) entegrasyonu ile gereksiz veri çekimini önler.

**Loglama (`logging/logger_setup.py`):**  
Dönen dosya handler'ı (5 MB × 5 yedek). Çıktı: `logs/app.log`.

---

### 4. UI (`src/ui/`)

PyQt5 tabanlı masaüstü arayüz katmanı.

**Sayfa Listesi (`pages/`):**

| Sayfa | İşlev |
|-------|-------|
| `dashboard/` | Ana portföy özeti, getiri oranları |
| `analysis/` | Çoklu hisse analizi, benchmark grafikleri |
| `stock_detail/` | Tek hisse detay ve geçmiş |
| `model_portfolio_page.py` | Sanal portföy simülasyonu |
| `optimization_page.py` | Markowitz optimizasyon arayüzü |
| `planning_page.py` | Finansal planlama ve hedef takibi |
| `risk_profile_page.py` | Risk anketi ve profil sonucu |
| `watchlist_page.py` | Hisse izleme listesi |
| `settings_page.py` | Tema, BIST tatil ve uygulama ayarları |
| `ai_page/` | Gemini AI entegrasyonu |

**Temel Bileşenler:**

- `main_window.py` — Ana pencere, sayfa yönlendirme
- `theme_manager.py` — QSS dark/light tema sistemi
- `navigation/page_factory.py` — Dinamik sayfa örnekleme
- `worker.py` — QThread sarmalayıcısı (UI'ı dondurmadan arka plan işlemleri)
- `widgets/` — Yeniden kullanılabilir tablo, diyalog, panel, kart bileşenleri
- `styles/` — Modüler QSS stil dosyaları

---

## Veri Akışı: Fiyat Güncellemesi

```
Kullanıcı "Güncelle" butonuna tıklar
    ↓
Worker (QThread) başlatılır
    ↓
PortfolioUpdateCoordinator çalışır:
    1. YFinanceClient → fiyat çek
    2. DailyPriceRepository → DB'ye kaydet
    3. Portfolio metrikleri yeniden hesapla
    4. EventBus.prices_updated.emit({stock_id: fiyat})
    ↓
UI sinyali alır → yalnızca değişen hücreleri günceller
```

---

## Portföy Hesaplama Mantığı

Portföy, işlem geçmişinden **her seferinde yeniden hesaplanır** (event-sourced):

```python
trades = portfolio_repo.get_all_trades()
portfolio = Portfolio.from_trades(trades)
market_value = portfolio.total_market_value(current_prices)
unrealized_pl = portfolio.total_unrealized_pl(current_prices)
```

Türev değerler (P&L, ağırlık, getiri) domain modelinde hesaplanır; veritabanında saklanmaz.

---

## Optimizasyon Motoru

`OptimizationService` Markowitz etkin sınırını SciPy ile çözer:

- **Kovaryans:** Ledoit-Wolf shrinkage tahmini (scikit-learn)
- **Kısıtlar:** Her hisse için min/max ağırlık limiti
- **Çıktı:** Hisse başına önerilen ağırlık, beklenen getiri ve volatilite

---

## Kalite Kapıları ve Modülerlik

Kod kalitesi kapıları için ana kaynak [RULES.md](../../RULES.md#4-kod-kalitesi-refactor-ve-test-kapilari) dosyasıdır. Mimari karar olarak büyük UI sayfaları ve uzun application servis metodları yeni davranış almadan önce modülerleştirilir.

- UI page sınıfları layout ve wiring ile sınırlı kalır; reset, görünüm, veri sağlığı, tablo doldurma ve worker orchestration ayrı panel/component sınıflarına taşınır.
- Application servisleri public API'yi koruyarak orkestrasyon yapar; trade replay, pozisyon üretimi, snapshot/metrik hesabı ve dış API erişimi helper veya adapter sınırlarına ayrılır.
- `SettingsPage` için hedef yapı: `src/ui/pages/settings/` altında reset, appearance ve price data panelleri; ana sayfa yalnızca başlık, tab layout ve geriye dönük proxy yüzeyleri taşır.
- `HistorySimulationService` için hedef yapı: state dataclass, günlük pozisyon builder'ı ve snapshot builder'ı; `simulate_history()` yalnızca akışı koordine eder.
- Refactor kapanışı hedefli testlerle ve ardından tam `pytest tests` koşumuyla yapılır.

---

## Yeni Özellik Ekleme Rehberi

1. **Servis** → `src/domain/ports/` arayüz → `src/application/services/` implementasyon → `container.py` kaydı
2. **Repository** → `src/domain/ports/repositories/` → ORM modeli → `src/infrastructure/db/sqlalchemy/repositories/` → `container.py`
3. **UI Sayfası** → `BasePage` alt sınıfı → `page_factory.py` kaydı → `MainWindow` yönlendirme

Bkz. [index.md](index.md) hızlı başlangıç için, [log.md](log.md) geçmiş değişiklikler için.
