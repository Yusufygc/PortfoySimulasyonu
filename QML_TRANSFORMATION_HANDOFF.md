# Portföy Simülasyonu — QML Dönüşümü Handoff & Devam Kılavuzu

> **Bu Belgenin Amacı:** Bu kılavuz, projenin PyQt5 QWidgets masaüstü mimarisinden modern **PySide6 + Qt Quick (QML)** mimarisine dönüştürülme sürecini, bugüne kadar tamamlanan tüm aşamaları, projenin nihai vizyonunu, bağlayıcı kurallarını ve kalan fazların detaylı uygulama planını açıklar. Başka bir sohbet oturumunda veya yeni bir ajanla çalışmaya başlandığında **doğrudan bu dosya referans alınarak** kalınan yerden kesintisiz devam edilebilir.

---

## 1. Hızlı Başlangıç & Devralma Özeti (Quick Start)

Yeni bir oturum açıldığında sırasıyla şu adımları uygulayın:

1. **Git Branch:** Daima `qml` branch'inde çalışılır.
   ```powershell
   git checkout qml
   git status
   ```
2. **Python Sanal Ortamı:** Tüm komutlarda kesinlikle proje kökündeki sanal ortam kullanılmalıdır:
   ```powershell
   .\venv\Scripts\python.exe -V
   ```
3. **Mevcut Testleri Doğrulama:**
   ```powershell
   .\venv\Scripts\python.exe -m pytest tests/ui_qml/
   ```
   *(Beklenen sonuç: 15/15 test %100 yeşil).*
4. **Uygulamayı QML Modunda Başlatma:**
   ```powershell
   .\venv\Scripts\python.exe app.py --ui=qml
   ```
5. **Veritabanı Durumu:** Sistem harici MySQL gerektirmez. Tüm portföy, hisse, işlem ve 360 bini aşkın tarihsel fiyat verisi yerel `data/portfolio.db` (SQLite) içerisindedir.

---

## 2. Proje Amacı ve Dönüşüm Vizyonu (The North Star)

Bu projenin temel amacı; Borsa İstanbul (BIST) hisse senetleri için geliştirilmiş, zengin finansal hesaplama ve analiz motoruna sahip olan mevcut portföy takip masaüstü uygulamasını:
* **Hantal ve eskiyen PyQt5 QWidgets katmanından kurtarıp**,
* **Donanım hızlandırmalı (OpenGL/DirectX), akıcı 60 FPS animasyonlu, koyu/açık tema uyumlu PySide6 + Qt Quick (QML) arayüzüne taşımak**,
* Ağır harici servis ve MySQL kurulum bağımlılığını sonlandırarak **sıfır kurulumlu, taşınabilir SQLite tabanlı bir mimariye oturtmak**,
* Clean Architecture (Domain ➔ Application ➔ Infrastructure ➔ UI_QML) katmanlarını, event-driven portföy motorunu ve kurumsal işlem mantığını (temettü/bedelli/bedelsiz) koruyarak profesyonel bir masaüstü yatırım terminali seviyesine çıkarmaktır.

---

## 3. Bağlayıcı Kurallar ve Tasarım Standartları (`RULES.md`)

Geliştirme yaparken aşağıdaki kurallar **istisnasız** uygulanır:

### 3.1 Katı Emoji Yasağı (Strict No-Emoji Policy — `RULES.md` Madde 2.1)
* Kod tabanında, arayüzde, QML butonlarında, kartlarda, tablolarda, toast mesajlarında veya başlıklarda **kesinlikle Unicode emoji (`🚀`, `💰`, `📈`, `🔄`, `⚠️`, `✕` vb.) KULLANILMAZ**.
* Emojiler Windows masaüstünde platform/yazıtipi uyumsuzluğuna, dikey hizalama bozulmalarına ve amatör bir görünüme yol açar.

### 3.2 Merkezi SVG İkon Sistemi (`RULES.md` Madde 2.2)
* Tüm görsel semboller `src/ui_qml/assets/icons/` dizinindeki optimize edilmiş vektörel Lucide SVG dosyalarından karşılanır.
* İkonlar `src/ui_qml/qml/theme/Icons.qml` singleton kataloğu üzerinden çekilir.
* QML içinde ikon gösterimi daima `ModernIcon.qml` bileşeni ile yapılır (`ModernIcon { name: "banknote"; size: 16; color: Theme.accent }`). `ModernIcon`, SVG maskelerini Qt Quick Effects `MultiEffect` GPU renklendirmesiyle açık/koyu temaya anında büründürür.

