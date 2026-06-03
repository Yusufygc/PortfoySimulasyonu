# Wiki Değişiklik Günlüğü

> Ana katalog: [index.md](index.md) | Mimari: [architecture.md](architecture.md)  
> Bu dosya **yalnızca ekleme** yapılır. Eski girişler hiçbir zaman silinmez veya düzenlenmez.  
> Grep ile son girişler: `grep "^## \[" docs/wiki/log.md | head -10`

---

## [2026-06-03] guncelleme | Uygulama geneli otomatik canli fiyat yenileme

- `LivePriceRefreshService` eklendi; ana + model portfoy acik pozisyon kapsamindaki hisseler icin intraday/guncel fiyatlari `PriceLookupService` ile ceker ve `daily_prices` tablosuna yazmaz.
- `LivePriceRefreshController` MainWindow'a baglandi; otomatik yenileme varsayilan acik, 15 dk aralikli, BIST islem gunu kontrollu ve `Worker + QThreadPool` ile arka planda calisir.
- Ayarlar sayfasina `Otomatik fiyat yenileme` toggle'i ve 5/15/30/60 dk aralik secimi eklendi; degisiklik restart gerektirmeden timer'a uygulanir.
- Model portfoy sayfasi `prices_updated` eventini dinler; manuel model portfoy fiyat yenileme de artik intraday fiyati veritabanina yazmadan bellek/EventBus uzerinden gunceller.
- Dogrulama: hedefli application/UI testleri -> **42 passed**; refactor guard -> **4 passed**; `tests` -> **387 passed**.
- Baglantili sayfalar: [service_portfolio_and_market.md](service_portfolio_and_market.md), [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-03] guncelleme | Portfoy bazli fiyat verisi kapsami

- Ayarlar > Fiyat Verisi Yonetimi icin portfoy combobox kapsami eklendi: tum aktif portfoyler, ana portfoy ve model portfoy secenekleri desteklenir.
- `PriceDataHealthService` analiz, toplu eksik tamamlama ve son gunden bugune guncelleme akislari opsiyonel scope parametresiyle calisir; eski cagrisiz davranis `all_active` kalir.
- Baslangic tarihi secili kapsamdaki ilk acik pozisyon islem tarihine set edilir; `daily_prices` ortak veri kaynagi olarak korunur.
- Dogrulama: hedefli application/UI testleri -> **23 passed**; `tests` -> **374 passed**.
- Baglantili sayfa: [service_portfolio_and_market.md](service_portfolio_and_market.md)

## [2026-06-03] duzeltme | Analiz aktif kapsam ve nakit dahil toplam deger

- Analiz kaynak/filtresi net acik pozisyon kapsamindan uretilir; tamamen satilmis BORSK benzeri hisseler otomatik filtre, holdings genisletmesi ve fiyat uyarilarindan cikarildi.
- Portfoy zaman serisi kapatilmis trade'leri cash replay icin korur; satis nakdi toplam degerde kalir, fiyat uyarilari yalniz analiz araliginda degerleme gereken hisseler icin uretilir.
- Dashboard toplam deger karti nakit + acik pozisyon piyasa degeri sozlesmesine cekildi; stale model portfoy secimi dashboard'a normalize edilir.
- Dogrulama: hedefli application/UI testleri -> **182 passed**; `tests -q` -> **369 passed**.
- Baglantili sayfalar: [service_analysis.md](service_analysis.md), [service_portfolio_and_market.md](service_portfolio_and_market.md)

## [2026-06-02] guncelleme | Model portfoy tutar alani ve dialog standardi

- Model portfoy al/sat dialoguna readonly `Tutar = Lot x Fiyat` alani eklendi; fiyat lookup, lot ve fiyat degisimleri tutari canli gunceller.
- `configure_dialog_behavior(...)` helper'i ile ozel `QDialog` pencerelerinde `?` context-help butonu kapatildi ve Enter/Return primary aksiyona baglandi.
- `DateRangeDialog` eksik buton/layout wiring'i minimal onarildi.
- Dogrulama: widget hedefli testler -> **12 passed**; `tests/ui -q` -> **107 passed**; `tests -q` -> **363 passed**.
- Baglantili sayfa: [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-02] duzeltme | Dashboard aktif fiyat kapsami

- Dashboard fiyat event handler'i `portfolio.total_cost` metodunu formatlamaya gonderdigi icin TypeError uretiyordu; summary hesaplari aktif pozisyonlardan yapilacak sekilde duzeltildi.
- Fiyat guncelleme ve Fiyat Verisi Yonetimi varsayilan kapsami net acik pozisyonlara cekildi; tamamen satilmis ALTNY gibi hisseler otomatik/toplu scope disinda kalir.
- Dogrulama: hedefli application/UI testleri -> **21 passed**; `tests/ui -q` -> **102 passed**; `tests -q` -> **358 passed**.
- Baglantili sayfa: [service_portfolio_and_market.md](service_portfolio_and_market.md)

## [2026-06-02] duzeltme | KAP MKK public fallback ve 404 degrade

- KAP/MKK aday provider'i calismayan `disclosureQuery` endpoint'ine bagimli kalmayacak sekilde public liste/detail fallback akisi ve typed unavailable hatasi ile guncellendi.
- Discovery result `errors` ve `source_unavailable` alanlariyla kaynak okunamama durumunu exception path'e dusmeden UI'a tasir.
- Startup discovery sessiz kalir; manuel `KAP/MKK Yenile` kullaniciya kisa warning gosterir.
- Dogrulama: hedefli provider/application/UI testleri -> **20 passed**; `tests -q` -> **354 passed**.
- Baglantili sayfa: [service_corporate_actions.md](service_corporate_actions.md)

## [2026-06-02] duzeltme | Comparison Lab Plotly WebEngine render

- QWebEngine eski Chromium motorunda Plotly `:focus-visible` insertRule hatasi grafiklerin bos kalmasina ve `Plotly is not defined` hatasina yol aciyordu.
- Comparison Lab Plotly HTML uretimi `plotly_html.py` helper'ina tasindi; shared Plotly JS artik insertRule patch'iyle birlikte temp dosyaya yazilir.
- Inline fallback ve regression testleri eklendi; CDN/canli network bagimliligi yoktur.
- Dogrulama: `tests/ui -q` -> **99 passed**; `tests -q` -> **344 passed**.
- Baglantili sayfa: [comparison_lab.md](comparison_lab.md)

