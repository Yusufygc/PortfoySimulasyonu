# Planlama, Optimizasyon, Risk Profili ve Model Portföyler

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Backtest: [service_simulation.md](service_simulation.md)

Kod: `src/application/services/planning/`. Bu sayfa dört alanı kapsar: finansal planlama (bütçe, hedefler), Markowitz optimizasyonu, risk profili ve model (sanal) portföyler.

## 1. Finansal Planlama (`PlanningService`)

| Konu | Davranış |
|---|---|
| Bütçe | Ay bazlı (`budgets`, benzersiz `month`) gelir ve gider kalemleri (`budget_items`) ve aylık tasarruf hedefi. `get_monthly_analysis` ayın finansal özetini ve otomatik durum mesajını (`Budget.status_message`) verir. |
| Pinleme | Sabit gelir/gider kalemleri "pinlenir" (`budget_pinned_items`, `item_type + name` benzersiz). Bütçesi olmayan aylar için pinli kalemlerden **taslak** üretilir (`get_budget_draft_from_pinned_items`); kayıtlı aylar değiştirilmez. |
| Hedefler | `financial_goals`: ad, hedef tutar, biriken tutar, vade, öncelik (YÜKSEK/ORTA/DÜŞÜK), durum. Ekleme, düzenleme, silme ve katkı ekleme (`add_contribution`). |
| Fizibilite | `analyze_feasibility`: en güncel bütçenin `net_savings_potential` değeri aylık tasarruf gücüdür; her hedef için gereken aylık tutar hesaplanır. Durumlar: `BİLGİ` (aktif hedef yok), `KRİTİK` (tasarruf gücü <= 0), `BAŞARILI` (güç >= toplam ihtiyaç), `YETERSİZ KAYNAK`. |
| DCA | "Her ay X TL alsaydım" geçmiş simülasyonu ([service_simulation.md](service_simulation.md)). |

Arayüz: Finansal Planlama sayfası (`PlanningController`): Bütçe, Hedefler, DCA ve Strateji Testi sekmeleri ([qml_pages_guide.md](qml_pages_guide.md)). Temettü ve nakit akışı bu servisin kapsamında değildir.

## 2. Markowitz Optimizasyonu (`OptimizationService`)

`OptimizationService.optimize_dashboard_portfolio()` ve `optimize_model_portfolio(portfolio_id, price_lookup_func)` mevcut pozisyonlar arasındaki ağırlığı maksimum Sharpe oranına göre dağıtır. Varlık sınıfı (nakit/tahvil) modellenmez; yalnızca portföydeki hisseler arasında çalışır.

- **Veri:** `OptimizationMarketDataProvider` (zorunlu bağımlılık). Üretimde `DuckDBOptimizationMarketDataProvider` 504 günlük düzeltilmiş kapanışı DuckDB'den okur, eksik hissede yfinance sağlayıcısına düşer. Servis doğrudan ağ çağırmaz; sağlayıcı test için sahte olabilir.
- **Getiri modeli:** günlük log getirilerin yıllıklandırılmış ortalaması (252 gün). **Kovaryans:** scikit-learn `LedoitWolf` büzüşmesi (büyük ve karışık varlık havuzlarında kararsızlığı önler).
- **Amaç ve kısıtlar:** SciPy SLSQP ile `-(getiri - risksiz) / volatilite` minimize edilir; ağırlıklar `[0, max_tek_hisse]` aralığında ve toplamı 1'dir. Tek hisse sınırı `max(sınır, 1/n)` ile uygulanır (n küçükken uygulanabilirliği korur). Varsayılan politika (`OptimizationPolicy`): risksiz faiz %30, tek hisse üst sınırı %40, yıl 252 gün.
- **Minimum volatilite noktası:** aynı kısıtlarla doğrudan volatiliteyi minimize eden ikinci bir çözüm (`min_volatility_metrics`).
- **Veri yetersizliği:** en az 2 geçerli hisse ve 60 gün fiyat gerekir; yetersiz hisseler listelenir ve kısmi öneri üretilir. Sıfır volatilite, `NaN/inf` metrikler ve SLSQP başarısızlığı anlamlı hata verir.
- **Sonuç:** `OptimizationResult` (mevcut, optimal ve minimum risk metrikleri; hisse bazlı EKLE/AZALT/TUT önerileri; geçersiz hisseler).
- `compute_max_sharpe_weights(price_df, policy)`: canlı portföyden bağımsız saf fonksiyon; geçmiş backtest'te kullanılır.

### Verimli Sınır ve Rebalance (`frontier_simulation.py`)

| Fonksiyon | Görev |
|---|---|
| `simulate_monte_carlo` | Dirichlet dağılımıyla 1.000 rastgele portföyü vektörel simüle eder. |
| `calculate_efficient_frontier_curve` | Hedef getiri ızgarasında SLSQP ile sınır eğrisini üretir. |
| `calculate_rebalance_plan` | Mevcut ve hedef ağırlıktan fark yüzdesi, parasal fark (TL), aksiyon ve tahmini lot hesaplar. |

