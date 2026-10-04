# Derleme, Dağıtım ve CI

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Geliştirme: [development_guide.md](development_guide.md)

## 1. Nuitka ile Windows `.exe` (`build_nuitka.bat`)

PyInstaller yerine **Nuitka** kullanılır (Python'u C'ye çevirip derler; performansı artırır, tersine mühendisliği zorlaştırır). Betik sırasıyla:

1. `venv` veya `.venv` içindeki Python'u (yoksa sistem Python'u) seçer.
2. `pip install -r requirements.txt -r requirements-build.txt` (`nuitka==2.7.14` pinli).
3. `scripts\build_preflight.py` ile yayın öncesi kontrolleri çalıştırır; başarısızsa durur.
4. Nuitka'yı çalıştırır: `--standalone --onefile --enable-plugin=pyside6 --include-data-dir=src/ui_qml=src/ui_qml --disable-console`, `--include-package=yfinance/pandas/openpyxl/sqlalchemy/keyring` (+ `--include-distribution-metadata=keyring`; arka uç keşfi için), simge `icons/icon.ico`, çıktı `dist/`, giriş `app.py`. Test ve pytest paketleri dışarıda bırakılır.
5. `dist\.env` varsa hata verip çıkar.

Dikkat:
- `src/ui_qml` dizini QML dosyaları, SVG ikonlar, JS kütüphaneleri ve HTML şablonlarıyla pakete dahildir.
- `data/` klasörü pakete **gömülmez** (2026-10-04'e kadar gömülüyordu; gerçek `portfolio.db` ve ~150 MB DuckDB kişisel veri taşıdığından kaldırıldı). Uygulama `.exe` dizininde boş `data/` oluşturur; piyasa verisi açılış senkronuyla veya `scripts/sync_bist_to_duckdb.py` ile dolar. **Doğrulanmadı:** `onefile` paketinde `sys.executable` dizininin kalıcı olup olmadığı (`app_root()`) gerçek bir derlemeyle denenmeli.
- Bilimsel kütüphaneler (SciPy, pandas, scikit-learn) ve WebEngine paketlemeyi ağırlaştırır; derleme uzun sürebilir.
- Gerçek `.env` pakete **gömülmez**. Paketlenen uygulama, çalıştığı dizindeki `.env` dosyasını okur (`settings_loader`, `sys.frozen` ise `sys.executable` dizini); `.env` yanına konulmalıdır.

## 2. Release Preflight (`scripts/build_preflight.py`)

Denetler: Python >= 3.10; `requirements.txt` ve `requirements-build.txt` aktif satırlarının `==` ile pinli olması; `nuitka==` varlığı; `icons/icon.ico`, `.env.example`, `build_nuitka.bat`, `pytest.ini` dosyalarının varlığı; `pytest.ini` marker'larının (`manual`, `network`, `ui`, `integration`) tanımlı olması; `dist/.env` yokluğu; `build_nuitka.bat`'ın `data/` klasörünü gömmemesi; etkin Python'da `nuitka` import edilebilirliği. `nuitka import` adımı düşerse yayın engelleyicidir: `python -m pip install -r requirements-build.txt`.

Testler preflight'ın statik koşullarını da denetler (`tests/infrastructure/test_production_guards.py`).

## 3. Bağımlılık Yönetimi

`requirements.txt` ve `requirements-build.txt` sürümleri **pinli** tutulur (`paket==sürüm`). Aksi halde yfinance, PySide6/WebEngine veya pandas'ın beklenmedik güncellemesi arayüz çöküşü ya da hesap hatası getirebilir. Uygulama Qt binding'i `PySide6`'dır (eski `PyQt5` pinleri kaldırılmıştır); kullanılmayan paketler (`tradingview-datafeed`, `websocket-client`) 2026-10-03'te kaldırılmıştır. Yeni paket eklerken sürüm yazılır ve `pip check` yeşil olmalıdır.

## 4. Çalışma Zamanı Ayarları

`.env.example` yüzeyi: `DB_SQLITE_PATH`, `DUCKDB_PATH` (isteğe bağlı), `GEMINI_API_KEY`, `AI_CORE_API_URL`, `EVDS_API_KEY`, `TCMB_DEPOSIT_RATE_FALLBACK`, `LOG_DIR`, `LOG_LEVEL`, `LOG_CONSOLE_LEVEL`, `LOG_FILE_LEVEL`. Donmuş (`frozen`) uygulamada yollar `sys.executable` dizinine göre çözülür; loglar `logs/` altında dönen dosyadır (5 MB x 5 yedek). Ayrıntı: [development_guide.md](development_guide.md).

## 5. CI (GitHub Actions)

`.github/workflows/tests.yml` üç iş çalıştırır (`push`, `pull_request` ve haftalık zamanlama): **test** (Windows; Python 3.10 ve 3.11 zorunlu, 3.12 deneysel/engelleyici değil; `QT_QPA_PLATFORM=offscreen`; `pip install -r requirements.txt`, `pip check`, `pytest --collect-only -q`, `pytest tests -q --cov=src --cov=config --cov-fail-under=80`, kapsam raporu artifact), **quality** (`scripts/measure_code_quality.py` tavanları: 14 sınıf, 98 fonksiyon, 0 dosya; yeni eşik ihlali eklenemez, borç azaldıkça tavanlar düşürülür) ve **security** (`pip-audit` ile kurulu ortamın tamamının, geçişli bağımlılıklar dahil, bilinen açıklara karşı taranması). `pytest.ini` filtresi `manual` ve `network` testlerini dışarıda bırakır. Nuitka derlemesi CI'da koşmaz. Lint (ruff/flake8) henüz yoktur: mevcut kodda toplu temizlik gerektirir.

## 6. Çalıştırma Betikleri

`run_prod.bat` (`PORTFOYSIM_ENV` boş) ve `run_test.bat` (`PORTFOYSIM_ENV=test`, `.env.test` okunur) uygulamayı başlatır; içlerinde bir geliştiricinin Python yolu yazılıdır ve başka makinede güncellenmelidir.

## 7. `auto_commit.py`

Kök dizindeki `auto_commit.py`, değişen dosyaların diff'ini Gemini API'ye (`gemini-2.5-flash`) göndererek Türkçe commit mesajı önerir. Hassas dosyalar (`.env*`, anahtar/sertifika uzantıları, `.db`, `.sqlite`, adında `secret`/`password`/`token`/`api_key` geçenler) dış API'ye gönderilmez; yine de diff içeriği dış servise gider. Zorunlu bir süreç adımı değildir. Gemini anahtarını önce işletim sistemi sır deposundan (Ayarlar sayfasının yazdığı yer), sonra ortam değişkeninden, en son `.env` dosyasından okur. Commit kuralları için [GOVERNANCE.md](../../GOVERNANCE.md).