## [2026-06-02] ekle | Bedelli bedelsiz KAP MKK aday otomasyonu

- Bedelli/bedelsiz sermaye artirimlari icin `CorporateActionCandidate` domain modeli, candidate repository portu ve `corporate_action_candidates` ORM tablosu eklendi.
- KAP/MKK provider parser, discovery servisi ve candidate review servisi mevcut `CorporateActionService` uygulama hattina baglandi.
- Ayarlar sayfasina Kurumsal Aksiyonlar sekmesi eklendi; aday listeleme, yenileme, duzenleme, yoksayma, kaynak acma ve onayla-uygula akisi saglandi.
- Startup icin sessiz/gunde bir kez discovery worker'i eklendi; default test suite canlı ağa bağlı kalmaz.
- Baglantili sayfa: [service_corporate_actions.md](service_corporate_actions.md)

## [2026-06-02] duzeltme | MERKO bedelsiz sonrasi gecmis fiyat duzeltmesi

- Sermaye artirimlari icin `daily_prices` gecmisini in-place normalize eden fiyat duzeltme mekanizmasi eklendi.
- MERKO.IS %638,33834 bedelsiz artirimi idempotent script ve DB adjustment alanlariyla onarilabilir hale getirildi.
- Baglantili sayfa: [service_corporate_actions.md](service_corporate_actions.md)

## [2026-06-02] guncelleme | Faz 6 production guvenlik build ve operasyon

- DB pool ayarlari `DB_POOL_RECYCLE_SECONDS` ve `DB_POOL_PRE_PING` env anahtarlariyla yonetilebilir hale getirildi; varsayilanlar eski davranisi korur.
- Logger `LOG_DIR`, `LOG_LEVEL`, `LOG_CONSOLE_LEVEL` ve `LOG_FILE_LEVEL` ile env kontrollu oldu; hassas env degerleri log formatter tarafinda maskelenir.
- `scripts/build_preflight.py` eklendi; Python, pinned requirements, Nuitka, icon, `.env.example`, pytest marker ve `dist/.env` guard kontrollerini yapar.
- `build_nuitka.bat` fail-fast hale getirildi ve build oncesi preflight calistiracak sekilde guncellendi.
- GitHub Actions workflow'u eklendi: Windows + Python 3.11 uzerinde dependency install, `pip check`, test collection ve default test suite calisir.
- Production guard testleri eklendi: secret literal taramasi, logger hardening, DB engine pool config ve build preflight statik kontrolleri.
- Baseline: `pip check` temiz, `tests -q` -> **305 passed**; aktif ortamda `python -m nuitka --version` -> **No module named nuitka** production blocker olarak kaydedildi.
- Etkilenen dosyalar: `.env.example`, `build_nuitka.bat`, `.github/workflows/tests.yml`, `scripts/build_preflight.py`, `config/settings_loader.py`, `src/infrastructure/db/`, `src/infrastructure/logging/`, `tests/infrastructure/`, `README.md`, `docs/wiki/`
- Baglantili sayfalar: [project_build_and_deployment.md](project_build_and_deployment.md), [testing_strategy.md](testing_strategy.md)

---

## [2026-06-02] guncelleme | Faz 5 test QA ve regresyon guardlari

- `pytest.ini` ile `ui`, `integration`, `network` ve `manual` marker'lari tanimlandi; default test akisi manual/network kontrolleri disarida birakir.
- `tests/conftest.py` ortak test fixture yuzeyiyle genisletildi: `qapp`, `drain_qt_events`, `fake_event_bus`, `fixed_today` ve domain builder fixture'lari.
- UI async testlerinde elle `QThreadPool.waitForDone`/`processEvents` kullanimi ortak helper'a tasindi; tarih bagimli comparison testi sabit tarih fixture'iyle deterministik hale getirildi.
- `tests/ui/test_refactor_guards.py` eklendi: UI icinde ozel `QThread`, dogrudan fiyat event emit'i, yeni buyuk UI sinifi ve otomatik testlerde canli HTTP cagrisi guard'lari.
- Manuel benchmark kontrolu `manual + network` marker'lariyla default suite disinda belgelendi.
- Dogrulama: `pytest --collect-only -q` -> **305 collected**; `tests/ui -q` -> **91 passed**; `tests/domain tests/application tests/infrastructure -q` -> **214 passed**.
- Etkilenen dosyalar: `pytest.ini`, `tests/conftest.py`, `tests/ui/`, `tests/infrastructure/market_data/test_benchmark_fetch_manual.py`, `docs/wiki/testing_strategy.md`, `docs/wiki/ui_architecture_and_events.md`
- Baglantili sayfalar: [testing_strategy.md](testing_strategy.md), [ui_architecture_and_events.md](ui_architecture_and_events.md)

---

## [2026-06-02] guncelleme | Faz 4 UI worker EventBus ve tema refactor

- `GlobalEventBus` public import yuzeyi `src.application.events` altinda sabitlendi; `prices_updated` payload sozlesmesi `dict[int, Decimal]` olarak testlendi.
- AI, Gemini ve optimizasyon async akislarinda ozel `QThread` siniflari ortak `Worker + QThreadPool` modeline tasindi; stale-result guard eklendi.
- UI fiyat guncelleme yayinlari `publish_prices_updated` helper'i altinda teklesitirildi; bos payload emit edilmiyor ve Decimal fiyatlar korunuyor.
- `DashboardActions`, `ComparisonDataManager` ve `StockDetailPage` icindeki buyuk orchestration sorumluluklari handler/helper siniflarina ayrildi.
- Inline stylesheet kullanimi QSS `cssClass` sistemine tasindi; tema token ve inline style guard testleri guncellendi.
- Etkilenen dosyalar: `src/application/events/`, `src/ui/worker.py`, `src/ui/pages/`, `src/ui/shared/`, `src/ui/styles/features/comparison.qss`, `tests/ui/`, `tests/application/test_event_bus.py`
- Baglantili sayfalar: [ui_architecture_and_events.md](ui_architecture_and_events.md), [testing_strategy.md](testing_strategy.md)

---

