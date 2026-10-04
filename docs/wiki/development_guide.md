> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Test: [testing_strategy.md](testing_strategy.md)

# Geliştirme Rehberi

Bu sayfa projeyi kurmak, çalıştırmak, test etmek ve güvenle değişiklik yapmak için gereken pratik bilgileri toplar.

## 1. Kurulum

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

- Tüm Python komutları proje kökündeki sanal ortamla çalıştırılır: `.\venv\Scripts\python.exe -m ...` ([RULES.md](../../RULES.md) §0.1).
- Geliştirme ortamı Python 3.10 ile çalışır (`build_preflight.py` en az 3.10 ister); GitHub Actions Python 3.11 kullanır.
- Bağımlılıklar `==` ile pinlidir (PySide6, yfinance, SQLAlchemy, DuckDB, pandas, SciPy, scikit-learn, openpyxl, plotly, google-genai...). Yeni paket eklerken sürüm yazılır.

## 2. Ayarlar (`.env`)

Proje kökündeki `.env` dosyası `config/settings_loader.py` ile okunur (`.env.example` şablondur):

| Anahtar | Anlam | Varsayılan |
|---|---|---|
| `DB_SQLITE_PATH` | SQLite dosyası (göreli yol uygulama köküne göre çözülür) | `data/portfolio.db` |
| `DUCKDB_PATH` | DuckDB dosyası | SQLite dosyasının yanındaki `market_history.duckdb` |
| `GEMINI_API_KEY` | Gemini API anahtarı (Yapay Zeka sayfası) | yok |
| `AI_CORE_API_URL` | AI_Core tahmin servisi adresi | `http://localhost:8000` |
| `EVDS_API_KEY` | TCMB EVDS anahtarı (TÜFE, mevduat faizi) | yok |
| `TCMB_DEPOSIT_RATE_FALLBACK` | EVDS erişilemezse yıllık mevduat faizi (%) | `45.0` |
| `LOG_DIR`, `LOG_LEVEL`, `LOG_CONSOLE_LEVEL`, `LOG_FILE_LEVEL` | Loglama | `logs/`, `INFO`... |
| `PORTFOYSIM_ENV` | `test` verilirse `.env.test` okunur | boş |