### 3.3 Merkezi Metin & Yerelleştirme Kataloğu (`RULES.md` Madde 2.3)
* Kullanıcıya görünen hiçbir sayfa başlığı, buton etiketi, tablo sütun adı, KPI başlığı veya modal mesajı bileşenler içine **hardcoded yazılmaz**.
* Tüm metinler `src/ui_qml/qml/theme/Strings.qml` singleton kataloğunda toplanır ve oradan çağrılır (`Strings.dashboardTitle`, `Strings.btnRefresh` vb.).

### 3.4 Taşmasız Esnek Düzen (Responsive & Anti-Overflow — `RULES.md` Madde 2.4)
* Hiçbir buton veya araç çubuğu öğesi sabit piksel genişliğine hapsedilerek metin kırpılmasına yol açmamalıdır (`ModernButton.qml` içeriğine göre esner).
* Dinamik veya çoklu liste/etiket barındıran yatay alanlar (örn. hızlı portföy hisseleri butonları, indikatör listeleri), pencere daraldığında taşmayı önleyecek şekilde `Flickable` veya `ScrollView` ile sarılmalıdır.

### 3.5 QML Singleton Kayıt Zorunluluğu (`qmldir`)
* QML'de `pragma Singleton` tanımlanan her dosyanın ait olduğu dizindeki `qmldir` dosyasına kaydedilmesi şarttır (`singleton Icons 1.0 Icons.qml` gibi). Aksi takdirde QML runtime nesneyi çözümleyemez.

### 3.6 SQLite Auto-Increment Kuralı
* MySQL'den aktarılan tablolarda `BIGINT PRIMARY KEY` sütunu SQLite tarafında otomatik `ROWID` alias'ı olmaz (yalnızca `INTEGER PRIMARY KEY` otomatik artar). Yeni hisse veya liste item'ı eklerken `max_id + 1` üreten koruyucu mantık repository'lerde (`sa_stock_repository.py`, `sa_watchlist_repository.py`) korunmalıdır.

---

## 4. Tamamlanan Fazlar ve Yapılan İşler

Şu ana kadar **Faz 0, MySQL-SQLite Göçü, Faz 2, Faz 3, İkon/String Refaktörü ve Faz 4** eksiksiz tamamlanmıştır.

### 4.1 Faz 0 & SQLite Tam Göçü (`commit: e25a851`, `7de5033`)
* `qml` git branch'i açıldı. PySide6 + WebEngine sanal ortamı kuruldu.
* MySQL veritabanı dump'ı `data/portfolio.db` SQLite veritabanına dönüştürüldü (362.158 satır günlük fiyat, hisseler, işlemler, nakit hareketleri eksiksiz aktarıldı).
* SQLAlchemy SQLite yapılandırması (`src/infrastructure/db/db_config.py` - `SQLiteConfig`) ve WAL mod optimizasyonları eklendi.

### 4.2 Faz 2 — QML Dashboard & Portföy Yönetimi (`commit: 2d784ef`, `f72051a`)
* **`DashboardController` (`src/ui_qml/controllers/dashboard_controller.py`):** Canlı portföy özeti, toplam piyasa değeri, toplam kâr/zarar, günlük değişim ve nakit oranı hesaplamaları.
* **`PositionsTableModel` (`src/ui_qml/models/positions_table_model.py`):** Açık pozisyonlar tablosu, fiyat değişimlerinde yeşil/kırmızı canlı yanıp sönme (flash) animasyonları.
* **`AssetAllocationCard.qml`:** QML `Canvas` üzerinde dinamik Donut grafik, hisse ağırlıkları ve nakit dilimleri lejantı (Decimal bölme hatası düzeltildi).
* **Modallar:** Hızlı BIST hisse alım/satım modalı (`QuickTradeModal.qml`) ve nakit yatırma/çekme modalı (`CapitalModal.qml`).
* **`ModernScrollBar.qml`:** Modern, yarı saydam, üzerine gelindiğinde genişleyen kapsül kaydırma çubuğu.