## [2026-06-02] guncelleme | Faz 3 infrastructure transaction ve adapter hardening

- SQLAlchemy repository yazma yollarinda ortak `commit_or_rollback` ve `commit_refresh_or_rollback` helper'lari kullanilmaya baslandi; repository tarafindaki kontrolsuz `except Exception` bloklari kaldirildi.
- `SQLAlchemyModelPortfolioRepository` icindeki ulasilamayan ORM mapper kodu `_to_orm_portfolio` metoduna tasindi ve regression testi eklendi.
- Market-data adapter hata sozlesmesi `MARKET_DATA_FALLBACK_ERRORS` ile merkezilestirildi; yfinance, urllib, JSON parse ve `MarketDataUnavailableError` kaynakli beklenen fallback davranislari testle sabitlendi.
- `ScrapedBenchmarkProvider` invalid JSON'u `MarketDataUnavailableError` olarak sarar; TCMB mevduat oranlari EVDS erisim hatasinda manuel fallback sozlesmesini korur.
- Statik kabul: `src/infrastructure/db/sqlalchemy/repositories` ve `src/infrastructure/market_data` altinda kontrolsuz `except Exception` kalmadi; secret log taramasinda deger sizdiran log bulunmadi.
- Dogrulama: `tests/infrastructure -q` -> **25 passed**; `tests/domain tests/application tests/infrastructure -q` -> **212 passed**; `tests -q` -> **292 passed**. Yalniz `.pytest_cache` permission warning devam ediyor.
- Etkilenen dosyalar: `src/infrastructure/db/sqlalchemy/repositories/`, `src/infrastructure/market_data/`, `tests/infrastructure/`
- Baglantili sayfalar: [database_schema_and_orm.md](database_schema_and_orm.md), [service_portfolio_and_market.md](service_portfolio_and_market.md)

---

## [2026-06-02] guncelleme | Faz 2D application servisleri yapisal refactor

- `PriceDataHealthService` facade olarak inceltildi; analiz, update/fetch-save ve fiyat kapsami cozumleme sorumluluklari `PriceHealthAnalyzer`, `PriceHealthUpdater`, `PriceScopeResolver` bileşenlerine ayrildi.
- `AnalysisService` DTO orchestration seviyesine indirildi; bundle kurma, para birimi donusumu ve karsilastirma portfoy serisi uretimi ayri servis siniflarina tasindi.
- Reporting tarafi parcalandi: Excel append/dedup/backup mantigi `ExcelAppendMerger`, dashboard istatistikleri `ExcelDashboardStatsCalculator`, chart uretimi `ExcelChartFactory` tarafindan yurutuluyor.
- Simulation builder ve servislerinde gunluk dongu, pozisyon metrikleri ve snapshot return/status hesaplari helperlara ayrildi; model portfoy trade replay mantigi `ModelPortfolioTradeSimulator` sinifina tasindi.
- Application services statik esik taramasi temiz: 300+ satir sinif ve 50+ satir fonksiyon kalmadi. Boundary taramasi da temiz: direct `yfinance`, concrete `EvdsClient`, application icinde `src.infrastructure`, `_analysis_current_value` ve runtime `setattr` kalmadi.
- Kalan `except Exception` noktalari fallback contract olarak siniflandirildi: market/EVDS veri akisi hata durumunda warning/result uretiyor, Excel corrupt workbook okumasi backup + fresh write davranisini koruyor, optimization price lookup callback hatasi fiyat fallback'ine dusuyor.
- Dogrulama: `C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe -m pytest tests -q` -> **284 passed**, yalniz `.pytest_cache` permission warning.
- Etkilenen dosyalar: `src/application/services/market/`, `src/application/services/analysis/`, `src/application/services/reporting/`, `src/application/services/simulation/`, `src/application/services/planning/model_portfolio_trade_service.py`, `src/application/services/portfolio/`, `src/application/services/corporate_actions/`, `tests/application/`
- Baglantili sayfalar: [service_portfolio_and_market.md](service_portfolio_and_market.md), [service_analysis.md](service_analysis.md), [service_reporting_and_export.md](service_reporting_and_export.md), [service_simulation.md](service_simulation.md), [service_planning_optimization.md](service_planning_optimization.md), [service_corporate_actions.md](service_corporate_actions.md)

---

## [2026-06-02] guncelleme | Faz 2 application servisleri boundary ve refactor duzeltmeleri

- Corporate action uygulama akisi failure-safe siraya alindi: sentetik trade insert basarisiz olursa action `applied` isaretlenmiyor; regression testi eklendi.
- Application servislerindeki dogrudan YFinance, EVDS concrete client ve infrastructure calendar importlari port/provider arkasina tasindi; gercek adapterlar `src/infrastructure/` altinda container ile enjekte ediliyor.
- `PriceLookupService`, `BackfillService`, `OptimizationService`, `PriceDataHealthService`, analysis benchmark ve BIST calendar kullanan servisler DI tabanli hale getirildi.
- `OptimizationService` provider zorunlu dependency oldu; kisa veri, SLSQP basarisizligi ve zero-volatility/NaN metrik guard testleri eklendi.
- `AnalysisService` domain position nesnelerine runtime attribute eklemeyi birakti; current value bilgisi analysis snapshot map uzerinden tasiniyor.
- `PlanningService.analyze_feasibility` ve `ModelPortfolioTradeService.add_trade` helperlara bolundu; public DTO/float cikti sozlesmesi korundu.
- Excel append on kontrolundeki silent `except Exception: pass` kaldirildi; dosya yoksa fresh write, OS-level erisim sorunu log davranisi ve corrupt workbook backup akisi korundu.
- Dogrulama: `C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe -m pytest tests -q` -> **284 passed**, sadece `.pytest_cache` permission warning.
- Etkilenen dosyalar: `src/application/services/market/`, `src/application/services/simulation/`, `src/application/services/planning/`, `src/application/services/analysis/`, `src/application/services/portfolio/price_update_service.py`, `src/application/services/reporting/excel_report_builder.py`, `src/application/container_parts/`, `src/infrastructure/market_data/`, `src/infrastructure/calendar/`, `tests/application/`
- Baglantili sayfalar: [service_portfolio_and_market.md](service_portfolio_and_market.md), [service_planning_optimization.md](service_planning_optimization.md), [service_analysis.md](service_analysis.md), [service_simulation.md](service_simulation.md), [service_reporting_and_export.md](service_reporting_and_export.md), [service_corporate_actions.md](service_corporate_actions.md)

