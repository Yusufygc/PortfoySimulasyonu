# 07 — Test ve Kalite

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md) | Önceki: [06_ayarlar_haber_kaynaklari.md](06_ayarlar_haber_kaynaklari.md) | Sonraki: [08_wiki_entegrasyon.md](08_wiki_entegrasyon.md)

Durum: **Taslak**

Kurallar [ARCHITECTURE_GATES.md](../ARCHITECTURE_GATES.md), [RULES.md](../RULES.md) ve [GOVERNANCE.md](../GOVERNANCE.md) ile uyumludur.

## 1. Genel Yöntem

- Her üretim değişikliği önce kırmızı testle kanıtlanır; sonra yeşile çekilir.
- Her aşama sonunda tam paket: `.\venv\Scripts\python.exe -m pytest tests/`.
- Aşama 1, 5, 6 ve 7 sonunda uygulama elle açılır (`/run` becerisi); altın yol ve kenar durumlar denenir: boş portföy, internet yok, kaynak kapalı, USD anahtarı.
- Testler gerçek veritabanına yazmaz; `QSettings` geçici INI dosyasına yönlenir (mevcut `conftest.py`).

## 2. Katman Bazlı Testler

| Katman | Dizin | Kapsam |
|---|---|---|
| Domain | `tests/domain/` | `AssetPosition`, `AssetLedger`, `NewsItem` değişmezleri |
| Application | `tests/application/services/` | `AssetLedgerService`, `AssetPriceRefreshService`, `FxRateService`, `UnifiedPortfolioService`, `NewsService` (sahte repo/sağlayıcı) |
| Infrastructure | `tests/infrastructure/` | SQLAlchemy repolar (geçici SQLite), haber sağlayıcı ayrıştırıcıları (kayıtlı örnek yanıt) |
| UI (QML) | `tests/ui_qml/` | Controller'lar, tablo modelleri, sayfa yükleme (uyarısız), `test_qml_views_runtime_smoke.py` genişletmesi |

## 3. Mevcut Koruma Testlerine Uyum

| Koruma | Gereksinim |
|---|---|
| `tests/test_repo_guards.py` | Test dosyalarında `requests.get(`, `requests.post(`, `urllib.request.urlopen(` yazılmaz; `monkeypatch` veya enjekte `fetcher` kullanılır |
| `tests/test_market_clock_guard.py` | Listedeki modüllerde `date.today()` / `datetime.now()` yasak; `market_clock` kullanılır |
| `tests/ui_qml/test_architecture_guards.py` | `src/ui_qml/**/*.py` içinde `src.infrastructure`, `sqlite3`, `duckdb`, `sqlalchemy` import'u ve `*_repo` erişimi yok |
| `tests/ui_qml/test_strings_catalog.py` | QML'de Türkçe literal yok; tanımsız, yinelenen ve kullanılmayan `Strings` anahtarı yok |
| `tests/ui_qml/test_qml_file_size_guard.py` | `Strings.qml` hariç hiçbir QML dosyası 900 satırı aşmaz |
| `pytest.ini` | Varsayılan olarak `network` ve `manual` işaretli testler atlanır; canlı yoklamalar `@pytest.mark.network` |

## 4. Kod Kalitesi Eşikleri

(`docs/wiki/code_quality_guardrails.md`, `scripts/measure_code_quality.py`)

- Sınıf ≤300 satır / 20 metot; QML denetleyicileri ≤400 satır / 30 metot.
- Fonksiyon ≤50 satır / 5 parametre / karmaşıklık ≤10.
- Mevcut eşik üstü sınıf sayısı artmaz (`--max-class-violations` tavanı).
- Kapsam: `--cov-fail-under=80`.
- `except Exception` yalnızca log + anlamlı sonuç + test ile kabul edilir.

## 5. Aşama Bazlı Doğrulama Özeti

| Aşama | Otomatik | Elle |
|---|---|---|
| 1 | `test_dashboard_*`, `test_qml_poc`, strings ve boyut korumaları | Genel Bakış'ta yalnızca grafik; Portföyüm'de işlem, sermaye, Excel, detay modalı çalışır |
| 2 | Domain + repo + servis testleri | — |
| 3 | Sembol çözümleyici, yenileme, kur testleri | Canlı yoklama betiği (isteğe bağlı) |
| 4 | Birleşik servis testleri | — |
| 5 | Controller + QML testleri | Altın / BTC / AAPL ekle, kesirli alım, dağılım, TRY↔USD, yeniden açılışta kalıcılık |
| 6 | Haber servisi + sağlayıcı + controller testleri | Haber akışı, tarayıcıda bağlantı açma, internet kesintisi |
| 7 | Ayarlar controller + QML testleri | KAP kapatılınca KAP haberi kaybolur |

## 6. Commit Düzeni

Aşama başına ayrı commit; mesajlar Türkçe, ayrıntılı gövdeli (`ekle:`, `düzelt:`, `iyileştir:` vb.). Commit mesajlarına ve PR açıklamalarına AI atıf satırı eklenmez ([RULES.md](../RULES.md) §0.2).
