> Ana sayfa: [index.md](index.md) | Sayfa rehberi: [qml_pages_guide.md](qml_pages_guide.md) | Kaynaklar: [service_market_data_providers.md](service_market_data_providers.md)

# Hisse 360 (Temel Analiz ve Genel Bakış)

Hisse 360, tek bir hisse için fiyat, teknik seviyeler, mali tablolar, değerleme rasyoları ve KAP ortaklık yapısını tek ekranda toplar. Yerel veriler anında, dış kaynaklı veriler arka planda ve birbirinden **izole** edilerek yüklenir; biri başarısız olursa diğerleri etkilenmez.

## 1. Servis Katmanı (`Stock360Service`)

`src/application/services/analysis/stock_360_service.py`, mevcut servisleri saran bir facade'dir:

| Boyut | Yöntem | Kaynak |
|---|---|---|
| Genel bakış | `get_overview(ticker)` | Son fiyat, günlük değişim %, hacim, 52 haftalık aralık. Yalnızca yerel veri: DuckDB (tüm BIST) ve SQLite. Pencere `date.today()`'e değil **verideki son bara** göre hesaplanır; verisi eski bir hissede de anlamlı sonuç verir. |
| Teknik seviyeler | `get_technical_levels(ticker)` | RSI14, MACD, SMA50, SMA200, EMA20 (`indicators.py`) ve en yakın destek/direnç (`support_resistance.py`). |
| Mali tablolar | `get_financials(ticker, n_quarters, currency)` | `FinancialAnalysisService.analyze` (İş Yatırım verisi). |
| Ortaklık yapısı | `get_shareholders(ticker, force_refresh)` | `ShareholderAnalysisService.get_history` (KAP). |
| Birleşik | `get_snapshot(ticker)` | Dört boyutu birleştirir; `financials_error` ve `shareholders_error` alanlarıyla izole. AI danışmanı da bunu kullanır. |
| Katalog | `get_catalog_tickers`, `get_company_name`, `get_all_stocks` | DuckDB kataloğu; portföyde olmayan hisselerin adı. |

## 2. Finansal Analiz (`financials/`)

- **`compute_metrics(data)`** çeyrek bazında türev metrik üretir: brüt/FAVÖK/net kâr marjı, FCF ve marjı, Capex/Satış, ROE, ROA, ihracat oranı, net borç/FAVÖK, cari oran, finansal kaldıraç, uzun vadeli borç/varlık, varlık devir hızı, DSO/DIO/DPO ve nakit çevrim süresi (CCC), DuPont ayrıştırması, bedelsiz potansiyeli, Piotroski F-Score, çeyreklik (QoQ) ve yıllık (YoY) değişim. Dönemsel akışlar TTM ve tekil çeyrek olarak ayrıştırılır.
- **`compute_valuation(metrics, snapshot)`**: F/K, PD/DD, FD/FAVÖK, F/S, temettü verimi, piyasa değeri ve firma değeri. Piyasa değeri ve hisse adedi `YFinanceValuationProvider`'dan (1 saat önbellekli) gelir.
- **Enflasyon** (`inflation.py`): TÜFE endeksiyle yıllık enflasyon ve reel büyüme (`real_growth`); TÜFE `EvdsTufeProvider`'dan gelir. Mali tablo alınamazsa `FinancialStatementProviderUnavailable` fırlatılır.
- İş Yatırım yanıtları `data/_cache/financials/` altında 12 saat önbelleklenir.

## 3. Ortaklık Yapısı (KAP)

`ShareholderAnalysisService.get_history` KAP'tan şirketin pay sahipliği tarihçesini alır ve SQLite `kap_companies`, `kap_shareholder_snapshots`, `kap_shareholder_rows` tablolarına yazar (`SQLAlchemyShareholderRepository`). Ticker -> `mkkMemberOid` eşleşmesi için BIST şirket listesi haftalık TTL ile önbelleklenir (`data/_cache/kap/`). Halka açıklık oranı, bilinen payların toplamının 100'den çıkarılmasıyla bulunur.

## 4. Denetleyici (`Stock360Controller`)

`src/ui_qml/controllers/stock_360_controller.py` ve yardımcı modülleri:

| Modül | İş |
|---|---|
| `stock_360_controller.py` | Arama, `currentTicker`, görünüm modu (`viewMode`), finansal sekme (`satis`, ...), tablo türü (`bilanco`...), dönem sayısı (4/8/12/tüm çeyrek), yenileme; dış çağrıları arka plan iş parçacığında çalıştırır. |
| `stock_360_calc.py` | Rasyo ayrıştırma, çeyreklik çubuk grafik, gelir grafiği, DuPont, nakit akışı, tablo satırları ve ortaklık zaman çizelgesi hesapları. |
| `stock_360_formatters.py` | Para birimi, fiyat, hacim biçimi ve donut renkleri. |
| `stock_360_fallback.py` | Dış servis kapalı veya veri eksikken varsayılan/örnek veri ve sektör tahmini. |
| `stock_360_html.py` | Plotly finansal dashboard ve ortaklık HTML'ini geçici dosyaya yazar; çıkışta temizlenir. |

QML bileşenleri: `RatioCard`, `FinancialBarChart`, `FintechStatementsTable`, `FintechDuPontCard`, `FintechCashFlowCard`, `FintechRevenueChart`, `ShareholderPieCard`, `FintechShareholderTimeline`, `FinancialsDashboardView` (WebEngine). Açılış performansı için sayfa ilk ziyarette yüklenir (`ensureLoaded`).

## 5. Bilinen Davranışlar

- Portföyde olmayan hisseler de aranabilir: fiyat DuckDB'den, ad DuckDB kataloğundan gelir.
- Ticker arama, `.IS` uzantılı girdiyi de kabul eder; kanonik biçime çevrilir.
- Mali veri veya KAP erişilemezse ilgili bölüm hata mesajı gösterir; genel bakış ve teknik seviyeler çalışmaya devam eder.
- Tüm BIST için toplu temel analiz taraması yoktur ([roadmap.md](roadmap.md)).

## 6. Testler

`tests/application/services/analysis/test_stock_360_service.py` (orkestrasyon ve hata izolasyonu), `financials/` metrik testleri, `tests/ui_qml/test_stock_360_phase5.py` ve `test_stock_360_modules.py` (denetleyici ve QML derleme).