Kurallar:
- `.env`, `override=True` ile yüklenir; ancak kabuktan açıkça verilen `DB_SQLITE_PATH` ve `DUCKDB_PATH` korunur. Gerçek veriye dokunmadan betik çalıştırmak için bu iki değişken kopya dosyalara yönlendirilir.
- API anahtarları (`GEMINI_API_KEY`, `EVDS_API_KEY`) Ayarlar > API Anahtarları sekmesinden girildiğinde **işletim sistemi sır deposuna** (Windows Kimlik Bilgisi Yöneticisi, `keyring`, hizmet adı `PortfoySimulasyonu`) yazılır ve `.env`'deki düz metin kalıntı silinir; çalışan ayarlar güncellenir. Okurken depo `.env`'den önceliklidir; depo veya `keyring` kullanılamıyorsa `.env` yedeğine düşülür. Geliştirmede `.env` ile anahtar vermeye devam edilebilir. Testler gerçek depoya dokunmaz (`secret_store` autouse fixture'ı bellek içi depo kullanır); gerçek depoyla elle deneme: `pytest -m manual tests/infrastructure/test_secret_store.py`.
- Gerçek `.env` derleme çıktısına gömülmez; paketlenen uygulama yanındaki `.env` dosyasını okur.
- `logger_setup`, API anahtarı ve parola benzeri ortam değişkenlerinin değerlerini loglarda maskeler.

## 3. Komutlar

| Görev | Komut |
|---|---|
| Uygulamayı çalıştır | `.\venv\Scripts\python.exe app.py` |
| Test ortamıyla çalıştır | `run_test.bat` (`PORTFOYSIM_ENV=test`) |
| Tüm testler | `.\venv\Scripts\python.exe -m pytest tests -q` |
| Tek dosya/test | `.\venv\Scripts\python.exe -m pytest tests/domain/test_portfolio.py::TestClass::test_method -v` |
| Kapsam raporu | `.\venv\Scripts\python.exe -m pytest tests --cov=src --cov-report=html` |
| Kod kalitesi ölçümü | `.\venv\Scripts\python.exe scripts\measure_code_quality.py` |
| Windows `.exe` derle | `.\build_nuitka.bat` |
| Logları izle | `Get-Content logs/app.log -Tail 20` |

`run_prod.bat` ve `run_test.bat` içinde geliştiricinin kendi Python yolu yazılıdır; farklı makinede güncellenmelidir.

## 4. Gerçek Veriyi Koruma

- **Testler gerçek veritabanlarına yazmaz.** `tests/conftest.py` oturum başında `data/portfolio.db` (SQLite yedekleme API'siyle) ve `data/market_history.duckdb` dosyalarının kopyasını geçici klasöre alır, `DB_SQLITE_PATH`/`DUCKDB_PATH`'i oraya yönlendirir. Kopya alınamazsa boş geçici veritabanı kullanılır. QSettings de testlerde geçici INI dosyasına yönlendirilir.
- Betik veya deneme çalıştırırken kopya veritabanı kullanın:
  ```powershell
  $env:DB_SQLITE_PATH = "C:\temp\pf_copy.db"; $env:DUCKDB_PATH = "C:\temp\mh_copy.duckdb"
  ```
- Veritabanını değiştiren betikler (`purge_stock.py`, `migrate_market_universe_to_duckdb.py --execute`) önce yedek alır veya kuru çalıştırma sunar; bkz. [database_maintenance_and_scripts.md](database_maintenance_and_scripts.md).

## 5. Yeni Özellik Ekleme Kalıpları

| Hedef | Adımlar |
|---|---|
| Servis | `src/domain/ports/` arayüzü -> `src/application/services/` uygulaması -> `container_parts/services.py` kaydı -> test |
| Repository | `src/domain/ports/repositories/` -> ORM modeli (`orm_models.py`) -> `src/infrastructure/db/sqlalchemy/repositories/` -> `container_parts/repositories.py`. Mevcut tabloya sütun eklemek `database_engine._add_missing_columns` ile idempotent yapılır. |
| UI sayfası/sekmesi | `src/ui_qml/controllers/` altında denetleyici -> `app.py` içinde `setContextProperty` -> `qml/views/` veya `qml/components/` -> `Sidebar.qml`/`Main.qml` yönlendirmesi -> metinler `Strings.qml` |
| Harici veri kaynağı | `src/infrastructure/` sağlayıcısı; ağ çağrısı `retry_call` ile sarılır ([service_market_data_providers.md](service_market_data_providers.md)); testte ağ kullanılmaz |

Her özellik için: birim test, `Strings.qml` metinleri, ilgili wiki sayfası ve `log.md` girişi ([RULES.md](../../RULES.md) §1).

## 6. Kod ve Arayüz Kuralları (Özet)

- Emoji yok; ikonlar `Icons.qml` + `ModernIcon`. Metinler `Strings.qml`. Taşmasız, esnek düzen. Ayrıntı: [RULES.md](../../RULES.md) §2 ve [ui_architecture_and_events.md](ui_architecture_and_events.md).
- Para değerleri `Decimal`. Katman ihlali ve boyut eşikleri testle ve ölçümle denetlenir ([code_quality_guardrails.md](code_quality_guardrails.md)).
- Commit mesajları Türkçedir ve tek mantıksal değişikliği anlatır ([GOVERNANCE.md](../../GOVERNANCE.md)).

## 7. Sık Karşılaşılan Durumlar

| Belirti | Neden / Çözüm |
|---|---|
| `NOT NULL constraint failed: ....id` | SQLite `BIGINT` anahtar otomatik artmaz; `orm_models.py` içindeki `before_insert` dinleyicisi yeni kayıtlara `id` atar. Elle `INSERT` yazıyorsanız `id` verin. |
| Başlangıçta "Veritabanı bağlantısı sağlanamadı" | `DB_SQLITE_PATH` yanlış veya dosya kilitli; arayüz çevrimdışı modda açılır. |
| Yapay Zeka sayfasında "Simülasyon" rozeti | AI_Core servisi (`AI_CORE_API_URL`) kapalıdır; hisse modeli analizi demo sağlayıcıya düşer. Portföy Danışmanı için `GEMINI_API_KEY` yeterlidir. |
| Plotly grafikleri boş (`Plotly is not defined`) | Eski Chromium Plotly'nin CSS kuralını ayrıştıramaz; `plotly_html.py` yama uygulanmış yerel JS (`plotly-shared-patched.min.js`) üretir, CDN kullanılmaz ([comparison_lab.md](comparison_lab.md)). |
| Piyasa verisi eski | Ayarlar > Veri Sağlığı & Senkronizasyon > "Eksik BIST Barlarını Şimdi Senkronize Et"; açılışta ve kapanış verisi hazır olunca (18:30, yarım gün 13:20) otomatik de çalışır. |