---

## [2026-06-01] güncelleme | Faz 0 sistem omurgası ve build güvenliği düzeltmeleri

- Build script gerçek `.env` dosyasını exe içine gömmeyecek şekilde güncellendi; build bağımlılıkları `requirements-build.txt` ile pinli hale getirildi.
- `docs/wiki` klasörünün Git tarafından ignored kalmasına neden olan `/docs` kuralı kaldırıldı; Obsidian metadata için dar ignore kuralı eklendi.
- `AppContainer` repository, market/client ve servis factory parçalarına ayrıldı; EventBus uygulama events modülüne taşındı ve eski UI import yolu geriye uyumlu re-export olarak bırakıldı.
- `config/settings_loader.py` DB dışındaki AI ve market ayarlarını da doğrulayan `AppSettings`, `AISettings` ve `MarketSettings` yapılarıyla genişletildi.
- Etkilenen dosyalar: `build_nuitka.bat`, `requirements.txt`, `requirements-build.txt`, `.gitignore`, `app.py`, `config/settings_loader.py`, `src/application/container.py`, `src/application/container_parts/`, `src/application/events/`, `docs/wiki/project_build_and_deployment.md`, `docs/wiki/architecture.md`
- Bağlantılı sayfa: [project_build_and_deployment.md](project_build_and_deployment.md)

## [2026-06-01] ingest | Kapsamlı Modüler Wiki Geçişi Faz 2 (Tüm Modüller)

- Uygulamanın kalan tüm özellikleri (Excel Raporlama, Kurumsal Aksiyonlar, Watchlist, Test Stratejisi, DB Bakımı ve Derleme süreçleri) bağımsız modüler wiki sayfalarına taşındı.
- Etkilenen dosyalar: `docs/wiki/service_reporting_and_export.md`, `docs/wiki/service_corporate_actions.md`, `docs/wiki/service_watchlist.md`, `docs/wiki/database_maintenance_and_scripts.md`, `docs/wiki/testing_strategy.md`, `docs/wiki/project_build_and_deployment.md`


## [2026-06-01] ingest | Kapsamlı Modüler Wiki Geçişi ve Yeni Dosyalar

- Tüm servislerin detaylı teknik özellikleri (optimizasyon, simülasyon, ui_architecture, db vb.) token tasarrufu sağlaması için parçalanarak modüler `.md` dosyalarına aktarıldı.
- Eski, şişmiş `architecture.md` dosyası bir Router (Yönlendirici) paneli haline getirildi ve yeni oluşturulan 7 modüler sayfaya bağlandı.
- Etkilenen dosyalar: `docs/wiki/service_planning_optimization.md`, `docs/wiki/service_simulation.md`, `docs/wiki/service_analysis.md`, `docs/wiki/service_portfolio_and_market.md`, `docs/wiki/ui_architecture_and_events.md`, `docs/wiki/database_schema_and_orm.md`, `docs/wiki/ai_integration.md`, `docs/wiki/architecture.md`, `docs/wiki/index.md`


## [2026-06-01] lint | Dökümantasyon sağlık kontrolü, çapraz referanslama ve token optimizasyonu

- Projedeki tüm wiki dosyaları (`index.md`, `architecture.md`, `comparison_lab.md`, `Plans.md`) gözden geçirilerek dökümantasyon sağlığı doğrulandı.
- Gelecekteki LLM oturumlarının bağlam kazanmasını hızlandırmak ve token maliyetini optimize etmek adına gereksiz açıklamalardan arındırılarak şematik tablolara, Mermaid diyagramlarına ve doğrudan kod dosyalarına yönlendiren tıklanabilir `file://` linklerine dönüştürüldü.
- Tarihsel tasarım spesifikasyonları (`analizSayfasi/` altındaki 4 aşama belgesi) ana dizin olan `index.md` dosyasına ve `comparison_lab.md` belgesine çapraz referanslarla bağlandı.
- Gelecek teknik borçlar, code review ihtiyaçları ve yol haritası `Plans.md` dosyası altında genişletilerek yapılandırıldı.
- Bağlantılı sayfalar: [index.md](index.md), [architecture.md](architecture.md), [comparison_lab.md](comparison_lab.md), [Plans.md](Plans.md)

---

## [2026-06-01] güncelleme | Karşılaştırma Laboratuvarı gelişmiş görsel ve grafik-özelinde özelleştirme

- Grafik Bilgi Kartlarının (`ChartInfoCard`) yazı tipi boyutları iki katına çıkarıldı, parlak neon mavi (`#00ffff`), neon sarı (`#fbbf24`) ve parlak beyaz renk şeması uygulandı.
- Sayfadaki emojiler tamamen kaldırılarak `IconManager` üzerinden Lucide SVG vektör ikon entegrasyonu sağlandı (AI bot ikonu, info ikonu, chart ikonları vb.).
- Her bir grafik için bağımsız çalışan portföy içi kıyaslama özelliği eklenerek grafik özelinde filtreleme yapılması sağlandı.
- Grafik-özelinde filtrelerin sıfırlanıp küresel filtreye geri dönmesini sağlayan checkable "Küresel Seçime Dön" aksiyonu (`refresh-cw` ikonu ile) `QMenu` menülerine entegre edildi. Koyu mod uyumlu kontrast stili QMenu üzerine uygulandı.
- Varlık karşılaştırma listesine "Portföy + Hisseleri" sanal seçeneği eklenerek portföyün kendisini ve içindeki tüm hisseleri tek tıkla Ribbon Bar filtrelerine yükleyen reaktif akış sağlandı.
- İlgili tüm unit testler güncellendi, `test_chart_specific_override` eklendi ve tüm testlerin (249 test) yeşil olduğu doğrulandı.
- Etkilenen dosyalar: `src/ui/pages/comparison/comparison_page.py`, `src/ui/pages/comparison/widgets/ribbon_bar.py`, `tests/ui/pages/test_comparison_page.py`, `docs/wiki/comparison_lab.md`, `docs/wiki/log.md`
- Bağlantılı sayfa: [comparison_lab.md](comparison_lab.md)

