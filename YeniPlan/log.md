# YeniPlan Değişiklik Günlüğü

> Ana katalog: [index.md](index.md)
> Bu dosya **yalnızca ekleme** yapılır; en yeni giriş üsttedir. Eski girişler silinmez veya düzenlenmez.
> Başlık biçimi: `## [YYYY-AA-GG] işlem | Konu`

---
## [2026-11-01] uygulama | Aşama 6: haber altyapısı, haber paneli ve global grafik

- Kullanıcı kararları: Google News varsayılan **açık**; çok hisseli KAP kurum bildirimleri varsayılan **gizli**.
- KAP kimlik haritası hatası düzeltildi (`GARAN, TGB` gibi virgüllü kodlar; test eklendi, önbellek v2). Hisse 360 ortaklık yapısı da düzeldi.
- Haber altyapısı: domain modelleri/portlar, RSS+Atom ayrıştırıcı, `RssNewsProvider`/`YahooRssNewsProvider`/`GoogleNewsRssProvider`/`KapDisclosureNewsProvider`, `NewsService` (hata yalıtımı, tekilleştirme, TTL önbellek, eski önbelleğe düşme), `NewsTargetService`, `news_sources` tablosu ve repository, JSON dosya önbelleği. Container'a kayıtlı.
- UI: `NewsController`, `NewsListModel`, `NewsPanel.qml`; Genel Bakış grafik + haber paneli (geniş/dar yerleşim). Görsel anlık görüntü betiğine panel örnek verisi eklendi.
- Genel Bakış grafiği varlık defteri sembollerini (BTC-USD, GC=F, AAPL vb.) çizer; BIST yolu ve karakterizasyon testleri değişmedi.
- Canlı doğrulama: genel RSS 150 haber/0,4 sn; şirket akışı 81 haber/3,1 sn (KAP GARAN dahil).
- Test: tam paket 1678 geçti, 4 xfailed. Kalite ölçümünde yeni ihlal yok (`chart_controller._resample_timeframe` önceden vardı).
- Kalan: Aşama 7 (Ayarlar > Haber Kaynakları: aç/kapa, özel RSS, KAP toplu bildirim seçeneği, bağlantı testi, yenileme aralığı).

---
## [2026-11-01] spike | Aşama 6 öncesi haber kaynakları yoklaması

- **KAP:** `POST /tr/api/disclosure/members/byCriteria` şirket bazlı bildirimleri döndürüyor (ISO tarih zorunlu, çoklu şirket tek istekte, 0,2-1,2 sn); bağlantı `https://www.kap.org.tr/tr/Bildirim/{disclosureIndex}`. Gürültü: ~üçte bir çok hisseli kurum bildirimi ve çoklu `FR` kaydı.
- **Hata bulundu (mevcut kod):** `kap_shareholder_provider._parse_bist_companies` birden fazla borsa kodu olan (`"GARAN, TGB"`) 45 şirketi atlıyor; GARAN dahil KAP kimliği çözülemiyor, Hisse 360 ortaklık yapısı da etkileniyor. Aşama 6'da test ile düzeltilecek.
- **yfinance haberi:** `finance.yahoo.com/xhr/ncp` 404; `get_news` ve `Search.news` sessizce boş. `YFinanceNewsProvider` iptal; yerine Yahoo sembol RSS (AAPL, BTC-USD, GC=F çalışıyor) ve Google News RSS (Türkçe THYAO, gram altın, bitcoin).
- **RSS:** 15 Türkçe + 6 global besleme doğrulandı; 5 adres çalışmıyor (Dünya Finans, Para Analiz, Borsagündem, Yahoo rssindex, KAP RSS). Tarih biçimleri karışık, bazı akışlar genel haber.
- `scripts/probe_news_sources.py` eklendi; notlar `tasarim_notlari/spike_*.md`. 05, 06 ve 01 sayfaları spike sonucuna göre güncellendi.
- Kullanıcı kararı bekleyen: Google News RSS varsayılan durumu ([01](01_mimari_kararlar.md) §6).

---
## [2026-11-01] uygulama | Aşama 5: Portföyüm arayüzü