### 4.3 Faz 3 — TradingView Teknik Analiz Laboratuvarı (`commit: 8bb37f4`, `81aac09`)
* **HTML5/JS Motoru (`src/ui_qml/resources/tradingview_chart.html`):** Lightweight Charts v5.2 motoru entegre edildi. Fiyat skalası otomatik uyumlandırma (`autoScale: true`) ve mum gövde/fitil türetimi yapıldı.
* **Çoklu Zaman Dilimleri:** Günlük (`1D`), Haftalık (`1W`), Aylık (`1M`) Pandas resampling mekanizması.
* **Grafik Tipleri:** Mum (`candle`), Çizgi (`line`), Alan (`area`), Bar (`bar`).
* **İndikatör Paketi:** SMA (20, 50, 200), EMA (20), Bollinger Bantları, Multi-pane RSI (14), MACD (12, 26, 9), otomatik Golden/Death Cross görsel sinyal okları.
* **Araç Çubuğu & Tam Ekran:** `TradingViewToolbar.qml` ve ekranın %96'sını kaplayan `ChartFullscreenModal.qml` analiz laboratuvarı.
* İndikatörlerin menüden geri kapatılamaması sorunu `activeIndicators` reaktif özelliği ve çift aşırı yüklemeli slotlarla çözüldü.

### 4.4 Merkezi İkon & String Mimarisi ve Emoji Temizliği (`commit: d3bd578`)
* 52 adet optimize Lucide SVG ikonu `src/ui_qml/assets/icons/` altına yerleştirildi.
* `Icons.qml`, `Strings.qml` ve `ModernIcon.qml` bileşenleri sisteme eklendi.
* Tüm QML bileşenlerindeki emojiler temizlendi; metinler `Strings.qml` içine taşındı.
* Butonların kart dışına taşması engellendi (`TradingViewToolbar`, `DashboardView` hızlı hisse barı `Flickable` yapıldı).

### 4.5 Faz 4 — Çoklu Takip Listeleri (Watchlist) & Mini Sparkline (`commit: 0d80ebb`)
* **`WatchlistController` (`src/ui_qml/controllers/watchlist_controller.py`):** Kullanıcının kayıtlı takip listelerini ("Spek hisseler", "indikatör grubu", "Uzun Vadeli") yönetme, yeni liste oluşturma, silme, hisse ekleme, hisse notu güncelleme.
* **`WatchlistTableModel` (`src/ui_qml/models/watchlist_table_model.py`):** Takip listesi tablosu (Fiyat, yüzde, gün içi aralık barı, 7 günlük mini sparkline serisi).
* **`MiniSparkline.qml`:** QML `Canvas` üzerinde pürüzsüz degrade dolgulu 7 günlük TradingView tarzı mini trend grafiği.
* **Modallar:** `AddStockModal.qml`, `ManageWatchlistModal.qml`, `EditStockNoteModal.qml`.
* **`WatchlistView.qml`:** Sol tarafta çoklu liste seçici kartı, sağ tarafta geniş hisse takip tablosu ve özet KPI çubuğu.
* **Testler:** `tests/ui_qml/test_watchlist_phase4.py` (15/15 test %100 yeşil).

---

## 5. Mevcut Sayfa İndeksleri Durumu (`Main.qml`)

`Main.qml` içerisindeki `StackLayout` indeksleri şu şekildedir:

| İndeks | Sayfa / Görünüm | Durum | İlgili Faz |
|:---:|:---|:---:|:---:|
| **0** | `DashboardView` | **CANLI / AKTİF** | Faz 2 & Faz 3 |
| **1** | `WatchlistView` | **CANLI / AKTİF** | Faz 4 |
| **2** | `Model Portföyler` | *Placeholder* | Faz 6 |
| **3** | `Hisse 360 & Temel Analiz` | *Placeholder* | **Faz 5 (SIRADAKİ ADIM)** |
| **4** | `Karşılaştırma Laboratuvarı` | *Placeholder* | Faz 7 |
| **5** | `Hisse Tarayıcı (Screener)` | *Placeholder* | Faz 7 |
| **6** | `Finansal Planlama & DCA` | *Placeholder* | Faz 8 |
| **7** | `Portföy Optimizasyonu` | *Placeholder* | Faz 9 |
| **8** | `Gemini AI Karar Destek` | *Placeholder* | Faz 10 |
| **9** | `Uygulama Ayarları` | *Placeholder* | Faz 11 |

