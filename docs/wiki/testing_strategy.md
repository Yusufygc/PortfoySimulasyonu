# Test Stratejisi

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Geliştirme: [development_guide.md](development_guide.md) | Manuel test: [manual_testing_guide.md](manual_testing_guide.md)

## 1. Durum

`pytest tests -q` (2026-11-01): **1694 geçti, 4 xfailed**. Varlık defteri, Portföyüm ve haber özellikleri `tests/domain/test_asset_*`, `tests/application/services/assets|news/`, `tests/infrastructure/news/`, `tests/infrastructure/db/test_asset_repositories.py`, `tests/ui_qml/test_my_portfolio_*`, `test_assets_controller.py`, `test_news_*` dosyalarındadır; kalan testler kök dizindeki koruma ve ölçüm testleridir. Dört `xfail`, `tests/application/test_friday_excel_export_bug.py` içindeki bilinen cuma/hafta sonu Excel davranışı vakalarıdır.

## 2. Test Piramidi

| Katman | Dizin | Yaklaşım |
|---|---|---|
| Domain | `tests/domain/` | Saf modeller (`Portfolio`, `Position`, `Trade`, `CorporateAction`, `RiskProfile`, `ticker`...); veritabanı ve ağ yok. |
| Application | `tests/application/` | İş kuralları; repository ve sağlayıcılar sahte/`MagicMock`. Saf motorlar (indikatör, backtest, risk metrikleri) sentetik veriyle doğrulanır. |
| Infrastructure | `tests/infrastructure/` | Gerçek **geçici** SQLite/DuckDB ile repository, şema göçü, sağlayıcı ayrıştırıcıları; HTTP yanıtları sahte (`monkeypatch`). |
| UI (QML) | `tests/ui_qml/` | Denetleyici davranışı, QML bileşenlerinin uyarısız derlenmesi ve örneklenmesi, koruma testleri. `pytest-qt` kullanılmaz; `QQmlApplicationEngine`/`QQmlComponent` ile doğrudan yüklenir. |
| Qt uyumluluk | `tests/qt_compat/` | Ekran ölçek normalizasyonu. |
| Depo geneli | `tests/test_repo_guards.py`, `tests/test_code_quality_measurement.py` | Aşağıya bakın. |

## 3. Koruma (Guard) Testleri

| Test | Korur |
|---|---|
| `tests/ui_qml/test_architecture_guards.py` | `src/ui_qml`: `src.infrastructure`, `sqlite3`, `duckdb`, `sqlalchemy`, `src.ui` import yok; denetleyicilerde `*_repo` erişimi yok. |
| `tests/ui_qml/test_strings_catalog.py` | `Strings.*` referansları tanımlı; yinelenen veya kullanılmayan anahtar yok; QML'de sabit kullanıcı metni ve Türkçe literal yok (izin listesi hariç). |
| `tests/test_layer_guards.py` | `src/application` (bileşim kökü hariç) ve `src/domain` altyapı/çerçeve (`duckdb`, `sqlite3`, `yfinance`, `requests`, SQLAlchemy, PySide6, `src.infrastructure`, `src.ui_qml`) import etmez. |
| `tests/ui_qml/test_numbers_singleton.py` | QML `Numbers.parse` Python `parse_decimal_text` ile aynı sonucu verir; bileşenlerde kullanıcı girdisine `parseFloat`/`parseInt` yazılmaz. |
| `tests/ui_qml/test_external_content_safety.py` | Bağlantı şeması, haber metni temizliği, grafik HTML'inde JS/HTML kaçışı. |
| `tests/ui_qml/test_controller_text_ratchet.py`, `test_message_catalog.py`, `test_formatting.py` | Python metin kataloğu: denetleyicide Türkçe literal tavanı 0 (`controller_text_baseline.json`, güncelleme: `python tests/ui_qml/test_controller_text_ratchet.py`), katalog bütünlüğü, tek biçimleyici davranışı. |
| `tests/application/test_position_query_service.py` | Pozisyon rakamlarının tek kaynağı: elle hesaplanmış değerler; Portföyüm = Hisse Detay = Excel geçmişi karakterizasyonu; model portföy ağırlığı; fiyat yedek sırası. |
| `tests/ui_qml/test_controller_money_math_ratchet.py`, `test_controller_helpers.py` | Denetleyicide para/yüzde aritmetiği tavanı (güncelleme: `python tests/ui_qml/test_controller_money_math_ratchet.py`); E3/E4 ile ayrılan Qt'siz yardımcılar. |
| `tests/ui_qml/test_app_composition.py` | Bileşim kökü: QML'de kullanılan her denetleyici bağlama kayıtlı; kritik denetleyiciler arası sinyaller bağlı; testte zamanlayıcı başlamaz. Yeni denetleyici `src/ui_qml/app.py::create_controllers` listesine eklenir (duman testi ve görsel anlık görüntü aynı listeyi kullanır). |
| `tests/test_repo_guards.py` | Testlerde canlı ağ çağrısı yok; `src/ui` paketi geri gelmez; `app.py` `AA_ShareOpenGLContexts` ayarını `run_qml_app`'ten önce yapar. |
| `tests/infrastructure/test_production_guards.py` | Depoda gerçek sır literal'i yok; derleme preflight statik koşulları. |
| `tests/infrastructure/test_test_isolation.py` | Testlerin gerçek veritabanına yazmaması. |
| `tests/test_code_quality_measurement.py` | Kalite ölçüm betiğinin çıktısı ([code_quality_guardrails.md](code_quality_guardrails.md)). |

