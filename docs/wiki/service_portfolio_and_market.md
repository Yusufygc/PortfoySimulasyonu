# Portföy, Fiyat Akışları ve Nakit

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Veri sahipliği: [data_architecture.md](data_architecture.md)

Bu sayfa ana portföyün nasıl hesaplandığını, işlem ve nakit kurallarını, iki ayrı fiyat akışını ve fiyat verisi sağlığını açıklar. Dış veri kaynakları için bkz. [service_market_data_providers.md](service_market_data_providers.md); kurumsal aksiyonlar ve temettü için [service_corporate_actions.md](service_corporate_actions.md).

## 1. Olay Kaynaklı Portföy

Türev değerler (lot, ortalama maliyet, gerçekleşmiş/gerçekleşmemiş K/Z) veritabanında **saklanmaz**. Kullanıcının `Trade` kayıtları (BUY/SELL) kronolojik olarak tutulur ve her ihtiyaçta `Portfolio.from_trades()` ile baştan işlenir. `Position`, hisse başına lot, toplam maliyet ve gerçekleşmiş K/Z'yi, `Portfolio` ise toplam piyasa değerini ve K/Z'yi hesaplar.

Avantajı: geçmişe dönük işlem, bedelsiz sermaye artırımı veya düzeltme tek doğruluk kaynağından (işlem geçmişi) tutarlı yeniden hesaplanır. Parasal hesaplar `Decimal` ile yapılır.

`build_portfolio_safely()` (`safe_portfolio_builder.py`) işlemleri `(tarih, saat, id)` sırasına koyar ve eldeki lottan fazla satışı geçersiz sayıp ayırır (`InvalidTrade`); böylece bozuk bir kayıt uygulamayı çökertmez, geçerli işlemlerle portföy kurulur.

## 2. İşlem Girişi

`TradeEntryService.submit_trade(TradeRequest)` sırasıyla:

1. Lot ve fiyatın pozitif olduğunu doğrular.
2. **BIST seans koruması:** `BistMarketSessionService` ile tarih/saat açık seansta olmalıdır (normal gün 10:00-18:10, yarım gün 10:00-13:00; hafta sonu, resmi tatil ve seans dışı saat reddedilir). Kural yalnızca hisse alım/satımı içindir; nakit hareketleri kapsam dışıdır. Aynı koruma model portföy işlemlerinde de uygulanır.
3. Alımda o tarih/saatteki nakit bakiyeyi denetler ("yeterli sermayeniz yoktu").
4. Hisseyi bulur; yoksa yalnızca **alımda** `is_valid_bist_ticker` ile doğrulayıp `stocks`'a ekler (kanonik ticker uzantısızdır).
5. `PortfolioService.validate_trade` ile zaman çizelgesini denetler (aşağıya bakın) ve kaydeder.

**Zaman çizelgesi doğrulaması** (`PortfolioTimelineValidator`): geçmişe dönük girilen işlem, kendisinden sonraki işlem ve nakit akışını geçersiz kılıyorsa ("sonraki nakit veya lot akışını geçersiz hale getiriyor") reddedilir. Olaylar `(tarih, saat, sıra, id)` ile sıralanır; aynı anda nakit girişleri (yatırma, temettü) işlemlerden önce uygulanır.

## 3. Nakit Hareketleri

`cash_movements` tablosu üç tür tutar: `DEPOSIT` (yatırma), `WITHDRAW` (çekme) ve `DIVIDEND` (nakit temettü; `stock_id` ile hisseye bağlı). Nakit bakiye hareketlerden ve işlemlerden türetilir (`PortfolioService.get_cash_balance`): yatırma, temettü ve satış nakdi artırır; çekme ve alım azaltır. Eksiye düşmeyi gerektiren geçmiş kayıtlar sıfırda sabitlenir.

- Çekme, bakiyeyi aşıyorsa reddedilir.
- Yatırma/çekme **dış sermaye akışıdır**; zaman ağırlıklı getiri (TWR) hesabında akış olarak ayrılır. Temettü ise getiridir (akış sayılmaz). Bkz. [service_corporate_actions.md](service_corporate_actions.md).
- `CashMovementService.delete_dividend` ve `PortfolioService.validate_cash_removal`, silmenin sonraki alım/çekimi yetersiz nakde düşürüp düşürmediğini denetler.

## 4. Değer ve Getiri Hesapları