---

## 6. Kalan Fazlar ve Detaylı Yol Haritası

### 🎯 FAZ 5: Hisse 360 & Temel Analiz Görünümü (SIRADAKİ ÖNCELİKLİ ADIM)
* **Kapsam:**
  - Tek arama kutusuyla (`THYAO`, `ASELS`, vb.) hisse sorgulama.
  - Şirket unvanı, sektör bilgisi, son fiyat ve gün içi özet istatistikler.
  - Finansal Rasyo Rozetleri: F/K, PD/DD, FD/FAVÖK, Temettü Verimi, Özsermaye Kârlılığı (ROE), Net Borç / FAVÖK (sektör ortalamalarıyla kıyaslamalı).
  - Çeyreklik Bilanço ve Gelir Tablosu Görünümü: Net Satışlar, Brüt Kâr, FAVÖK ve Net Kâr trendlerinin çeyreklik karşılaştırmalı çubuk grafiği (`FinancialBarChart.qml` - QML Canvas).
  - KAP Ortaklık Yapısı: Büyük ortaklar, pay oranları ve halka açıklık oranını gösteren pasta/donut grafiği (`ShareholderPieCard.qml`).
* **Kullanılacak Mevcut Servisler:**
  - `container.services.stock_360_service`
  - `container.services.financial_analysis_service`
  - `container.services.shareholder_analysis_service`
* **Geliştirilecek Dosyalar:**
  - `src/ui_qml/controllers/stock_360_controller.py`
  - `src/ui_qml/qml/views/Stock360View.qml`
  - `src/ui_qml/qml/components/RatioCard.qml`
  - `src/ui_qml/qml/components/FinancialBarChart.qml`
  - `src/ui_qml/qml/components/ShareholderPieCard.qml`
  - `tests/ui_qml/test_stock_360_phase5.py`

---

### FAZ 6: Model Portföyler (Sanal Simülasyon & Çoklu Portföy)
* **Kapsam:**
  - Çoklu sanal model portföy oluşturma, düzenleme ve silme.
  - Model portföye sanal hisse alımı/satımı ve nakit ekleme/çekme.
  - Model portföy performansının ana portföy ve BIST 100 ile karşılaştırılması.
* **Kullanılacak Servisler:**
  - `container.services.model_portfolio_service`
  - `container.services.model_portfolio_trade_service`
* **Geliştirilecek Dosyalar:**
  - `src/ui_qml/controllers/model_portfolio_controller.py`
  - `src/ui_qml/qml/views/ModelPortfolioView.qml`
  - Model portföy al/sat ve transfer modalları.

---

### FAZ 7: Karşılaştırma Laboratuvarı & Hisse Tarayıcısı (Screener)
* **Kapsam:**
  - Çoklu varlık kıyaslama (Normalize Baz 100 getiri eğrileri: Portföy vs. BIST 100, Altın, USD, TÜFE).
  - Varlık korelasyon matrisi ve risk metrikleri (Sharpe, Sortino, Beta, Alpha, Maksimum Drawdown).
  - Çoklu Sinyal Tarayıcısı: BIST hisselerini teknik ve temel filtrelere göre tarama (RSI < 30 Aşırı Satım + EMA200 Üzeri, MACD Bullish + Hacim Patlaması, Bollinger Alt Bant Teması).
* **Kullanılacak Servisler:**
  - `container.services.comparison_service`
  - `container.services.screener_service`
  - `container.services.portfolio_analytics_service`

---

### FAZ 8: Finansal Planlama & DCA Simülatörü
* **Kapsam:**
  - Aylık bütçe ve tasarruf hedefleri yönetimi (Gelir/gider kalemleri, birikim hedefleri ilerleme çubukları).
  - DCA (Dolar Maliyeti Ortalaması / Kademeli Düzenli Alım) Simülatörü: "Her ay X TL hisse alsaydım bugün ne olurdu?" tarihsel simülasyonu ve enflasyona karşı reel getiri grafiği.
