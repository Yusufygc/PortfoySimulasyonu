# Proje Derleme ve Dağıtım (Build & Deployment)

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, kodun son kullanıcıya sunulabilir bir masaüstü uygulaması haline (Windows `.exe`) nasıl getirildiğini ve versiyonlama süreçlerini kapsar.

## 1. Nuitka ile Derleme (`build_nuitka.bat`)

Python kodlarını paketlemek için PyInstaller yerine **Nuitka** kullanılır. Nuitka, Python kodunu C diline çevirip (transpile) derleyerek, performans artışı sağlar ve tersine mühendisliği (reverse engineering) PyInstaller'a kıyasla zorlaştırır.

### Derleme Süreci
1. `build_nuitka.bat` scripti çalıştırılır.
2. Script `requirements.txt` ve `requirements-build.txt` dosyalarındaki pinli bağımlılıkları kurar.
3. Nuitka, `app.py` ana dosyasından başlayarak tüm iç ve dış bağımlılıkları (`PySide6`, Qt WebEngine, `pandas`, `scipy` vb.) C koduna çevirir.
4. Uygulamanın ikonu `icons/portfoy-simulasyonu.ico` dosyasıyla ayarlanır.
5. `.exe` çıktısı oluşturulur.

Güvenlik kuralı: Gerçek `.env` dosyası build çıktısına gömülmez. Paketlenen uygulama, çalıştığı dizindeki kullanıcıya/ortama özel `.env` dosyasını runtime sırasında okur.

*Not:* Bilimsel kütüphanelerin (SciPy, Pandas, YFinance) paketlenmesi Nuitka için ağırdır. Derleme süreci bilgisayar gücüne bağlı olarak uzun sürebilir.

## 2. Bağımlılık Yönetimi (`requirements.txt`)

Uygulamanın sürdürülebilirliği için `requirements.txt` ve `requirements-build.txt` dosyalarındaki kütüphane versiyonları "Pinli" (sabitlenmiş) olarak tutulmalıdır (`paket==versiyon`). Aksi halde YFinance, PySide6/Qt WebEngine veya Pandas'ın bir anda yeni versiyona geçmesi, beklenmedik arayüz çöküşlerine veya hesaplama hatalarına yol açabilir.

Qt binding standardı: üretim kodu Qt sınıflarını doğrudan PySide6 modüllerinden değil `src/qt_compat/` paketinden alır. `requirements.txt` içinde uygulama binding'i `PySide6==6.11.1` olarak pinlidir; eski `PyQt5` ve `PyQtWebEngine` pinleri kaldırılmıştır.

Yeni bir paket eklendiğinde sürüm numarası açıkça belirtilmelidir.

## 3. Faz 6 Release Preflight ve CI

Faz 6 ile release akışına `scripts/build_preflight.py` eklenmiştir. Script aşağıdaki kontrolleri yapar:

- Python sürümü `>= 3.11`.
- `requirements.txt` ve `requirements-build.txt` içindeki aktif dependency satırları `==` ile pinlidir.
- `requirements-build.txt` içinde `nuitka==...` bulunur.
- `icons/portfoy-simulasyonu.ico`, `.env.example`, `build_nuitka.bat` ve `pytest.ini` mevcuttur.
- `pytest.ini` içinde `manual`, `network`, `ui`, `integration` marker'ları tanımlıdır.
- `dist/.env` bulunmaz.
- Aktif Python ortamında `nuitka` import edilebilir.

Aktif ortamda `python scripts/build_preflight.py` komutu `nuitka import` adımında fail verirse bu production blocker'dır; build ortamı `python -m pip install -r requirements-build.txt` ile tamamlanmalıdır.

GitHub Actions workflow'u `.github/workflows/tests.yml` altında tutulur. Windows + Python 3.11 üzerinde dependency install, `pip check`, `pytest --collect-only -q` ve `pytest tests -q` çalışır. Nuitka build CI'da koşmaz; manuel release öncesi preflight ile doğrulanır.

## 4. Production Ortam Anahtarları

`.env.example` aşağıdaki production yüzeyini belgelemelidir:

- DB: `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, `POOL_NAME`, `POOL_SIZE`, `DB_POOL_RECYCLE_SECONDS`, `DB_POOL_PRE_PING`
- AI/Market: `GEMINI_API_KEY`, `AI_CORE_API_URL`, `EVDS_API_KEY`, `TCMB_DEPOSIT_RATE_FALLBACK`
- Logging: `LOG_DIR`, `LOG_LEVEL`, `LOG_CONSOLE_LEVEL`, `LOG_FILE_LEVEL`

## 5. Git ve Otomatik Commit (`auto_commit.py`)

Proje geliştirilirken `auto_commit.py` scripti kullanılarak, yapılan değişikliklerin Git geçmişine daha düzenli ve proje kurallarındaki (`RULES.md` içindeki `güncelle:`, `ekle:`, `düzelt:` formatına uygun) şekilde atılması teşvik edilir. CI/CD (Sürekli Entegrasyon) eklenecekse, pipeline'lar bu formatları baz alarak versiyonlama (Semantic Versioning) yapabilir.