---

## [2026-06-01] yeni-sayfa | Karşılaştırma Laboratuvarı kart büyütme, portföy içi kıyaslama ve dokümantasyon entegrasyonu

- Grafik bilgi kartları (`ChartInfoCard`) ve AI analiz panellerinin yazı boyutları, kenar boşlukları ve padding'leri büyütülerek görsel okunabilirlik artırıldı.
- Grafik panelleri `ChartPanel` adlı container bileşeniyle sarmalanarak başlık ve dinamik aksiyon butonları eklendi.
- Her grafik üzerine yerleştirilen "Portföy İçeriğini Kıyasla" açılır menüsü ile seçilen portföyün içindeki hisselerin kümülatif getirileri ve drawdown performanslarının portföyle yan yana kıyaslanması sağlandı.
- Karşılaştırma Laboratuvarı mimarisini, veri entegrasyonunu ve Gemini AI asistan akışını detaylandıran `docs/wiki/comparison_lab.md` sayfası oluşturuldu ve `index.md` ile `architecture.md` belgesine bağlandı.
- Etkilenen dosyalar: `src/ui/pages/comparison/comparison_page.py`, `src/ui/pages/comparison/widgets/ribbon_bar.py`, `tests/ui/pages/test_comparison_page.py`, `docs/wiki/comparison_lab.md`, `docs/wiki/index.md`, `docs/wiki/architecture.md`, `docs/wiki/log.md`
- Bağlantılı sayfa: [comparison_lab.md](comparison_lab.md)

## [2026-06-01] güncelleme | Karşılaştırma Laboratuvarı hata çözümleri ve dikey kaydırma iyileştirmesi

- Gram Gümüş ("silver") ve EUR/TRY ("euro") benchmark seçimlerinin doğru tanınmasını engelleyen filtreleme hatası düzeltildi.
- Kullanıcı explicitly hisse seçimi yapmadığında portföy içindeki bireysel hisselerin grafiğe eklenmesi engellendi.
- Grafik modu "Rasyo Modu" olduğunda tüm alt grafiklerin (drawdown, aylık getiri vb.) ve getiri tablosunun rasyo serisini temel alması sağlandı.
- Getiri tablosunun scrollbar'ı kaldırıldı, yüksekliği dinamikleştirildi ve hücre verileri ortalandı.
- QWebEngineView bileşenlerinde dikey kaydırma (mouse wheel) hareketini ana dikey scroll alanına ileten olay filtresi (WheelRedirectFilter) entegre edildi.
- Etkilenen dosyalar: `src/ui/pages/comparison/comparison_page.py`, `tests/ui/pages/test_comparison_page.py`, `docs/wiki/log.md`

---

## [2026-06-01] güncelleme | Analiz filtre panelinin sadeleştirilmesi

- Kıyaslama sekmesinin kaldırılmasının ardından analiz sayfasındaki filtre panelinde gereksiz kalan çoklu karşılaştırma portföy seçicisi (`compare_combo`) ve çoklu benchmark seçici çip grubu (`BenchmarkChipGroup`) kaldırıldı.
- Genel Bakış sekmesindeki kıyaslama farkı hesabı için tekil kıyaslama endeksi seçilmesini sağlayan bir Benchmark Seçici ComboBox entegre edildi.
- İlgili tüm entegrasyonlar (`AnalysisPage`) ve testler (`test_analysis_page.py`) güncellendi.
- Etkilenen dosyalar: `src/ui/pages/analysis/analysis_control_panel.py`, `src/ui/pages/analysis/analysis_page.py`, `tests/ui/pages/test_analysis_page.py`, `docs/wiki/log.md`

---

## [2026-06-01] güncelleme | Karşılaştırma Laboratuvarı layout ve KeyError çözümleri

- Rasyo modunda ("dashboard" kodu ile "Ana Portföy" etiketi eşleşmemesinden kaynaklanan) `KeyError: 'Dashboard'` hatası çözüldü. DTO'dan gelen varlık kodlarını ve etiketlerini dinamik eşleyen `code_to_label` yapısı eklendi.
- Grafik yerleşimi, kullanıcının talebi üzerine yan yana grid / splitter yapısından kurtarılarak dikey scroll listesi (tek sütunda alt alta tam genişlikte listeleme) haline getirildi.
- Etkilenen dosyalar: `src/ui/pages/comparison/comparison_page.py`, `docs/wiki/log.md`

---

## [2026-06-01] güncelleme | Karşılaştırma Laboratuvarı entegrasyonu ve mimari dokümantasyonu

- Karşılaştırma Laboratuvarı'na yönelik matematiksel motor (`ComparisonService`), görselleştirme motoru (`ComparisonChartFactory`), UI katmanı (`ComparisonPage`, `ComparisonRibbonBar`) ve navigasyon entegrasyonu tamamlandı.
- Eski "Karşılaştırma" sekmesi `AnalysisPage` içerisinden tamamen kaldırıldı, portföy kokpiti sadeleştirildi.
- Mimari dokümanı (`architecture.md`) yeni sayfalar ve servislerle güncellendi.
- Etkilenen dosyalar: `docs/wiki/architecture.md`, `src/application/services/analysis/comparison_service.py`, `src/ui/pages/comparison/chart_factory.py`, `src/ui/pages/comparison/comparison_page.py`, `src/ui/pages/comparison/widgets/ribbon_bar.py`, `src/ui/main_window.py`, `src/ui/navigation/page_factory.py`, `src/ui/pages/analysis/analysis_page.py`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-06-01] güncelleme | Analiz tasarım dokümanlarının proje kuralları ve mimariye göre düzeltilmesi

- `analizSayfasi` altındaki 4 tasarım dokümanı incelendi ve proje kurallarına (sabit light tema yerine dinamik tema, ayrı sayfa yerine AnalysisPage sekmeleri, dosya yolları vb.) uymayan kısımlar düzeltildi.
- Etkilenen dosyalar: `analizSayfasi/1_COMPARISON_SERVICE.md`, `analizSayfasi/2_COMPARISON_CHART_FACTORY.md`, `analizSayfasi/3_UI_LAYERS_AND_SIGNALS.md`, `analizSayfasi/4_NAVIGATION_AND_INTEGRATION.md`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-06-01] güncelleme | Analiz Sayfası Arayüz Tasarımı Yenilenmesi ve Yerleşim İyileştirmeleri