| Servis | Görev |
|---|---|
| `ReturnCalcService` | Belirli tarihte portföy değeri (`compute_portfolio_value_on`, eksik fiyatlar son bilinen kapanışla tamamlanır), iki tarih arası getiri, haftalık ve aylık getiri. |
| `PortfolioSeriesBuilder` | Günlük portföy değer serisi ve TWR serisi; nakit akışı olarak yalnızca yatırma/çekme ve (nakit izlenmiyorsa) alım/satım sayılır ([service_analysis.md](service_analysis.md)). |
| `CurrentPriceResolver` | Değerleme için "güncel fiyat" kaynağını seçer (aşağıya bakın). |

## 5. İki Ayrı Fiyat Akışı

| Akış | Tablo | Yazan | Kullanan |
|---|---|---|---|
| **Kapanış (tarihsel)** | `daily_prices` (SQLite, portföy hisseleri) ve DuckDB (tüm BIST) | `PriceUpdateService`, `BackfillService`, `PriceDataHealthService`, `MarketDataSyncService` | Rapor, backtest, fiyat sağlığı, analiz, tarihsel performans |
| **Canlı / gün içi** | `latest_prices` (SQLite, hisse başına tek satır: `price`, `as_of`, `source`, `provider`, `fetched_at`) | `LivePriceRefreshService` | Dashboard ve Model Portföy anlık değerleme |

`CurrentPriceResolver`: canlı fiyatın kullanılıp kullanılmayacağına `src/domain/live_price_rule.live_price_applies` karar verir. Kayıt `intraday` olmalı ve bir işlem gününün seans penceresinde (açılış ile kapanış verisinin hazır olduğu an, Istanbul saati) alınmış olmalı; gece/hafta sonu/seans öncesi kayıt son kapanıştır ve yeni gün sayılırsa günlük değişim %0 görünürdü. Pencere içindeki kayıt son bardan yeni güne aitse kullanılır; son barla aynı güne aitse yalnızca o günün kapanış verisi henüz hazır değilken kullanılır. Aksi halde son kapanış döner. İzleme Listesi aynı kuralı `live_applies` ile kullanır. Günlük değişim için önceki kapanış, seçilen fiyatın gününden **önceki** son geçerli kapanıştır. Eski bir canlı fiyatı yeni kapanışla kıyaslayıp anlamsız değişim üretmemek için bu ayrım yapılır. Ekranlar fiyatı yalnızca bu çözümleyiciyle DB'den okur; EventBus yükündeki fiyat doğrudan ekrana yazılmaz.

