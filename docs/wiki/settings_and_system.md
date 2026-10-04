> Ana sayfa: [index.md](index.md) | Sayfa rehberi: [qml_pages_guide.md](qml_pages_guide.md) | Veri: [data_architecture.md](data_architecture.md)

# Ayarlar, Arka Plan İşleri ve Sistem

Bu sayfa Ayarlar sayfasının sekmelerini, uygulama açılışında ve zamanlayıcıyla çalışan otomatik işleri ve `QSettings` anahtarlarını anlatır.

## 1. Ayarlar Sayfası Sekmeleri

| Sekme | Denetleyici | İçerik |
|---|---|---|
| Görünüm & Tema | `SettingsController` | Koyu/açık tema (`Theme.isDark`, `QSettings` `ui/isDarkTheme`). |
| API Anahtarları | `SettingsController` | Gemini ve TCMB EVDS anahtarlarını işletim sistemi sır deposuna (`keyring`; yoksa `.env`) yazar (`persist_api_keys`; çalışan ayarlar yeniden başlatma gerektirmeden güncellenir) ve Gemini anahtarını canlı çağrıyla sınar. |
| Veri Sağlığı & Senkronizasyon | `SettingsController`, `MarketSyncController` | SQLite ve DuckDB dosya boyutu, tablo satır sayıları (hisse, işlem, nakit hareketi, izleme listesi, model portföy, finansal hedef), DuckDB hisse/bar sayısı ve son seans tarihi, bütünlük kontrolü, "Eksik BIST Barlarını Şimdi Senkronize Et". Dosya yolları gösterilir. |
| Dışa Aktarım & Yedekleme | `SettingsController` | Portföy raporunu Excel olarak, tam veri yedeğini JSON olarak (`stocks`, `trades`, `cash_movements`, `watchlists`) masaüstüne (yoksa `reports/`) yazar. |
| Kurumsal Aksiyonlar | `CorporateActionController` | KAP/MKK aday listesi: yenile, kaynak aç, düzenle, yoksay, onayla ve uygula ([service_corporate_actions.md](service_corporate_actions.md)). |
| Fiyat Verisi | `PriceDataController` | Kapsam seçili fiyat sağlığı: analiz, eksikleri tamamla, seçili hisseyi tamamla, son günden güncelle, aralığı sil, raporu kopyala ([service_portfolio_and_market.md](service_portfolio_and_market.md)). |
| Piyasa Düzeltmeleri | `MarketAdjustmentController` | Tüm BIST için veriden tespit edilen sermaye artırımı adayları: tara, onayla (faktör düzenlenebilir), yoksay, yeniden aç ([market_corporate_actions.md](market_corporate_actions.md)). Liste olay sayacı gösterir. |
| Sistem | `SystemController` | Otomatik canlı fiyat yenileme ve sistem sıfırlama (aşağıya bakın). |

Veritabanı istatistiği, bütünlük (`PRAGMA integrity_check` ve DuckDB okuma testi) ve yedek dışa aktarımı `DatabaseMaintenanceService` üzerinden yapılır ([database_maintenance_and_scripts.md](database_maintenance_and_scripts.md)).

## 2. Arka Plan İşleri

| İş | Tetik | Denetleyici / servis |
|---|---|---|
| **DuckDB artımlı senkron** (catch-up) | Açılıştan 5 sn sonra; ayrıca işlem günü kapanış verisi hazır olunca (**18:30**, yarım gün 13:20; Istanbul saati, tatil takvimi) ve elle | `MarketSyncController` -> `MarketDataSyncService.sync_daily_delta`: DuckDB'deki son bar ile son tamamlanmış işlem günü arasındaki eksik günleri yalnızca eksik barlar için indirir; portföy hisselerinin yeni barlarını SQLite'a taşır (`reconcile_sqlite_from_duckdb`); portföy kurumsal aksiyonlarını DuckDB'ye aktarır ve onaylı olayları ham veriye karşı doğrular (çift düzeltme koruması). Bitince `dataSynced` ile Dashboard ve Model Portföy yenilenir; başlıkta senkron rozeti görünür. |
| **Canlı fiyat yenileme** | Açılıştan 6 sn sonra, sonra 5/15/30/60 dk aralıkla (varsayılan açık, 15 dk) | `SystemController` -> `LivePriceRefreshService.refresh_active_prices`; yalnızca BIST seansı açıkken (10:00-18:10); portföy pozisyonları ve izleme listesi hisseleri; `latest_prices`'a yazar ve `prices_updated` yayınlar. |
| **Açılış bakım işleri** | Açılıştan 8 sn sonra, tek iş parçacığında sırayla | `StartupJobsController` |

