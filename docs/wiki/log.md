# Wiki Değişiklik Günlüğü

> Ana katalog: [index.md](index.md) | Mimari: [architecture.md](architecture.md)  
> Bu dosya **yalnızca ekleme** yapılır. Eski girişler hiçbir zaman silinmez veya düzenlenmez.  
> Grep ile son girişler: `grep "^## \[" docs/wiki/log.md | head -10`

---
## [2026-10-04] refaktör | Dev QML Görünümlerinin Bölünmesi (Denetim Bulgu 14)

- **Güvence:** Yeni `tests/ui_qml/test_qml_views_runtime_smoke.py`: beş büyük görünüm uygulamadaki tüm bağlam özellikleriyle oluşturulur, her sekme/mod etkinleştirilir ve QML motorunun **hiç uyarı** üretmediği doğrulanır (kopan `root.*` / kimlik başvurularını yakalar). Test başlangıçta `ModelAnalysisPanel.qml` içinde 3 `Unable to assign undefined to QString` uyarısı buldu (analiz verisi yokken); boş metin yedeğiyle giderildi.
- **Adım 1 - `SettingsView.qml`** (1117 -> 231 satır): sekme 0-3 yeni bileşenlere çıkarıldı (`SettingsAppearanceTab`, `SettingsApiKeysTab`, `SettingsDataHealthTab`, `SettingsExportTab`); sekme 4-7 zaten ayrı bileşendi. Bileşenler eskisi gibi doğrudan örneklenir (yük/bellek davranışı ve sekmeler arası durum korunur, `Loader` kullanılmadı). `test_strings_catalog.py` izin listesi taşınan `Başarılı` literali için güncellendi.
- **Adım 2 - `OptimizationView.qml`** (1128 -> 101 satır): sol parametre paneli `OptimizationParamsPanel` (`stacked` özelliği, `riskQuestionnaireRequested` sinyali; diyalog görünümde kalır), KPI şeridi `OptimizationKpiStrip` (`stacked`, `hostWidth`), sekme çubuğu + içerik kartı `OptimizationResultsPanel`.
- **Adım 3 - `Stock360View.qml`** (1113 -> 122 satır): üç `Component` gövdesi `Stock360OverviewSection`, `Stock360FinancialsSection`, `Stock360ShareholdersSection` (`hostWidth` = Loader genişliği), satır içi bölümler `Stock360TopBar`, `Stock360ModeTabs`, `Stock360HeroCard` (`root.ctrl` her bileşende yeniden tanımlı). Duman testi artık Hisse 360 görünüm modlarını (0/1/2) `setViewMode` ile sürer; üç bölümün de örneklendiği doğrulandı.
- **Adım 5 - `AiAdvisorView.qml`** (1080 -> 122 satır): `AiAdvisorHeader` (`historyRequested`), `AiChatTerminal` (`scrollToEnd()`; yeni mesajda sayfa bu işlevi çağırır), `AiHealthPanel` (`stacked`).
- **Sonuç:** beş görünümün hiçbiri 900 satırı aşmıyor (en büyük QML dosyası `Strings.qml` 879, sonra `PlanningBudgetTab` 840); `test_qml_file_size_guard.py` 900 satır tavanını korur. `qml_pages_guide.md`'ye bileşen tablosu eklendi.
- **Adım 4 - `StockDetailModal.qml`** (1107 -> 178 satır): `StockDetailHeader` (sinyaller: grafik, Hisse 360, sermaye artırımı, temettü), `StockDetailKpiCards` (`boxWidth`), `StockDetailTabsPanel` (`activeTab` durumu burada), `StockDetailOrderForm` (yön/lot/fiyat/zaman durumu, `resetTradeMoment()` ve `syncPrice()` burada; modal görünür olunca ve hisse değişince çağırır). Diyaloglar ve toast modalda kaldı. Duman testi alt sekme durumunu çocuk bileşen üzerinden sürer.

---
## [2026-10-04] düzeltme | yfinance Kapısı Zaman Aşımı (Denetim Bulgu 13)