## 4. Fixture ve İzolasyon (`conftest.py`)

`tests/conftest.py` (tüm testler):
- **Gerçek veritabanı koruması** (oturum, otomatik): gerçek `data/portfolio.db` SQLite yedekleme API'siyle ve `data/market_history.duckdb` geçici klasöre kopyalanır; `DB_SQLITE_PATH` ve `DUCKDB_PATH` oraya yönlendirilir. Kopya alınamazsa boş geçici veritabanı kullanılır. Gerçek dosyalara asla yazılmaz.
- `_isolate_env_file`: `.env` yazımı (API anahtarı kaydı) geçici dizine yönlenir.
- `_no_retry_sleep`: ağ yeniden denemesi beklemesi kapatılır ([service_market_data_providers.md](service_market_data_providers.md)).
- Paylaşılan: `fake_event_bus`, `qapp`, `drain_qt_events`, `fixed_today`, `sample_stock_factory`, `sample_trade_factory`, `sample_daily_price_factory`.

`tests/ui_qml/conftest.py` (otomatik):
- Qt Quick Controls "Basic" stili (uygulamayla aynı).
- `MarketSyncController` açılış zamanlayıcısı kapatılır (arka plan DuckDB erişimi başka testlerle çakışıp native çökmeye yol açıyordu).
- `QSettings` / `last_update_store` geçici INI dosyasına yönlendirilir (gerçek kayıt defterine yazılmaz).
- `DashboardController._reload_returns` kapatılır (arka plan iş parçacığı test sonrası silinmiş QObject'e sinyal gönderip çökmeye yol açıyordu); ilgili testler işlemi doğrudan çağırır.

Arka plan işi yapan denetleyicilerde testler `ImmediateExecutor` benzeri bir yürütücüyle işleri eşzamanlı çalıştırır; böylece sinyaller deterministik olur.

## 4.0 E2E Ürün Testleri

`tests/e2e/` gerçek `Main.qml` penceresinde fare ve klavye olayıyla çalışan ürün testleridir (taze test veritabanı, ağ kapalı, ekran görüntüsü kanıtı). `pytest.ini` varsayılan koşudan hariç tutar (`not e2e`); komut: `python -m pytest -m e2e tests/e2e -v`. Plan, izlenebilirlik ve bulgular: [product_test_plan.md](product_test_plan.md).

## 4.1 Ağ ve Marker'lar

`pytest.ini`: `addopts = -m "not manual and not network"`. Marker'lar: `ui`, `integration`, `network` (canlı ağ), `manual` (elle çalıştırılacak). Varsayılan paket canlı kaynaklara bağlı değildir. Arka plan iş parçacığı bekleyen QML/denetleyici testleri sabit uyku yerine ortak `wait_until` fixture'ını (koşul + zaman aşımı, Qt olay döngüsü) kullanır; zamanlamaya bağlı durumlar `threading.Event` kapısıyla deterministik yapılır (`test_market_sync_controller.py`). `QT_QUICK_CONTROLS_STYLE=Basic` kök `conftest.py`'de ayarlıdır; böylece QML yükleyen her test tek başına da geçer. Gerçek işletim sistemi sır deposunu deneyen tek `manual` test `test_secret_store.py` içindedir.

## 5. Komutlar

```powershell
.\venv\Scripts\python.exe -m pytest tests -q                    # tüm paket
.\venv\Scripts\python.exe -m pytest tests/ui_qml -q             # yalnız arayüz
.\venv\Scripts\python.exe -m pytest tests/application/services/simulation -q
.\venv\Scripts\python.exe -m pytest tests -k dividend -q        # anahtar kelimeyle
.\venv\Scripts\python.exe -m pytest --collect-only -q           # toplanan test sayısı
```

Her yeniden düzenlemeden sonra ve yeni özellik eklemeden önce paketin yeşil olduğu doğrulanır. `.pytest_cache` izin uyarısı ortam kaynaklı bilinen bir uyarıdır.

## 6. CI

`.github/workflows/tests.yml`: test işi (Windows, Python 3.10/3.11 zorunlu + 3.12 deneysel, offscreen Qt, kapsam eşiği %80; yerel taban %84), kalite kapısı ve `pip-audit` güvenlik taraması ([project_build_and_deployment.md](project_build_and_deployment.md)). Görsel eşdeğerlik: büyük QML yeniden düzenlemelerinde `scripts/qml_visual_snapshot.py render` ile eski ve yeni koddan ofscreen ekran görüntüsü alınıp `compare` ile piksel piksel karşılaştırılır (bkz. [qml_pages_guide.md](qml_pages_guide.md)). Kapsamı yerelde ölçmek: `pytest tests -q --cov=src --cov=config --cov-report=term`. Nuitka derlemesi CI'da koşmaz; yayın öncesi `scripts/build_preflight.py` ile elle doğrulanır ([project_build_and_deployment.md](project_build_and_deployment.md)).

## 7. Yeni Test Yazarken

- Servis testinde mock repository kullanın; zaman çizelgesi, nakit ve geçmişe dönük girişler için gerçek `PortfolioService` + sahte repo birleşimi (`tests/application/test_dividend_cash_flow.py` örneği) tercih edilir.
- SQLite davranışı (`BIGINT` id, göç, FK) için gerçek geçici veritabanı kullanın; mock bu sınıf hatayı yakalamaz (örnek: BIGINT id hatası yalnızca gerçek veritabanıyla görüldü).
- QML bileşeni için `QQmlComponent` ile yükleyip uyarı listesinin boş olduğunu doğrulayın; bileşen nesnesini testin sonuna dek referansta tutun (aksi halde çöp toplanıp "already deleted" hatası verir).
- Canlı ağ çağrısı eklemeyin; sağlayıcıları `monkeypatch` ile sahteleyin. Haber sağlayıcılarında `fetcher`/`poster` enjekte edilir, ayrıştırıcılar kayıtlı örnek yanıtla saf fonksiyon olarak sınanır; kaynakların hâlâ çalışıp çalışmadığı `scripts/probe_news_sources.py` ile (salt okunur, elle) doğrulanır.
- Arka plan işi yapan yeni denetleyiciler `autostart=False` varsayılanıyla yazılır ve testte `executor`'ı eşzamanlı sahte yürütücüyle değiştirir (`NewsController`, `AssetsController`, `NewsSettingsController`).
- QML'de Repeater/ListView temsilcileri `findChildren` ile değil `count` özelliğiyle sınanır; QML dosyasında parametre sayısı çoksa test yardımcılarını `**options` ile yazın (kalite ölçümü test dosyalarını da sayar).
- Yeni `Strings` anahtarı kullanılmıyorsa `test_strings_catalog` kırar; kullanılmayan anahtarı silin.
- **Gerçek saate bağlı test yazmayın:** piyasa saati/günü kodu `src/domain/market_clock.py` (`market_now`, `market_today`) kullanır; testler bunları kodun içe aldığı modülde yamalar (`monkeypatch.setattr("...startup_jobs_controller.market_now", ...)`). Saat 19:00'dan sonra kırılan iki başlangıç işi testi bu hatadan çıktı.
- **Yama hedefi kalkınca testleri tarayın:** koddan bir bağımlılık (ör. `datetime`) kalkarsa veya yer değiştirirse `grep -rn "<modül>.<ad>" tests` ile o hedefi yamalayan testler bulunup güncellenir; yama sessizce etkisiz kalıp test yalnızca belirli saatlerde geçer.
- **Oran/yüzde formüllerini elle hesaplanmış değerle doğrulayın:** türev yüzde değerleri (ROE, marj, büyüme) için girdisi basit sayılarla (ör. marj %10, devir 1, kaldıraç 4 -> ROE %40) beklenen değeri elle hesaplayan birim test yazın; "çıktı biçimi doğru" testi birimi 100 kat yanlış formülü yakalamaz (DuPont yedek ROE hatası).
- **Taşıma refaktörü için karakterizasyon:** davranışı koruyan bölmeden önce sabit girdilerle çıktıyı kaydedin (JSON/SHA-256) ve sonra aynı girdilerle karşılaştırın; uygun olanı kalıcı teste çevirin.