- Sağ filtre panelinin genişliği 320px-360px aralığına düşürülerek sol taraftaki grafiğe ekstra 200px çalışma alanı açıldı
- Karşılaştırma sekmesindeki benchmark metrik kartları yatay kaydırılabilir scroll alanı (InfoCard Carousel) içine alınarak sıkışmalar ve taşmalar tamamen engellendi
- Tarih kartları "Tarih Aralığı" adı altında yan yana yerleşen birleşik bir yapıya kavuşturuldu, dikey alan tasarrufu sağlandı
- Benchmark seçim çipleri 4 sütundan 2 sütuna düşürülerek daralan filtre paneline uyumlu hale getirildi
- MetricCard optimal değer yazı boyutu infoCardValueSmall ile eşitlendi ve negatif delta işareti hatası (örn. ▼ +2.95 yerine ▼ -2.95) düzeltildi
- Etkilenen dosyalar: `src/ui/widgets/shared/cards/metric_card.py`, `src/ui/pages/analysis/analysis_control_panel.py`, `src/ui/pages/analysis/analysis_comparison_section.py`, `src/ui/pages/analysis/benchmark_chip_group.py`, `tests/ui/pages/test_analysis_page.py`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-06-01] güncelleme | EVDS ve YFinance veri akışı entegrasyonu düzeltmeleri

- EVDS API istek rotası yeni EVDS3 `/igmevdsms-dis/` API uç noktasına taşınarak HTTP HTML yönlendirme hatası çözüldü
- YFinance `Pandas4Warning` import hatası giderildi ve Python ortamları arası uyumluluk sağlandı
- YFinance `get_price_series` ve `get_closing_price` içindeki MultiIndex DataFrame yapısı uyumlulaştırıldı, benchmark serilerinin fırlattığı parse hataları giderildi
- EVDS Deposit ve CPI lookback süreleri genişletilerek veri açıklanma gecikmelerinde (lag) son verinin forward-fill ile korunması sağlandı
- Etkilenen dosyalar: `src/infrastructure/market_data/evds_client.py`, `src/infrastructure/market_data/yfinance_client.py`, `src/infrastructure/market_data/yfinance_price_client.py`, `src/application/services/analysis/benchmark_service.py`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-05-30] güncelleme | Modüler QSS sistemi ve design token altyapısı

- `src/ui/styles/base/` silindi; yerine `primitives/` klasörü oluşturuldu
- `src/ui/styles/tokens.py` eklendi: tüm `@TOKEN_ADI` yer tutucuları tek sözlükte toplandı
- `theme_manager.py` `STYLE_MANIFEST` cascade sırası güncellendi (themes → primitives → shared → features)
- `features/ai/`, `features/risk_profile/` alt klasörlerine bölündü; `shared/typography.qss` eklendi
- QSS kapsam kuralı: bileşen-özel `cssState`/`cssClass` kuralları global widget seçicisine taşınmadı
- `ThemeManager.validate_theme_tokens()` ile 0 çözülmemiş token doğrulandı (dark + light)
- 3 ön-var test hatası giderildi: `active_positions` mock attr + `QThreadPool` async zamanlama
- Test sonucu: **238 passed, 0 failed**
- Etkilenen dosyalar: `src/ui/styles/`, `src/ui/theme_manager.py`, `src/ui/styles/tokens.py`, `tests/`
- Bağlantılı sayfa: [architecture.md → Modüler QSS Sistemi](architecture.md#modüler-qss-sistemi-srcuistyles)

---

## [2026-05-31] güncelleme | Asenkron bağlantı yönetimi ve UI iyileştirmeleri

- AI_Core model bağlantı kontrolü UI thread'ini engellememesi için asenkron yapıya (Worker/QThreadPool) taşındı
- AI sayfası yüklendiğinde bağlantı deneniyor durumunu gösteren `show_connecting` ara durumu eklendi
- `price_data_panel` içerisindeki bağımsız threadpool yerine `QThreadPool.globalInstance()` kullanımına geçildi
- Ayarlar fiyat verisi tablosundaki kolon genişlikleri (Stretch mode), metin hizalamaları ve başlık renk tonları iyileştirildi
- Etkilenen dosyalar: `src/ui/pages/ai_page/`, `src/ui/pages/settings/price_data_panel.py`, `src/ui/styles/shared/tables.qss`

---

## [2026-05-31] güncelleme | Finansal planlama ve bütçe modellerinin genişletilmesi

- Bütçe hedefleri için alanlar (budget modeli) detaylandırıldı ve veritabanı yansımaları (`orm_models`) güncellendi
- Planlama servisi ve `sa_planning_repository` yeni özelliklere göre uyarlandı
- Planlama sayfasındaki bütçe form paneli (`budget_form_panel`) ve hedef paneli (`goals_panel`) geliştirildi
- QSS stilleri (planning.qss, shared) UI tasarım sistemiyle uyumlu hale getirildi
- Etkilenen dosyalar: `src/domain/models/`, `src/application/services/planning/`, `src/ui/pages/planning_page.py`, `src/ui/widgets/planning/`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-05-31] lint | Wiki sağlık kontrolü yapıldı

- Silinmiş olan `architecture.md` belgesi git geçmişinden restore edilerek onarıldı
- Yetim kalan `Plans.md` dosyası `index.md` içerik kataloğuna eklendi ve zorunlu navigasyon başlığı eklendi
- Kırık bağlantılar onarıldı ve wiki bütünlüğü sağlandı
- Etkilenen dosyalar: `docs/wiki/architecture.md`, `docs/wiki/index.md`, `docs/wiki/Plans.md`

---

## [2026-05-31] güncelleme | Analiz ve optimizasyon ekranlarında iyileştirmeler

- Analiz servisleri ve grafik motorunda (analysis_chart_engine) güncellemeler yapıldı
- Optimizasyon sayfası ve öneri tablolarında (suggestions_table) stil iyileştirmeleri eklendi
- Etkilenen dosyalar: `src/application/services/analysis/`, `src/ui/pages/`, `src/ui/widgets/optimization/`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-05-31] güncelleme | Tema sistemi modernizasyonu ve UI bileşenleri