- Portföyüm tüm rakamlarını `UnifiedPortfolioService`'ten okur (BIST sekmesi dahil; günlük kazanç tam formül). `MyPortfolioController`: KPI'lar, TRY/USD anahtarı, sınıf dilimleri, sekmeler, tablo modeli; `AssetsController`: varlık ekleme (arka plan), işlem kaydı, fiyat yenileme, öneri, kaldırma.
- QML: `HoldingsTable` (eski `OpenPositionsTable` kaldırıldı), `AssetAddModal`, `AssetTradeModal`, `MyPortfolioView` yeniden yazıldı, `AssetAllocationCard` sınıf dilimleriyle beslenir.
- `app.py`: iki denetleyici, `pricesChanged`/`portfolioChanged`/`systemReset`/`dataChanged` bağlantıları, 5 dakikalık otomatik varlık fiyat yenilemesi.
- Test: 4 yeni test dosyası (sunum, iki denetleyici, uçtan uca QML) + duman testi genişletmesi; tam paket 1604 geçti, 4 xfailed.
- Haftalık/aylık getiri kartları yalnızca BIST (etiketlendi); birleşik TWR v2.

---
## [2026-11-01] uygulama | Aşama 4: Birleşik portföy servisi

- `UnifiedPortfolioService.get_summary(display_currency)`: BIST pozisyonları + BIST nakdi + varlık defteri → tek TRY özeti (`UnifiedSummary`): toplam değer, maliyet, K/Z, günlük kazanç, sınıf bazlı dilimler, pozisyon ağırlıkları, TRY/USD gösterim oranı.
- `BistHoldingsReader` (mevcut `PortfolioService` ve `CurrentPriceResolver`), `AssetHoldingsReader` (en yeni fiyat seçimi, güncel kur, gram birimi için `Asset.unit_price`).
- Eksik fiyat veya kur: pozisyon TRY maliyetiyle değerlenir, `is_priced=False`; özet `is_partial` ve `unpriced_symbols` taşır (sessiz atlama yok).
- Container: `unified_portfolio_service`; `build_services` paylaşılan çözümleyici ve arama servisini yerel değişkenlere aldı.
- Test: 36 yeni (domain DTO, servis, container); tam paket 1528 geçti, 4 xfailed.
- Parite (gerçek DB kopyası): toplam değer, maliyet, nakit `DashboardController` ile aynı; günlük kazanç farklı (birleşik tam formül: -14.730 TL; dashboard yaklaşığı: -13.780 TL). Dashboard hesabı değiştirilmedi; karar notu [04_portfoyum_sayfasi.md](04_portfoyum_sayfasi.md) §2.

---
## [2026-11-01] uygulama | Aşama 3: Fiyat ve kur hattı

- `resolve_yf_symbol` (sınıfa duyarlı, `.IS` eklemez), `src/domain/units.py` ortak ons→gram sabiti (iki kopya tek kaynağa indi).
- `IAssetPriceProvider` portu ve `YFinanceAssetPriceProvider` (son fiyat: dakika barı → günlük kapanış yedeği; geçmiş; sembol doğrulama). Container'a `asset_price_provider` olarak bağlı; `AssetLedgerService` doğrulayıcıyı kullanır.
- `AssetMarketCalendar` (kripto 7/24, ABD hisse, CME metal), `AssetPriceRefreshService` (`refresh_latest`, `backfill_history`), `FxRateService` (okuma, ters kur, yenileme, geçmiş).
- Test: 62 yeni (sembol, takvim, kur, yenileme, sağlayıcı ayrıştırma; sahte `yf.download`). Tam paket: 1492 geçti, 4 xfailed. Canlı salt okunur deneme başarılı (BTC-USD, GC=F, AAPL, TRY=X, EURTRY=X).
- Deneme bulgusu: Yahoo günlük kapanışları da float32 kalıntısı taşıyor; fiyatlar 7 anlamlı haneye yuvarlanır.
- Ertelenen (Aşama 4/5): gram değerleme, `pricesChanged` bağlantısı, varlık eklenince geçmiş doldurma orkestrasyonu.

---
## [2026-11-01] uygulama | Aşama 2: Varlık defteri (domain, DB, repository, servis)