* **Kullanılacak Servisler:**
  - `container.services.planning_service`
  - `container.services.dca_backtest_service`

---

### FAZ 9: Markowitz Portföy Optimizasyonu Görünümü
* **Kapsam:**
  - Risk profili seçimi (Muhafazakar ➔ Dengeli ➔ Büyüme ➔ Agresif).
  - Verimli Sınır (Efficient Frontier) interaktif saçılım grafiği: Mevcut Portföy, Maksimum Sharpe Portföyü ve Minimum Oynaklık Portföyü noktaları.
  - Rebalance Öneri Tablosu: Hangi hisseden ne kadar azaltılmalı, hangisine ne kadar eklenmeli.
* **Kullanılacak Servisler:**
  - `container.services.optimization_service`
  - `container.services.risk_optimization_bridge_service`

---

### FAZ 10: Gemini AI Karar Destek Danışmanı
* **Kapsam:**
  - QML arayüzüne gömülü interaktif yatırım danışmanı sohbet paneli.
  - Portföyün güçlü ve zayıf yönlerini değerlendiren XAI (Açıklanabilir Yapay Zeka) risk faktörü analizi.
  - Portföydeki hisseler için yapay zeka destekli güncel senaryo analizleri ve piyasa yorumları.
* **Kullanılacak Servisler:**
  - `container.services.gemini_advisor_service`

---

### FAZ 11: Uygulama Ayarları, Tema Seçici ve Dağıtım
* **Kapsam:**
  - Koyu / Açık tema geçişi (`Theme.isDark` dinamik tetikleyici).
  - API Anahtarları (Gemini API, EVDS vb.) yönetimi ve güvenli saklama.
  - SQLite veritabanı yedekleme ve Excel dışa aktarım araçları.
  - Nuitka ile derleme ve bağımsız çalıştırılabilir `.exe` oluşturma hazırlığı.

---

## 7. Yeni Bir Sohbet Başlatıldığında Verilecek Komut / Prompt Örneği

Yeni bir oturum açtığınızda asistana şu talimatı ileterek doğrudan başlayabilirsiniz:

```text
QML_TRANSFORMATION_HANDOFF.md dosyasını incele. 
Faz 0, 2, 3 ve 4 başarıyla tamamlandı. 
Kurallara (RULES.md: strict no-emoji, Icons.qml, Strings.qml, taşmasız düzen) sadık kalarak,
sıradaki aşama olan "FAZ 5: Hisse 360 & Temel Analiz Görünümü" geliştirmesine başla.
```

---

## 8. Önemli Dosya ve Dizin Referansları

* **Giriş Noktası:** `app.py` (`--ui=qml` argümanı ile `src/ui_qml/app.py` çalıştırılır).
* **Veritabanı:** `data/portfolio.db` (SQLite).
* **QML Kök Dosyası:** `src/ui_qml/qml/Main.qml`.
* **Tema ve Sabitler:** `src/ui_qml/qml/theme/` (`Theme.qml`, `Icons.qml`, `Strings.qml`, `qmldir`).
* **Yeniden Kullanılabilir Bileşenler:** `src/ui_qml/qml/components/` (`ModernIcon.qml`, `ModernButton.qml`, `ModernScrollBar.qml`, `MiniSparkline.qml`, vb.).
* **Sayfa Görünümleri:** `src/ui_qml/qml/views/` (`DashboardView.qml`, `WatchlistView.qml`, vb.).
* **Python QML Denetleyicileri:** `src/ui_qml/controllers/` (`DashboardController`, `ChartController`, `WatchlistController`, vb.).
* **Python QML Tablo Modelleri:** `src/ui_qml/models/` (`PositionsTableModel`, `WatchlistTableModel`, vb.).
* **Birim Testleri:** `tests/ui_qml/` (`test_dashboard_phase2.py`, `test_chart_phase3.py`, `test_watchlist_phase4.py`).
* **Wiki & Günlük:** `docs/wiki/log.md`, `docs/wiki/index.md`, `RULES.md`.