- Tema yöneticisi (theme_manager) ve stil tokenleri (tokens.py) modern bir yapıya kavuşturuldu
- Buton, kart, liste ve geri bildirim (toast) gibi paylaşımlı QSS bileşenleri güncellendi/eklendi
- Ayarlar sayfası görünüm paneli (appearance_panel) yeni token altyapısına bağlandı
- Etkilenen dosyalar: `src/ui/theme_manager.py`, `src/ui/styles/`, `src/ui/widgets/shared/`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-05-30] commit | Model portföy geçmiş simülasyonu ve Excel raporu

- Model portföyler için geçmiş simülasyon servisi eklendi
- Excel dışa aktarım (export) fonksiyonları eklendi
- `HistorySimulationService` kod ve test yapısı güçlendirildi
- Etkilenen dosyalar: `src/application/services/simulation/`, `src/application/services/reporting/`, `tests/`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-05-30] commit | BIST piyasa oturum kontrolü ve kullanıcı onayı

- Piyasa saatleri dışı ve tatil günleri için oturum kontrol servisi eklendi
- Kullanıcı işlem yaparken piyasa kapalıysa onay penceresi (`market_session_confirm.py`) gösterilecek
- Etkilenen dosyalar: `src/application/services/market/`, `src/ui/shared/`, `src/infrastructure/calendar/`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-05-27] güncelleme | Yeni işlem sihirbazında şirket adı ve fiyat kaynağı temizlendi

