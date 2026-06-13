# Wiki Değişiklik Günlüğü

> Ana katalog: [index.md](index.md) | Mimari: [architecture.md](architecture.md)  
> Bu dosya **yalnızca ekleme** yapılır. Eski girişler hiçbir zaman silinmez veya düzenlenmez.  
> Grep ile son girişler: `grep "^## \[" docs/wiki/log.md | head -10`

---
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

