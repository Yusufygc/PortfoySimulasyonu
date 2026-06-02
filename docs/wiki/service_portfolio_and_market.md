# Portföy ve Piyasa Verisi (Market Data) Servisleri

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, işlem geçmişinin tutulmasını (`Trade`) ve piyasa verilerinin (`Market Data`) nasıl çekilip işlendiğini açıklar.

## 1. Event-Sourcing ile Portföy Hesaplaması

Geleneksel sistemler, portföyün P&L değerini (realize edilmemiş kâr/zarar) veri tabanında tutmaya meyillidir. Ancak `Portföy Simülasyonu` projesinde veri bütünlüğünü korumak için Event-Sourcing (Olay Kaynağı) mantığı benimsenmiştir:

- Türev değerler (P&L, maliyet) **veritabanında saklanmaz.**
- Kullanıcının "Alış" (BUY) ve "Satış" (SELL) işlemleri (`Trade` objeleri) kronolojik olarak veritabanında tutulur.
- Uygulama açıldığında veya yeni bir işlem eklendiğinde, `Portfolio.from_trades()` çağrılarak tüm işlemler baştan sona işlenir ve portföyün güncel hali sıfırdan hesaplanır.

### Avantajları:
- Bölünme, temettü (Corporate Actions) veya geçmişe dönük işlem düzenlemelerinde veri tutarsızlığı yaşanmaz.
- Tüm hesaplamalar tek bir "Truth" (Gerçek) kaynağına dayanır: İşlem geçmişi.

## 2. Piyasa Verisi (Market Data) ve `YFinanceClient`

Gerçek zamanlı piyasa fiyatları ve geçmiş fiyat (historical prices) verileri `src/infrastructure/market_data/yfinance_client.py` üzerinden YFinance kütüphanesi ile çekilir.

### Eksik Veri ve Tatil Sağlığı
Bir piyasa takip uygulamasında en büyük sorunlardan biri tatil günleri ve fiyat dönmeyen (eksik veri) günleridir.
`MarketDataService` şu sorumlulukları üstlenir:
1. **Tatil Takvimi:** BIST (Borsa İstanbul) takvimi göz önüne alınarak, Cumartesi ve Pazar günleri haricinde veri dönmeyen günleri "Tatil Adayı" olarak sınıflandırır.
2. **Eksik Veri Tespiti:** Seçili hisseler arasında eksik günleri saptar ve arayüze eksik veri sağlığı raporu sunar.
3. **Kapanış Düzeltmeleri:** Bölünme veya temettü sonrası fiyat düzeltmelerini (Adjusted Close) yFinance'ten alır ve veritabanındaki `daily_prices` tablosunu asenkron olarak günceller.

```mermaid
graph TD
    A[UI Fiyat Sağlığı Ekranı] --> B[Eksik Verileri Bul]
    B --> C[YFinance'ten Eksik Günleri Çek]
    C --> D[DailyPrices Tablosuna Yaz]
    D --> E[EventBus: prices_updated Sinyali Yay]
    E --> F[Tüm Açık Ekranları Otomatik Güncelle]
```
## Faz 2 Notu (2026-06-02)

- `PriceLookupService` application katmanında yalnız ticker normalize eder ve `PriceLookupProvider` sonucunu DTO'ya çevirir; YFinance erişimi `YFinancePriceLookupProvider` adapter'ındadır.
- `BackfillService` doğrudan YFinance kullanmaz; fiyat serilerini `IMarketDataClient.get_price_series` portundan alır.
- `PriceDataHealthService` BIST tatil bilgisini `MarketHolidayProvider` üzerinden alır; production adapter `BistHolidayProvider` olarak infrastructure altında konumlanır.
- `PriceUpdateService` ve BIST seans servisi trading-day kararlarını `MarketTradingCalendar` portu ile alır; BIST takvimi container'dan enjekte edilir.

## Faz 2D Notu (2026-06-02)

- `PriceDataHealthService` facade olarak kalır; analiz `PriceHealthAnalyzer`, update/fetch-save `PriceHealthUpdater`, portföy/model trade kapsamı `PriceScopeResolver` ile yürütülür.
- `PriceUpdateService` kapanış fiyatı çekme ve `DailyPrice` üretimini helper'lara ayırır; public result contract değişmedi.
- `PortfolioTimelineValidator` timeline event hazırlama ve event uygulama adımlarını ayırır; retroaktif trade güvenlik davranışı korunur.

## Faz 3 Notu (2026-06-02)

- Infrastructure market adapter'larında fallback hata ailesi `MARKET_DATA_FALLBACK_ERRORS` ile merkezileştirildi; yfinance, urllib, JSON parse ve `MarketDataUnavailableError` kaynaklı beklenen hatalar deterministik fallback'e düşer.
- Repository ve market-data adapter taramasında kontrolsüz `except Exception` kalmadı; beklenmeyen programlama hataları artık sessizce yutulmaz.
- `ScrapedBenchmarkProvider._request_json` invalid JSON durumunu `MarketDataUnavailableError` olarak sarar; TCMB mevduat oranı akışı EVDS erişim hatasında manuel fallback sözleşmesini korur.
- YFinance fiyat lookup ve optimizasyon adapter'ları network/veri hatalarında sırasıyla `None` veya anlamlı hata sonucu üretir; canlı network testleri default pytest koşumuna bağımlı değildir.