- `PriceLookupService` sonucu şirket adı, normalize ticker ve anlık/son kapanış kaynak bilgisini taşıyacak şekilde genişletildi
- Yeni işlem sihirbazında şirket adı manuel girişten çıkarıldı; lookup sonucu otomatik gösteriliyor
- İşlem detay başlığındaki inline HTML/CSS kaldırıldı, ticker ve şirket adı ayrı QSS sınıflı label'lara ayrıldı
- Etkilenen dosyalar: `src/application/services/market/price_lookup_service.py`, `src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py`, `src/ui/styles/shared/dialogs.qss`, `tests/`
- Bağlantılı sayfa: [architecture.md → Application](architecture.md#2-application-srcapplication)

---

## [2026-05-27] güncelleme | Nakit gösterimi sıfır tabanlı yapıldı ve THYAO temizleme servisi eklendi

- Nakit hesaplama negatif borç üretmeyecek şekilde olay akışında `0` tabanına sabitlendi
- Dashboard nakit kartı ve seçili hisse hızlı işlem paneli negatif kalan nakit göstermeyecek şekilde güncellendi
- THYAO/THYAO.IS kayıtlarını gerçek portföy, fiyat, watchlist, model portföy ve kurumsal aksiyon tablolarından temizlemek için bakım servisi ve script eklendi
- Etkilenen dosyalar: `src/application/services/portfolio/`, `src/infrastructure/db/sqlalchemy/repositories/`, `src/ui/pages/`, `scripts/purge_stock.py`, `docs/wiki/architecture.md`
- Bağlantılı sayfa: [architecture.md → Portföy Hesaplama Mantığı](architecture.md#portföy-hesaplama-mantığı)

---

## [2026-05-27] güncelleme | Dashboard nakit doğrulaması ve güvenli trade replay eklendi

- Gerçek portföy için kalıcı `cash_movements` tablosu, nakit hareket servisi ve al/sat doğrulaması eklendi
- Nakit yetersizse alım, eldeki lot yetersizse satış kaydı engellenecek şekilde merkezi `TradeEntryService` doğrulaması güncellendi
- Eski geçersiz satış kayıtları hesaplamadan hariç tutulup DB bütünlük raporunda listelenecek şekilde güvenli portföy kurucu eklendi
- Etkilenen dosyalar: `src/domain/`, `src/application/services/portfolio/`, `src/infrastructure/db/sqlalchemy/`, `src/ui/pages/dashboard/`, `docs/wiki/architecture.md`
- Bağlantılı sayfa: [architecture.md → Portföy Hesaplama Mantığı](architecture.md#portföy-hesaplama-mantığı)

---

## [2026-05-26] commit | Seçili hisse ekranı ve tablo seçim davranışı iyileştirildi

- Seçili hisse detay grafiği pyqtgraph ile responsive hale getirildi; referans çizgi açıklamaları çakışmayacak legend alanına taşındı
- Hızlı işlem paneli sabit yerleşime alındı; splitter resize handle kaldırıldı ve onay butonu işlem etkisi kartının altında konumlandı
- Pasif tablolarda seçim/focus kapatıldı; dashboard ana tablo dahil renkli hücrelerin seçim tarafından ezilmesi engellendi
- Stok detay kartları emoji yerine tema duyarlı SVG ikonlara geçti; kâr/zarar kartı pozitif/negatif duruma göre ikon ve renk değiştiriyor
- Etkilenen dosyalar: `src/ui/`, `tests/ui/`, `docs/wiki/architecture.md`, `docs/wiki/log.md`
- Bağlantılı sayfa: [architecture.md → UI](architecture.md#4-ui-srcui)

---

## [2026-05-26] commit | UI tema modernizasyonu ve dashboard rapor akışı güncellendi

- Component token tabanlı light/dark tema kontrastları güçlendirildi; dashboard kartları ve butonları modernize edildi
- `QStackedWidget` seviyesindeki fade/graphics effect kaldırılarak hover sırasında buton kaybolması ve QPainter uyarıları giderildi
- UI gösteriminde BIST `.IS` suffix'i gizlendi, Türkçe metin standardizasyonu yapıldı
- Dashboard rapor üretimi tek `Rapor Al` menüsünde `Bugün` ve `Tarih Aralığı` seçeneklerine indirildi
- Etkilenen dosyalar: `src/ui/`, `tests/ui/`, `docs/wiki/architecture.md`, `docs/wiki/log.md`
- Bağlantılı sayfa: [architecture.md → UI](architecture.md#4-ui-srcui)

---

## [2026-05-21] güncelleme | Kalite kapıları ve refactor planı belgelendi

- `RULES.md` kod kalitesi, refactor güvenliği, test ve bağımlılık kapılarıyla genişletildi
- `SettingsPage` panel ayrımı ve `HistorySimulationService` helper ayrımı mimari not olarak kaydedildi
- Etkilenen dosyalar: `RULES.md`, `CLAUDE.md`, `docs/wiki/architecture.md`, `docs/wiki/log.md`
- Bağlantılı sayfa: [architecture.md → Kalite Kapıları ve Modülerlik](architecture.md#kalite-kapilari-ve-modulerlik)

---

## [2026-05-09] yeni-sayfa | Wiki sistemi başlatıldı

- `docs/wiki/index.md` içerik kataloğuna dönüştürüldü (LLM Wiki pattern)
- `docs/wiki/log.md` append-only formatına geçirildi (`## [YYYY-AA-GG] işlem | Başlık`)
- `docs/wiki/architecture.md` oluşturuldu: katmanlar, modeller, DB şeması, veri akışı
- `RULES.md` oluşturuldu: wiki güncelleme, commit mesajı ve LLM operasyon kuralları
- `CLAUDE.md` yeniden düzenlendi: wiki kuralları `RULES.md`'ye taşındı, teknik içerik korundu
- Etkilenen dosyalar: `docs/wiki/index.md`, `docs/wiki/log.md`, `docs/wiki/architecture.md`, `RULES.md`, `CLAUDE.md`

---

## [2026-05-09] ingest | Proje ilk incelemesi ve CLAUDE.md oluşturuldu

- Proje yapısı incelendi: Clean Architecture, PyQt5, MySQL, YFinance, SciPy
- `CLAUDE.md` oluşturuldu: tech stack, mimari, kurulum, komutlar belgelendi
- Etkilenen dosyalar: `CLAUDE.md`

---

## Geçmiş Commit Özeti (git log'dan)

Aşağıdaki girişler geçmiş commit'lerden özet olarak alınmıştır.  
Detay için: `git log --oneline`

---

## [2026-05-09] commit | Optimizasyon motorunu Ledoit-Wolf ve ağırlık limitiyle sağlamlaştır

- `b0cb6ff` — SciPy optimize çağrısı büyük portföylerde kararsız sonuç veriyordu
- Ledoit-Wolf kovaryans shrinkage eklendi (scikit-learn)
- Per-hisse min/max ağırlık kısıtı eklendi
- Bkz. [architecture.md → Optimizasyon Motoru](architecture.md#optimizasyon-motoru)

---

## [2026-05-09] commit | Altın ve mevduat benchmark'larını gerçek piyasa verisine bağla

- `e649277` — YFinance + TCMB entegrasyonu ile benchmark verileri gerçek kaynaklara bağlandı

---

## [2026-05-09] commit | Açık tema ve BIST tatil görünümünü ayarlara ekle

- `cbe83fd` — Light mode ve BIST tatil takvimi ayarlar sayfasında kullanılabilir oldu

---

## [2026-05-09] commit | Dashboard getiri oranlarını kalıcılaştır

- `b94863e` — Uygulama kapanıp açıldığında getiri oranları korunuyor

---

## [2026-05-09] commit | Excel geçmiş raporunu günlük özetlerle iyileştir

- `8d1f179` — Excel çıktısı günlük özet sütunlarıyla zenginleştirildi

---

## [2026-05-09] commit | Bedelli ve bedelsiz sermaye artırımı akışını ekle

- `9ba100c` — CorporateAction domain modeli ve akış tamamlandı
- Bkz. [architecture.md → Temel Tablolar](architecture.md#temel-tablolar)

---

## [2026-05-09] commit | Risk Profili analiz sistemi profesyonel seviyeye yükseltildi

- `0da967a` — Detaylı skor hesaplama ve görsel raporlama eklendi

---

## [2026-05-09] commit | Analiz modülü yenilendi, Price Data Health servisi eklendi

- `0f3c62e` — Fiyat veri sağlığı kontrolü ayrı servis olarak çıkarıldı
- `fc665bb` — Ayarlar sayfası modernize edildi, veri sağlığı paneli iyileştirildi

---

## [2026-05-09] commit | QSS stil sistemi modülerleştirildi

- `2212a3c` — Stiller `src/ui/styles/` altında kategorilere ayrıldı
- `4e34e31` — Emoji ikonlar SVG ikonlarla değiştirildi
- Bkz. [architecture.md → UI Katmanı](architecture.md#4-ui-srcui)

---

## [2026-05-09] commit | UI bileşen mimarisi ve servisler modülerleştirildi

- `083cf17` — UI bileşen klasör yapısı yeniden düzenlendi
- `c0a7fc6` — Her domain için ayrı servis klasörü oluşturuldu
- `9f0db4d` — Toast bildirim sistemi, portföy analiz servisi güncellendi
---

## [2026-06-02] guncelleme | Faz 1 domain modelleri invariant ve precision duzeltmeleri

- `Position` siralama anahtari `trade_time=None` ve saatli trade karisiminda guvenli hale getirildi; invalid satislarda trade gecmisinin kismen mutasyona ugramasi engellendi.
- `FinancialGoal` deadline tipi `Optional[date]` oldu; ay hesabi testten sabit `today` alabilecek sekilde geriye uyumlu genisletildi.
- `Trade`, `CashMovement`, `ModelPortfolioTrade`, `CorporateAction` ve `RiskProfile` modellerine constructor seviyesinde invariant validasyonlari eklendi.
- `Budget`, `BudgetItem` ve `FinancialGoal` para alanlari `Decimal` ile normalize edildi; planning service cikti sozlesmesi float kalacak sekilde korundu.
- `Stock` ve `DailyPrice` temel piyasa modellerine ticker/currency/fiyat validasyonlari eklendi; `Portfolio` domain modelinden logging yan etkisi kaldirildi.
- Etkilenen dosyalar: `src/domain/models/position.py`, `src/domain/models/financial_goal.py`, `src/domain/models/trade.py`, `src/domain/models/cash_movement.py`, `src/domain/models/model_portfolio.py`, `src/domain/models/corporate_action.py`, `src/domain/models/budget.py`, `src/domain/models/risk_profile.py`, `src/application/services/planning/planning_service.py`, `src/infrastructure/db/sqlalchemy/repositories/sa_planning_repository.py`, `src/ui/widgets/planning/panels/budget_form_panel.py`, `tests/domain/`, `tests/application/test_planning_service_budget.py`

---
