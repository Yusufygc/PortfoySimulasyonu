# Simülasyon ve Backtest Servisleri

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Planlama: [service_planning_optimization.md](service_planning_optimization.md)

Kod: `src/application/services/simulation/`. Üç ayrı iş burada toplanır: (1) kullanıcının gerçek işlem geçmişinin gün gün yeniden oynatılması, (2) DCA backtest, (3) strateji backtest (yeniden dengeleme ve stop-loss/take-profit). Üçü de saf hesap ve orkestrasyon ayrımını izler: saf motor ağsız, durumsuz, IO'suzdur; servis veriyi okur ve doğrular.

## 1. Tarihsel Portföy Simülasyonu

`HistorySimulationService.simulate_history(start, end)` işlemleri en baştan oynatarak her gün için portföy snapshot'ı (K/Z, getiri, açık pozisyon satırları) üretir. Excel raporu (günlük detaylar) bu çıktıyı kullanır. `ModelPortfolioHistorySimulationService` aynısını model portföyler için yapar.

| Bileşen | Sorumluluk |
|---|---|
| `SimulationState` (`history_simulation_state.py`) | Portföy durumu, işlem imleci, son kapanış fiyatları ve baz değerler. |
| `HistoryPositionBuilder` | Her gün için açık pozisyon satırlarını üretir. |
| `HistorySnapshotBuilder` | Günlük ve kümülatif K/Z ile getiri metriklerini hesaplar. |
| `HistorySimulationService` | Koordinatör; BIST takvimini `MarketTradingCalendar` portundan alır. |

Zorlu durumlar (testle korunur):
1. **Hafta sonu ve tatil:** değer sabit kalır; son kapanış ileri taşınır (carry-forward).
2. **Aynı gün çoklu işlem:** gün sonu kapanışına göre nihai durum hesaplanır.
3. **Eksik veri:** önceki geçerli günün fiyatı kullanılır.

Karmaşıklık O(N*M) (N gün, M açık pozisyon): durum günden güne artımlı güncellenir, portföy her işlemde baştan kurulmaz.

`BackfillService` dış kaynağa doğrudan bağlanmaz; fiyat serisini `IMarketDataClient` portundan alır, `DailyPrice` kayıtlarına çevirir ve yazar (aralık veya tek hisse). Aralık silme de buradadır.

## 2. DCA Backtest

`simulate_dca` (`dca_backtest.py`) "geçmişte her ay X TL ekleseydim" senaryosunu çalıştırır: her ayın ilk işlem gününde katkı, sabit ağırlıkla (varsayılan eşit) hisselere bölünür; fiyat eksik günlerde son bilinen fiyat taşınır. Çıktı: portföy değer serisi, toplam yatırılan, nihai değer, hisse bazlı lot, toplam getiri ve katkı sayısı.

`DCABacktestService.run(tickers, aylık_katkı, başlangıç, bitiş, ağırlıklar)` fiyatları ortak okuyucudan alır (`price_series_loader.load_price_series`): **birincil DuckDB piyasa geçmişi** (tüm BIST, sermaye artırımı düzeltmeli), yedek SQLite portföy fiyatları. Planlama > DCA Simülatörü sekmesi bu servisi kullanır; sonuç Lightweight Charts ile çizilir.

## 3. Strateji Backtest

`strategy_backtest.py` (saf) + `StrategyBacktestService` (doğrulama, veri, Markowitz ağırlığı). Planlama > Strateji Testi sekmesi (`StrategyBacktestController`) bunları çağırır. Her simülasyon aynı başlangıç dağılımıyla bir **"al ve tut" taban çizgisi** de hesaplar; böylece stratejinin katkısı doğrudan görülür.

### 3.1 Periyodik yeniden dengeleme

- Başlangıçta ve her N ayda (1, 3, 6, 12) bir, ayın ilk işlem gününde hedef ağırlığa dönülür; başlangıç ayının kendisi dengeleme sayılmaz.
- **Ağırlık yöntemi:** `equal` (eşit) veya `markowitz`. Markowitz için her dengeleme gününde yalnızca **o güne kadarki** son 252 günlük veriden `compute_max_sharpe_weights` (Ledoit-Wolf kovaryans, SLSQP, tek hisse üst sınırı %40) hesaplanır; ileriye bakış yoktur. Isınma verisi için başlangıçtan 420 takvim günü öncesi okunur. En az 60 günlük veri ve 2 hisse yoksa o gün eşit ağırlığa dönülür ve olay listesine "Uyarı" yazılır.
- Dengeleme günü portföy değeri hedef ağırlıklara göre yeniden dağıtılır; komisyon, işlem gören tutar üzerinden düşülür. Olay listesine dengeleme öncesi ağırlık ile hedef ağırlık farkı %0,5'ten büyük hisseler yazılır.

### 3.2 Stop-loss / take-profit

Eşit ağırlıkla alım; her pozisyon **giriş fiyatına göre** günlük kapanışta stop-loss (örn. %10 düşüş) veya take-profit (örn. %30 yükseliş) eşiğine ulaşırsa tüm pozisyon satılıp nakde geçilir ve yeniden alınmaz. Eşiklerden en az biri girilmelidir. Eşik karşılaştırması kayan nokta hatasına karşı küçük bir toleransla yapılır.

### 3.3 Çıktı ve varsayımlar

`StrategyBacktestResult`: strateji ve taban çizgisi değer serileri, nihai değerler, toplam getiri %, maksimum düşüş %, olay listesi (`REBALANCE`, `STOP_LOSS`, `TAKE_PROFIT`, `FALLBACK`), dengeleme ve çıkış sayısı, fiyatı olmayan hisseler.

Varsayımlar (arayüzde de yazılıdır): işlemler günlük kapanıştan yapılır; gün içi dalgalanma ve fiyat boşluğu (gap) modellenmez; kesirli lot; nakit getirisi sıfır; komisyon (varsayılan 0) alım ve satım tutarının oranıdır (%0 ile %10 arası). **Başlangıç, tüm hisselerin fiyatının bulunduğu ilk işlem günüdür**; sonradan işlem görmeye başlayan hisse başlangıcı öteler. Geçmiş performans gelecek getiriyi garanti etmez.

Doğrulama (`StrategyBacktestService`): en az 2 hisse (dengeleme), geçerli ağırlık yöntemi, 1-12 ay aralığı, pozitif sermaye, bitiş > başlangıç, stop-loss > 0 ve < %100, take-profit > 0. Gerçek veride (THYAO/ASELS/BIMAS/FROTO, 2023-2026) bir yeniden dengeleme testi yaklaşık 0,4 sn sürer.

## 4. Ortak Fiyat Okuyucu

`price_series_loader.load_price_series(price_repo, stock_repo, market_history_repo, tickers, start, end)` -> `{tarih: {ticker: kapanış}}`. DuckDB'de olmayan hisse SQLite portföy fiyatlarına düşer (`.IS` uzantılı eşleşmeyi de dener). Hem DCA hem strateji backtest bunu kullanır.

## 5. Testler

`tests/application/test_history_simulation_service.py`, `test_model_portfolio_history_simulation_service.py`, `test_backfill_service.py`; `tests/application/services/simulation/test_dca_backtest*.py`, `test_strategy_backtest.py` (saf motor), `test_strategy_backtest_service.py` (doğrulama, Markowitz, hata durumları); `tests/ui_qml/test_strategy_backtest_controller.py`.

## 6. Kapsam Dışı

Vergi ve işlem günü bazlı komisyon modeli, çok dönemli optimizasyon, stop-loss sonrası yeniden giriş ve gün içi veri yoktur ([roadmap.md](roadmap.md)).
