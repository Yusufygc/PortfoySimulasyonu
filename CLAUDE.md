# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Oturum Başlangıcı

Her ajan/LLM oturumu, kod veya plan üretmeden önce proje kökündeki `AGENTS.md` ve `CLAUDE.md` dosyalarını okur. Ardından commit, wiki ve test kuralları için `RULES.md` takip edilir.

---

## Kurallar ve Wiki

Bu projedeki tüm **commit kuralları**, **wiki güncelleme protokolü** ve **LLM Wiki operasyon akışı** için bkz:

→ **[RULES.md](RULES.md)**

Özet:
- Her oturumda `docs/wiki/index.md` önce okunur.
- Mimari karar, yeni özellik veya önemli hata çözümü → ilgili wiki sayfası güncellenir + `log.md`'ye eklenir.
- Tüm commit mesajları Türkçe, detaylı gövde ile yazılır (`güncelle:`, `ekle:`, `düzelt:` vb.).
- Büyük sınıf/fonksiyon eşiklerinde refactor zorunluluğu ve tam test koşumu için `RULES.md` içindeki kalite kapıları takip edilir.
- Arayüzdeki (UI) tüm kullanıcı metinlerinde doğru Türkçe karakterler kullanılmalı ve bu metinler `src/ui/shared/locale_tr.py` (`L10N`) içinde yönetilmelidir.

---

## Proje Özeti

**Portföy Simülasyonu** — BIST ve küresel hisseleri takip eden PyQt5 masaüstü uygulaması.  
Markowitz optimizasyonu, risk profili analizi, backtest simülasyonu, Excel raporlama ve AI destekli analiz içerir.

| Katman | Teknoloji |
|--------|-----------|
| UI | PyQt5, QSS theming, pyqtgraph |
| Uygulama Mantığı | Python 3.10+, DI Container |
| Veritabanı | MySQL 8.0+ / SQLAlchemy ORM |
| Piyasa Verisi | YFinance |
| Veri Bilimi | NumPy, Pandas, SciPy, scikit-learn |
| Build | Nuitka (Windows .exe) |
| Test | pytest, pytest-mock |
| AI | Google Generative AI (Gemini API) |

---

## Mimari

**Clean Architecture** — bağımlılıklar yalnızca içe akar:

```
UI  →  Application  →  Infrastructure  →  Domain
```

- **Domain** (`src/domain/`): Saf iş modelleri ve port arayüzleri. Hiçbir dış bağımlılık yok.
- **Application** (`src/application/`): Servisler, DI container (`container.py`), EventBus (Pub/Sub).
- **Infrastructure** (`src/infrastructure/`): SQLAlchemy repository'ler, YFinanceClient, logger.
- **UI** (`src/ui/`): PyQt5 sayfalar, ThemeManager, PageFactory, QThread Worker.

Detay için bkz. [docs/wiki/architecture.md](docs/wiki/architecture.md).

### Event Bus

`GlobalEventBus` (PyQt5 QObject sinyalleri) arka plan iş parçacıklarından UI'a thread-safe veri iletir:

```python
container.event_bus.prices_updated.emit({"stock_id": Decimal("123.45")})
container.event_bus.prices_updated.connect(self._on_price_change)
```

### Portföy Hesaplama

Portföy her seferinde işlem geçmişinden yeniden hesaplanır (event-sourced). Türev değerler (P&L, getiri) veritabanında **saklanmaz**.

```python
portfolio = Portfolio.from_trades(repo.get_all_trades())
unrealized_pl = portfolio.total_unrealized_pl(current_prices)
```

### Optimizasyon

`OptimizationService` → SciPy minimize + Ledoit-Wolf kovaryans → per-hisse ağırlık limiti kısıtı.

---

## Veritabanı Şeması (Özet)

| Tablo | İçerik |
|-------|--------|
| `stocks` | ticker, isim, para birimi |
| `trades` | BUY/SELL işlemleri |
| `daily_prices` | Günlük kapanış fiyatları |
| `model_portfolios` / `model_trades` | Sanal portföy |
| `risk_profiles` | Risk anketi sonuçları |
| `corporate_actions` | Sermaye artırımı, temettü |
| `budgets` | Aylık birikim hedefleri |
| `watchlists` / `watchlist_items` | İzleme listeleri |

ORM ilk çalıştırmada tabloları otomatik oluşturur.

---

## Geliştirme Kurulumu

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

`.env` dosyası (proje kökünde):
```ini
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=portfoySim
POOL_NAME=portfoy_pool
POOL_SIZE=5
TCMB_DEPOSIT_RATE_FALLBACK=45.0
GEMINI_API_KEY=your_gemini_key
```

---

## Komutlar

| Görev | Komut |
|-------|-------|
| Uygulamayı çalıştır | `python app.py` |
| Testleri çalıştır | `python -m pytest tests/ -v` |
| Tek test | `python -m pytest tests/domain/test_portfolio.py::TestClass::test_method -v` |
| Kapsam raporu | `python -m pytest tests/ --cov=src --cov-report=html` |
| Windows .exe derle | `.\build_nuitka.bat` |
| Logları izle | `Get-Content logs/app.log -Tail 20` |

---

## Yeni Özellik Ekleme Kalıbı

1. **Servis:** `src/domain/ports/` → interface → `src/application/services/` → impl → `container.py` kaydı
2. **Repository:** `src/domain/ports/repositories/` → ORM modeli → `src/infrastructure/db/sqlalchemy/repositories/` → `container.py`
3. **UI Sayfası:** `BasePage` alt sınıfı → `page_factory.py` kaydı → `MainWindow` yönlendirme

---

## Test

- `tests/domain/` — saf domain modeli testleri
- `tests/application/services/` — servis birim testleri (mock repository)
- `tests/infrastructure/` — SQLAlchemy entegrasyon testleri
- Paylaşılan fixture'lar: `tests/conftest.py`

---

## Loglama

- Dosya: `logs/app.log` (dönen, 5 MB × 5 yedek)
- Setup: `src/infrastructure/logging/logger_setup.py`