## 3. Optimizasyon Arayüzü (`OptimizationController`)

Kaynak seçimi (ana portföy veya model portföy), risk profili seçici (Çok Muhafazakar, Muhafazakar, Dengeli, Büyüme, Agresif, Manuel), tek hisse sınırı kaydırıcısı, risksiz faiz. Hesap `ThreadPoolExecutor` ile arka planda çalışır. Üç sekme: Verimli Sınır (Monte Carlo bulutu, sınır eğrisi; mevcut, maksimum Sharpe ve minimum risk noktaları), Ağırlık Dağılımı, Yeniden Dengeleme. Kaydırıcı kayıtlı profili değiştirmez; yalnızca bu görünüm için geçici bir etiket (`risk_label_override`) üretir. Model portföy optimizasyonu canlı API çağırmaz (`price_lookup_func` verilmez).

## 4. Risk Profili (`RiskProfileService`)

- **Anket:** 4 bölüm (Finansal Durum, Yatırım Hedefi, Risk Toleransı, Bilgi ve Tecrübe) ve 4 boyut: Risk Kapasitesi (%30), Risk Toleransı (%30), Bilgi ve Tecrübe (%20), Hedef ve Likidite (%20). Her seçeneğin puanı vardır; boyut puanları ağırlıklı toplanır (0-100).
- **Tutarlılık düzeltmeleri:** tolerans >= 75 ve kapasite < 45 ise -10; kısa vade ve tolerans >= 70 ise -8; bilgi < 35 ve (skor >= 65 veya tolerans >= 70) ise -10. Sonuç 0-100'e sıkıştırılır; gerekçeler `suitability_notes` içine yazılır. Her sonuçta "yatırım tavsiyesi değildir" notu bulunur.
- **Etiketler:** skor <= 24 Çok Muhafazakar, <= 44 Muhafazakar, <= 64 Dengeli, <= 79 Büyüme Odaklı, üstü Agresif. Her etiketin açıklaması, azami oynaklık ve önerilen varlık dağılımı (`PROFILE_INFO`: nakit, tahvil/bono, fon, hisse, alternatif) vardır.
- **Kalıcılık:** `risk_profiles` tablosu (yanıtlar, boyut puanları, dağılım JSON). Eski (yaş, vade, tepki) şeması için `legacy` hesap yolu ve repository uyumluluğu korunmuştur.
- Arayüz: `RiskQuestionnaireDialog` (Optimizasyon sayfası) ve `RiskProfileController`.

## 5. Risk Profili - Optimizasyon Köprüsü (`RiskOptimizationBridgeService`)

Kayıtlı profil, optimizasyonun tek hisse ağırlık üst sınırını belirler:

| Etiket | Tek hisse üst sınırı |
|---|---|
| Çok Muhafazakar | %8 |
| Muhafazakar | %10 |
| Dengeli | %20 |
| Büyüme Odaklı | %28 |
| Agresif | %35 |

Kayıtlı profil yoksa `Dengeli` varsayılır (`used_default_profile` ile işaretlenir). `optimize_*_with_risk_profile(risk_label_override)` DI'daki paylaşımlı `OptimizationService` politikasını kalıcı değiştirmeden çağrı başına `policy` verir. Sonuçta bilgilendirici `equity_ceiling_pct` (profilin hisse tavanı) da döner; varlık sınıfı kısıtı mekanik olarak uygulanmaz. Yapay zekâ danışmanının `suggest_optimization` aracı bu servisi kullanır.

## 6. Model Portföyler

`ModelPortfolioService` eski API'yi koruyan facade'dir; sorumluluklar ayrılmıştır:

| Servis | Görev |
|---|---|
| `ModelPortfolioAdminService` | Oluşturma, düzenleme, silme, sıralama (`sort_order`). |
| `ModelPortfolioTradeService` + `ModelPortfolioTradeSimulator` | İşlem ve sermaye hareketi doğrulama/kayıt; işlem ve sermaye hareketini aynı zaman çizelgesinde yeniden oynatır, geçmişe dönük hareket sonraki akışı bozuyorsa reddeder; BIST seans koruması uygulanır. |
| `ModelPortfolioSnapshotService` | Portföy özeti ve pozisyon ayrıntıları (fiyat haritasıyla). |

Kurallar: başlangıç sermayesi `initial_cash`; sonradan eklenen/çekilen sermaye `model_portfolio_cash_movements` tablosunda tutulur; K/Z = toplam değer - net sermaye. Fiyat ve rapor kuralları: [service_portfolio_and_market.md](service_portfolio_and_market.md). Model portföyler için sermaye artırımı ve temettü yoktur.

## 7. Testler

`tests/application/test_optimization_service.py` (sıfır volatilite, kısa geçmiş, politika geçersiz kılma), `test_risk_profile_service.py`, `test_risk_optimization_bridge_service.py`, `test_planning_service_budget.py`, `test_model_portfolio_service.py`, `tests/ui_qml/test_optimization_phase9.py`, `test_planning_phase8.py`.