`StartupJobsController` işleri (gün içinde zaten çalışanlar atlanır; sonuç ve işaretler `QSettings`'te):

1. **Portföy kapanış tamamlama:** kapanış verisi hazır son işlem gününe kadar eksik kapanışlar (`PriceDataHealthService.update_from_latest_to_today`). Hedef gün `BistMarketSessionService.last_completed_trading_day`: 18:30'dan (yarım gün 13:20) sonra bugün, öncesinde önceki işlem günü. BIST dışı pozisyonlar için tek kapanış yoludur.
2. **KAP/MKK aday taraması:** günde bir kez (Istanbul günü).
3. **Golden/Death Cross taraması:** son taramadan 24 saat geçmişse.

Tüm BIST tamamlaması yalnızca `MarketSyncController`'dadır (eskiden açılış işi de aynı `sync_daily_delta`'yı ayrı yürütücüde eşzamanlı çalıştırıyordu).

Sonuçlar küresel toast ile bildirilir (yeni fiyat kaydı, yeni aday, yeni sinyal); hata durumunda kısa uyarı verilir. Yeni fiyat yazıldığında Dashboard/Model Portföy yenilenir.

## 3. Canlı Fiyat Yenileme ve Sıfırlama (`SystemController`)

- Aç/kapa ve aralık (5/15/30/60 dk) ayarı kalıcıdır; "Şimdi Yenile" anında çalıştırır.
- Tekil ticker hataları toast üretmez; art arda genel hata (eşik 3) birikirse kısa uyarı gösterilir.
- **Sistemi sıfırla:** `PortfolioResetService.reset_all` model portföyleri, izleme listelerini, işlemleri, nakit hareketlerini, fiyatları ve hisse kayıtlarını siler. DuckDB piyasa verisi, bütçe/hedefler ve risk profili sıfırlanmaz. Geri alınamaz; onay ister. Sonrasında Dashboard, Model Portföy ve izleme listesi yeniden yüklenir.

## 4. `QSettings` Anahtarları

Kuruluş/uygulama adı `PortfoySimulasyonu`. Başlıca anahtarlar:

| Anahtar | Anlam |
|---|---|
| `ui/isDarkTheme` | Tema |
| `settings/last_auto_price_backfill_at` | Açılış kapanış tamamlama işareti (hedef gün) |
| `settings/last_auto_corporate_action_discovery_at` | Günlük aday taraması işareti |
| `settings/last_auto_technical_scan_at` | Golden Cross tarama zamanı |
| `settings/live_price_refresh_enabled`, `settings/live_price_refresh_interval_minutes`, `settings/last_live_price_refresh_at` | Canlı fiyat yenileme |
| `dashboard/last_price_update_at`, `dashboard/weekly_return_pct`, `dashboard/monthly_return_pct`, `model_portfolios/<id>/last_price_update_at` | Son güncelleme ve dönemsel getiriler (`last_update_store.py`) |
| Sohbet geçmişi anahtarları | AI sohbet oturumları (`QSettingsChatHistoryRepository`) |

Testler `QSettings`'i geçici INI dosyasına yönlendirir; gerçek kayıt defterine yazılmaz.

## 5. Testler

`tests/ui_qml/test_settings_phase11.py`, `test_system_controller.py`, `test_market_sync_controller.py`, `test_group2_corporate_price_startup.py` (açılış işleri), `test_market_adjustment.py`, `tests/application/test_database_maintenance_service.py`.