- **Hedef tarih kapanış verisi hazır son işlem günüdür** (`BistMarketSessionService.last_completed_trading_day`: 18:30'dan sonra bugün). Açılıştaki otomatik tamamlama bunu kullanır. Dashboard'daki eski "Fiyatları Güncelle" düğmesi kaldırıldı; `PortfolioUpdateCoordinator` artık arayüzden çağrılmıyor.
- `LivePriceRefreshService.refresh_active_prices(scope)`: varsayılan `all_active` kapsamında ana portföy ve model portföylerin açık pozisyonlarını (`PriceDataHealthService.active_stock_ids`) ve tüm izleme listelerindeki hisseleri (`extra_stock_ids_provider`) önce tek toplu istekle (`PriceLookupService.lookup_prices_bulk`: son dakika barı, `as_of` = bar zamanı), gelmeyenleri tekli sorguyla (`lookup_price_for_ticker`) alır, `latest_prices`'a yazar ve `prices_updated` yayınlar. Dakika barı kapanış seansını (18:00-18:10) içermez; bu yüzden 18:00-18:30 arasında son sürekli işlem fiyatı görünür, 18:30'dan sonra günlük kapanış barı esastır. Tek tek ticker hataları sonuçta `errors` listesinde toplanır, diğer hisseleri engellemez; tur 120 sn'lik zaman bütçesini aşarsa kalan hisseler atlanır. `daily_prices` yazmaz.
- Otomatik canlı yenileme `SystemController` zamanlayıcısıyla (5/15/30/60 dk) yalnızca BIST seansı açıkken (işlem günü ve 10:00-18:10) çalışır; 300 sn'yi aşan (takılmış) yenileme bırakılıp yeni yürütücüyle yeniden başlatılır; periyodik tekil hatalar toast göstermez, art arda genel hata birikirse kısa uyarı verilir ([settings_and_system.md](settings_and_system.md)).
- `PortfolioUpdateCoordinator.update_today_prices_and_get_snapshot()` kapanış fiyatlarını günceller, EventBus ile yayınlar ve portföy anlık görüntüsünü döner.

## 6. Fiyat Verisi Sağlığı

`PriceDataHealthService` (facade; `PriceHealthAnalyzer`, `PriceHealthUpdater`, `PriceScopeResolver`) eksik işlem günü kapanışlarını bulur ve tamamlar.

- **Kapsam:** varsayılan yalnızca net açık pozisyonlardır; tamamen satılmış hisseler kapsamdan çıkar (eski fiyatlar silinmez). Kapsam seçenekleri: `Tüm aktif portföyler`, `Ana Portföy`, `Model Portföy: <ad>`. Başlangıç tarihi seçili kapsamdaki hisselerin ilk işlem tarihidir; eksik hesabı her hisse için kendi ilk işlem tarihinden yapılır.
- **Takvim:** `MarketTradingCalendar` ve `MarketHolidayProvider` (BIST tatil takvimi, 2020-2030) kullanılır. Bilinen tatiller beklenen gün sayısına girmez; veri dönmeyen hafta içi günler "tatil adayı" sınıflanır. Dar kapsamda tüm seçili hisseler aynı gün boşsa ama başka aktif kapsamda o gün fiyat varsa gün eksik veri sayılır; tüm evren boşsa heuristik tatil adayı korunur.
- **Aksiyonlar:** analiz, eksikleri tamamla, seçili hisseyi tamamla, son günden son tamamlanmış işlem gününe güncelle, aralığı sil. Arayüz: Ayarlar > Fiyat Verisi (`PriceDataController`).
- Rapor, `PriceDataReportFormatter` ile arayüzden bağımsız HTML veya düz metne çevrilir (panoya kopyalama).
- Model portföy Excel raporu öncesi eksik kapanış denetlenir ([service_reporting_and_export.md](service_reporting_and_export.md)).

## 7. Diğer Servisler

| Servis | Görev |
|---|---|
| `StockLookupService` | Arayüz için salt okunur hisse ve fiyat sorguları (`find_stock`, `is_known_ticker`, `get_price_series(_bulk)`, `get_previous_close`, `get_latest_price_map`, `get_market_bars`, `get_market_company_name`, `verify_ticker_online`). `THYAO` ve `THYAO.IS` aynı kaydı bulur; hata durumunda boş sonuç döner. |
| `MarketIndicatorsService` | Üst şerit: USD/TRY, EUR/TRY, BIST 100, gram altın ve gümüş; alınamayanlar atlanır. |
| `PortfolioMaintenanceService.purge_stock_by_ticker` | Hisseyi ve tüm bağlantılı kayıtlarını kalıcı siler (dikkatli kullanım). |
| `PortfolioResetService.reset_all` | Tüm portföy, fiyat ve hisse verisini sıfırlar (Ayarlar > Sistem). |
| `PriceLookupService` | Ticker normalize eder ve sağlayıcı sonucunu DTO'ya çevirir; `lookup_prices_bulk` sağlayıcı destekliyorsa toplu sorgu yapar. |
| `BackfillService` | Tarih aralığı için fiyat serisini `IMarketDataClient` portundan alıp `daily_prices`'a yazar; hisse tek başına da tamamlanabilir. |

## 8. Model Portföy Sermaye ve Fiyat Kuralları

- Model portföy başlangıç sermayesi korunur; sonradan eklenen/çekilen sermaye `model_portfolio_cash_movements` tablosunda tarih-saatli hareket olarak tutulur. İşlem ve sermaye hareketi aynı zaman çizelgesinde işlenir; aynı anda sermaye hareketi işlemden önce uygulanır.
- Alım ve çekme, o andaki nakde göre doğrulanır; geçmişe dönük hareket sonraki işlemi geçersiz kılıyorsa reddedilir.
- K/Z = `toplam değer - net sermaye`; sermaye eklemek kâr, çekmek zarar sayılmaz.
- Model portföy kendi fiyat düğmesine sahip değildir; canlı fiyat `latest_prices`'a yazılır (`daily_prices` değil) ve `PriceRefreshController.pricesChanged` ile seçili portföy DB'den yeniden okunur. Tarihsel rapor ise yalnızca `daily_prices` kapanışını kullanır.