- Domain: `Asset`, `AssetClass`, `AssetUnit`, `AssetTrade` (Decimal, kesirli miktar, işlem kuru), `AssetPosition` (ağırlıklı ortalama maliyet, varlık para birimi + TRY), `AssetLedger.from_trades`, `AssetPrice`, `AssetLatestPrice`, `FxRate`.
- DB: `assets`, `asset_trades`, `asset_prices`, `asset_latest_prices`, `fx_rates` tabloları (`Integer` anahtar, `Numeric(28,10)` miktar/fiyat, `uq_assets_class_symbol` vb.). Şema göçü gerekmedi.
- Repository ve portlar: varlık, işlem, fiyat (günlük + son), kur; `IAssetSymbolVerifier` portu (gerçekleştirimi Aşama 3).
- `AssetLedgerService`: ekleme (katalog veya sembol), pasife alma, işlem kaydı/silme (tarih sıralı defter doğrulaması), `get_ledger`. `ASSET_CATALOG`: XAU, XAG, XPT, XPD (ons), BTC, ETH, SOL, XRP.
- Container: dört repository ve `asset_ledger_service` kayıtlı; `test_container_services.py` sahte repo kümesine iki alan eklendi.
- Testler: 67 yeni (domain, repo, servis) + şema ve container testi. Tam paket: 1429 geçti, 4 xfailed. Kalite ölçümünde yeni ihlal yok.
- Karar notları [02_varlik_defteri.md](02_varlik_defteri.md) §0.1.

---
## [2026-11-01] uygulama | Aşama 1: Genel Bakış ve Portföyüm sayfa bölünmesi

- Yeni `src/ui_qml/qml/views/MyPortfolioView.qml` (indeks 10, Sidebar'da 2. sıra): başlık düğmeleri, 4 KPI kartı, varlık dağılımı, haftalık/aylık getiri kartları, açık pozisyonlar tablosu, işlem/sermaye/Excel modalları ve toast.
- Yeni `src/ui_qml/qml/components/OpenPositionsTable.qml`: pozisyon tablosu `DashboardView`'dan taşındı. Satırdaki "Grafik" düğmesi `chartController.loadTicker` + `navigateTo(0)` yapar; satır tıklaması yalnızca `stockDetailController.openStock` açar; "İşlem" `tradeRequested` sinyaliyle üst görünümdeki modalı açar.
- `DashboardView.qml` (Genel Bakış) yalnızca başlık, `PriceStatusChip`, `TradingViewToolbar`, hızlı hisse seçici ve `TradingViewChart` (+ tam ekran modal) taşır; `minContentHeight: 560`.
- `ShellController.PAGE_TITLES[10]`, `Main.qml` tembel yüklemeli Loader, `Sidebar.qml` girişi, `Strings.qml` (`navMyPortfolio`, `myPortfolioTitle/Subtitle`; `dashboardTitle/Subtitle` yeniden yazıldı).
- `dashboardController` adı ve davranışı değişmedi; Portföyüm'e bağlı kalır.
- Testler: `tests/ui_qml/test_my_portfolio_navigation.py` (yeni, 5 test), `test_qml_views_runtime_smoke.py`'ye `DashboardView` ve `MyPortfolioView`. Tam paket: 1360 geçti, 4 xfailed.
- Görsel: `scripts/qml_visual_snapshot.py` iki sayfayı çizer; eski commit ile yerleşim karşılaştırıldı, KPI/tablo/dağılım yerleşimi korundu. Ofscreen ortamda sağ kenar kesilmesi eski sayfada da vardır (artefakt).
- Açık not: Genel Bakış'ta "Hızlı Alım / Satım" düğmesi artık yok; Portföyüm'dedir.

---
## [2026-11-01] yeni-sayfa | YeniPlan klasörü ve Aşama 0 iskeleti

- `YeniPlan/` klasörü açıldı: `index.md`, `log.md` ve 00-08 numaralı konu sayfaları yazıldı, `tasarim_notlari/` oluşturuldu.
- Plan, keşif sonuçlarına (Genel Bakış ve navigasyon, portföy domain ve veri katmanı, haber ve dış veri) dayanır. Kullanıcı kararları [01_mimari_kararlar.md](01_mimari_kararlar.md) içinde.
- Kod değişikliği yok.

---