- Denetim bulgusu kodla doğrulandı ve **kısmen düzeltildi**: toplu BIST indirmeleri (`bist_bulk_downloader.py`, `market_data_sync_service.py`) `yfinance_lock` kullanmıyor ve zaten eşzamanlı çalışıyor; yani "toplu senkron kullanıcının fiyat sorgusunu bekletir" iddiası yanlıştı. yfinance 1.7.0 `multi.py` paylaşılan küresel durum (`shared._DFS`) kullanmıyor. Gerçek risk: kilit alma süresiz olduğundan takılan tek bir etkileşimli çağrı diğer tüm etkileşimli yfinance çağrılarını bekletebilir.
- `yfinance_lock` artık zaman aşımlı `YFinanceGate`: 30 sn içinde alınamazsa uyarı yazılır ve çağrı kilitsiz sürdürülür (fail-open); 2 sn üzeri beklemeler bilgi olarak loglanır; zaman aşımına düşen giriş başkasının kilidini serbest bırakmaz (iş parçacığı başına yığın). Mevcut `with yfinance_lock:` kullanımları değişmedi.
- Testler: `test_yfinance_gate.py` (serileştirme, takılan tutucuya karşı fail-open, istisnada serbest bırakma, iç içe kullanım).
- Kasıtlı olarak yapılmadı: kilidi tamamen kaldırmak (yfinance'in tüm yolları için kanıt yok) veya iki kilide bölmek.

---
## [2026-10-04] düzeltme | Test Hijyeni (Denetim Bulgu 12)

- Silindi: `tests/infrastructure/market_data/test_benchmark_fetch_manual.py` (kaldırılmış `_investing_client` alanına başvuruyordu, çalışamazdı); `conftest.py` marker dalı ve `test_repo_guards.py` izin listesi temizlendi.
- Kök `conftest.py`: `wait_until` fixture'ı (koşul + zaman aşımı + Qt olay döngüsü) ve `QT_QUICK_CONTROLS_STYLE=Basic`. Stil ayarı daha önce yalnızca `tests/ui_qml/conftest.py`'deydi; bu yüzden `test_chat_session_service.py::test_chat_history_dialog...` tek başına koşunca kırılıyordu (roadmap'teki "sıra bağımlı QML testi" kalemi kapandı).
- `test_market_sync_controller.py`: 0,05 sn uyku yerine `threading.Event` kapısı (`isSyncing` durumu deterministik), 1 sn'lik sınırlı döngü yerine `wait_until`. `test_comparison_screener_phase7.py`: aynı şekilde `wait_until` (10 sn).
- Bilinçli bırakılan: `test_stock_360_phase5.py` ve `test_stock_detail_and_excel.py` zaten 4 sn / 15 sn zaman aşımlı koşul beklemesi kullanıyor (sabit uyku değil); `test_bigint_id_concurrency.py` içindeki 0,3 sn bekleme yarışı kurmak için gerekli ve yorumlu.

---
## [2026-10-04] güncelleme | CI Genişletildi (Denetim Bulgu 11)

- `.github/workflows/tests.yml`: Python matrisi 3.10 ve 3.11 (zorunlu) + 3.12 (deneysel, `continue-on-error`); `QT_QPA_PLATFORM=offscreen`; pip önbelleği; `pytest-cov` ile kapsam (`--cov=src --cov=config --cov-fail-under=80`, yerel taban %84, `coverage.xml` artifact); eşzamanlı çalışma iptali.
- Yeni **quality** işi: `measure_code_quality.py` tavan kapısı (14 sınıf, 104 fonksiyon, 0 dosya). Betiğe `--max-class-violations`, `--max-function-violations`, `--max-file-violations` bayrakları ve `ceiling_failures` eklendi (`tests/test_code_quality_measurement.py` içinde 3 test).
- Yeni **security** işi: `pip-audit` kurulu ortamı tarar (push, PR ve haftalık zamanlama). Yerelde: doğrudan bağımlılıklarda açık yok; yerel `venv` içindeki `setuptools 65.5.0` için 4 açık raporlanıyor (çalışma zamanı bağımlılığı değil, derleme aracı; `pip install -U setuptools` önerilir).
- `requirements.txt`'e `pytest-cov==7.1.0`. **Doğrulanmadı:** iş akışı GitHub üzerinde koşmadı (YAML yerelde ayrıştırıldı; testler yerelde `QT_QPA_PLATFORM=offscreen` ile 1257 geçti, Python 3.12 denenmedi). Lint (ruff) bilinçli eklenmedi.

---
## [2026-10-04] güncelleme | API Anahtarları İşletim Sistemi Sır Deposunda (Denetim Bulgu 10)

- Yeni `config/secret_store.py` (`SecretStore`, `KeyringSecretStore`): Gemini ve EVDS anahtarları Windows Kimlik Bilgisi Yöneticisi'nde (`keyring==25.7.0`, hizmet `PortfoySimulasyonu`) saklanır. `persist_api_keys` depoya yazar ve `.env`'deki düz metin kalıntıyı siler; depo yoksa/hata verirse `.env` yedeğine düşer. Boş değer depodan, `.env`'den ve ortamdan siler. Yükleme sırasında depo `.env`'den önceliklidir. Değer hiçbir zaman log'a yazılmaz.
- Testler gerçek depoya asla dokunmaz: `conftest.py` autouse `secret_store` fixture'ı bellek içi depo kullanır. `test_secret_store.py` (öncelik, kalıntı temizliği, yedek, silme, güvenli hata, log sızıntısı, gerçek depoda elle koşulan `manual` testi); `test_group1_fixes.py` ve `test_settings_phase11.py` yeni davranışa uyarlandı.
- `requirements.txt` `keyring==25.7.0`; `build_nuitka.bat` `--include-package=keyring --include-distribution-metadata=keyring`. **Doğrulanmadı:** Nuitka derlemesinde `keyring` arka uç keşfi (derleme denenmedi; başarısız olursa uygulama `.env` yedeğiyle çalışır). Gerçek Windows deposu `pytest -m manual` ve elle deneme ile doğrulandı (yazma/okuma/silme).

---
## [2026-10-04] düzeltme | Piyasa Saati: Istanbul Saat Dilimi (Denetim Bulgu 8)

- Yeni `src/domain/market_clock.py` (`market_now`, `market_today`, `market_time`): `Europe/Istanbul` duvar saati, naive döner; `tzdata` yoksa sabit UTC+3 yedeği.
- Piyasa takvimine bağlı 17 modülde (seans/bugün kontrolü, işlem ve nakit tarihi varsayılanları, açılış işleri, tarayıcı ve teknik analiz, fiyat sağlığı, Hisse 360, AI araçları, hedef ilerlemesi) `date.today()` / `datetime.now()` değiştirildi; yerel zamanın doğru olduğu yerler (sohbet saati, dosya damgaları, kayıt damgaları) bilinçli bırakıldı.
- Testler: `tests/domain/test_market_clock.py` (UTC 22:30 -> ertesi gün, mikrosaniyesiz saat, UTC+3 yedeği), `tests/test_market_clock_guard.py` (dönüştürülen modüller). `test_group2_corporate_price_startup.py` artık `market_now` yamalıyor.
- Kullanılmayan `date`/`datetime` importları temizlendi. `service_market_data_providers.md` §6 güncellendi.

---
## [2026-10-04] refaktör | Karmaşık Fonksiyonların Bölünmesi (Denetim Bulgu 3)

- **Adım 1 - `financials/metrics.py::_single_period`** (140 satır, CC 41 -> 12 satır, CC 2): ham kalem okuma (`_income_items`, `_balance_items`, `_note_and_cash_flow_items`), türetilmiş metrikler (`_derived_metrics`, `_favok`, `_net_debt`, `_export_ratio`, `_payout_ratio`), oranlar (`_ratio_metrics`), işletme sermayesi (`_working_capital_metrics`) ve ham-çıktı ad eşlemesi (`_RAW_TO_OUTPUT`) olarak ayrıldı. Çıktı değişmedi: `test_metrics_single_period.py` refaktör öncesi koddan alınan 6 senaryolu karakterizasyon testidir (tam veri, boş, kısmi, sıfır payda, enflasyon bayrağı, FAVÖK amortismansız).
- **Adım 2 - `isyatirim_provider.py::_scrape`** (92 satır, CC 43 -> 25 satır, CC 5): iki kopya probe döngüsü tek `_probe_financial_group` fonksiyonunda birleşti (iki turdaki mantık aynıydı); çeyrek toplama `_collect_periods` (+ `_StatementSource`, `_Probe`, `_rows_for_batch`, `_register_periods`, `_add_rows_to_store`) olarak ayrıldı. İstek sırası ve çıktı değişmedi: `test_isyatirim_scrape_characterization.py` ve `golden/isyatirim_scrape_golden.json` (5 senaryo, sahte `_fetch_batch`, sabit tarih) refaktör öncesi koddan üretildi. Korunan eski tuhaflık: ilk paket yeniden kullanımı her zaman *ilk* 4 aday çeyreğin etiketleriyle karşılaştırılır; veri ikinci pakette bulunursa önbellek hiç kullanılmaz ve bir fazla istek atılır (çıktıyı etkilemez, bilerek değiştirilmedi).
- **Adım 3 - `ChartController._fetch_and_emit_chart_data`** (131 satır, CC 42 -> 7 satır): mum kaynakları yeni saf modül `chart_candle_sources.py`'ye taşındı (`load_market_history_candles`, `load_price_series_candles`, `demo_candles`, `last_price_summary`); denetleyicide yalnızca `_load_candles`, `_update_last_price`, `_build_payload` ve ince orkestratör kaldı (`ChartController` 392 -> 298 etkin satır). Karakterizasyon: `test_chart_fetch_characterization.py` + `golden/chart_fetch_golden.json` (6 senaryo: DuckDB günlük/haftalık/aylık, SQLite yedeği iki yoldan, veri yok; tüm paketin SHA-256 özeti). Küçük davranış farkı: DuckDB okuması kısmen ilerleyip hata verirse artık yarım mum listesi SQLite yedeğine karışmıyor.
- **Adım 4 - `ChartController._calculate_indicators`** (101 satır, CC 22 -> 1 satır delege): saf modül `chart_indicators.py` (`calculate_indicators`, `cross_markers`, `_markers_from_events`, `_markers_from_sma_difference`, `to_line_data`, `empty_indicators`); `ChartController` 392 -> 199 etkin satır. Karakterizasyon: `test_chart_indicators_characterization.py` + `golden/chart_indicators_golden.json` (8 durum: boş, tek mum, 70/260/300/420 mum, SMA yedeği, `detect_crosses` istisnası; SHA-256 özetli). Küçük fark: yedek SMA işaretçi hesabı ortasında istisna olursa artık kısmi liste yerine boş liste dönüyor.
- **Adım 5 - `financials/metrics.py::_piotroski`** (48 satır, CC 24 -> 5 satır, CC 2): `_compare` yardımcısı, `_PeriodView` (dönem ve bir önceki yılın aynı dönemi için `cur/prv/rose/fell/positive`) ve `_piotroski_period` olarak ayrıldı; iç içe kapanışlar kalktı. Karakterizasyon: `test_piotroski_characterization.py` + `golden/piotroski_golden.json` (8 sınır durumu: tümü iyileşen/kötüleşen, eşit değerler, YoY dönemi yok, eksik ölçüler, boş dönem, nakit akışı = kâr, pay azalması + 40 tohumlu rastgele girdi).
- **Adım 6 - `stock_360_fallback.py::get_fallback_financials`** (89 satır, CC 31 -> 11 satır, CC 1): çevrimdışı örnek veri kümesi sabit bir sözlük değişmezi + onlarca sözlük kavrayışıydı; `_fallback_ratios`, `_fallback_quarterly_series`, `_fallback_flat_metrics`, `_fallback_raw_sections` ve tek `_flat_series` yardımcısına ayrıldı. Her çağrı yeni sözlük üretir (paylaşılan değişebilir sabit yok). Karakterizasyon: `test_stock_360_fallback_characterization.py` + `golden/stock_360_fallback_financials_golden.json` (tüm veri kümesi birebir, tickerdan bağımsızlık, bağımsız kopya).
- **Adım 7 - `Stock360Controller._load_local_overview_and_technical`** (79 satır, CC 34 -> 15 satır, CC 6): şirket adı/sektör çözümü, genel bakış alanları ve teknik seviye alanları yeni saf modül `stock_360_overview.py`'ye taşındı (`resolve_identity`, `overview_fields`, `technical_fields`, `rsi_status`, `trend_status`). Gerçek ve varsayılan veri artık aynı yoldan uygulanır: `_apply_overview` / `_apply_technical` (`_set_default_*` bunları çağıran ince sarmalayıcılar). Karakterizasyon: `test_stock_360_overview_characterization.py` + `golden/stock_360_overview_golden.json` (9 senaryo; denetleyicinin tüm basit durum alanları ve sinyal sayısı). `Stock360Controller` 685 -> 623 etkin satır (hâlâ eşik dışı).
- **Bulgu 3 sonucu:** raporda adı geçen yedi fonksiyonun hepsi eşik altına indi; eşik dışı fonksiyon sayısı 110 -> 104. Kalan eşik ihlalleri `code_quality_guardrails.md` §3'te.
- Not: `test_chat_session_service.py::test_chat_history_dialog_compiles_and_lists_sessions` tek başına koşunca "native style" QML uyarısıyla kırılıyor (tam pakette geçiyor); bu refaktörden bağımsız, sıra bağımlılığı.

---
## [2026-10-04] düzeltme | BIGINT Kimlik Atamasında Eşzamanlı Yazıcı Çakışması (Denetim Bulgu 7)

- `before_insert` dinleyicisi (`orm_models.py`) `max(id)` okumadan önce `UPDATE ... WHERE 0` ile SQLite yazma kilidini alıyor. İkinci yazıcı ilki commit edene kadar bekler ve güncel `max(id)` değerini görür.
- Çakışma önce yeniden üretildi: iki oturum, A flush edilmiş ama commit edilmemişken B kayıt ekleyince `UNIQUE constraint failed: stocks.id`. Test: `tests/infrastructure/db/test_bigint_id_concurrency.py` (düzeltmeden önce kırmızı, sonra yeşil; 5 tekrarda kararlı).
- Kalıcı çözüm (`INTEGER PRIMARY KEY`, tablo yeniden kurulumu) `roadmap.md`'ye eklendi; `database_schema_and_orm.md` ve `data_architecture.md` güncellendi.

---
## [2026-10-04] düzeltme | AI Yerel Motoru Sorgu Niyeti Eşleştirmesi (Denetim Bulgu 6)

- `AiAdvisorController._generate_local_portfolio_analysis` optimizasyon raporuna karar verirken `"al"` ve `"sat"` için alt dize araması yapıyordu; `maliyet`, `analiz`, `altın` gibi sözcükler her soruda Markowitz aracını tetikliyordu.
- Yeni saf modül `advisor_query_intent.py` (`is_optimization_query`, `turkish_lower`): sözcük sınırlı regex, açık sözcük kökleri, `İ/I` duyarlı küçük harf. Denetleyiciye yeni mantık eklenmedi (eşik ihlali olan sınıf).
- Testler: `tests/ui_qml/test_advisor_query_intent.py` (19 test, denetleyici düzeyinde iki davranış testi dahil).

---
## [2026-10-04] düzeltme | Sürümlü Şema Göçleri (Denetim Bulgu 5)

- Yeni `src/infrastructure/db/sqlalchemy/schema_migrations.py`: numaralı `Migration` listesi, `schema_migrations` sürüm tablosu, göç öncesi `data/backups/` yedeği (son 5), göç başına transaction, hata yükseltme (`SchemaMigrationError`). Üç eski açılış adımı (golden_cross DROP, `.IS` ticker, `cash_movements.stock_id`) 1-3 numaralı göçlere taşındı.
- `SQLAlchemyEngineProvider._init_db_schema` artık göç hatasını yutmuyor (eskiden tüm blok `except Exception` ile loglanıp geçiliyordu).
- Gerçek `portfolio.db` kopyasında doğrulandı: satır sayıları değişmedi, 59 MB yedek alındı, ikinci açılışta göç yok.
- Testler: `test_schema_migrations.py` (taze veritabanı, yedek, tek seferlik uygulama, hatada yedek ve yükselme, yedek hatasında durma, yedek budama); `test_database_engine.py` şema kurulumunu sahte engine ile atlayacak şekilde düzeltildi.
- Açık: göç hatası `app.py` tarafından çevrimdışı modda sessizce karşılanıyor; kullanıcıya hata penceresi gösterilmiyor.

---
## [2026-10-04] düzeltme | Sessiz Yutulan İstisnaların Giderilmesi (Denetim Bulgu 4)

- Sessiz `except ... pass/continue` yerleri görünür hale getirildi: AI yerel analiz araçları, model portföy toplam değeri, planlama pin kalemleri (`logger.warning`, `exc_info`); EVDS TÜFE ayrıştırma ve önbellek, Stock 360 YoY hesabı, verimli sınır noktası, DuckDB bağlantı kapatma (`logger.debug`, dar istisna türleri).
- `DashboardController` Excel işçisi tarihleri `date.fromisoformat` ile okur; geçersiz değer sessizce yok sayılmaz, `excelExported(False, ...)` ile bildirilir.
- `BistBulkDownloader` şema göçü `ADD COLUMN IF NOT EXISTS` kullanır (hata yutan `try/except` kaldırıldı).
- `stock_360_controller.py` `__del__` temizliği bilinçli olarak bırakıldı. Test: `test_dashboard_excel_worker_reports_invalid_iso_date_instead_of_silent_fallback`.

---
## [2026-10-04] düzeltme | Derlemeden Gerçek `data/` Klasörünün Çıkarılması (Denetim Bulgu 1)

- `build_nuitka.bat` artık `--include-data-dir=data=data` kullanmıyor; kişisel `portfolio.db` ve DuckDB `.exe`'ye girmez.
- `scripts/build_preflight.py` yeni `bundled data guard` denetimi ekledi (REM satırları yok sayılır); `test_production_guards.py` içinde iki test.
- `project_build_and_deployment.md` güncellendi. Açık nokta: `onefile` derlemede `app_root()` (`sys.executable` dizini) gerçek derlemeyle doğrulanmadı.

---
## [2026-10-04] inceleme | Kapsamlı Sistem Denetim Raporu

- **Eklenen:** `system_audit_report_2026-10-04.md` (V2 denetim şablonu ve AI geliştirme metodolojisine göre). 16 bulgu: kritik yok; öne çıkanlar `build_nuitka.bat` gerçek `data/` klasörünü `.exe`'ye gömüyor, 14 denetleyici sınıfı ve CC>40 fonksiyonlar, 18 sessiz `except`, sürümsüz şema göçü, AI yerel motorunda `"al"/"sat"` alt dize eşleşmesi.
- **Durum:** Bulgular sırayla uygulanıyor (1-7); biten bulgu ayrı `düzeltme` girişiyle kaydedilir.

---
## [2026-10-04] temizlik | Kullanılmayan Keşif Betiklerinin Silinmesi

- **Silinenler:** `scripts/bencmarkVeri.py`, `tcmbApi.py`, `tcmbFaizApi.py`, `inspect_db.py`, `show_violations.py` ve `scripts/finansal_lab/` (prototipler ve üretilen örnek veri dosyaları). Hiçbiri kod, test, derleme veya CI tarafından çağrılmıyordu.
- **Etkilenen belgeler:** `database_maintenance_and_scripts.md` (betik tablosu), `roadmap.md` (teknik borç satırı artık yalnızca kalan eskimiş tek seferlik betikleri listeler), `code_quality_guardrails.md` (fonksiyon eşik ihlali 129 -> 110).
- **Kalanlar:** `import_bist_ohlcv_to_db.py`, `backfill_missing_friday_prices.py`, `fix_technical_analysis.py` eskimiş tek seferlik betikler olarak belgelendi; silme kararı bekliyor.

---
## [2026-10-04] güncelleme | Dokümantasyonun Kod Tabanına Göre Baştan Doğrulanması ve Yenilenmesi

- **Silinenler:** Gitignore'daki `docs/MyDocs` (37 dosya: eski widget arayüzü planları, MySQL dönemi raporları, tamamlanmış görev listeleri, eski denetimler) kaldırıldı; silmeden önce yedeği alındı. Yalnızca hâlâ uygulanmamış fikirler `roadmap.md`'ye taşındı. Wiki'den `refactor_handoff_2026-06-13.md`, `pyside6_migration_analysis.md` ve çözülmüş bulgulardan oluşan `system_audit_report_2026-09-30.md` silindi (tarihçe `log.md` ve git geçmişinde).
- **Yeni sayfalar:** `project_structure.md`, `development_guide.md`, `qml_pages_guide.md`, `service_market_data_providers.md`, `technical_analysis_and_screener.md`, `stock_360.md`, `settings_and_system.md`, `glossary.md`; `Plans.md` -> `roadmap.md` (doğrulanmış fikir havuzu ve teknik borç).
- **Baştan yazılanlar:** `architecture.md`, `ui_architecture_and_events.md` (yalnızca QML), `qml_pages_guide.md`, `comparison_lab.md` (Plotly değil Lightweight Charts/Chart.js), `ai_integration.md` (tool-calling, girdi güvenliği, AI_Core), `service_portfolio_and_market.md`, `service_corporate_actions.md` (eski tablodaki `STOCK_SPLIT/DIVIDEND/RIGHTS_ISSUE` türleri kodda yoktu), `service_analysis.md`, `service_planning_optimization.md`, `service_simulation.md`, `service_watchlist.md`, `service_reporting_and_export.md`, `database_schema_and_orm.md` (23 tablo), `database_maintenance_and_scripts.md` (olmayan `replicate_db.py`, `DbIntegrityService` anlatımı kaldırıldı), `testing_strategy.md`, `manual_testing_guide.md` (QML sayfalarına göre), `project_build_and_deployment.md`, `code_quality_guardrails.md` (güncel 14 sınıf/129 fonksiyon ihlali), `index.md`.
- **Güncellenenler:** `data_architecture.md` (DuckDB şeması), `market_corporate_actions.md` (gezinme), kök `README.md` (PyQt5/MySQL dönemi anlatımı kaldırıldı).
- **Taşınanlar:** Kök `teknik_analiz_tartisma.md` ve `temel_analiz_filtre_tartisma.md` -> `docs/wiki/tasarim_notlari/` (üstlerine durum notu eklendi).
- **Kodda bulunan hatalar:** `DatabaseMaintenanceService` finansal hedef sayısını olmayan `dca_goals` tablosundan okuyordu (`financial_goals` olarak düzeltildi); `CorporateActionService` modül açıklaması eski sentetik BUY modelini anlatıyordu (geriye dönük düzeltme modeli olarak düzeltildi); `pytest.ini` `ui` marker açıklaması güncellendi.
- Doğrulama: wiki içi bağlantılar ve dizin kapsamı betikle denetlendi (kırık bağlantı, dizinde olmayan sayfa ve yetim sayfa yok).

---
## [2026-10-03] ekle | Strateji Backtest (Periyodik Yeniden Dengeleme, Stop-Loss / Take-Profit)

- **Motor:** `strategy_backtest.py` (saf) + `StrategyBacktestService`. Yeniden dengeleme eşit veya Markowitz ağırlığıyla (her dengeleme gününde yalnızca geçmiş veriden maksimum Sharpe, `optimization_service.compute_max_sharpe_weights`); stop-loss/take-profit giriş fiyatına göre günlük kapanışla. Her ikisi de "al ve tut" taban çizgisiyle ve maksimum düşüşle karşılaştırılır.
- **Ortak fiyat okuyucu:** `price_series_loader.py` (DCA servisi de bunu kullanır).
- **Arayüz:** Planlama > "Strateji Testi" sekmesi (`PlanningStrategyTab.qml`, `StrategyBacktestController`, çok serili `lw_chart_html.py` grafiği); sayı girişleri `number_input.py` (Türkçe `1.234,5` ve `50.000` biçimleri; temettü tutarı da aynı ayrıştırıcıyı kullanır).
- Gerçek DuckDB kopyasında THYAO/ASELS/BIMAS/FROTO 2023-2026 doğrulaması: yeniden dengeleme ~0,4 sn. Plan §9.13 güncellendi. Wiki: `service_simulation.md`.

---
## [2026-10-03] ekle | Nakit Temettü Kaydı

- **Backend:** `CashMovementType.DIVIDEND`, `cash_movements.stock_id` (açılışta idempotent ALTER; gerçek veritabanı kopyasında doğrulandı), `CashMovementService.add/get/delete_dividend`, `PortfolioService.validate_cash_removal`. Temettü nakit bakiyeye girer ve TWR getirisi olarak sayılır; yatırma gibi dış sermaye akışı değildir.
- **Arayüz:** Hisse Detay modalına "Temettü" düğmesi (ana portföy, açık pozisyon), `DividendDialog.qml` ve `DividendController` (kayıt, geçmiş, silme). `app.py`'de bağlandı; kayıt/silme sonrası Dashboard ve model portföy ekranları yenilenir.
- **Doğrulama kuralları:** O tarihte pozisyon olmalı, gelecek tarih yok, silme sonraki nakit akışını bozamaz.
- Testler: `tests/application/test_dividend_cash_flow.py`, `tests/infrastructure/db/test_cash_movement_dividend_repository.py`, `tests/ui_qml/test_dividend_controller.py`. Wiki: `service_corporate_actions.md`.

---
## [2026-10-03] düzelt | SQLite BIGINT Birincil Anahtar Otomatik Atama

- **Hata:** SQLite'ta `BIGINT` birincil anahtar rowid takma adı olmadığı için otomatik artmaz. `id` vermeden kayıt ekleyen repository'ler (`insert_trade`, `insert_movement`, model portföy, bütçe vb.) gerçek veritabanında `NOT NULL constraint failed: ...id` ile başarısız oluyordu; yalnızca `id`'yi elle atayan repository'ler (fiyat, hisse, izleme listesi) çalışıyordu. Mock'lu testler bunu yakalamıyordu.
- **Düzeltme:** `orm_models.py` içine `Base` için `before_insert` dinleyicisi eklendi; tek `BIGINT id` birincil anahtarlı tabloda `id` boşsa `max(id)+1` (aynı flush içinde sayaç) atanır. Elle `id` verenler etkilenmez.
- Testler: `tests/infrastructure/db/test_cash_movement_dividend_repository.py` (gerçek geçici SQLite). Wiki: `data_architecture.md` kural 5.

---
## [2026-10-03] ekle | ADX ve Supertrend Göstergeleri, İki Yeni Tarayıcı Stratejisi

- **Göstergeler:** `indicators.py` içine `adx` (Wilder; ADX, +DI, -DI) ve `supertrend` (çizgi ve yön) eklendi.
- **Tarayıcı:** `IndicatorSnapshot` ADX/DI ve Supertrend yönü (son ve önceki bar) alanlarını kazandı; `SCREENER_FILTERS` 8'den 10'a çıktı: "Güçlü Yükseliş Trendi (ADX > 25, +DI > -DI)" ve "Supertrend Al Sinyali (Trend Dönüşü)". Açılır liste filtreleri `SCREENER_FILTERS`'tan okuduğundan arayüz değişikliği gerekmedi.
- Gerçek DuckDB kopyasında tam BIST taraması ~3,6 sn; ADX filtresi 18, Supertrend al sinyali 6 hisse yakaladı.
- Testler: `test_indicators_trend.py`, `test_screener_trend_filters.py`. Wiki: `service_analysis.md`.

---
## [2026-10-03] ekle | Ağ Çağrılarına Ortak Yeniden Deneme (Retry/Backoff)

- **`src/infrastructure/retry.py`:** `retry_call` (üstel geri çekilme, varsayılan 3 deneme) ve `is_transient_error` (URLError, zaman aşımı, bağlantı hatası, HTTP 408/429/5xx, `YFRateLimitError`). Kalıcı hatalar ilk denemede çağırana döner.
- **Bağlanan istemciler:** `YFinanceMarketDataClient`, yfinance optimizasyon sağlayıcısı, `EvdsClient`, KAP kamuya açık kaynak ve ortaklık sağlayıcıları, İş Yatırım toplu çekimi, ölçüt kazıyıcısı. `BistBulkDownloader` kendi döngüsü yerine ortak yardımcıyı kullanır (davranış aynı: her hata 2 sn, 4 sn bekleyerek denenir).
- yfinance kilidi denemeler arasında bırakılır. Tek hisse anlık fiyat sorguları arayüzü bekletmemek için bilerek denenmez.
- Testler: `tests/infrastructure/test_retry.py`, `tests/infrastructure/market_data/test_network_retry_integration.py`; `tests/conftest.py` testlerde beklemeyi kapatır. Wiki: `data_architecture.md` kural 7.

---
## [2026-10-03] belge | Dönüşüm Belgeleri Güncel Duruma Çekildi

- **`QML_TRANSFORMATION_HANDOFF.md`:** Test sayısı (964 geçti, 4 xfailed), veritabanı boyutları, denetleyici listesi ve Faz 9-11 durumu düzeltildi; "Faz 11 Sonrası Eklemeler" bölümü (tek piyasa evreni, sermaye artırımı düzeltmesi, eski arayüzün kaldırılması, koruma testleri, ölü kod temizliği) eklendi.
- **`TRANSFORMATION_PLAN.md`:** Başa tarihsel plan notu eklendi (gerçek arayüz yapısı, WebEngine kararı, eski arayüz silinmesi). §9.11 ve §9.12 çözüldü olarak işaretlendi, Aşama 5 kapatıldı, uygulanmayan maddeler §9.13'te listelendi.
- **Wiki `index.md`:** Handoff satırı güncellendi.
- **Silinen:** kullanılmayan `views/PlaceholderView.qml` ve `test_strings_catalog.py` izin listesindeki girdileri.

---
## [2026-10-03] sil | Ölü Kod Temizliği

Eski arayüz kaldırıldıktan sonra `vulture` + dize/QML çapraz kontrolüyle yapılan tarama sonucu (AI_Core istemcisine dokunulmadı):

- **Silinen dosyalar:** `investing_fallback_client.py`, `tvdatafeed_client.py`, `db_integrity_service.py` (hiçbir arayüzde kullanılmıyordu), `qt_compat` altındaki 7 kullanılmayan sarmalayıcı. Container'dan `tv_backfill_service`, `tv_client`, `db_integrity_service` alanları; `requirements.txt`'ten `tradingview-datafeed` ve `websocket-client` kalktı.
- **Silinen metotlar:** application/domain katmanında çağrılmayan ~15 metot ve kullanılmayan importlar.
- **Denetleyici üyeleri:** QML'den çağrılmayan üyeler silindi (Dashboard/model portföy `exportToExcel*` tarihsel rapor diyaloğu ile değiştirilmişti, `deleteTrade`, Stock 360 ve Hisse Detay kullanılmayan alanları vb.); artık dinleyicisiz 3 sinyal kaldırıldı. Kullanılabilir olanlar arayüze bağlandı: Ayarlar > veritabanı kartlarında SQLite/DuckDB dosya yolları, Piyasa Düzeltmeleri sekmesinde "listelenen / toplam olay" sayısı.
- **Strings.qml:** kullanılmayan 77 anahtar silindi; `test_strings_catalog.py` artık kullanılmayan anahtarı da yakalar.
- **Doğrulama (denetim):** silinenlerin hiçbirinin eski arayüzde, betikte, testte veya QML'de çağrısı yoktu (`git grep` ile önceki commit'te doğrulandı); yalnızca `DatabaseIntegrityService` ve TradingView istemcisi dokümanlarda anılıyordu, ilgili wiki sayfaları güncellendi. Tüm sayfalar (10) açılarak QML çalışma zamanı uyarısı olmadığı doğrulandı.
- Bilinçli olarak bırakılanlar: repository port/implementasyon çiftleri (CRUD tamlığı), `IInflationDataProvider`/`IMarketValuationProvider` protokolleri (modülleri başka istisna sınıfları için kullanılıyor), openpyxl/DTO alanı yanlış pozitifleri.

---
## [2026-10-03] sil | Eski Qt Widgets Arayüzü (`src/ui`) Kaldırıldı

- **Kaldırılanlar:** `src/ui` (sayfalar, widget'lar, QSS stilleri, tema yöneticisi, `L10N`), `tests/ui` (eski arayüz testleri), `scripts/migrate_ui_strings.py` (L10N göç betiği).
- **Giriş noktası:** `app.py` artık doğrudan QML arayüzünü açar (`run_qml_app`). `--ui=qml` bayrağı ve `PORTFOYSIM_UI` ortam değişkeni kaldırıldı; AppContainer kurulamazsa arayüz çevrimdışı modda açılır.
- **Korunan testler taşındı:** HTML üretici testleri `tests/application/reporting_html/`, Qt ölçek testi `tests/qt_compat/`; ağ çağrısı koruması ve giriş noktası testleri `tests/test_repo_guards.py` içinde. Yeni test `src/ui` paketinin ve ona yapılan importların geri gelmemesini denetler.
- **Betikler:** `fix_technical_analysis.py` son işlem günü için `price_update_service` kullanır; `measure_code_quality.py` içindeki `src/ui/pages` sayfa boyutu kuralı kaldırıldı.
- **Dokümanlar:** CLAUDE.md, ARCHITECTURE_GATES.md, README.md ve ilgili wiki sayfaları QML'e göre güncellendi; tarihsel wiki anlatımları (comparison_lab, ui_architecture_and_events, ai_integration) üstte not bırakılarak korundu.
- Silinen her şey git geçmişinde durur (`git log -- src/ui`); önceki commit'ten geri alınabilir.

---
## [2026-10-03] ekle | Eski Arayüzde Olup QML'de Eksik Kalan Özellikler Tamamlandı

Eski `src/ui` ile QML karşılaştırması sonunda bulunan 7 eksik giderildi:

- **Hisse detay hızlı işlem formu:** tarih (YYYY-AA-GG) ve saat (SS:DD) alanları; `parse_trade_moment` geçersiz biçim ve gelecek tarih/saati engeller. Boş bırakılırsa bugün/şimdi (geçmiş günde 12:00).
- **Dashboard:** "Fiyatları Güncelle" (`update_coordinator`, son kapanış fiyatları), haftalık/aylık getiri kartları (`return_calc_service`) ve "Son güncelleme" bilgisi. `ui_qml/last_update_store.py` eski arayüzle aynı QSettings anahtarlarını kullanır.
- **Model portföy "Fiyat Güncelle":** yalnızca veritabanını yeniden okuyordu; artık `live_price_refresh_service` ile (`model:{id}` kapsamı) çevrimiçi fiyat çeker, portföy bazlı son güncelleme zamanı gösterilir.
- **Listeye hisse eklerken kod doğrulaması:** `StockLookupService.is_known_ticker` (SQLite + DuckDB kataloğu, ağsız) ve bilinmeyen kodlar için arka planda `verify_ticker_online`; geçersizse "Geçersiz hisse kodu" ve kayıt oluşmaz.
- **Karşılaştırma grafik açıklama kartları** (`ChartInfoCard.qml`): sekmeye ve ana grafik moduna göre "Nedir / Nasıl Yorumlanır".
- **Sabit metinler:** ikinci geçişte ternary ve JS içindeki 29 Türkçe metin daha `Strings.qml`'e taşındı. `test_strings_catalog.py` artık property adından bağımsız, Türkçe harf içeren her dize literalini yakalar (controller ile değiş tokuş edilen durum kodları izin listesinde).
- Test kararlılığı: `DashboardController` açılışta getiri hesaplayan iş parçacığı başlattığından testlerde devre dışı bırakıldı (silinmiş QObject'e sinyal gönderip tam suitte ara sıra native çökme yapıyordu).
- Bilinçli fark: karşılaştırma metrik tablosu eski "Dönem Sonu Getiri Özeti" ile aynı içerikte olmadığı için ona açıklama kartı eklenmedi; TradingView yükleme butonu kaldırılmış kalır.

---
## [2026-10-03] duzelt | Mimari/Kalite Borcu: QML Katmanı Temizliği

- **`src.ui` bağımlılıkları kalktı:** Plotly/finansal/ortaklık HTML üreticileri `src/application/services/reporting/html/` altına, `ComparisonSeriesBuilder` `analysis/comparison_chart_series.py` altına taşındı; eski sayfalar ve testler yeni yolu kullanır. `L10N` ve `display_ticker` bağımlılıkları kaldırıldı. Eski `src/ui` hâlâ varsayılan giriş noktasıdır, silinmedi.
- **Denetleyicilerde doğrudan repository çağrısı kalmadı:** yeni `StockLookupService` (hisse, fiyat, önceki kapanış, canlı fiyat, DuckDB piyasa verisi) ve `DatabaseMaintenanceService`; piyasa düzeltmeleri `MarketCorporateActionService` üzerinden; planlama ham SQL yerine `portfolio_service.get_first_trade_date`; Gemini sağlayıcısı enjekte edilir.
- **Bu geçişte görülen mevcut hatalar giderildi:** model portföy Excel dışa aktarımı var olmayan repo metodu yüzünden tüm fiyatları 100 yazıyordu; hisse detayında var olmayan `price_repo.get_latest_price` yutulan hataydı.
- **QML sabit metinleri `Strings.qml`'e taşındı** (58 yeni anahtar, 19 dosya). Denetim testleri: `test_architecture_guards.py`, `test_strings_catalog.py`.
- Bilinçli olarak yapılmadı: denetleyicilerdeki dinamik Türkçe bildirim metinleri (biçimlendirme verisiyle iç içe), `AssetAllocationCard` örnek verisi, `settings_controller` içindeki `db_config` okuması.

---
## [2026-10-03] ekle | QML'de Kalan Backend Özellikleri Tamamlandı

- **Ayarlar > Sistem sekmesi:** otomatik canlı fiyat yenileme (aç/kapa, 5/15/30/60 dk; eski kodda aralık 15'e sabitti, düzeltildi; yalnızca seans açıkken) ve sistem sıfırlama (ortak `ConfirmDialog.qml` ile onaylı). `SystemController`.
- **Üst piyasa şeridi:** ALTIN, GÜMÜŞ, USD/TRY, EUR/TRY, BIST 100 (`MarketIndicatorsService`, `IMarketIndicatorProvider`, yfinance `fast_info`; 5 dk yenileme; dar pencerede gizli).
- **Excel "mevcut dosyaya ekle"** (`ExportMode.APPEND`) seçeneği; Dashboard ve model portföy dışa aktarımında.
- **Sürükle-bırak sıralama:** izleme listeleri ve model portföyler (`ReorderHandle.qml`, `moveWatchlist`, `movePortfolio`).
- **AI sohbet geçmişi:** `ChatSessionService` (uygulama katmanı, eski arayüzle aynı QSettings deposu), oturum listesi/devam/silme/yeni sohbet (`ChatHistoryDialog.qml`).
- **Hisse bazlı AI model analizi:** Yapay Zeka sayfası "Hisse Modeli" modu (`ModelAnalysisController`, `ModelAnalysisPanel.qml`). AI_Core erişilemezse sonuçlar rastgele DEMO verisidir ve belirgin biçimde işaretlenir.
- **Hisse Detay grafiğinde ortalama maliyet çizgisi** (`ChartController.loadTickerWithCost`, şablonda `renderAverageCostLine`).

---
## [2026-10-03] düzelt | Test ve Betik Güvenliği: Gerçek Veritabanına Yazma Engellendi

- **Sorun:** `.env` `override=True` ile yüklendiği için kabuktan verilen `DB_SQLITE_PATH` ezildi; "kopyada deneme" gerçek `portfolio.db` üzerinde çalıştı. `tests/ui_qml` içindeki gerçek `AppContainer()` kullanan testler de gerçek veritabanlarına yazıyordu (ör. izleme listesi testi `stocks` tablosuna kayıt bırakıyordu).
- **Düzeltme:** `_load_project_env` açıkça verilmiş `DB_SQLITE_PATH`/`DUCKDB_PATH` değerlerini korur. `tests/conftest.py` oturum başına gerçek SQLite (yedekleme API'siyle) ve DuckDB dosyalarını geçici klasöre kopyalayıp yolları oraya yönlendirir; test koşumu öncesi/sonrası gerçek dosya özetleri aynı kalır. Göç betiği çalışmadan önce çözümlenen SQLite/DuckDB yollarını yazdırır.
- Testler: 839 geçti, 4 xfail.

---
## [2026-10-03] degistir | Piyasa Evreni DuckDB'ye Taşındı, Sermaye Artırımı Düzeltmesi DuckDB'de, Ticker Tek Tip

- **Tüm BIST taraması:** Hisse Tarayıcı, Golden Cross, Hisse 360, grafik ve DCA evreni/fiyatlarını DuckDB'den (624 hisse) alır; `IMarketHistoryRepository` toplu okuma (`list_tickers`, `get_price_series_bulk`, `get_latest_dates`, `find_price_breaks`) kazandı. Gerçek veride tarayıcı ~2 sn, Golden Cross ~5 sn. Golden Cross olayları ticker anahtarlı `cross_events` tablosuna taşındı (eski `golden_cross_events` açılışta silinir). Açılışta BIST güncellemesi `MarketDataSyncService.sync_daily_delta` kullanır; TradingView yükleme düğmesi kaldırıldı.
- **Sermaye artırımı DuckDB'de:** ham barlar değişmez; `market_corporate_actions` faktörleriyle düzeltilmiş okuma (`adjusted=True` varsayılan). Veri güdümlü tespit (tek barlık hata ve kriz günü piyasa hareketi ayıklanır), onay/red, ham veride kırılma kalmayan olayları `NO_BREAK` yapan çift düzeltme koruması. Ayrıntı: [market_corporate_actions.md](market_corporate_actions.md).
- **SQLite göçü:** kullanıcı verisine bağlı olmayan 133 hissenin SQLite fiyatı ve kaydı silindi (305.692 satır, yedekli); 35 hisse kaldı. SQLite düzeltilmiş geçmişinden 10 geçmiş olay DuckDB'ye türetildi (yalnızca ham seri aynı kırılmayı gösteriyorsa; ham seri sürekliyse SQLite'ın hatalı olduğu anlaşılıp olay üretilmedi).
- **Ticker tek tip:** kanonik biçim uzantısız (`THYAO`); `.IS` yalnızca yfinance sınırında (`src/domain/ticker.py`). `stocks` kayıtları açılışta çevrilir; yazıcılar uzantı eklemez.
- **DuckDB bakımı:** kısmi (NULL kapanışlı) son 30 günlük barlar yeniden indirilir; indirici NaN/0 kapanışı eler ve 3 denemeli geri çekilme yapar.
- Testler: 831 geçti, 4 xfail.

---
## [2026-10-02] temizle | MySQL Kalıntıları Kaldırıldı ve SQLite/DuckDB Veri Katmanı Tutarlı Hale Getirildi

- **MySQL kaldırıldı:** `MySQLConfig`, `_create_mysql_engine`, MySQL `ON DUPLICATE KEY` dalları, `mysql-connector-python`, `DB_ENGINE/DB_HOST/DB_USER/DB_PASSWORD/DB_NAME/POOL_*` ortam değişkenleri (eski `.env` dosyalarında kalsa da yok sayılır), MySQL ORM `BIGINT(unsigned)` tipi (genel `BigInteger`), MySQL'e özgü betikler (`backup_mysql`, `migrate_mysql_to_sqlite`, `sync_mysql_backup_to_sqlite`, `compare_backup_to_sqlite`, `replicate_db`, 8 adet `apply_*_schema.py`, tüm `scripts/*.sql` DDL dosyaları) ve ilgili testler silindi. Tablolar `create_all` ile otomatik oluşur. `backups/` altındaki veri yedeklerine dokunulmadı.
- **Tek yol kaynağı:** `src/infrastructure/db/paths.py`; göreli yollar artık çalışma dizinine değil uygulama köküne göre çözülür (`DB_SQLITE_PATH`, `DUCKDB_PATH`). Dağınık `"data/market_history.duckdb"` sabitleri kaldırıldı.
- **DuckDB kalıntıları:**
  - `DuckDBPriceRepository` kullanılmıyordu ama her `AppContainer()` oluşturulurken DuckDB'ye yazma bağlantısı açıp tablo oluşturuyordu; silindi. Yerine salt okunur `DuckDBMarketHistoryRepository` (`IMarketHistoryRepository`) geldi.
  - **Köprü hatası:** `MarketDataSyncService._sync_to_sqlite` ham `sqlite3` ile `id` vermeden yazıyordu; her senkronda `NOT NULL constraint failed: daily_prices.id` ile sessizce başarısız oluyordu (SQLite portföy fiyatları güncellenmiyordu). Artık repository üzerinden yazılır, ayrıca `reconcile_sqlite_from_duckdb` geçmişte kaçan yeni barları (gerçek veride ~10 bin bar) kapatır.
  - Ayarlar > "Senkronize et" olmayan `sync_missing_data` metodunu çağırıyordu; `sync_daily_delta` ile düzeltildi.
  - DCA'daki "DuckDB fallback" `price_repo.get_price_series_by_ticker` varlığına bakıyordu (SQLAlchemy repo'da yok, ölü koddu); gerçek `market_history_repo` fallback'i bağlandı.
  - Grafik: portföyde (SQLite) olmayan hisseler için DuckDB'den veri okunur. Hisse Detay ham `duckdb.connect(read_only=False)` yerine salt okunur depoyu kullanır.
- Yeni wiki sayfası: [data_architecture.md](data_architecture.md) (hangi veri hangi veritabanında, kurallar, bilinen sınırlar).
- Testler: 791 geçti (yeni: yol çözümleme, DuckDB okuyucu, DCA fallback, köprü, uzlaştırma).

---
## [2026-10-02] düzelt | Bayat Fiyat: Dashboard Günlük Değişimi, Canlı Fiyat Önbelleği SQLite Upsert'i ve Golden Cross Yazımı

- **Belirti:** Dashboard "Günlük Kâr/Zarar +%81" gibi anlamsız değerler gösteriyordu.
- **Kök neden 1:** `latest_prices` (canlı fiyat önbelleği) 11 Eylül'den kalmıştı; `daily_prices` ise 1 Ekim'e kadar güncel. Dashboard eski canlı fiyatı yeni kapanışla karşılaştırıyordu. Canlı yenileme hiç kalıcı olmuyordu çünkü `SQLAlchemyLatestPriceRepository.upsert_latest_prices` MySQL'e özgü `ON DUPLICATE KEY UPDATE` kullanıyordu ve SQLite'ta `UnsupportedCompilationError` fırlatıyordu (hata arka plan thread'inde yutuluyordu).
- **Kök neden 2:** `SQLAlchemyGoldenCrossRepository.upsert_events_bulk` aynı MySQL SQL'ini kullanıyordu; yeni Golden Cross taraması SQLite'ta kayıt yazamazdı.
- **Çözüm:**
  - Her iki repository'ye SQLite dalı eklendi (`ON CONFLICT`, BIGINT birincil anahtar otomatik artmadığı için id elle verilir; golden cross yalnızca yeni olayları sayar).
  - Yeni `CurrentPriceResolver` (`src/application/services/market/current_price_resolver.py`, container'da `current_price_resolver`): canlı fiyat yalnızca son günlük kapanıştan daha yeni bir güne aitse kullanılır, aksi halde son kapanış. Günlük değişim, seçilen fiyatın gününden önceki kapanışa göre hesaplanır (`get_last_price_before` "verilen gün dahil" olduğu için bir gün öncesi istenir).
  - Dashboard, Model Portföy (fiyat haritası, önceki kapanış, son fiyat arama), Hisse Detay ve Sermaye Artırımı fiyat okumaları resolver'a bağlandı.
- **Doğrulama (gerçek veri):** Toplam değer ₺598.908 -> ₺376.970, günlük +%1.53 (OBAMS +%6.74, grafikle aynı).
- Testler: resolver birim testleri, SQLite upsert testleri (`tests/infrastructure/db/test_sqlite_upserts.py`); `test_production_guards` sahte API anahtarı literalini yakalıyordu, test değeri değiştirildi. 791 test geçti.

---
## [2026-10-02] ekle | QML: Golden Cross, Risk Anketi, Karşılaştırma Eklentileri, Excel Aralığı, İşlem Tarih/Saat ve Responsive Düzen (Eski UI Eşitleme - Grup 3)

- **Hisse Tarayıcı > Golden Cross sekmesi:** `GoldenCrossController` + `GoldenCrossTab.qml`. EMA50/EMA200 kesişim sinyalleri (dönem/tip filtresi), tüm BIST taraması, veri tamamlama, TradingView'den yükleme, hisse bazlı geçmiş. Açılışta son taramadan 24 saat geçmişse otomatik tarama (`StartupJobsController`). Tarayıcı ekranı `ScreenerStrategiesTab` + `GoldenCrossTab` sekmelerine bölündü; tek tıkta Hisse 360'a gidişteki yanlış slot adı (`searchStock` -> `searchTicker`) düzeltildi.
- **Risk profili anketi:** `RiskProfileController` + `RiskQuestionnaireDialog.qml` (Optimizasyon > Risk Anketi). Kayıtlı profil seçimi ve tek hisse ağırlık kısıtı anket sonrası güncellenir; risk combo'su controller durumuna bağlandı.
- **Karşılaştırma:** özel tarih aralığı, TL/USD/Reel para birimi, "Portföy + Hisseleri" (tek tek hisse kıyası), Gemini AI yorumu (`ComparisonAiDialog`). `GeminiChatProvider` anahtarı artık her istekte okur (Ayarlar'dan değiştirince yeniden başlatma gerekmez).
- **Excel:** `ExcelExportDialog` ile tarih aralığı + kayıt konumu (Dashboard günlük rapor, Model Portföy tarihsel rapor).
- **İşlem:** Hızlı işlem modalına tarih/saat, hisse kodundan şirket adı ve son fiyat (sabit 294.25 fiyat kaldırıldı); Hisse Detay'da işlem etkisi tahmini (yeni lot, ortalama maliyet, kalan nakit).
- **Responsive/esnek düzen:** pencere asgari boyutu 720x480; 1100 px altında kenar çubuğu otomatik daralır; sayfa içeriği asgari ölçünün (`minContentWidth/minContentHeight`) altında kaydırılır; iki panelli sayfalar (Model Portföy, Karşılaştırma, Optimizasyon, AI, İzleme Listeleri, Planlama) dar pencerede alt alta dizilir; KPI şeritleri 2x2'ye iner; pozisyon/izleme tabloları yatay kaydırılır; Hisse Detay modalı tek sütuna iner; başlık ve sekme çubukları `Flow`/`GridLayout` ile sarar. Ofscreen render ile 780x560, 900x600, 1024x640, 1366x768 boyutlarında görsel doğrulandı.
- Test: eski kodda gerçek piyasa verisine sabit sayıyla bağlı `test_stock_detail_controller_live_price_and_diff` repository'lerden beklenen değeri hesaplayacak şekilde güncellendi. 168/168 QML testi yeşil.

---
## [2026-10-02] ekle | QML: Kurumsal Aksiyon, Fiyat Verisi Sağlığı ve Açılış Veri Bakım İşleri (Eski UI Eşitleme - Grup 2)

- Eski PyQt5 arayüzünde olup QML'e taşınmamış backend özellikleri bağlandı:
  - **Sermaye artırımı girişi:** `CorporateActionController` + `CorporateActionDialog.qml`. Hisse Detay modalındaki "Sermaye Artırımı" butonundan (yalnızca ana portföy pozisyonu) bedelli/bedelsiz kaydı, canlı ön izleme (yeni lot, yeni ort. maliyet, teorik baz fiyat), portföye uygulama ve geçmiş fiyatları yeniden indirme. Uygulama başarısız olursa kaydedilen bekleyen aksiyon silinir (yeniden denemeyi engellemesin).
  - **KAP/MKK aday paneli:** Ayarlar > Kurumsal Aksiyonlar sekmesi (`SettingsCorporateActionsTab.qml`): tarama, düzenleme, onayla ve uygula, yoksay, kaynağı aç.
  - **Fiyat Verisi Yönetimi:** `PriceDataController` + Ayarlar > Fiyat Verisi sekmesi (`SettingsPriceDataTab.qml`): eksik gün analizi, toplu/seçili/son günden bugüne güncelleme, aralık silme, raporu panoya kopyalama. Rapor biçimlendirmesi UI'dan bağımsız `price_data_report_formatter.py` modülüne alındı.
  - **Açılış otomatik işleri:** `StartupJobsController` portföy hisseleri backfill'i, 18:30 sonrası tüm BIST backfill'i ve günlük KAP/MKK taramasını eski UI ile aynı QSettings anahtarlarıyla (günde bir kez) çalıştırır; sonuçlar global toast ve ekran yenilemesiyle bildirilir.
- Ayarlar ekranı toast'ı hiç görünmüyordu (`settingsToast` mesajı bağlı değildi ve `visible` bağlaması `isVisible`'ı gizliyordu); doğrudan `show()` çağrılarına çevrildi. Başlık/sekme çubuğu 6 sekme için `Flow`'a alındı (dar pencerede alt satıra sarar).
- **Grup 1 (kırık akışlar):** API anahtarı kaydı frozen ayarlarda `FrozenInstanceError` veriyordu, artık `persist_api_keys` ile `.env`'ye yazılıyor; Hisse Detay işlemi `TradeEntryService` üzerinden geçiyor; seans durumu `bist_market_session_service`'ten okunuyor; piyasa senkronu sonrası Dashboard/Model Portföy yenileniyor; demo veri yalnızca container yokken üretiliyor.
- Test altyapısı: `tests/conftest.py` testlerin gerçek `.env`'ye yazmasını engeller; `tests/ui_qml/conftest.py` Basic stili ayarlar ve `MarketSyncController` açılış zamanlayıcısını devre dışı bırakır (test süresi uzayınca gerçek DuckDB senkronu başka testlerle çakışıp native çökmeye yol açıyordu). 128/128 QML testi yeşil.
- Etkilenen modüller: src/ui_qml/controllers/corporate_action_controller.py, price_data_controller.py, startup_jobs_controller.py, src/application/services/market/price_data_report_formatter.py, src/ui_qml/qml/components/ (CorporateActionDialog, CorporateActionCandidateEditDialog, SettingsCorporateActionsTab, SettingsPriceDataTab, ModernInput, StockDetailModal), src/ui_qml/qml/views/SettingsView.qml, src/ui_qml/qml/theme/Strings.qml, src/ui_qml/app.py, tests/ui_qml/

---
## [2026-10-02] düzelt | Dashboard Açık Pozisyonlar Tablosu Kolon Başlıkları ve Hücre Hizalaması

- `DashboardView.qml` içerisindeki açık pozisyonlar tablosunda başlık satırı (`RowLayout`) ile veri satırları (`RowLayout`) arasındaki kolon kayması sorunu giderildi:
  - Sorun: Tablo başlığı ile veri delegesinde esnek/sabit genişlik tanımlarının tam kilitlenmemesi ve Qt Quick `RowLayout` yerleşim motorunun kalan alanı metin uzunluklarına göre paylaştırması nedeniyle kolon başlıkları ile veri hücreleri bir basamak sağa kayıyordu (örneğin LOT başlığı boşluğa, MALİYET başlığı lot adedine denk geliyordu).
  - Çözüm: Başlık ve veri satırlarındaki tüm sayısal sütunlar ve aksiyon butonları (`SEMBOL & ŞİRKET`, `LOT: 70px`, `MALİYET: 85px`, `SON FİYAT: 85px`, `GÜNLÜK %: 75px`, `PİYASA DEĞERİ: 115px`, `K/Z (₺): 110px`, `K/Z %: 75px`, `AĞIRLIK: 65px`, `İŞLEMLER: 195px`) `Layout.preferredWidth`, `Layout.minimumWidth` ve `Layout.maximumWidth` değerleriyle 1:1 piksel kilitlendi.
  - Esnek genişlik sadece ilk sütuna (`Layout.fillWidth: true; Layout.minimumWidth: 160`) verilerek pencere yeniden boyutlandırılsa dahi tüm sayısal hücrelerin başlıklarıyla kusursuz hizada kalması sağlandı.
  - Testler: 82/82 QML testi başarıyla tamamlandı.
- Etkilenen modüller: src/ui_qml/qml/views/DashboardView.qml, docs/wiki/log.md

## [2026-10-02] düzelt | Hisse Detay Modalı Fiyat & K/Z Senkronizasyonu ve UI .IS Temizliği

- Hisse Detay Modalı (`StockDetailModal`) ve `StockDetailController` bünyesindeki canlı fiyat, günlük değişim, piyasa değeri ve K/Z uyumsuzlukları giderildi:
  - Fiyat Kaynağı Senkronizasyonu: `_get_latest_price` metodu öncelikle `latest_price_repo` ve `price_repo` üzerinden canlı portföy değerlendirme fiyatlarını (`1.21` TL MERKO, `3.15` TL PSGYO) çekecek şekilde güncellendi; DuckDB'de eksik/boş barlardan kaynaklanan `₺ - %-100.00` anomalisine karşı `WHERE close_price IS NOT NULL AND close_price > 0` filtresi uygulandı.
  - Pozisyon & K/Z Hesaplaması: Piyasa değeri (`market_value`), kâr/zarar tutarı (`unrealized_pnl`) ve yüzdesi (`unrealized_pnl_pct`) Dashboard tablosuyla kuruşu kuruşuna eşitlendi.
  - Hızlı Emir Formu: Modal açıldığında veya hisse değiştiğinde birim fiyatın hardcoded `10.00` kalması engellendi; hissenin anlık fiyatına otomatik senkronize edildi.
  - Sermaye Artırımı Şeffaflığı: MERKO gibi bölünme (bedelsiz %638.34) yaşamış hisselerde işlem geçmişindeki lot adedi güncel bölünmüş pozisyonla eşleştirildi; bölünme öncesi orijinal işlem tutarı için "B" (Bölünme/Bedelsiz) rozeti ve hover tooltip desteği eklendi.
  - Model Portföy Entegrasyonu: Modal model portföy bağlamında açıldığında pozisyon metriklerinin ve alım/satım emirlerinin model portföy servisine yönlendirilmesi sağlandı.
  - UI .IS Temizliği: Varlık dağılımı donut pasta grafiği legend etiketleri (`allocationSlices`), hızlı butonlar (`quickTickers`) ve TradingView grafik başlığındaki `.IS` kalıntıları temizlendi.
- Testler: `tests/ui_qml/test_stock_detail_and_excel.py` (10/10 yeni test), toplam QML testleri 82/82 %100 yeşil.
- Etkilenen modüller: src/ui_qml/controllers/stock_detail_controller.py, src/ui_qml/controllers/dashboard_controller.py, src/ui_qml/controllers/chart_controller.py, src/ui_qml/qml/components/StockDetailModal.qml, src/ui_qml/qml/Main.qml, src/ui_qml/assets/templates/tradingview_chart.html, tests/ui_qml/test_stock_detail_and_excel.py, docs/wiki/log.md

## [2026-10-02] özellik | Hisse Detay Modalı ve Çok Sayfalı Profesyonel Excel Dışa Aktarımı QML Mimarisine Eklendi

- Eski PyQt5 arayüzündeki hisse detay sayfası ve Excel raporlama motorları taranarak QML mimarisine temiz bir Clean Architecture adaptörüyle kazandırıldı:
  - `StockDetailController` (`src/ui_qml/controllers/stock_detail_controller.py`): Asenkron ThreadPoolExecutor, pozisyon metrikleri (lot, maliyet, k/z, ağırlık), hisseye özel geçmiş işlem listesi (`portfolio_service.get_trades_for_stock`), sermaye artırımları/bedelsiz/bedelli geçmişi (`corporate_action_service.get_by_stock`), doğrudan hisse alım/satım emri (`submitTrade`), ve hisseye özel açık/kapalı işlem ve sermaye hareketlerini içeren biçimlendirilmiş Excel raporu üretimi (`exportStockToExcel`).
  - `StockDetailModal.qml` (`src/ui_qml/qml/components/StockDetailModal.qml`): Modern fintech koyu tema overlay modalı. Canlı fiyat başlığı, 4 KPI kartı, sekmeli geçmiş işlemler & sermaye artırımları tablosu, hızlı alım/satım işlem formu ve TradingView / Hisse 360 / Excel kısayol butonları.
  - Suffix Temizliği: UI üzerinde hiçbir yerde `.IS` uzantısı kalmaması kuralı titizlikle uygulandı (`_clean_ticker`).
  - Excel Raporlama: `ExcelExportService` (Dashboard, Günlük Getiriler, Hisse Dağılımı ve KPI'lar) ve `ModelPortfolioExcelExportService` (Model Portföy pozisyon ve performans dökümü) servisleri `DashboardController`, `ModelPortfolioController` ve `SettingsController` bileşenlerine tek tıkla Excel dışa aktarım (`exportToExcel`) aksiyonları olarak entegre edildi.
  - Testler: `tests/ui_qml/test_stock_detail_and_excel.py` (8/8 yeni test), toplam QML testleri 80/80 %100 yeşil.
- Etkilenen modüller: src/ui_qml/controllers/stock_detail_controller.py, src/ui_qml/controllers/dashboard_controller.py, src/ui_qml/controllers/model_portfolio_controller.py, src/ui_qml/controllers/settings_controller.py, src/ui_qml/app.py, src/ui_qml/qml/theme/Strings.qml, src/ui_qml/qml/components/StockDetailModal.qml, src/ui_qml/qml/views/DashboardView.qml, src/ui_qml/qml/views/ModelPortfolioView.qml, src/ui_qml/qml/Main.qml, tests/ui_qml/test_stock_detail_and_excel.py, docs/wiki/log.md

## [2026-10-02] güncelleme | FAZ 9: Markowitz Portföy Optimizasyonu & Efficient Frontier Tamamlandı

- PySide6 + Qt Quick (QML) mimarisi için Faz 9 Markowitz Portföy Optimizasyonu ve Verimli Sınır modülü eksiksiz tamamlandı.
- `DuckDBOptimizationMarketDataProvider` geliştirilerek `market_history.duckdb` (624 BIST hissesi, 2.2M bar) ile kovaryans matrisi ve tarihsel fiyatlar milisaniyeler içinde çekilebilir kılındı.
- `frontier_simulation.py` modülü ile vektörel Monte Carlo simülasyonu (1.000 portföy noktası), SLSQP Verimli Sınır eğrisi koordinatları ve parasal/lot bazlı yeniden dengeleme (rebalance) planlayıcısı uygulandı.
- `OptimizationController` (asenkron ThreadPoolExecutor, Qt Queued Signals, Chart.js HTML5 scatter/bar grafiği, risk profili/ağırlık kısıtı yönetimi) ve `OptimizationView.qml` (modern fintech arayüzü, 4 KPI kartı, 3 sekme, dinamik rebalance tablosu) geliştirildi.
- Testler: `tests/ui_qml/test_optimization_phase9.py` (5/5 yeni test), toplam QML testleri 56/56 %100 yeşil.
- Etkilenen modüller: src/infrastructure/market_data/duckdb_optimization_market_data_provider.py, src/application/services/planning/frontier_simulation.py, src/ui_qml/controllers/optimization_controller.py, src/ui_qml/qml/views/OptimizationView.qml, src/ui_qml/qml/theme/Strings.qml, src/ui_qml/app.py, src/ui_qml/qml/Main.qml, tests/ui_qml/test_optimization_phase9.py, QML_TRANSFORMATION_HANDOFF.md, docs/wiki/log.md

## [2026-10-02] belge | QML Dönüşüm Handoff Kılavuzu Faz 6-8, DuckDB ve Otomatik Senkronizasyonla Güncellendi

- `QML_TRANSFORMATION_HANDOFF.md` dosyası projenin yeni oturumlardan pürüzsüzce devralınabilmesi için baştan sona güncellendi.
- Tamamlanan aşamalar (Faz 6: Model Portföyler, Faz 7: Karşılaştırma & Screener & Treemap, Faz 8: Bütçe & Hedefler & DCA Simülatörü, DuckDB 624 BIST hissesi 2.2M bar OLAP altyapısı, 18:15 otomatik seans kapanış senkronizasyonu) detaylıca belgelendi.
- Kalan fazların (Faz 9: Markowitz Portföy Optimizasyonu & Efficient Frontier, Faz 10: Gemini AI Karar Destek Danışmanı, Faz 11: Ayarlar & Veritabanı Yönetimi & Dağıtım) kapsamı, servis gereksinimleri, QML bileşenleri ve test planları yazıldı.
- Yeni oturumlarda asistana verilecek doğrudan komut şablonu eklendi.
- Etkilenen modüller: QML_TRANSFORMATION_HANDOFF.md, docs/wiki/index.md, docs/wiki/log.md

## [2026-09-30] refaktör | Bulgu 5: Stock360Controller Monolit Yapısı Modüler Alt Bileşenlere Ayrıştırıldı

- `Stock360Controller` bünyesindeki 1.442 satırlık monolit "God Object" yapısı Clean Architecture ve tek sorumluluk prensibi (SRP) doğrultusunda modüler alt bileşenlere ayrıştırıldı:
  - `src/ui_qml/controllers/stock_360_formatters.py`: Finansal para birimi, fiyat, hacim ve grafik renk paleti mantığı taşındı.
  - `src/ui_qml/controllers/stock_360_fallback.py`: Dış servisler çevrimdışı olduğunda kullanıcı deneyimini kesintisiz kılan sektör haritası ve fallback bilanço/rasyo/KAP verileri izole edildi.
  - `src/ui_qml/controllers/stock_360_html.py`: QML WebEngine için geçici HTML dashboard derleme ve geçici dosya temizleme lojiği modülerleştirildi.
  - `src/ui_qml/controllers/stock_360_calc.py`: DuPont analizi, serbest nakit akımı, gelir grafiği, bilanço detay tablosu ve KAP pay sahipliği çizelgesi hesaplama motorları saf fonksiyonlara dönüştürüldü.
- `Stock360Controller` satır sayısı 1.442'den 834'e düşürüldü; sınıf salt QML ViewModel durumunu ve sinyallerini yönetir hale getirildi.
- Geriye dönük uyumluluk ve tüm QML test sözleşmesi (`tests/ui_qml/test_stock_360_phase5.py`, 11 test; `test_stock_360_modules.py`, 6 test) %100 korundu.
- Etkilenen modüller: src/ui_qml/controllers/stock_360_controller.py, src/ui_qml/controllers/stock_360_formatters.py, src/ui_qml/controllers/stock_360_fallback.py, src/ui_qml/controllers/stock_360_html.py, src/ui_qml/controllers/stock_360_calc.py, tests/ui_qml/test_stock_360_modules.py, docs/wiki/log.md

## [2026-09-30] refaktör | Bulgu 6: QML Controller Doğrudan Repository Katman İhlalleri Application Servislerine Bağlandı

- `ARCHITECTURE_GATES.md §6` ("UI katmanı asla doğrudan Repository çağırmaz; tüm veri erişimleri Application servisleri üzerinden gerçekleşmelidir") kuralı sağlandı.
- `Stock360Service` bünyesine Application facade metodları (`get_all_stocks`, `get_stock_by_ticker`, `get_price_series`) eklendi.
- `ChartController` ve `Stock360Controller` içindeki doğrudan `stock_repo` ve `price_repo` çağrıları temizlenerek `Stock360Service` ve `PortfolioService` servis katmanlarına devredildi.
- Etkilenen modüller: src/application/services/analysis/stock_360_service.py, src/ui_qml/controllers/chart_controller.py, src/ui_qml/controllers/stock_360_controller.py, docs/wiki/log.md

## [2026-09-30] refaktör | Bulgu 7: ChartController Teknik İndikatör ve Cross Hesaplamaları DRY Standardına Bağlandı

- `ChartController` bünyesinde elle yazılan ve kod tekrarına (DRY ihlali) yol açan Golden/Death Cross tespit döngüsü, `src/application/services/analysis/technical/golden_cross.py` içindeki `detect_crosses` motoruna delege edildi.
- Kısa vadeli veya az verili seriler için SMA bazlı zarif geri dönüş (graceful fallback) mekanizması korunarak TradingView sinyal işaretçileri merkezi domain kurallarıyla üretildi.
- Etkilenen modüller: src/ui_qml/controllers/chart_controller.py, docs/wiki/log.md

## [2026-09-30] optimize | Bulgu 8: QML Controller'larında N+1 Senkron DB Sorguları Toplu Sorguya (Bulk) Dönüştürüldü

- `WatchlistController` ve `DashboardController` döngüleri içinde her hisse için ayrı ayrı çalıştırılan senkron veritabanı sorguları (N+1 problemi) tespit edilerek toplu (bulk) yöntemlere geçirildi.
- `IPriceRepository` arayüzüne ve `SQLAlchemyPriceRepository` uygulamasına `get_price_series_bulk(stock_ids, start_date, end_date)` metodu eklendi; takip listesindeki hisselerin geçmiş fiyat serileri tek bir `WHERE stock_id IN (...)` sorgusuna indirildi.
- `DashboardController._load_portfolio_data` içinde her pozisyon için tekrarlanan `get_stock_by_id` çağrıları `get_stocks_by_ids` toplu sorgusuna bağlanarak bellek içi O(1) eşleşmeye dönüştürüldü; UI thread bloklanmaları ortadan kaldırıldı.
- Etkilenen modüller: src/domain/ports/repositories/i_price_repo.py, src/infrastructure/db/sqlalchemy/repositories/sa_price_repository.py, src/ui_qml/controllers/watchlist_controller.py, src/ui_qml/controllers/dashboard_controller.py, docs/wiki/log.md

## [2026-09-30] düzelt | Bulgu 12: PositionsTableModel İçindeki K/Z ve Piyasa Değeri Hesaplamaları Decimal Hassasiyetine Bağlandı

- `RULES.md` ve `ARCHITECTURE_GATES.md` finansal hesaplama standartları gereğince açık pozisyonlar tablosundaki canlı fiyat güncelleme mantığı (`PositionsTableModel.update_prices`) `Decimal` hassasiyetine bağlandı.
- Ham kayan nokta (`float`) işlemlerinden kaynaklanabilecek yuvarlama hataları ve parasal tutar sapmaları önlendi; piyasa değeri, gerçekleşmemiş kâr/zarar ve yüzde değişimleri kesin matematiksel aritmetik üzerinden hesaplandı.
- Etkilenen modüller: src/ui_qml/models/positions_table_model.py, docs/wiki/log.md

## [2026-09-30] düzelt | Bulgu 17: Deprecated datetime.utcnow() Çağrıları timezone.utc ile Modernize Edildi

- Python 3.12+ ile kullanımdan kaldırılan ve saat dilimi (timezone) uyuşmazlıklarına neden olabilen `datetime.utcnow()` çağrıları `datetime.now(timezone.utc)` ile modernize edildi.
- `src/application/services/analysis/shareholder_analysis_service.py` ve `src/infrastructure/db/sqlalchemy/repositories/sa_shareholder_repository.py` dosyalarında UTC zaman karşılaştırmaları naive/aware istisnalarına karşı korumalı hale getirildi.
- Etkilenen modüller: src/application/services/analysis/shareholder_analysis_service.py, src/infrastructure/db/sqlalchemy/repositories/sa_shareholder_repository.py, docs/wiki/log.md

## [2026-09-30] düzelt | Bulgu 19: Sayı ve Hacim Formatları Türkçe Kısaltma Standardına (Mr/Mn/Bin) Çevrildi

- `RULES.md §3` kuralı ("Para ve sayı formatları Türkçe standartlarında olmalıdır") uyarınca İngilizce kalan `B` (Billion), `M` (Million) ve `K` (Thousand) sayı/hacim kısaltmaları Türkçe finansal standart olan `Mr` (Milyar), `Mn` (Milyon) ve `Bin` olarak güncellendi.
- `src/ui_qml/controllers/stock_360_controller.py` içindeki `_format_volume` fonksiyonu ve `src/ui_qml/controllers/watchlist_controller.py` bünyesindeki hacim gösterimleri tutarlı hale getirildi.
- Etkilenen modüller: src/ui_qml/controllers/stock_360_controller.py, src/ui_qml/controllers/watchlist_controller.py, docs/wiki/log.md

## [2026-09-30] düzelt | Bulgu 14: QML Arayüzündeki Sabit (Hardcoded) Metinler Strings Sözlüğüne Taşındı

- `RULES.md §3` kuralı ("Tüm kullanıcı metinleri ve etiketler Strings.qml içinde toplanmalıdır") uyarınca QML bileşenlerinde sabit gömülü kalan tüm metinler `src/ui_qml/qml/theme/Strings.qml` merkezi sözlüğüne aktarıldı.
- `CapitalModal.qml`, `QuickTradeModal.qml`, `FintechDuPontCard.qml`, `FintechCashFlowCard.qml`, `FintechRevenueChart.qml`, `MetricCard.qml`, `WatchlistView.qml` ve `Stock360View.qml` içerisindeki form başlıkları, rasyo rozetleri (badge), finansal gösterge adları ve alt metinler `Strings.<değişken>` çağrılarına bağlandı.
- Etkilenen modüller: src/ui_qml/qml/theme/Strings.qml, src/ui_qml/qml/components/CapitalModal.qml, src/ui_qml/qml/components/QuickTradeModal.qml, src/ui_qml/qml/components/FintechDuPontCard.qml, src/ui_qml/qml/components/FintechCashFlowCard.qml, src/ui_qml/qml/components/FintechRevenueChart.qml, src/ui_qml/qml/components/MetricCard.qml, src/ui_qml/qml/views/Stock360View.qml, src/ui_qml/qml/views/WatchlistView.qml, docs/wiki/log.md

## [2026-09-30] düzelt | Bulgu 20: auto_commit.py Hassas Dosya ve Anahtar Sızıntısı Koruması Eklendi

- `auto_commit.py` scriptinde `.env`, gizli anahtarlar, veritabanı dosyaları ve kimlik bilgilerini (`*.pem`, `*.key`, `*secret*`, `*credential*`, `*token*`, `*.db`, `.env*`) tespit eden `is_sensitive_file` güvenlik süzgeci entegre edildi.
- Hassas dosyaların ve diff içeriklerinin harici yapay zeka modeline (Gemini API) kazara sızdırılması hem dosya listeleme aşamasında hem de diff üretim aşamasında çift katmanlı olarak engellendi.
- Etkilenen modüller: auto_commit.py, docs/wiki/log.md

## [2026-09-30] yapılandır | Bulgu 10: requirements.txt Bağımlılıkları ve Sürümleri Sanal Ortamla Eşitlendi

- `requirements.txt` dosyasındaki gerçek dışı / yayınlanmamış sürüm pinleri (numpy 2.4.4, pandas 3.0.2, scipy 1.17.1, scikit-learn 1.8.0, plotly 6.7.0, pytest 9.0.3) sanal ortamdaki fiili kararlı sürümlerle (`numpy==2.2.6`, `pandas==2.3.3`, `scipy==1.15.3`, `scikit-learn==1.7.2`, `PySide6==6.11.2`, `SQLAlchemy==2.0.54`, `yfinance==1.7.0`, `plotly==7.1.0` vb.) senkronize edildi.
- yfinance ve scraping için zorunlu olan `beautifulsoup4`, `lxml` ve `curl_cffi` bağımlılıkları açıkça listeye eklendi; `pip check` ve `scripts/build_preflight.py` statik pin kontrolü (%100 yeşil) başarıyla doğrulandı.
- Etkilenen modüller: requirements.txt, docs/wiki/log.md

## [2026-09-30] düzelt | Bulgu 13: Sessiz Hata Yutma (except Exception: pass) Blokları Logger İle Değiştirildi

- `ARCHITECTURE_GATES.md` ve temiz kod standartları gereğince sistem genelinde istisnaların sessizce yutulduğu (`except Exception: pass`) 7 kritik nokta refaktör edildi.
- `src/ui_qml/controllers/chart_controller.py`, `src/ui_qml/controllers/dashboard_controller.py`, `src/ui_qml/controllers/stock_360_controller.py`, `src/infrastructure/db/sqlalchemy/database_engine.py`, `src/infrastructure/market_data/yfinance_valuation_provider.py`, `src/application/services/ai/safety_guard.py` ve `src/application/services/planning/optimization_service.py` dosyalarında oluşan tüm istisnalar seviyesine uygun logger (`logger.warning` veya `logger.debug`) çağrılarıyla kayıt altına alındı.
- Etkilenen modüller: src/ui_qml/controllers/chart_controller.py, src/ui_qml/controllers/dashboard_controller.py, src/ui_qml/controllers/stock_360_controller.py, src/infrastructure/db/sqlalchemy/database_engine.py, src/infrastructure/market_data/yfinance_valuation_provider.py, src/application/services/ai/safety_guard.py, src/application/services/planning/optimization_service.py, docs/wiki/log.md

## [2026-09-30] düzelt | Bulgu 9 & Bulgu 15: Flaky UI Testleri Deterministik Yapıldı ve Geçici Dosya Temizliği Bağlandı

- `tests/ui_qml/test_stock_360_phase5.py` içindeki `time.sleep(1.5)` statik beklemeleri kaldırılarak `_wait_for_condition` (Qt event loop polling) deterministik asenkron beklemeye dönüştürüldü; test koşum süresi 11 saniyeden 6.6 saniyeye indi (%40 hızlanma).
- `Stock360Controller` bünyesine `QCoreApplication.aboutToQuit`, `destroyed` sinyalleri ve `__del__` yıkıcısı bağlanarak `_cleanup_temp_files()` otomatik çağrıma kavuşturuldu; diskte biriken geçici HTML raporlarının sızıntısı kalıcı olarak önlendi.
- Etkilenen modüller: src/ui_qml/controllers/stock_360_controller.py, tests/ui_qml/test_stock_360_phase5.py, docs/wiki/log.md

## [2026-09-30] düzelt | Bulgu 18: FintechShareholderTimeline.qml İçindeki Unicode Ok Karakteri Temizlendi

- `RULES.md §2.1` ve `§2.2` strict no-emoji ve merkezi vektörel ikon politikası uyarınca `FintechShareholderTimeline.qml` dosyasındaki ham Unicode ok karakterleri (`\u2794`) temizlendi ve standart `->` formatına dönüştürüldü.
- `src/ui_qml` genelinde kalan emoji sayısı 0'a indirildi.
- Etkilenen modüller: src/ui_qml/qml/components/FintechShareholderTimeline.qml, docs/wiki/log.md

## [2026-09-30] test | Bulgu 11 & Bulgu 16: İş Yatırım Cache Testi ve Python Sürüm Preflight Guard Düzeltildi

- `tests/infrastructure/market_data/test_isyatirim_provider.py` içindeki `_MINIMAL_RAW` fixture'ına 4 çeyrek veri eklenerek cache hit testi başarılı kılındı (11/11 test yeşil).
- `scripts/build_preflight.py` içerisindeki Python sürüm eşiği, `CLAUDE.md` standardı olan `Python >= 3.10` ile uyumlandırıldı; `test_production_guards.py` yeşile döndü.
- Tüm `tests/infrastructure` testleri (120/120) sıfır hatayla geçti.
- Etkilenen modüller: tests/infrastructure/market_data/test_isyatirim_provider.py, scripts/build_preflight.py, docs/wiki/log.md

## [2026-09-30] yapılandır | Bulgu 4: Nuitka Build Betiği PySide6 ve QML Mimarisine Uyurlandı

- `build_nuitka.bat` içindeki sabit geliştirici yolu (`C:\Users\ysfygc\...`) kaldırılıp yerel sanal ortam dinamik tespitine bağlandı (`.\venv\Scripts\python.exe`).
- Nuitka derleyicisine `--enable-plugin=pyside6`, `--include-data-dir=src/ui_qml=src/ui_qml` ve `--include-data-dir=data=data` parametreleri eklendi; eski PyQt5 plugin'i kaldırıldı.
- Etkilenen modüller: build_nuitka.bat, docs/wiki/log.md

## [2026-09-30] düzelt | Bulgu 3: test_settings_loader.py Test Ortam İzolasyonu ve SQLite Desteği Eklendi

- `tests/infrastructure/test_settings_loader.py` içindeki `OPTIONAL_ENV` kümesine `DB_ENGINE` ve `DB_SQLITE_PATH` eklendi; işletim sistemi ortamından sızan SQLite değişkenlerinin MySQL testlerini patlatması önlendi (7 test yeşile döndü).
- `test_load_settings_builds_sqlite_config` birim testi eklenerek SQLite yapılandırmasının dinamik yüklenmesi test kapsamına alındı (10/10 test %100 yeşil).
- Etkilenen modüller: tests/infrastructure/test_settings_loader.py, docs/wiki/log.md

## [2026-09-30] düzelt | Bulgu 2: Dashboard Fiyat Yenilemedeki Sahte Veri Kaldırıldı ve Canlı Servise Bağlandı

- `DashboardController.refreshMetrics()` içindeki sentetik `np.random.normal` fiyat üretim mantığı tamamen kaldırıldı.
- Fiyat yenileme işlemi asenkron arka plan iş parçacığı üzerinden gerçek `LivePriceRefreshService` servisine bağlandı; yenileme bittiğinde güvenli bir şekilde `_load_portfolio_data()` tetiklendi.
- Etkilenen modüller: src/ui_qml/controllers/dashboard_controller.py, docs/wiki/log.md

## [2026-09-30] düzelt | Bulgu 1: QtWebEngine XSS ve Ham JS Enjeksiyon Açığı Kapatıldı

- `TradingViewChart.qml` içinde `settings.localContentCanAccessRemoteUrls: false` ve `localContentCanAccessFileUrls: false` yapılarak yerel dosya ve harici URL erişimi sınırlandırıldı.
- `${jsonPayload}` ve parametrik JS yürütmeleri string interpolation yerine `JSON.stringify(...)` ile güvenli parametre geçişine bağlandı; XSS ve kod enjeksiyonu engellendi.
- Etkilenen modüller: src/ui_qml/qml/components/TradingViewChart.qml, docs/wiki/log.md

## [2026-09-30] belge | Kapsamlı Sistem Denetim ve Mimari İnceleme Raporu

- QML arayüz katmanı (`src/ui_qml`), Domain, Application, Infrastructure, güvenlik, build ve test altyapısı kıdemli denetim ekibi perspektifiyle (Mimari, DevSecOps, QA, SRE) incelendi.
- 4 öncelik seviyesinde 20 detaylı teknik bulgu, etki analizleri ve kanıt kod blokları belgelendi.
- Kriz yönetimi ve 24 saat / bu hafta / bu ay aksiyon planı oluşturuldu.
- Bağlantılı sayfa: [system_audit_report_2026-09-30.md](system_audit_report_2026-09-30.md)

## [2026-09-30] özellik | Faz 5 — Hisse 360 & Temel Analiz Görünümü (Rasyolar, Bilanço Çubuk Grafiği ve KAP Ortaklık Donut'ı)

- **Hisse 360 Denetleyicisi (`Stock360Controller` — `src/ui_qml/controllers/stock_360_controller.py`):**
  - Genel Bakış (son fiyat, günlük değişim, hacim, 52 haftalık aralık [min-max]), Teknik Seviyeler (RSI, MACD, SMA 50/200, EMA 20, Destek, Direnç), Değerleme Rasyoları (F/K, PD/DD, FD/FAVÖK, Temettü Verimi, ROE, Net Borç / FAVÖK, Piotroski, Cari Oran), Çeyreklik Bilanço ve KAP Ortaklık Yapısı tek merkezden yönetildi.
  - Asenkron Arka Plan İş Parçacığı (Threading): Ağ ve dış API çağrıları (`Stock360Service.get_financials`, `get_shareholders`) UI'ı bloke etmeden arka planda çalıştırılıp Qt ana iş parçacığına `_remoteDataReady` sinyaliyle güvenli aktarılarak 60 FPS akıcı arayüz garantilendi.
- **KAP SQLAlchemy Repository SQLite Desteği (`sa_shareholder_repository.py`):**
  - `kap_companies`, `kap_shareholder_snapshots` ve `kap_shareholder_rows` tablolarındaki `BIGINT PRIMARY KEY` sütunları için SQLite uyumlu dinamik `max_id + 1` koruma mantığı eklendi.
- **Finansal Rasyo Rozetleri (`RatioCard.qml`):**
  - F/K, PD/DD, FD/FAVÖK, Temettü Verimi, ROE, Net Borç/FAVÖK, Piotroski F-Score ve Cari Oran için yeniden kullanılabilir, şık, GPU hızlandırmalı ve taşmasız rozet bileşeni geliştirildi.
- **Çeyreklik Bilanço ve Gelir Tablosu Çubuk Grafiği (`FinancialBarChart.qml`):**
  - QML `Canvas` üzerinde anti-aliased, degrade dolgulu, yuvarlatılmış köşeli ve interaktif hover destekli çubuk grafik motoru inşa edildi.
  - Sekme değiştirici ile tek tıkla "Net Satışlar", "Brüt Kâr", "FAVÖK" ve "Net Kâr" serileri arasında anında geçiş desteği sağlandı.
- **KAP Ortaklık Yapısı & Halka Açıklık Kartı (`ShareholderPieCard.qml`):**
  - QML `Canvas` üzerinde dinamik Donut grafik, ortasında Halka Açıklık Oranı (% Free Float) göstergesi ve sağ tarafında pay sahipleri, nominal tutarlar ve oy hakkı oranları tablosu geliştirildi.
- **Hisse 360 Görünümü (`Stock360View.qml`):**
  - Tek arama kutusu ve hızlı hisse hapları (`Flickable`) ile anında BIST hissesi arama ve seçme.
  - "TradingView'da Aç" butonu ile tek tıkla hisseyi tam kapsamlı teknik grafik sayfasına aktarma.
  - `Main.qml` içerisinde indeks 3'e canlı olarak bağlandı.
- **Kural Uyumu (`RULES.md`):** Sıfır emoji kuralı titizlikle korundu; tüm ikonlar `Icons.qml` üzerinden Lucide SVG ve `ModernIcon` ile sağlandı; tüm metinler `Strings.qml`'e eklendi.
- **Test Kapsamı:** `tests/ui_qml/test_stock_360_phase5.py` test paketi yazılarak controller başlatma, hisse arama/temizleme, çeyreklik sekmeler, ortaklık yapısı ve QML tam render test edildi (23/23 test %100 yeşil).

## [2026-09-30] düzelt | İzleme Listesi Aksiyon Butonları, İkon Tema Renklendirmesi ve Sade Ekle Butonları

- **İzleme Listesi Aksiyon Butonları Tıklama Hiyerarşisi (`WatchlistView.qml`):**
  - Sol takip listesi delegatında (`wlRow`) ve sağ hisse tablosu delegatında (`stockRow`) satırı saran ana `MouseArea`'ların en arkada kalması (`z: 0`) sağlandı.
  - Aksiyon butonları (`RowLayout` z: 1, aksiyonlar z: 2) ön plana taşınarak; liste düzenleme (kalem), liste silme (çöp kutusu), hisse notu düzenleme (kalem), listeden çıkarma (çöp kutusu), TradingView'a aktarma ("Grafik") ve hızlı alım/satım ("İşlem") butonlarının tıklanabilirliği eksiksiz sağlandı.
  - `ChartController` bünyesine `@Slot(str) def loadStock` takma adı eklendi ve QML çağrısı `loadTicker` ile senkronize edilerek `TypeError: Property 'loadStock' is not a function` hatası giderildi.
  - "Grafik" butonuna basıldığında hem hissenin TradingView grafiğine yüklenmesi hem de otomatik olarak Dashboard'a yönlendirilmesi sağlandı (`shellController.navigateTo(0)`).
  - "İşlem" butonu tıklandığında ilgili hissenin sembol ve fiyatıyla `QuickTradeModal` penceresini açması bağlandı.
- **ModernIcon Koyu/Açık Tema Renklendirmesi (`ModernIcon.qml`):**
  - Siyah/monokrom SVG ikonların Qt Quick Effects `MultiEffect` modunda luminance sıfır olduğu için koyu temada siyah kalması sorunu tespit edildi.
  - `ModernIcon.qml` bileşeni `Qt5Compat.GraphicalEffects.ColorOverlay` motoruna geçirilerek tüm SVG ikonların hem koyu hem de açık temada dinamik olarak hedef renklerine (`Theme.accent`, `Theme.textMuted`, `Theme.bearRed`, `#ffffff` vb.) tam bürünmesi sağlandı.
- **Ekle Butonlarının Sadeleştirilmesi (Çift Artı ve String Temizliği):**
  - `Strings.qml` dosyasındaki `btnNewWatchlist`, `btnAddStockToWatchlist` ve `btnQuickTrade` metinlerindeki fazladan `+ ` karakterleri temizlendi.
  - Kullanıcı talebi doğrultusunda araç çubuğu ve panel başlıklarındaki ekle butonları kompakt, şık ikon-only (`iconName: "plus"`, `tooltip: ...`) formatına getirildi; üzerine gelindiğinde açıklamayı gösteren `ToolTip` desteği `ModernButton.qml` içine entegre edildi.
- **Test Kapsamı:** `test_watchlist_phase4.py` içine `test_chart_controller_load_stock_alias` ve `test_modern_icon_color_overlay_rendering` birim testleri eklenerek tüm testler %100 yeşil doğrulandı (17/17 test geçti).

## [2026-09-30] yeni-sayfa | QML Dönüşümü Handoff & Devam Kılavuzu (QML_TRANSFORMATION_HANDOFF.md)

- Başka bir sohbet veya yeni bir ajanla çalışmaya devam edilebilmesi amacıyla kapsamlı el devir belgesi oluşturuldu.
- Belge; projenin amacı ve QML dönüşüm vizyonunu, bağlayıcı UI/UX ve sistem kurallarını (`RULES.md`: emoji yasağı, Icons.qml, Strings.qml, taşmasız düzen), tamamlanan Faz 0, 2, 3, 4 detaylarını, `Main.qml` sayfa indekslerini ve Faz 5'ten Faz 11'e kadar tüm kalan aşamaların yol haritasını içermektedir.
- Bağlantılı sayfa: [QML_TRANSFORMATION_HANDOFF.md](../../QML_TRANSFORMATION_HANDOFF.md)

## [2026-09-30] özellik | Faz 4 — Çoklu Takip Listeleri (Watchlist), Mini Sparkline Trendleri ve Hisse Yönetimi

- **Çoklu Takip Listesi Mimarisi (`WatchlistController` & `WatchlistTableModel`):**
  - Kullanıcının SQLite veritabanında saklanan mevcut takip listeleri ("Spek hisseler", "indikatör grubu", "Uzun Vadeli") ve hisse notları QML tarafına tam reaktif bağlandı.
  - CRUD yetenekleri: Liste oluşturma, isim/açıklama güncelleme, liste silme, hisse ekleme, hisse notu güncelleme ve listeden hisse çıkarma işlemleri Python slotları ve QML bağlantılarıyla tamamlandı.
  - SQLite auto-increment uyumluluğu: `stocks` ve `watchlist_items` tablolarında `BIGINT PRIMARY KEY` için SQLite uyumlu dinamik ID üretimi sağlandı.
- **7 Günlük Mini Sparkline Trend Bileşeni (`MiniSparkline.qml`):**
  - QML `Canvas` üzerinde anti-aliased çizim ve dikey degrade dolgu (bullGreen / bearRed) ile TradingView tarzı ultra hafif mini trend grafiği geliştirildi.
  - Veritabanındaki geçmiş kapanış fiyatları dinamik normalize edilerek tablo satırlarına gömüldü.
- **Gün İçi Aralık Göstergesi (Day Range Bar):**
  - Günün en düşük (Low) ve en yüksek (High) fiyatları arasında mevcut fiyatın yüzdelik konumunu dinamik gösteren kapsül progress bar eklendi.
- **Modallar ve Etkileşimler:**
  - `AddStockModal.qml`: Hisse sembolü ve kişisel strateji notu girişi.
  - `ManageWatchlistModal.qml`: Yeni liste oluşturma ve mevcut listeyi düzenleme.
  - `EditStockNoteModal.qml`: Hisseye özel hedef fiyat ve not düzenleme.
  - Tek tıkla TradingView grafiğine aktarma ("Grafik" butonu) ve Dashboard hızlı işlem modalına ("İşlem" butonu) geçiş desteği.
- **Tasarım ve Kural Uyumu (`RULES.md`):**
  - Sıfır emoji politikası eksiksiz uygulandı; tüm ikonlar `Icons.qml` ve `ModernIcon` üzerinden SVG ile sağlandı.
  - Tüm kullanıcı arayüzü metinleri `Strings.qml` içine taşındı.
- **Test Kapsamı:** `tests/ui_qml/test_watchlist_phase4.py` geliştirilerek controller, model rolleri, CRUD döngüsü ve QML Main.qml rendering test edildi (15/15 test %100 yeşil).

Etkilenen modüller: `src/ui_qml/`, `src/infrastructure/db/`, `tests/ui_qml/`, `docs/wiki/log.md`

## [2026-09-30] düzelt | Merkezi SVG İkon ve String Mimarisi, Emoji Temizliği ve Buton Taşmalarının Giderilmesi

- **Katı Emoji Yasağı (Strict No-Emoji Policy):** Windows masaüstünde yazıtipi uyumsuzluğuna, dikey hizalama problemlerine ve gayriciddi görünüme yol açan tüm Unicode emojiler (🚀, 💰, 📈, 🔄, ⚠️, ✕ vb.) arayüzden ve kod tabanından tamamen kaldırıldı (`RULES.md` Madde 2.1).
- **Merkezi Vektörel İkon Sistemi (`Icons.qml` & `ModernIcon.qml`):**
  - `src/ui_qml/assets/icons/` altına 50'yi aşkın optimize Lucide SVG ikonu yerleştirildi.
  - `Icons.qml` singleton kataloğu oluşturuldu ve `theme/qmldir` kaydı sağlandı.
  - `ModernIcon.qml` bileşeni geliştirilerek Qt Quick Effects `MultiEffect` GPU renklendirmesi (`colorization: 1.0`, `colorizationColor`) ile açık/koyu tema uyumlu dinamik renklendirme uygulandı.
- **Merkezi Metin ve Yerelleştirme Kataloğu (`Strings.qml`):**
  - Tüm sayfa başlıkları, buton etiketleri, KPI başlıkları, tablo sütun adları ve modal mesajları `Strings.qml` singleton'ına taşınarak hardcoded metin bağımlılığı ortadan kaldırıldı (`RULES.md` Madde 2.3).
- **Buton Taşmalarının (Overflow) Çözümü:**
  - `TradingViewToolbar.qml`: Ekran genişliği < 560px olduğunda şirket unvanı elide/gizlenerek, buton yükseklikleri (24-26px) ve aralıkları optimize edilerek dar ekranlarda butonların kart dışına taşması engellendi.
  - `DashboardView.qml`: "PORTFÖY HİSSELERİ" hızlı butonları esnek ve taşmasız `Flickable` kapsayıcısı içine alındı.
  - `ModernButton.qml`: İçeriğe göre otomatik esnek genişlik alacak şekilde (`implicitWidth: contentRow.implicitWidth + 20`) güncellendi.
- **Tüm Bileşenlerin Dönüşümü:** `Sidebar.qml`, `WindowHeader.qml`, `TradingViewToolbar.qml`, `MetricCard.qml`, `AssetAllocationCard.qml`, `QuickTradeModal.qml`, `CapitalModal.qml`, `ChartFullscreenModal.qml`, `PlaceholderView.qml`, `ToastNotification.qml` ve `Main.qml` eksiksiz dönüştürüldü.
- **Yönetişim & Kurallar (`RULES.md`):** `2. Arayüz ve UI/UX Standartları (QML & Tasarım Kuralları)` başlığı altında emoji yasağı, merkezi ikon, merkezi string ve responsive taşma önleme standartları kalıcı proje kuralı haline getirildi.

Etkilenen modüller: `RULES.md`, `src/ui_qml/`, `docs/wiki/log.md`

## [2026-09-30] düzelt | TradingView İndikatörlerinin Menüden Geri Kapatılamaması Sorununun Çözümü

- **QML Reaktif Durum Bağlantısı Düzeltildi:** `TradingViewToolbar.qml` içerisindeki `isChecked` alanı daha önce `chartController.isIndicatorActive()` slot çağrısına bağlıydı. Slot çağrılarının QML tarafında otomatik dinleme (dependency tracking) mekanizması bulunmadığından `isChecked` her zaman ilk değerinde (`false`) kalıyor ve kullanıcı menüden tekrar tıkladığında `!isChecked` sürekli `True` olarak Python'a gidiyordu. `isChecked` alanı doğrudan `activeIndicators` Qt özelliğine (`indexOf(id) !== -1`) bağlanarak tam reaktif hale getirildi.
- **Python Tek Parametreli Slot Aşırı Yüklemesi:** `ChartController.toggleIndicator` metodu tek parametreli çağrıyı destekleyecek şekilde aşırı yüklendi (`@Slot(str)` / `@Slot(str, bool)`). İndikatör aktifse Python içinde doğrudan `discard`, pasifse `add` yapılarak UI ile Python arasındaki olası durum uyumsuzlukları tamamen ortadan kaldırıldı.
- **JS Motoru Boolean Doğrulaması & Lejant Güncellemesi:** `tradingview_chart.html` içerisindeki `toggleIndicator` fonksiyonuna string/boolean dönüşüm koruması eklendi (`boolVal = (isEnabled === true || isEnabled === "true" || isEnabled === 1)`). İndikatör kapatıldığında ilgili çizgi veya alt panel (RSI/MACD) grafikten kaldırılırken, üst bilgi lejantındaki etiketler de anında senkronize şekilde temizlenmektedir.
- **Test Kapsamı:** `test_chart_phase3.py` testlerine tek ve çift parametreli indikatör açma/kapama doğrulamaları eklendi (11/11 test %100 yeşil).

Etkilenen modüller: `src/ui_qml/`, `tests/ui_qml/`, `docs/wiki/log.md`

## [2026-09-30] özellik | Faz 3 — TradingView Teknik Analiz Laboratuvarı, Çoklu Zaman Dilimleri ve İndikatör Paketi

- **Çoklu Zaman Dilimleri (Timeframes):** `ChartController` bünyesinde günlük (`1D` / `1G`), haftalık (`1W` / `1H`) ve aylık (`1M` / `1A`) yeniden örnekleme (resampling) mekanizması geliştirildi. BIST takvimine uygun şekilde haftalık ve aylık OHLCV barları vektörize üretilerek TradingView grafiğine dinamik aktarılıyor.
- **Teknik İndikatör Paketi Entegrasyonu:** `src/application/services/analysis/technical/indicators.py` saf NumPy/Pandas fonksiyonları kullanılarak hesaplanan indikatörler TradingView motoruna bağlandı:
  - **Ana Grafik Üstü (Overlay):** SMA 20 (Turkuaz), SMA 50 (Turuncu), SMA 200 (Mor), EMA 20 (Yeşil) ve Bollinger Bantları (Üst, Orta, Alt bantlar).
  - **Alt Osilatör Panelleri (Multi-Pane):** Lightweight Charts v5.2 çoklu bölme mimarisi ile RSI (14) (70 aşırı alım / 30 aşırı satım kesikli referans çizgili) ve MACD (12, 26, 9) (histogram, MACD ve sinyal çizgili) dinamik alt panelleri eklendi.
  - **Al / Sat Sinyal İşaretçileri (Markers):** SMA 50 ve SMA 200 kesişimlerini takip eden otomatik Golden Cross (`▲ Golden Cross`, yeşil ok) ve Death Cross (`▼ Death Cross`, kırmızı ok) görsel işaretçileri oluşturuldu.
- **Grafik Türü Değişimi:** Mum (`candle`), Çizgi (`line`), Alan (`area`) ve Bar (`bar`) grafik türleri arasında anında akıcı geçiş desteği sağlandı.
- **TradingView Üst Kontrol Araç Çubuğu (`TradingViewToolbar.qml`):**
  - Aktif hisse sembolü, tam şirket unvanı ve canlı fiyat / yüzde değişim rozeti (`₺4.90  ▲ +2.08%`).
  - Hızlı zaman dilimi butonları (`1G`, `1H`, `1A`).
  - Grafik türü seçici butonları (`🕯️`, `📈`, `🌊`, `📊`).
  - İndikatör açılır menüsü (Popup) ile anlık indikatör açma/kapatma.
  - Otomatik sığdırma (`🎯`) ve tam ekran analiz butonu (`⛶`).
- **Tam Ekran Teknik Analiz Modalı (`ChartFullscreenModal.qml`):** Masaüstü analiz derinliği için ekranın %96'sını kaplayan, tüm indikatör ve çizim alanı ferahlığı sunan tam ekran analiz laboratuvarı geliştirildi.
- **Birim Testleri (`test_chart_phase3.py`):** 4 yeni test ile zaman dilimi yeniden örneklemesi, indikatör veri yapısı, toggle kontrolleri ve SQLite entegrasyonu %100 doğrulandı (toplam 11 QML testi yeşil).

Etkilenen modüller: `src/ui_qml/`, `tests/ui_qml/`, `docs/wiki/log.md`

## [2026-09-30] düzelt | Donut Varlık Dağılımı Decimal Hatası Giderimi ve Modern Kapsül ScrollBar Tasarımı

- **Decimal Bölme Hatası Giderildi:** `DashboardController.allocationSlices` içinde `pct = (p.get("weight", 0.0)) / 100.0` hesaplanırken ortaya çıkan `TypeError: unsupported operand type(s) for /: 'decimal.Decimal' and 'float'` hatası giderildi; tüm ağırlık, piyasa değeri ve nakit değerleri açıkça `float()`'a cast edildi.
- **Donut Grafiği Güncelleme Tetikleyicisi:** `AssetAllocationCard.qml` üzerinde `onSlicesChanged` ve `Component.onCompleted` sinyallerine `donutCanvas.requestPaint()` eklenerek, sayfa açılışında ve hisse geçişlerinde donut grafiğinin anında yeniden çizilmesi sağlandı.
- **Modern Kapsül ScrollBar Bileşeni (`ModernScrollBar.qml`):** Varsayılan hantal Windows işletim sistemi kaydırma çubuğu yerine TradingView & modern web standartlarında ince, yarı saydam ve akıcı bir kaydırma çubuğu geliştirildi:
  - Dinamik genişlik: Normalde 6px ince kapsül, üzerine gelindiğinde (hover) veya sürüklendiğinde (drag) yumuşak geçişle (`NumberAnimation`, 140ms) 10px'e genişleme.
  - Akıllı opaklık: Sayfada kaydırma yapılmadığında dikkat dağıtmamak için zarif yarı saydam (0.35), kaydırma anında veya hover durumunda belirgin (0.90), sayfa taşmıyorsa tamamen görünmez (0.0).
  - TradingView teması ile uyumlu renkler (`Theme.scrollbarThumb`, `Theme.scrollbarThumbHover`, `Theme.scrollbarThumbActive`).
  - `DashboardView.qml` içerisindeki `ScrollView`'a dikey kaydırma olarak bağlandı; yatay çubuk kapatıldı (`ScrollBar.AlwaysOff`) ve `contentWidth` döngüsel bağlanma (binding loop) uyarısı giderildi.
- **QQuickStyle "Basic" Ayarı:** Windows native stilinin özel QML kontrollerini (özel `contentItem` ve `background`) ezmesini engellemek için `src/ui_qml/app.py` başlangıcında `QQuickStyle.setStyle("Basic")` etkinleştirildi.
- **Test Kapsamı:** `test_dashboard_phase2.py` testlerine `allocationSlices` yapısı ve gerçek SQLite portföy dilimleri doğrulaması eklendi; tüm QML testleri sıfır uyarı ve sıfır hata ile doğrulandı.

Etkilenen modüller: `src/ui_qml/`, `tests/ui_qml/`, `docs/wiki/log.md`

## [2026-09-30] düzelt | TradingView Fiyat Ölçeği Otomatik Uyumlandırması, Mum Gövde/Fitil Türetimi ve Dinamik Varlık Dağılımı

- **Fiyat Ölçeği Kilitlenmesi Giderildi:** Farklı fiyat seviyelerine sahip hisseler arasında geçiş yapıldığında (örn. THYAO ~300 TL'den OBAMS.IS ~5 TL'ye), TradingView motorunun fiyat skalasını kilitleyip mumları ekran dışına atması sorunu çözüldü. `setCandleData` fonksiyonunda `rightPriceScale` ve `candleSeries` için `autoScale: true` zorunlu kılındı; `priceScaleId: 'right'` açıkça atandı.
- **Close-Only Veriler İçin Mum Gövdesi ve Fitil Türetildi:** SQLite'ta `open_price`/`high_price`/`low_price` değerleri `NULL` olan hisselerde `open == high == low == close` eşitliğinden kaynaklanan 0 piksellik çizgi görünümü giderildi; `prev_close` ve tipik gün içi spread baz alınarak gerçekçi yeşil/kırmızı mum gövdeleri ve fitilleri üretildi.
- **Dinamik Varlık Dağılımı (Allocation) Kartı:** `AssetAllocationCard.qml` içerisindeki sabit/mock değerler kaldırıldı; `DashboardController.allocationSlices` üzerinden kullanıcının SQLite portföyündeki gerçek hisse ağırlıkları (`PSGYO`, `BINHO`, `BINBN`, `RUZYE`, `Diğer` ve `Nakit`) Donut grafiğe ve lejant listesine dinamik bağlandı.
- **Dinamik Hızlı Hisse Seçici Barı:** Grafik üstündeki hızlı seçim butonları portföydeki gerçek hisseler (`dashboardController.quickTickers`) ile dinamik hale getirildi; seçili hisseye göre butonun maviye dönmesi sağlandı ve varsayılan grafik portföyün ilk hissesine (`OBAMS.IS`) ayarlandı.

## [2026-09-30] düzelt | TradingView Lightweight Charts v5 API Uyumluluğu & Ekran Konumlandırması

- **Lightweight Charts v5.2 API Geçişi:** Bundle edilen Lightweight Charts sürümünün v5.2 olması sebebiyle meydana gelen `chart.addHistogramSeries is not a function` ve `chart.addCandlestickSeries` hataları, v5 `chart.addSeries(LightweightCharts.HistogramSeries, ...)` ve `chart.addSeries(LightweightCharts.CandlestickSeries, ...)` API formatına geçirilerek giderildi.
- **Pencerenin Ekran Dışında Açılması Çözüldü:** Sabit `1320x840` boyutu özellikle %125/%150 DPI ölçekli veya 1366x768 çözünürlüklü ekranlarda pencereyi ekran dışına taşıyordu. Hem `Main.qml` hem de `src/ui_qml/app.py` üzerinde birincil ekranın kullanılabilir geometrisine göre dinamik boyutlandırma (`availableGeometry()`) ve otomatik ortalama (`center`) eklendi.

## [2026-09-30] düzelt | TradingView Mum Çizimi, ₺ Glif Desteği ve SQLite Portföy Pozisyonları Bağlantısı

- **TradingView Mum Çizimi Düzeltildi:** `TradingViewChart.qml` içerisindeki çift JSON serileştirme (`JSON.stringify`) hatası giderildi; `ChartController` üzerinden `stock_repo` ve `price_repo` kullanılarak SQLite veritabanındaki gerçek günlük OHLCV mum verileri artan tarih sırasıyla Lightweight Charts motoruna aktarıldı.
- **₺ Para Birimi Glifi Düzeltildi:** Windows üzerinde `Consolas` yazı tipinin Türk Lirası sembolünü (`₺` / `\u20ba`) desteklemeyip `b` harfi olarak render etmesi sorunu, `Theme.monoFontFamily` için `'Segoe UI'` ve `'Cascadia Code'` önceliklendirilerek çözüldü.
- **Pencere Başlığı Encoding Düzeltildi:** Win32 başlık çubuğundaki Unicode tire bozulması ASCII standart tireye çevrildi.
- **SQLite Gerçek Portföy Entegrasyonu:** `DashboardController._load_portfolio_data()` mock liste yerine `portfolio_service.get_current_portfolio()` üzerinden veritabanındaki 7 adet aktif pozisyonu (`OBAMS.IS`, `RUZYE.IS`, `UNLU.IS`, `BINHO.IS`, `BINBN.IS`, `PSGYO.IS`, `MERKO.IS`), güncel kapanış fiyatlarını ve gerçekleşmemiş K/Z metriklerini hesaplayacak şekilde bağlandı.
- `submitTrade` ve `manageCapital` slotları `trade_entry_service` ve `cash_movement_service` üzerinden SQLite'a kalıcı kayıt yapacak şekilde entegre edildi.
- Birim testleri güncellendi (`test_dashboard_phase2.py`, 7 test %100 yeşil).

Etkilenen modüller: `src/ui_qml/`, `tests/ui_qml/`, `docs/wiki/log.md`

## [2026-09-30] özellik | MySQL'den SQLite'a Tam Geçiş & Yedek Senkronizasyonu

- Masaüstündeki MySQL yedekleri (`portfoysim.sql` vb.) `backups/mysql/` dizinine güvenle kopyalandı.
- `.env` yapılandırması `DB_ENGINE=sqlite` ve `DB_SQLITE_PATH=data/portfolio.db` olarak güncellendi.
- `scripts/sync_mysql_backup_to_sqlite.py` script'i ile MySQL dump'ındaki en son veriler (362.158 günlük fiyat, KAP ortaklık ve hisse kayıtları) `data/portfolio.db` içerisine başarıyla aktarıldı.
- `AppContainer`, repository ve servis katmanları SQLite ile test edildi; sistem MySQL servis bağımlılığından tamamen kurtarıldı.
- Hem klasik Qt Widgets hem de yeni QML arayüzü doğrudan SQLite üzerinden sıfır konfigürasyonla çalışır hale getirildi.

Etkilenen modüller: `.env`, `data/portfolio.db`, `scripts/`, `docs/wiki/log.md`

## [2026-09-30] özellik | Faz 2 — QML Dashboard, Açık Pozisyonlar Tablosu, Canlı Fiyat & İşlem Modalları

- QML için `PositionsTableModel` list/table modeli yazıldı; anlık fiyat değişimlerinde yeşil/kırmızı tick yanıp sönme (flash) animasyonu eklendi.
- `DashboardController` zenginleştirildi; canlı portföy KPI'ları (Toplam Değer, Gerçekleşmemiş K/Z, Günlük K/Z, Nakit Oranı), Al/Sat emir kaydı ve sermaye yatırma/çekme işlevleri eklendi.
- `QuickTradeModal` bileşeni ile canlı fiyat/lot çarpımlı hisse alım ve satım penceresi oluşturuldu.
- `CapitalModal` bileşeni ile portföye nakit ekleme ve çekme penceresi eklendi.
- `AssetAllocationCard` ile QML Canvas tabanlı modern Donut varlık dağılım grafiği entegre edildi.
- `ToastNotification` bildirim bileşeni ile kullanıcı geri bildirimleri görselleştirildi.
- `DashboardView.qml` tam interaktif hale getirildi; satır tıklamasıyla TradingView grafiğine hisse aktarımı bağlandı.
- Faz 2 birim testleri yazıldı (`tests/ui_qml/test_dashboard_phase2.py`, %100 yeşil).

Etkilenen modüller: `src/ui_qml/models/`, `src/ui_qml/controllers/`, `src/ui_qml/qml/`, `tests/ui_qml/`, `docs/wiki/log.md`

## [2026-09-29] özellik | Faz 0 — QML Branch Başlatma, venv Ortamı ve TradingView Entegrasyon POC

- `qml` branch'i açılarak paralel QML UI geliştirme süreci başlatıldı.
- Proje içi `venv` sanal ortamı kuruldu, RULES.md güncellendi.
- PySide6 + QtQuick + QtWebEngineQuick bağımlılıkları doğrulandı.
- TradingView Lightweight Charts (v4.x) yerel standalone kütüphanesi ve HTML şablonu eklendi.
- `src/ui_qml/` altında Controller'lar (Shell, Chart, Dashboard) ve Theme mimarisi oluşturuldu.
- `app.py` içine `--ui=qml` parametresi eklendi; eski ve yeni UI paralel yaşatıldı.
- QML POC yükleme ve kontrolcü testleri yazıldı (`tests/ui_qml/test_qml_poc.py`).

Etkilenen modüller: `src/ui_qml/`, `tests/ui_qml/`, `app.py`, `RULES.md`, `docs/wiki/log.md`

## [2026-09-12] refaktör | PyQt5/PySide6 UI Konsolidasyonu & Yeni Özellik Sayfaları Entegrasyonu

- Deneysel `src/ui_qml/` katmanı temizlendi; ana PyQt5/PySide6 mimarisi korundu.
- `ScreenerPage` (Hisse Tarayıcı) ve `Stock360Page` (Hisse 360 Görünümü) PyQt5/PySide6 sayfaları olarak yazıldı.
- Finansal Planlama sayfasına DCA Simülasyon paneli (`DcaSimulationPanel`) entegre edildi.
- `CheckableComboBox` bileşeni `src/ui/widgets/shared/controls/` altına taşındı.
- UI sayfa ve panel birim testleri güncellendi (935 test %100 yeşil).

Etkilenen modüller: `src/ui/pages/`, `src/ui/widgets/`, `src/ui/navigation/page_factory.py`, `docs/wiki/log.md`

## [2026-09-12] özellik | Faz 3–6 — Servis Konsolidasyonu, QML UI Katmanı & AI Karar Destek Ajanı

- Clean Architecture uygulama katmanı 5 yeni servis (Stock360, PortfolioAnalytics, RiskOptimizationBridge, DcaBacktest, AiAdvisor) ile konsolide edildi.
- Destek/Direnç (Pivot points + Cluster) ve DCA Backtest simülasyon motorları tamamlandı.
- Gemini 2.5/3.6 Flash tabanlı Function Calling / Tool Use altyapısı (`AiAdvisorService`, `AdvisorTools`) ve `GeminiAdvisorChatProvider` uygulandı.
- PySide6 QML UI katmanı 9 görünüm (Dashboard, Portfolio, Stock360, Analytics, Screener, Optimization, Simulation, Cashflow, AiAdvisor) ve QQuickPaintedItem grafikleriyle sıfırdan inşa edildi.
- 388 yeni test yazılarak toplam test sayısı 1234'e çıkarıldı (%100 yeşil).

Etkilenen modüller: `src/ui_qml/`, `src/application/services/`, `src/infrastructure/ai/`, `src/qt_compat/`, `tests/`

## [2026-09-11] özellik | Faz 2 — OHLCV Veri Genişletmesi, Vektörel İndikatör Motoru & Teknik Tarayıcı Servisi

- `DailyPrice` domain modeli ve `ORMDailyPrice` şeması `open_price`, `high_price`, `low_price`, `volume` kolonlarıyla genişletildi.
- Safe upsert COALESCE stratejisi ile close-only güncellemelerin önceden çekilmiş OHLCV verisini ezmesi önlendi.
- Vektörel indikatör motoru (`indicators.py`), 10 kural kriterli teknik tarayıcı çekirdeği (`screener.py`) ve `TechnicalScreenerService` eklendi.
- Risk metrikleri modülü (`risk_metrics.py`) VaR, CVaR, Sortino, Calmar, Ulcer Index, Gain-to-Pain, Win Rate gibi 10+ finansal metrikle zenginleştirildi.
- 90 yeni unit test eklendi (toplam 846 test yeşil).

Etkilenen modüller: `src/domain/models/daily_price.py`, `src/infrastructure/db/sqlalchemy/`, `src/application/services/analysis/technical/`, `src/application/services/analysis/risk_metrics.py`, `scripts/import_bist_ohlcv_to_db.py`, `tests/`

## [2026-09-11] yeni-sayfa | Portföy Simülasyonu Modernizasyon ve Mimari Dönüşüm Planı

- Backend Clean Architecture omurgası korunarak; SQLite geçişi, pandas-ta/quantstats entegrasyonu, servis konsolidasyonu, AI karar destek mimarisi ve QML entegrasyon köprüsünü kapsayan ana plan hazırlandı.
- Arayüz (UI-UX) tasarımı QML ile sıfırdan planlanacak şekilde köprü katmanı tasarlandı.
- Bağlantılı dosya: [TRANSFORMATION_PLAN.md](../../TRANSFORMATION_PLAN.md)

## [2026-08-21] güncelleme | ATC2.5 İndikatörü ve Trend Sinyal Alt Sisteminin Temizlenmesi

- ATC2.5 (Alpha Trader Capital) indikatörü, Bayesian istatistik motoru ve trend tarayıcı modülleri (`atc/`, `trend_scanner_service.py`, `trend_backtest_service.py`) kaldırıldı.
- Trend sinyali domain modelleri (`TrendSignal`, `TrendSignalPerformance`), portlar ve SQLAlchemy repository'leri silindi.
- `TechnicalAnalysisPage` üzerinden ATC sekmesi ve ilgili buton/slotlar temizlendi; Golden/Death Cross ve Ticker Detay sekmeleri korundu.
- `requirements.txt` ve `locale_tr.py` içindeki kullanılmayan ATC referansları ve bağımlılıkları temizlendi.
- Tüm test seti (753 test) başarıyla yeşile ulaştırıldı.

Etkilenen modüller: `src/application/services/analysis/technical/`, `src/infrastructure/db/sqlalchemy/`, `src/ui/pages/technical/`, `src/ui/shared/locale_tr.py`, `requirements.txt`

## [2026-08-14] commit | Finansallar dashboard 4 ana grup ve UI geliştirmeleri

- Finansallar dashboard'unda 18 sekme 4 ana kategori grubu altında toplandı (Finansal Tablolar & Özet, Performans & Büyüme, Kârlılık & Değerleme, Borç/Likidite/Kalite).
- İki kademeli Kategori + Sekme nav arayüzü ve akıllı Plotly grafik boyutlandırması eklendi.
- Finansal tablo dikey scrollbar ve QComboBox aşağı ok stili güncellendi.

Etkilenen dosyalar: `src/ui/pages/financials/utils/dashboard_html.py`, `src/ui/pages/financials/utils/finansal_tablo.py`, `src/ui/styles/primitives/forms.qss`, `src/ui/pages/financials/financials_page.py`, `docs/wiki/log.md`

## [2026-08-14] commit | TradingView entegrasyonu, teknik analiz güncellemeleri ve Cuma verisi tamamlama

- TradingView datafeed istemcisi entegre edildi (`tvdatafeed_client.py`, `tradingview-datafeed==2.1.1`).
- Golden cross ve teknik analiz servisi/repository güncellemeleri yapıldı.
- Eksik Cuma fiyatlarını tamamlamak için backfill scripti ve testleri eklendi (`scripts/backfill_missing_friday_prices.py`).
- Teknik analiz ve Temel analiz filtre tartışma dokümanları eklendi (`teknik_analiz_tartisma.md`, `temel_analiz_filtre_tartisma.md`).
- UI ve ticker bar geliştirmeleri yapıldı.

Etkilenen dosyalar: `src/infrastructure/market_data/tvdatafeed_client.py`, `src/application/services/analysis/technical/`, `scripts/backfill_missing_friday_prices.py`, `teknik_analiz_tartisma.md`, `temel_analiz_filtre_tartisma.md`, `requirements.txt`, `docs/wiki/log.md`

## [2026-06-16] özellik | Phase B — Golden / Death Cross detect + DB + servis (backend)

SMA50 / SMA200 kesişimi (klasik teknik analiz boğa/ayı sinyali) tüm BIST için backend
olarak entegre edildi. UI sonraki turda (Teknik Analiz sayfası).

- **Domain:** `GoldenCrossEvent` + `CrossType (GOLDEN/DEATH)` + `IGoldenCrossRepository` port
  (`src/domain/models/golden_cross_event.py`, `i_golden_cross_repo.py`).
- **Saf detect** (`src/application/services/analysis/technical/golden_cross.py`):
  vektörel pandas `rolling().mean()` + sign flip; `detect_crosses(closes, short=50, long=200)`
  → `list[DetectedCross]` (date, type, short_ma, long_ma, close). Ağsız, IO yok.
- **Infra:**
  - `ORMGoldenCrossEvent` + `CrossTypeEnum('GOLDEN','DEATH')` (`orm_models.py`); unique
    (stock_id, cross_date, cross_type) + index'ler.
  - `scripts/apply_golden_cross_schema.py` (mevcut apply_*_schema kalıbı).
  - `SQLAlchemyGoldenCrossRepository` — `INSERT ON DUPLICATE KEY` idempotent upsert + JOIN'lu
    recent/per-stock query.
- **Application servisi:** `TechnicalAnalysisService` (`src/application/services/analysis/technical/`)
  - `scan_all(today)` → tüm 641 ticker tara, yeni cross'ları DB'ye yaz.
  - `scan_ticker(ticker)` → tek ticker scan.
  - `get_recent_events(days, cross_type)`, `get_events_for_ticker(ticker)` — UI sorgu API'leri.
- **Container:** `repositories.golden_cross_repo`, `services.technical_analysis_service`.
- **Testler:** 15 yeni test (8 saf detect + 7 servis mock — yetersiz veri, cross tespiti,
  query delegate). Toplam 404/404 yeşil.
- **İlk scan (test env):** 641 ticker × ~60s → **6385 cross eventi**, 58 atlandı (≤200 gün veri).

**Sonraki:**
- UI fazı — "Teknik Analiz" sayfası (sidebar): Son Sinyaller sekme (tablo + filtre) +
  Ticker Detay sekme (Plotly kapanış + SMA50/200 + cross marker'lar) + manuel
  "Taramayı Çalıştır" / "Veri Tamamla" butonları.

---
## [2026-06-16] özellik | Phase A2 — Tüm BIST için günlük otomatik veri tamamlama

Phase A1 (CSV import, commit `34b14e8`) ile 586 ticker × 10y verisi `daily_prices` tablosuna
yüklendi. Phase A2: her gün BIST kapanışı (18:30) sonrası app açılışında otomatik tamamlama.

**Anahtar karar:** Yeni servis yazılmadı; mevcut `PriceDataHealthService.update_from_latest_to_today(today, scope)`
genişletildi (yeni scope sabiti).

- **Yeni scope:** `PRICE_SCOPE_ALL_BIST = "all_bist"` (`price_data_health_service.py:24`).
  - `PriceScopeResolver.stocks_in_scope()`: scope == "all_bist" → portföye bakmadan `stock_repo.get_all_stocks()` döner.
  - `PriceScopeResolver.first_trade_dates_by_stock()`: scope == "all_bist" → `{}` (portföye ait first-trade kısıtı yok).
- **Auto-trigger** (`main_window.py`): yeni method `_start_auto_bist_backfill_once()` —
  saat ≥ 18:30 ise + last_run != target_date ise Worker tetikler. QSettings cache
  (`AUTO_BIST_BACKFILL_SETTINGS_KEY`) aynı işlem günü tekrar tetiklemez.
  `BIST_MARKET_CLOSE_TIME = 18:30` modül sabiti.
- **"Açmayı unuttum" desteği:** her ticker için `latest_date + 1 → today` aralığı çekilir.
  2-3 gün boşluk birikmişse otomatik dolar — `update_from_latest_to_today` mevcut davranışı,
  ek kod yok.
- **L10N:** `OTOMATIK_BIST_GUNCELLEME_{TAMAMLANDI,HATA,CALISTIRILAMADI}_TMPL`.
- **Test:** `test_price_data_health_service.py`'ye 3 yeni test
  (all_bist tüm stocks döner, first_trade_dates {}, default scope mevcut davranış korunur).
  389/389 yeşil.

**Verification:**
- `PORTFOYSIM_ENV=test python app.py` saat 18:30 öncesi → log "BIST backfill atlandı" + DB değişmez.
- 18:30 sonrası → Worker tetiklenir, `daily_prices`'a yeni satırlar; Toast.success.
- Aynı gün tekrar açılış → trigger atlanır (QSettings cache).

**Sonraki:** Phase B (Golden Cross detect + `golden_cross_events` tablo + scan servisi) ve
UI fazı (Teknik Analiz sayfası + manuel "Veri Tamamla" + "Taramayı Çalıştır" butonları).

---
## [2026-06-16] özellik | Ortaklık Yapısı sayfası MVP — KAP pay sahipliği tarihçesi

- **Veri kaynağı:** KAP (kap.org.tr) `/api/company-detail/get-history/{OID}/kpy41_acc5_sermayede_dogrudan/N` endpoint'i; tek istek tüm tarihçe (~60-70 snapshot).
- **Ticker → KAP OID:** `https://www.kap.org.tr/tr/bist-sirketler` sayfasının inline JSON'undan haftalık cache (`data/_cache/kap/bist_companies.json`).
- **Yeni Domain:** `src/domain/models/shareholder.py` (`ShareholderRow`, `ShareholderSnapshot`); port `src/domain/ports/services/i_shareholder_provider.py`; repo port `src/domain/ports/repositories/i_shareholder_repo.py`.
- **Yeni Infra:**
  - `src/infrastructure/corporate_actions/kap_shareholder_provider.py` — HTTP + TR locale parse + cache.
  - `src/infrastructure/db/sqlalchemy/orm_models.py` — `ORMKapCompany`, `ORMKapShareholderSnapshot`, `ORMKapShareholderRow` (auto-create).
  - `src/infrastructure/db/sqlalchemy/repositories/sa_shareholder_repository.py` — atomik history replace.
- **Yeni Application:** `src/application/services/analysis/shareholder_analysis_service.py` — TTL 24h, force_refresh seçeneği.
- **Container:** `market_clients.py` + `repositories.py` + `services.py` wiring.
- **Yeni UI sayfa:** `src/ui/pages/shareholders/` paketi — `ShareholdersPage` (sidebar PAGE_SHAREHOLDERS=12, PAGE_COUNT 12→13).
  - Üst: Plotly çoklu çizgi grafiği (X=tarih, Y=pay %, her shareholder ayrı çizgi). Pay sahipliği değişim trendi tek bakışta görünür.
  - Alt: snapshot timeline — her bildirim için card + dark-tema tablo (Ad, Pay TL, Pay %, Oy %).
- **L10N:** `ORTAKLIK_YAPISI`, `ORTAKLIK_YAPISI_ACIKLAMA`, `ORTAKLIK_YUKLENIYOR_TMPL`, `ORTAKLIK_TAMAMLANDI_TMPL`, `YENILE`.
- **Mimari kararlar:**
  - §15: Application servisi KAP'a doğrudan değil port üzerinden erişir.
  - §1: ShareholdersPage 158 satır (BasePage extension), dashboard_html.py ≤200 satır.
  - Veri kalıcılığı: dosya cache (BIST haritası) + MySQL (tarihçe denormalize) — sorgu hızı için.
- **Yeni testler:** `test_kap_shareholder_provider.py` (17 birim test — TR sayı parse, tarih parse, history parse, BIST regex), `test_shareholder_analysis_service.py` (5 mock test — TTL davranışı).
- **Sonraki faz (bu PR'da DEĞİL):** Yönetim Kurulu (`kpy41_acc6_yonetim_kurulu_uyeleri`), Bağlı Ortaklıklar (`kpy41_acc7_bagli_ortakliklar`), Genel Bilgiler (sektör vs.) sekmeleri.

---
## [2026-06-15] iyileştirme | Finansallar sayfası Plan 4 — UX düzeltmeleri (7 madde)

- **EVDS hata propagasyonu:** `_enrich_tufe` catch bloğuna `metrics["_tufe_error"] = str(exc)` eklendi. `_chart_reel_buyume` gerçek hata mesajını gösterir; artık yanıltıcı "EVDS_API_KEY ortam değişkenini ayarlayın" mesajı yok.
- **USD uyarı göstergesi:** `_chart_kpi_table` ve `_chart_satis_favok` başlıklarına `currency != "TRY"` kontrolü; başlıkta "⚠ USD verisi yaklaşık" notu görünür.
- **Dönem esnekliği:** `financials_page.py`'e QComboBox (4 / 8 / 12 / Tümü) eklendi. `_on_analysis_done` seçime göre `n_periods` hesaplar.
- **Font büyütme + max-height kaldırma:** `finansal_tablo.py` CSS güncellemesi — `.76rem→.88rem`, `.7rem→.82rem`, `.68rem→.78rem`, `.68em→.75em`; `max-height:68vh` kaldırıldı; satır padding `4px→6px`.
- **Grafik yüksekliği artırıldı:** `_layout(height=520)` varsayılan; heatmap `height=420`, piotroski `height=460`, KPI tablo `height=480`; margin `{"t":60,"b":50,"l":70,"r":30}`.
- **Teknik bilgi kutucukları:** `dashboard_html.py`'e `_INSIGHTS` dict eklendi (17 sekme için). Pane loop `_INSIGHTS.get(tid, "")` enjekte eder. Mavi kenarlıklı `.insight-box` CSS.
- **SVG ikonlar:** Emoji yerine Tabler Icons (MIT) inline SVG. `_IP` dict + `_ic(key)` helper; her sekme butonunda 13×13 SVG + metin.

---
## [2026-06-15] özellik | Finansallar sayfası Faz 3 — kalan 7 grafik + Finansal Tablo (18 sekme)

- **Kapsam:** `scripts/finansal_lab/viz_prototype.py`'deki tüm eksik özellikler entegre edildi. Dashboard 10 → 18 sekmeye çıktı.
- **7 yeni Plotly grafik** (`charts.py` ekleri):
  - `_chart_net_borc` — Bar (kırmızı/yeşil işarete göre) + Scatter secondary_y (Net Borç/FAVÖK).
  - `_chart_waterfall` — `go.Waterfall` Gelir Köprüsü (Satışlar → Net Kar, en son dönem).
  - `_chart_fcf_vs_netkar` — FCF fill-area + Net Kar dashed-line (Kazanç Kalitesi).
  - `_chart_nakit_akis` — Grouped Bar: İşletme CF, FCF, Capex.
  - `_chart_heatmap` — `go.Heatmap` 8 metrik × n dönem YoY% (özel colorscale, annotated).
  - `_chart_bedelsiz` — Bar (bedelsiz_potansiyel_x) + Scatter × 2 (özkaynak, ödenmiş sermaye); enflasyon muhasebesi subtitle.
  - `_chart_satis_breakdown` — Stacked Bar (Yurtiçi/Yurtdışı) + Scatter secondary_y (İhracat Oranı); banka graceful.
- **`_bedelsiz_ef_info` helper:** §1 (≤50 satır) uyumu için `_chart_bedelsiz`'den ayrıştırıldı.
- **Finansal Tablo sekmesi** (`utils/finansal_tablo.py`, YENİ):
  - Interaktif HTML tablo — Plotly değil; kendi CSS/JS'i.
  - `build_finansal_tablo_pane(m, n)` → `<style>+<div>+<script>` (tab pane'e gömülür).
  - `_raw_sections` (compute_metrics çıktısı) ham veriyi BİLANÇO / GELİR / DİPNOT / NAKİT AKIŞ tablolarında gösterir.
  - Dönem seçici, satır paketleri (localStorage), YoY Δ% badge.
- **`dashboard_html.py` güncellemesi:** 18 sekme (Finansal Tablo ilk); `_content(x)` helper `go.Figure | str` birleştirmesi; tüm 17 yeni import.
- **Testler:** `test_finansal_dashboard.py` — 19 test (HTML yapısı, JS değişkenler, graceful boş veri, 7 chart tipi kontrolü).
- Doğrulama: 19 yeni test yeşil; toplam pre-existing hariç yeşil set değişmedi.
- **Yalnız UI katmanı değişti** — Domain/App/Infra dokunulmadı.

## [2026-06-15] özellik | Finansallar sayfası Faz 2 — 7 yeni sekme + TÜFE + Değerleme

- **Grafik sekmeleri (Faz 1):** `charts.py` yeni modülü — tüm chart builder'lar + paylaşılan yardımcılar buraya taşındı. `dashboard_html.py` yalnız orkestratör kaldı. 10 sekme: KPI, Satışlar & Marjlar, Bilanço, DuPont, İşletme Sermayesi, Piotroski, Sezonsellik, Temettü, Reel Büyüme, Değerleme.
- **Reel Büyüme — TÜFE (Faz 2):**
  - Domain port: `i_inflation_data_provider.py` (`IInflationDataProvider` + `InflationDataUnavailable`).
  - Infrastructure adapter: `evds_tufe_provider.py` — `EvdsClient.get_series("TP.FG.J0")` + parse + dosya cache 24 saat TTL (`tufe_index.json`).
  - Application saf math: `financials/inflation.py` — `real_growth`, `get_yoy_tufe`, `period_to_month` (ağsız).
  - Service enrichment: `_enrich_tufe(metrics)` helper (opsiyonel, graceful hata).
- **Değerleme — yfinance (Faz 3):**
  - Domain port: `i_market_valuation_provider.py` (`IMarketValuationProvider` + `MarketValuationUnavailable`).
  - Infrastructure adapter: `yfinance_valuation_provider.py` — `yf.Ticker.fast_info` + `.info` fallback + dosya cache 1 saat TTL (`valuation_{TICKER}.json`).
  - Application saf math: `financials/valuation.py` — `compute_valuation` F/K, PD/DD, EV/FAVÖK, F/S, `_safe_div`.
  - Service enrichment: `_enrich_valuation(metrics, ticker)` helper (opsiyonel, graceful hata).
- **Container wiring:** `MarketClientSet` → `evds_tufe_provider`, `yfinance_valuation_provider`; `FinancialAnalysisService` iki opsiyonel provider alıyor.
- **Testler:** 4 yeni test modülü (inflation, valuation, evds_tufe_provider, yfinance_valuation_provider); `test_financial_analysis_service.py` genişletildi (enrichment mock); `test_container_services.py` mock güncellendi.
- Doğrulama: 363 application/infra/domain testi yeşil; önceki pre-existing UI hataları değişmedi.
- Bağlantılı sayfa: [service_analysis.md](service_analysis.md)

## [2026-06-15] özellik | Bilanço ve Finansallar sayfası — Clean Architecture entegrasyonu

- **Mimari karar:** `scripts/finansal_lab/` prototipinden tam Clean Architecture entegrasyonu.
  - Domain port: `src/domain/ports/services/i_financial_statement_provider.py` (`IFinancialStatementProvider` Protocol + `FinancialStatementProviderUnavailable`).
  - Infrastructure adapter: `src/infrastructure/market_data/isyatirim_provider.py` — isyatirim.com.tr JSON API scraper, dosya cache + 12 saat TTL (`data/_cache/financials/`).
  - Application metrics: `src/application/services/analysis/financials/metrics.py` — saf, ağsız metrik hesabı (de-kümülasyon, TTM, Piotroski, DuPont, işletme sermayesi).
  - Application service: `src/application/services/analysis/financial_analysis_service.py` — §15 uyumlu (dış API doğrudan çağrılmaz).
  - DI kaydı: `market_clients.py` + `services.py` container parts güncellendi.
- **UI katmanı** (§1: sayfa ≤400 satır):
  - `src/ui/pages/financials/financials_page.py` — orkestrasyon (layout+wiring+Worker).
  - `src/ui/pages/financials/panels/ticker_input_panel.py` — ticker + para birimi girişi.
  - `src/ui/pages/financials/panels/financials_chart_panel.py` — SilentWebEngineView + offline Plotly.
  - `src/ui/pages/financials/utils/dashboard_html.py` — 3-sekme Plotly HTML builder (CDN yok, `ensure_patched_plotly_js()`).
- **Sidebar entegrasyonu:** `PAGE_FINANCIALS=11`, `PAGE_COUNT=12`, `page_factory.py` index 11, `_build_sidebar_nav` güncellendi.
- **L10N:** 7 yeni giriş — `BILANCO_VE_FINANSALLAR`, `FINANSALLAR_*`.
- **Testler:** 16 yeni test; `test_container_services.py` mock güncellendi.
- Doğrulama: yeni 22 test yeşil; pre-existing 2 hata değişmedi.
- Bağlantılı sayfa: [service_analysis.md](service_analysis.md)

## [2026-06-14] refaktor | Faz 2+3 tamamlandı; src fonksiyon satır ihlalleri giderildi; violations=134→109 (src:115→90)

- Faz 2 (UI _init_ui döngüsü, 12 fonksiyon): peer_card, appearance_panel, goal_input_dialog, goals_panel, corporate_action_candidates_panel, date_range_dialog, action_list_item, model_panel, trade_dialog, main_window — modül düzeyi builder'lara bölündü.
- Faz 3 (application servisleri + UI handler'lar, 14 fonksiyon): corporate_action_service._apply_bedelli/_apply_bedelsiz → _record_and_update_trade; price_adjustment_service → _find_price_transition_date + _determine_adjust_before_date; portfolio_series_builder._run_simulation_loop → _advance_twr_index; dashboard_corporate_action_actions → _register_action, _on_ca_backfill_success/_error; model_portfolio_ui_builder.build_ui → _build_action_buttons; ai_helper → _collect_table_rows, _build_commentary_prompt, _build_ai_panel_title_row, _build_ai_browser_widget; xai_card → _build_factor_header_row; stock_chart_widget → _draw_price_series, _draw_reference_lines; analysis_comparison_section → _build_mode_selector_panel; performance_card → _build_metric_row; chatbot_panel → _build_prompt_data_sections; risk_profile_page → _build_survey_header_row, _build_survey_btn_row; comparison_data_manager → _start_comparison_worker; price_data_report → _build_problematic_html.
- Kalan 90 src ihlali: fonksiyon_satır ihlali ≈0 (parse_kap_mkk_disclosure tam sınırda=50); **cyclomatic complexity ihlali 49** + **parametre sayısı ihlali 44** — farklı refactor türü.
- Doğrulama: 582 test geçti, 2 pre-existing hata değişmedi.
- Bağlantılı sayfa: [refactor_handoff_2026-06-13.md](refactor_handoff_2026-06-13.md)

## [2026-06-14] refaktor | UI sınıf ihlalleri giderildi; violating_classes=4→1

- `WatchlistPage._load_stocks` içindeki aksiyon buton bloğu `_make_stock_action_cell()` modül fonksiyonuna taşındı.
- `NewStockTradeDialog._init_page1` ve `_init_page2` widget oluşturma bloklarının tamamı `_build_page1_widgets()` ve `_build_page2_widgets()` modül fonksiyonlarına taşındı.
- `StockDetailPage._build_left_scroll_area`, `_build_history_table`, `_build_corp_actions_table` modül düzeyine taşındı; `_build_header` içeriği `_build_header_widgets(back_cb)` modül fonksiyonuna çıkarıldı.
- Önceki oturumda: `SAModelPortfolioRepository`, `CurrencySpinBox`, `NewStockTradeDialog`, `ChatbotPanel` sınıf metod sayısı ve satır eşikleri düşürüldü.
- Baseline güncellendi: **sınıf ihlali 4→1** (`L10N` belgeli istisna); fonksiyon/metot ihlali `134`.
- Doğrulama: `tests -q` → 612/612 passed.
- Etkilenen dosyalar: `src/ui/pages/watchlist_page.py`, `src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py`, `src/ui/pages/stock_detail/stock_detail_page.py`, `docs/wiki/code_quality_baseline_2026-06-13.md`, `docs/wiki/refactor_handoff_2026-06-13.md`.
- Bağlantılı sayfa: [refactor_handoff_2026-06-13.md](refactor_handoff_2026-06-13.md)

## [2026-06-13] refaktor | Application Faz 1 servis eşik azaltımı

- `ModelPortfolioService` public facade API'si korunarak method-count ihlali kaldırıldı.
- `OptimizationService._optimize` fiyat geçmişi doğrulama, return model, ağırlık optimizasyonu ve öneri üretimi helper'larına ayrıldı; `_optimize` eşik altına indirildi.
- Baseline yeniden üretildi: sınıf ihlali `9`, fonksiyon/metot ihlali `153`, sağlık raporu crosswalk `84/84`.
- Doğrulama: hedefli application testleri geçti; final test kapısı commit öncesi çalıştırılacak.
- Etkilenen dosyalar: `src/application/services/planning/model_portfolio_service.py`, `src/application/services/planning/optimization_service.py`, `docs/wiki/code_quality_baseline_2026-06-13.md`, `docs/wiki/code_quality_baseline_2026-06-13.json`, `docs/wiki/refactor_handoff_2026-06-13.md`.
- Bağlantılı sayfa: [refactor_handoff_2026-06-13.md](refactor_handoff_2026-06-13.md)

## [2026-06-13] yeni-sayfa | Refactor handoff ve devam notu

- Sağlık baseline refactorunun amacı, tamamlanan commitleri, kalan fazları, dirty worktree uyarılarını ve devam komutlarını tek sayfada toplandı.
- Application Faz 1 için hedefler ve kabul kriterleri başka bir ajan tarafından sürdürülebilecek şekilde kaydedildi.
- Etkilenen dosyalar: `docs/wiki/refactor_handoff_2026-06-13.md`, `docs/wiki/index.md`, `docs/wiki/Plans.md`, `docs/wiki/log.md`.
- Bağlantılı sayfa: [refactor_handoff_2026-06-13.md](refactor_handoff_2026-06-13.md)

## [2026-06-13] refaktor | İlk kalite baseline refactor dilimi

- `ModelPortfolioTradeService` içindeki builder, sıralama ve zaman filtresi helper'ları sınıf dışına taşındı; sınıf `299 effective satır / 20 metot` ile eşik altına indi.
- `ChartRenderer` figure üretimi ve dosya adı helper'ları sınıf dışına taşındı; sınıf `299 effective satır / 19 metot` ile UI whitelist'inden çıkarıldı.
- Doğrulama: `tests/application -q` -> 188 passed; `tests/ui/pages/test_comparison_page.py -q` -> 24 passed; `tests/ui/test_refactor_guards.py -q` -> 8 passed; `tests -q` -> 612 passed.
- Etkilenen dosyalar: `src/application/services/planning/model_portfolio_trade_service.py`, `src/ui/pages/comparison/utils/chart_renderer.py`, `tests/ui/test_refactor_guards.py`.
- Bağlantılı sayfa: [code_quality_baseline_2026-06-13.md](code_quality_baseline_2026-06-13.md)

## [2026-06-13] yeni-sayfa | Kod kalitesi guardrail rehberi

- Sağlık raporu sonrası kalıcı eşikler, istisna protokolü, UI page/component standardı ve application service facade standardı belgelendi.
- Yeni ölçüm çıktıları ve refactor öncesi kontrol akışı rehbere bağlandı.
- Etkilenen dosyalar: `docs/wiki/code_quality_guardrails.md`, `docs/wiki/index.md`, `docs/wiki/architecture.md`, `docs/wiki/testing_strategy.md`, `docs/wiki/Plans.md`.
- Bağlantılı sayfa: [code_quality_guardrails.md](code_quality_guardrails.md)

## [2026-06-13] guncelleme | Sağlık raporu ölçüm baseline'ı

- `scripts/measure_code_quality.py` ile yorum, boş satır ve docstring ayrıştırmalı kod kalitesi ölçümü üretildi.
- Baseline JSON ve Markdown raporları `code_quality_baseline_2026-06-13` adıyla wiki'ye kaydedildi.
- Sağlık HTML'i tek karar kaynağı olmaktan çıkarıldı; HTML path'leri yeni ölçüm raporuyla crosswalk edildi.
- Etkilenen dosyalar: `scripts/measure_code_quality.py`, `tests/test_code_quality_measurement.py`, `docs/wiki/code_quality_baseline_2026-06-13.md`, `docs/wiki/code_quality_baseline_2026-06-13.json`.
- Bağlantılı sayfa: [code_quality_baseline_2026-06-13.md](code_quality_baseline_2026-06-13.md)

## [2026-06-13] duzeltme | Toast kapatma ikonu ve tema kontrasti

- Toast kapatma kontrolu metin tabanli `x` yerine IconManager uzerinden uretilen tema-duyarli SVG `x` ikonuna tasindi.
- `TOAST_CLOSE_ICON` ve `TOAST_CLOSE_HOVER_BG` tokenlari eklendi; dark/light toast zeminlerinde kapatma ikon kontrasti testle korunur.
- Parent argumani eksik Toast API cagrisini yakalayan AST guard eklendi; Finansal Planlama'daki eksik parent cagrisi duzeltildi.
- Dogrulama: `python -m pytest tests -q -p no:cacheprovider` -> 537 passed.
- Etkilenen dosyalar: `src/ui/widgets/shared/feedback/toast.py`, `src/ui/styles/`, `src/ui/assets/icons/x.svg`, `tests/ui/`.

## [2026-06-13] duzeltme | Analiz async lifecycle ve WebEngine lazy init

- PySide6 sonrasi Analiz sayfasinda payload render edilmesine ragmen `Analiz Hesaplaniyor...` butonunun acik kalmasi, Worker cleanup ve sayfa request-id tamamlama akisi ile kapatildi.
- `Worker` aktif referansi artik `finished` sinyali dis dinleyicilere teslim edildikten sonra internal cleanup sinyaliyle birakilir; QThreadPool event-loop regresyon testleri eklendi.
- Analiz sayfasi ilk acilista yalniz overview+risk payload ister; eski `get_page_payload()` kontrati korunur, UI icin `get_overview_risk_payload()` kullanilir.
- Risk tabindaki Plotly/WebEngine view'lari sayfa kurulumunda degil, kullanici `Dagilim & Risk` tabina gecince lazy olusturulur; ilk Analiz girisindeki odak/sicrama maliyeti azaltildi.
- Dogrulama: `python -m pytest tests -q -p no:cacheprovider` -> 531 passed.
- Etkilenen dosyalar: `src/ui/worker.py`, `src/ui/pages/analysis/`, `src/application/services/analysis/analysis_service.py`, `tests/ui/`, `tests/application/test_analysis_service.py`.

## [2026-06-12] duzeltme | PySide6 sonrasi UI etkileşim ve tema regresyonları

- Karşılaştırma WebEngine grafiklerinde mouse wheel artık event tekrar gönderimi yerine doğrudan sayfa scroll bar'ını hareket ettirir; grafik üzerindeyken sayfa scroll davranışı geri getirildi.
- `SilentWebEngineView` focus almayacak şekilde ayarlandı; analiz/karşılaştırma grafik yüklenirken ana pencere odağının zıplaması azaltıldı.
- Analiz dağılım grafiklerinde Plotly metin rengi Qt palette yerine aktif tema tokenlarından alınır; koyu temada legend ve başlıklar okunur.
- Dialoglarda `WindowCloseButtonHint` açıkça korunur; context help butonu kaldırılırken X ile kapatma davranışı bozulmaz.
- Global QSS kök fontu pixel-size yerine `10pt` olarak tanımlandı; Qt/pyqtgraph tarafındaki `QFont::setPointSize <= 0` uyarısı hedeflendi.
- Doğrulama: `python -m pytest tests -q -p no:cacheprovider` -> 522 passed.
- Etkilenen dosyalar: `src/ui/pages/comparison/widgets/chart_panels.py`, `src/ui/widgets/shared/controls/silent_web_view.py`, `src/ui/pages/analysis/`, `src/ui/widgets/**/dialogs/`, `src/ui/styles/themes/`, `tests/ui/`.

## [2026-06-12] duzeltme | PySide6 sonrasi Windows DPI buyumesi normalize edildi

- PySide6/Qt6'nin Windows 125% ekran olcegini otomatik uygulamasi nedeniyle sayfa icerikleri, sidebar ve sabit px tabanli QSS metrikleri buyuyordu.
- `src/qt_compat/scaling.py` eklendi; `QApplication` olusmadan once Windows scale percent okunup 100% ustunde ters `QT_SCALE_FACTOR` uygulanir.
- Bu makinede duz PySide6 `dpr=1.25`, `geom=1536x864`; app baslangic normalizasyonu sonrasi `QT_SCALE_FACTOR=0.8`, `dpr=1.0`, `geom=1920x1080` olarak dogrulandi.
- Acil durum kapatma anahtari: `PORTFOYSIM_DISABLE_QT_SCALE_NORMALIZATION=1`; elle override icin mevcut `QT_SCALE_FACTOR` korunur.
- Etkilenen dosyalar: `app.py`, `src/qt_compat/scaling.py`, `tests/ui/test_qt_scale_normalization.py`, `docs/wiki/ui_architecture_and_events.md`, `docs/wiki/log.md`.

## [2026-06-12] refaktor | PySide6 göçü ve Qt compat katmanı uygulandı

- `src/qt_compat/` paketi eklendi; QtCore/QtGui/QtWidgets/QtSvg/QtWebEngine/QtTest re-exportları ve `shiboken6.isValid` tabanlı lifecycle helper merkezi hale getirildi.
- Üretim ve test importları PyQt5/PyQtWebEngine/sip yüzeyinden compat katmanına taşındı; `pyqtSignal/pyqtSlot`, `exec_()` ve `sip.isdeleted` kalıntıları temizlendi.
- WebEngine download akışı Qt6 API'sine geçirildi: `setDownloadDirectory`, `setDownloadFileName`, `accept`.
- PySide6 runtime farkları kapatıldı: `QDate.toPyDate`, `QTime.toPyTime`, eski enum alias'ları, `QVariant` yerine `None`, Qt6 `QWheelEvent` test fixture'ı ve QRunnable worker yaşam süresi.
- Dependency pinleri güncellendi: `PySide6==6.11.1`; `PyQt5` ve `PyQtWebEngine` kaldırıldı.
- Doğrulama: `python -m pytest tests` -> 517 passed; `pip check` -> temiz; `rg "PyQt5|PyQtWebEngine|pyqtSignal|pyqtSlot|import sip|sip\.isdeleted|exec_\(" app.py src tests` -> temiz.
- Etkilenen ana yüzeyler: `src/qt_compat/`, `app.py`, `src/ui/**`, `tests/**`, `requirements.txt`, `docs/wiki/*`.

## [2026-06-12] yeni-sayfa | PySide6 göç analizi ve faz planı

- PyQt5 -> PySide6 geçişi için kod tabanı katmanlara ve UI alt parçalarına bölünerek analiz edildi.
- PyQt5 import yüzeyi, `pyqtSignal`, `QThreadPool`, `QSettings`, `sip`, `exec_`, WebEngine/Plotly ve QSS riskleri belgelendi.
- Önerilen göç modeli `compat-first, page-by-page` olarak kaydedildi; test, WebEngine ve Nuitka kabul kriterleri eklendi.
- Etkilenen dosyalar: `docs/wiki/pyside6_migration_analysis.md`, `docs/wiki/index.md`, `docs/wiki/log.md`
- Bağlantılı sayfa: [pyside6_migration_analysis.md](pyside6_migration_analysis.md)

## [2026-06-06] iyilestirme | Stock Detail grafik UX (TR aylar, crosshair, sembol Y-ekseni)

- `StockChartWidget` (`pyqtgraph`) tamamen Turkce lokal: X-ekseni TR ay kisaltmalari (`"15 Oca"`), Y-ekseni `₺ 1.234,56` formati.
- Mouse-over crosshair (`vLine/hLine`) + tarih+fiyat tooltip (`SignalProxy.sigMouseMoved`, bisect ile en yakin noktaya snap).
- Reference legend offset `(14, 44)`: basligin altina cekildi, basliki/eksen tick'leriyle cakismaz.
- Baslik L10N: `FIYAT_GECMISI_TMPL` (em-dash `—`).
- `optimization_page._load_sources` sessiz `except Exception: pass` -> `logger.warning` + combo placeholder `MODEL_PORTFOY_YOK`.
- Etkilenen dosyalar: `src/ui/pages/stock_detail/stock_chart_widget.py`, `src/ui/shared/locale_tr.py`, `src/ui/pages/optimization_page.py`, `tests/ui/pages/test_stock_detail_page.py`, `tests/ui/test_refactor_guards.py`, `docs/wiki/ui_architecture_and_events.md`
- Tam suite 510 gecti.
- Baglantili sayfa: [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-06] refaktor | AI katmani ve grafik veri erisimi temiz mimariye tasindi

- UI icindeki backend sizintisi giderildi: `src/ui/pages/ai_page/core/` (HTTP istemci, Gemini SDK, QSettings sohbet deposu, is kurallari) kaldirildi ve katmanlara dagitildi.
- Domain: `src/domain/models/ai_analysis.py` (saf modeller, `ModelOutlook` semantik) + portlar `src/domain/ports/services/i_ai_analysis_provider.py`, `i_ai_chat_provider.py`, `src/domain/ports/repositories/i_chat_history_repo.py`.
- Infrastructure: `src/infrastructure/ai/` (ai_core_fastapi_client, gemini_chat_provider, mock_ai_analysis_provider, qsettings_chat_history_repo).
- Application: `src/application/services/ai/` (ai_analysis_service, ai_chat_service, safety_guard) + DI `src/application/container_parts/ai.py` -> `container.ai_analysis_service / ai_chat_service / chat_history_repo`.
- UI: `src/ui/pages/ai_page/labels.py` (L10N etiket/disclaimer, `outlook_label`), `src/ui/pages/ai_page/right_panel/chat_session_manager.py`. Paneller servisleri DI ile tuketir.
- `StockChartWidget` yfinance'i dogrudan cagirmaz; `container.market_client.get_price_series` provider'i kullanilir.
- Guard: `tests/ui/test_refactor_guards.py` -> `src/ui` altinda `requests`/`yfinance`/`google` importu ve `ai_page/core` klasoru yasak. Tam suite 505 gecti.
- Baglantili sayfa: [ui_architecture_and_events.md](ui_architecture_and_events.md), [architecture.md](architecture.md)

## [2026-06-06] duzeltme | Kapali piyasa seansinda islem kaydi blokaji

- Hisse al/sat kayitlari icin BIST acik seans kontrolu onayla gecilebilir uyari olmaktan cikarildi; kapali gun/saatte kayit kesin olarak durdurulur.
- UI helper'i `QMessageBox.question` yerine bloklayici warning gosterir; Dashboard, Model Portfoy ve Stock Detail trade akislarinda servis cagrisi yapilmaz.
- `TradeEntryService` ve `ModelPortfolioTradeService` production container'da `BistMarketSessionService` ile guard edilir; UI atlanirsa da kapali seans trade kaydi olusmaz.
- Etkilenen dosyalar: `src/application/services/market/`, `src/application/services/portfolio/trade_entry_service.py`, `src/application/services/planning/model_portfolio_trade_service.py`, `src/ui/shared/market_session_confirm.py`, `tests/application/`, `tests/ui/`
- Baglantili sayfa: [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-06] yeni-sayfa | Test ortamı veritabanı ve güvenli çalışma altyapısı

- Geliştiricilerin sistemi canlı verileri riske atmadan zorlayabilmeleri için `PORTFOYSIM_ENV=test` ortam değişkeniyle `.env.test` yapılandırmasını yükleyen dinamik ortam yönetimi eklendi.
- Canlı verileri test veritabanına yapısı ve verileriyle (Foreign Key kontrollerini geçici kapatarak ve chunk'lar halinde) kopyalayan `scripts/replicate_db.py` betiği oluşturuldu.
- Test ortamında çalışıldığında kullanıcının bunu fark etmesi için MainWindow pencere başlığına `[TEST ORTAMI]` ibaresi ve sidebar menüsüne turuncu renkli `TEST ORTAMI` etiketi (badge) entegre edildi.
- Test kapsamları için `test_settings_loader.py` genişletildi, `test_replicate_db.py` ve `test_main_window_env.py` yazıldı; `test_style_manifest.py` whitelisting yapılarak kalite kapıları korundu.
- Etkilenen dosyalar: `config/settings_loader.py`, `src/ui/main_window.py`, `scripts/replicate_db.py`, `tests/infrastructure/test_settings_loader.py`, `tests/infrastructure/db/test_replicate_db.py`, `tests/ui/test_main_window_env.py`, `tests/ui/test_style_manifest.py`, `docs/wiki/database_maintenance_and_scripts.md`
- Bağlantılı sayfa: [database_maintenance_and_scripts.md](database_maintenance_and_scripts.md)

## [2026-06-06] guncelleme | Finansal inputlarda canli binlik ayraci

- `CurrencySpinBox` edit modunda `TL` suffix'ini gizlemeye devam ederken binlik ayraclarini anlik uygulayacak sekilde guncellendi.
- Nokta/virgul ondalik gecisinde cursor pozisyonu korunarak sonraki rakamlar dogru ondalik kisma yazilir.
- Etkilenen dosyalar: `src/ui/widgets/shared/controls/currency_spin_box.py`, `tests/ui/widgets/test_currency_spin_box.py`, `docs/wiki/ui_architecture_and_events.md`
- Baglantili sayfa: [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-06] guncelleme | Finansal input formatlama standardi eklendi

- TL tutar/fiyat girisleri icin ortak `CurrencySpinBox` bileseni eklendi; focus sirasinda ham sayi, focus disinda `1.234,56 TL` gorunumu standardize edildi.
- Eski `InstantDoubleSpinBox` her tus vurusunda formatlama yapan teknik borctan arindirilarak yeni finansal input standardina baglandi.
- Finansal hesaplamalarda formatli metin parse etmek yerine `value()` ve `decimal_value()` raw degerleri kullanilacak sekilde dialog ve panel kullanimlari guncellendi.
- Etkilenen dosyalar: `src/ui/widgets/shared/controls/`, `src/ui/widgets/**/dialogs/`, `src/ui/widgets/planning/`, `src/ui/pages/stock_detail/`, `tests/ui/widgets/`
- Baglantili sayfa: [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-06] duzeltme | Finansal Planlama hedef durumu karti dinamik satir yuksekligi

- Finansal Planlama ozetindeki `Hedef Durumu` karti dar pencere genisliginde iki satira kirilan durum metni icin minimum deger yuksekligi ayiracak sekilde guncellendi.
- Kart renkleri mevcut `cssState` ve tema QSS token'lariyla korunur; Python tarafinda renk hardcode'u eklenmedi.
- Etkilenen dosyalar: `src/ui/widgets/shared/cards/info_card.py`, `src/ui/widgets/planning/panels/budget_form_panel.py`, `tests/ui/widgets/test_budget_form_panel_pin.py`
- Baglantili sayfa: [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-06] guncelleme | Baslangic pencere boyutu analiz genisligine hizalandi

- Ana pencere baslangic boyutu `1400x900` merkezi sabitleriyle tanimlandi; Analiz sayfasi genislik sozlesmesiyle uyumlu hale getirildi.
- Sayfa bazli resize, minimum size veya fullscreen davranisi eklenmedi.
- Etkilenen dosyalar: `src/ui/main_window.py`, `tests/ui/test_app_startup.py`
- Baglantili sayfa: [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-06] guncelleme | Dashboard gorunen adi Ana Sayfa yapildi

- Dashboard teknik kimligi ve `dashboard` scope anahtari korunarak kullaniciya gorunen sayfa adi `Ana Sayfa` olarak guncellendi.
- Optimizasyon ve ilgili UI metinlerinde `Dashboard Portfoyu` yerine `Ana Portfoy` kullanilacak sekilde merkezi L10N sabitleri degistirildi.
- Manuel test kilavuzundaki kullanici gorunen Dashboard ifadeleri Ana Sayfa diline cekildi.
- Etkilenen dosyalar: `src/ui/shared/locale_tr.py`, `tests/ui/test_formatters.py`, `docs/wiki/manual_testing_guide.md`, `docs/wiki/service_watchlist.md`, `docs/wiki/ui_architecture_and_events.md`
- Baglantili sayfalar: [manual_testing_guide.md](manual_testing_guide.md), [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-06] guncelleme | Canli fiyat ve kapanis fiyat akisi ayrildi

- Intraday/latest fiyatlar icin `latest_prices` tablosu, domain modeli ve SQLAlchemy repository eklendi; 15 dakikalik canli yenileme ve model portfoy manuel fiyat yenileme artik bu cache'e upsert ediyor.
- `daily_prices` yalniz kapanmis islem gunu kapanis verisi olarak sinirlandi; uygulama acilisi, Dashboard manuel kapanis guncellemesi ve Ayarlar "son gunden bugune" akisi bugun yerine son tamamlanmis islem gununu hedefler.
- Dashboard ve Model Portfoy ekran degerlemeleri `latest_prices` fallback'ini kullanirken Excel rapor, backtest ve fiyat sagligi `daily_prices` sozlesmesini korur.
- Etkilenen dosyalar: `src/domain/`, `src/application/services/market/`, `src/application/services/portfolio/`, `src/infrastructure/db/sqlalchemy/`, `src/ui/`, `scripts/apply_latest_prices_schema.py`, `tests/`
- Baglantili sayfalar: [service_portfolio_and_market.md](service_portfolio_and_market.md), [database_schema_and_orm.md](database_schema_and_orm.md), [ui_architecture_and_events.md](ui_architecture_and_events.md), [service_reporting_and_export.md](service_reporting_and_export.md)

## [2026-06-06] güncelleme | Dashboard Özet Kartları ve Güncelleme Bilgisi Görsel İyileştirmesi

- Hem **Dashboard** hem de **Model Portföyler** sayfalarında yer alan "Son güncelleme" (`lbl_last_update`) etiketleri, `lastUpdateLabel` CSS sınıfı üzerinden ortaklaşa biçimlendirilecek şekilde standartlaştırıldı.
- `lastUpdateLabel` sınıfının stili [dashboard.qss](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/styles/features/dashboard.qss) dosyasında güncellenerek; yazı boyutu büyütüldü (`@FONT_MD`, 15px) ve rengi parlak cyan/vurgu rengi (`@COLOR_ACCENT`) olarak ayarlandı.
- Model Portföyler sayfasındaki butonlar ve altındaki güncelleme bilgisi etiketi `QVBoxLayout` sarmalayıcısı ile üst başlık (`header`) hizasına yerleştirildi.
- Dashboard sayfasındaki tüm özet kartlarının (Toplam Portföy Değeri, Toplam Maliyet, Nakit Sermaye, Dönemsel Getiriler) arka plan renk ve kenarlık tasarımları, mavi tonlu "Toplam Portföy Değeri" (`cardType="total"`) kartının tasarımıyla (`@COLOR_CARD_GRADIENT_TOTAL` ve `@CARD_TOTAL_BORDER` kullanılarak) birleştirilerek ortaklaştırıldı.
- Özet kartı başlıklarının (`summaryCardTitle`) yazı boyutu büyütüldü (`@FONT_BASE`, 14px), yazı fontu `bold` yapıldı ve renkleri tema geçişlerine duyarlı, parlak `@COLOR_TEXT_BRIGHT` tokenına bağlandı.
- Etkilenen dosyalar: `src/ui/pages/model_portfolio/utils/model_portfolio_ui_builder.py`, `src/ui/styles/features/dashboard.qss`, `src/ui/styles/features/model_portfolio.qss`, `tests/ui/pages/test_model_portfolio_page.py`
- Bağlantılı sayfa: [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-06] güncelleme | Takip Listesinde Hisse Düzenleme Mekanizması

- Takip listesindeki ("Listelerim") hisselerin notlarını düzenlemeyi sağlayan kalem (`pencil`) butonu silme butonunun soluna yerleştirildi.
- Hissenin notlarını güncellemek için modern `EditStockInWatchlistDialog` dialog penceresi oluşturuldu.
- Butonların üst üste binmesini önlemek amacıyla eylem sütunu 100px sabit genişliğe alındı ve butonlar yatayda orantılı hizalandı.
- Tabloda kelime kaydırma (word wrap) aktif edilerek uzun notların eylem butonlarını ezmeden alt satıra geçmesi ve satır yüksekliklerinin içeriğe göre otomatik uyum sağlaması (`resizeRowsToContents()`) sağlandı.
- Clean Architecture katmanlarında (Domain, Application, Infrastructure) `update_item_in_watchlist` ve `update_watchlist_item_notes` metodları eklenerek veri akışı ve kalıcılık sağlandı.
- Arayüzdeki yeni metinler `L10N` sınıfına (`locale_tr.py`) eklenerek Türkçe lokalizasyon standartları korundu.
- Etkilenen dosyalar: `src/domain/ports/repositories/i_watchlist_repo.py`, `src/infrastructure/db/sqlalchemy/repositories/sa_watchlist_repository.py`, `src/application/services/watchlist/watchlist_service.py`, `src/ui/shared/locale_tr.py`, `src/ui/widgets/watchlist/dialogs/edit_stock_in_watchlist_dialog.py`, `src/ui/widgets/watchlist/dialogs/__init__.py`, `src/ui/pages/watchlist_page.py`
- Bağlantılı sayfa: [service_watchlist.md](service_watchlist.md)

## [2026-06-06] guncelleme | Model portfoy rapor fiyat sagligi kapisi

- Model portfoy raporlari icin tarihsel `daily_prices` kapanis verisi sozlesmesi netlestirildi; canli ekran fiyatlari Excel raporuna karistirilmiyor.
- Dar fiyat sagligi kapsamlarinda tum secili hisseler ayni is gununde eksikse, baska aktif kapsamda fiyat varsa gun artik tatil adayi olarak gizlenmiyor ve eksik veri sayiliyor.
- Model portfoy export akisi eksik kapanis fiyati varken dosya secme ve Excel uretimini baslatmadan kullaniciya hisse/tarih listesi gosterir.
- Etkilenen dosyalar: `src/application/services/market/price_data_health_service.py`, `src/ui/pages/model_portfolio/`, `docs/wiki/service_portfolio_and_market.md`, `docs/wiki/service_reporting_and_export.md`
- Baglantili sayfalar: [service_portfolio_and_market.md](service_portfolio_and_market.md), [service_reporting_and_export.md](service_reporting_and_export.md)

## [2026-06-05] guncelleme | Excel raporlarindan grafik sayfalari kaldirildi

- Excel history export workbook sozlesmesi sadeleştirildi; `Grafikler` ve gizli `Grafik Verileri` sayfalari tamamen kaldirildi.
- Reporting katmanindaki chart builder/factory bagimliligi, chart data hazirlama yardimcilari ve bu sayfalara ozel test beklentileri temizlendi.
- Dogrulama: hedefli `tests/application/test_excel_report_builder.py` ve `tests/application/test_model_portfolio_excel_export_service.py`, ardindan tam `tests` kosumu planlandi.
- Etkilenen dosyalar: `src/application/services/reporting/`, `tests/application/test_excel_report_builder.py`, `docs/wiki/service_reporting_and_export.md`
- Baglantili sayfalar: [service_reporting_and_export.md](service_reporting_and_export.md), [architecture.md](architecture.md)

## [2026-06-04] güncelleme | Hedef Validasyonu ve Tablo İçi Aksiyonlar

- "Yeni Hedef" diyaloğunda geçmiş tarihlerin seçilmesi takvim üzerinde kısıtlandı; elle girilirse dinamik validasyon etiketi gösterilip "Ekle" butonu pasifleştirildi.
- Hedef Takibi tablosunun üstündeki global "Katkı Ekle" ve "Sil" butonları kaldırılarak her satırın "İşlemler" sütununa modern, ikonlu iki buton (Ekle, Sil) olarak yerleştirildi.
- Seçili satır olmaması uyarı toast bildirimleri gereksizleştiği için kaldırıldı.
- Inline `setStyleSheet` kullanımı engellenerek QSS tabanlı `@COLOR_DANGER` ve `@FONT_XS` uyumlu `validationErrorLabel` stili forms.qss'e eklendi.
- Etkilenen dosyalar: `src/ui/widgets/planning/dialogs/goal_input_dialog.py`, `src/ui/widgets/planning/panels/goals_panel.py`, `src/ui/pages/planning_page.py`, `src/ui/styles/shared/forms.qss`
- Bağlantılı sayfa: [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-04] güncelleme | Arayüz Türkçe Karakter Düzeltmesi ve L10N Altyapısı

- Arayüzdeki (Frontend/UI) tüm kullanıcı metinlerinin Türkçe karakter kullanım hataları giderildi.
- Gelecekte arayüz metinlerinin yönetimini kolaylaştırmak amacıyla merkezi lokalizasyon yapısı (`locale_tr.py`) kurularak tüm metinler `L10N` sınıfına taşındı.
- Arayüz dosyalarını otomatik olarak tarayıp kullanıcıya dönük metinleri dönüştüren `scripts/migrate_ui_strings.py` aracı geliştirildi.
- Kodlama standartlarına UI metinlerinde Türkçe karakterlerin doğru kullanımını ve `L10N` yapısını zorunlu kılan kurallar eklendi.
- Etkilenen dosyalar: `src/ui/**/*.py`, `src/ui/shared/locale_tr.py`, `scripts/migrate_ui_strings.py`, `RULES.md`, `CLAUDE.md`
- Bağlantılı sayfalar: [RULES.md](../../RULES.md), [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-04] güncelleme | AI Asistanı Sidebar ve Arayüz Güncellemesi

- AI Finans Asistanı sayfasındaki "Sohbetler" butonu ve sidebar içindeki "Kapat" butonu kaldırıldı.
- Sidebar uzunluğu chat panelinin sol/üst köşesinden (`x=0, y=0`) başlayıp tam yükseklik (`self.height()`) kaplayacak şekilde güncellendi.
- `QParallelAnimationGroup` ve `QPropertyAnimation` ile hem sidebar hem de yeni `btn_toggle_sidebar` butonu 250 ms süreyle smooth bir şekilde eş zamanlı kayacak şekilde animasyonlandırıldı. Buton, sidebar kapalıyken `x=20, y=14` konumunda "Merhaba" mesajının üstünde durur, açılırken ise sidebar'ın sağ üst köşesine (`x=sidebar_width - 46, y=14`) taşınır.
- Etkilenen dosyalar: `src/ui/assets/icons/sidebar.svg`, `src/ui/pages/ai_page/right_panel/chatbot_panel.py`, `src/ui/pages/ai_page/right_panel/chat_history_sidebar.py`, `tests/ui/pages/ai_page/test_ai_page_right_panel.py`
- Bağlantılı sayfa: [ui_architecture_and_events.md](ui_architecture_and_events.md)

## [2026-06-04] güncelleme | YFinance Fiyat Uyumsuzluğu Düzeltmesi ve Kurallar Güncellemesi

- Yahoo Finance'in split ex-date kayması ve double-adjustment sorununu çözen dinamik kırılma noktası analizi (transition-aware) fiyat düzeltme altyapısı uygulandı.
- DB'deki daily_prices ve indirilen fiyat serileri dinamik geçiş tarihine göre kontrollü güncellenecek şekilde revize edildi.
- RULES.md dosyasına, geçici/debug/test dosyalarının işi bitince kullanıcı onayıyla repodan silinmesine dair yeni kural eklendi. Ana dizindeki geçici test scriptleri temizlendi.
- Etkilenen dosyalar: `src/application/services/corporate_actions/price_adjustment_service.py`, `src/application/services/simulation/backfill_service.py`, `src/application/services/market/price_data_health_service.py`, `RULES.md`
- Bağlantılı sayfalar: [RULES.md](../../RULES.md), [service_corporate_actions.md](service_corporate_actions.md)

## [2026-06-04] güncelleme | Sermaye Artırımı ve Düzeltme Entegrasyonu

- Kurumsal işlemler sonrasında oluşan maliyet/adet uyuşmazlıklarını geçmişe yönelik denetim izli düzeltme (Retroactive Adjustment with Audit Trail) mimarisiyle çözüldü.
- `trades` tablosuna `original_quantity` ve `original_price` kolonları eklendi.
- `trade_adjustments` tablosu oluşturuldu ve SQLAlchemy modelleri güncellendi.
- `CorporateActionService` sentetik trade ekleme yerine geçmiş işlemleri retroactive olarak bölünecek şekilde güncellendi ve `trade_adjustments` tablosuna denetim izi yazıldı.
- Seçili Hisse Detay UI sayfasına "Uygulanan Sermaye Artırımları" tablosu yerleştirildi ve işlem geçmişi tablosunda orijinal alım değerlerinin gösterilmesi sağlandı.
- Etkilenen dosyalar: `src/application/services/corporate_actions/corporate_action_service.py`, `src/ui/pages/stock_detail/stock_detail_page.py`, `src/infrastructure/db/sqlalchemy/orm_models.py`, `src/application/container_parts/services.py`, `tests/application/test_corporate_action_service.py`, `tests/ui/test_refactor_guards.py`
- Bağlantılı sayfalar: [database_schema_and_orm.md](database_schema_and_orm.md), [service_corporate_actions.md](service_corporate_actions.md)

## [2026-06-04] yeni-sayfa | Kapsamli manuel test yonergesi

- Uygulamanin tum ana sayfalari ve kritik capraz akislar icin `docs/wiki/manual_testing_guide.md` eklendi.
- Rehber; ortam hazirligi, minimum test verisi, sayfa bazli manuel senaryolar, negatif testler, capraz akislar ve surum oncesi smoke checklist bolumlerini kapsar.
- Her manuel test maddesi icin ID, on kosul, adimlar, beklenen sonuc, kanit ve temizlik/not formati standardize edildi.
- Uygulama kodu degismedi; calisma yalnizca dokumantasyon ve wiki katalog/log guncellemesidir.
- Baglantili sayfa: [manual_testing_guide.md](manual_testing_guide.md)

## [2026-06-03] guncelleme | Butce kalemi pinleme

- Finansal Planlama > Butce Yonetimi icin tekrar eden gelir/gider kalemleri `budget_pinned_items` tablosunda baslik + varsayilan tutar olarak saklanacak sekilde eklendi.
- Bos ay acildiginda pinli kalemlerden otomatik butce taslagi uretilir; kayitli aylarin `budget_items` icerigi sessizce degistirilmez.
- UI tarafinda butce satiri bileseni ayrildi ve gelir/gider satirlarina bookmark tabanli pin/unpin aksiyonu eklendi.
- Dogrulama: hedefli domain/application/infrastructure/UI testleri -> **23 passed**; tam `tests -q` kosumu -> **405 passed, 1 failed** (`ChartRenderer._load_plotly_to_view` eksikligi, pinleme disi comparison modulu); pytest cache yazma izni uyarisi test sonucunu etkilemedi.
- Baglantili sayfalar: [database_schema_and_orm.md](database_schema_and_orm.md), [architecture.md](architecture.md)

## [2026-06-03] guncelleme | Model portfoy sermaye yonetimi ve secim state'i

- Model portfoy sayfasi son secim gecersizse ilk portfoyu otomatik secer; portfoy yoksa sag panel temizlenir ve tum islem butonlari pasif kalir.
- `model_portfolio_cash_movements` sermaye hareketi modeli, ORM tablosu, repository metodlari ve mevcut DB icin idempotent schema script'i eklendi.
- Model portfoy trade simulasyonu sermaye hareketlerini trade timeline'i ile birlikte isler; ayni tarih/saatte sermaye hareketi trade'den once uygulanir.
- K/Z hesabi net sermaye bazina cekildi; sermaye eklemek kar, sermaye cekmek zarar sayilmaz.
- Model portfoy UI'ina tarih/saatli `Sermaye Yonetimi` dialogu eklendi; pozisyonsuz portfoyde `Hisse Sat` pasif kalir.
- Dogrulama: hedefli application/UI/domain/infrastructure testleri -> **33 passed**; refactor guard -> **4 passed**; `tests` -> **398 passed**.
- Baglantili sayfalar: [service_portfolio_and_market.md](service_portfolio_and_market.md), [ui_architecture_and_events.md](ui_architecture_and_events.md)

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

## [2026-06-06] refactor | P0: AI Core tasinmasi & P1: L10N Hardcoded-String Temizligi

- AI modulu yfinance UI'dan tamamen bagimsizlastirildi ve core modullerine tasindi.
- Kullaniciya gosterilen UI metinleri (duz stringler ve f-stringler) tespit edilerek L10N (locale_tr.py) yapisina baglandi.
- Sadece "t {price:,.2f}" gibi saf para/sayi formatlari dokunulmadan korundu.
- RULES.md kural seti Python sanal ortam kullanimi yonergeleri ile guncellendi.
- test_ui_user_facing_text_uses_l10n_not_hardcoded_literals ve diger UI test guardlari (toplam 7 adet) basariyla gecti.
- Etkilenen dosyalar: RULES.md, src/ui/shared/locale_tr.py, src/ui/main_window.py ve bircok UI widget/sayfa modulu.

