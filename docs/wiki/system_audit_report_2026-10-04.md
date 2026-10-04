> Ana sayfa: [index.md](index.md) | Kalite: [code_quality_guardrails.md](code_quality_guardrails.md) | Yol haritası: [roadmap.md](roadmap.md)

# Kapsamlı Sistem Denetim Raporu (2026-10-04)

Denetim şablonu: `V2-GenelSablon.md`. Süreç uyumu ölçütü: `AI-Gelistirme-Metodolojisi.md`. Bulgular statik inceleme ve komut çıktısına dayanır; çalıştırılan komutlar ve sayılar rapor içinde belirtilmiştir. Tam test paketi bu denetimde 1118 geçti, 4 xfailed.

## Tarama Planı

1. Dizin ağacı: 269 `src` Python dosyası (31.215 etkin satır), 136 test dosyası (1050 test fonksiyonu, 14.987 etkin satır), 8 betik, QML dosyaları ~26.000 satır.
2. Giriş noktaları: `app.py`, `src/ui_qml/app.py`, `config/settings_loader.py`, `src/application/container.py`.
3. İş mantığı: servisler, repository'ler, DuckDB/SQLite katmanı, sağlayıcılar.
4. Eşik taraması: `scripts/measure_code_quality.py` (JSON çıktısı) ve ayrı bir AST betiği (parametre sayısı, import sayısı).
5. Güvenlik ve üretim taraması: `grep` ile sır, SQL, subprocess, `verify=False`, `except`, `print`, `time.sleep`, naive datetime.

## Bölüm A — Yönetici Özeti

Proje olgun ve disiplinli: katman ihlalleri testle korunuyor, parasal hesaplar `Decimal`, parametreli SQL, sır yönetimi `.env` + log maskeleme ile yapılmış, bağımlılıklar pinli, CI var. Kritik (veri kaybı veya sızıntı) düzeyinde **doğrulanmış bir bulgu yoktur**; en ciddi risk, derleme betiğinin gerçek `data/` klasörünü `.exe`'ye gömmesidir. Yapısal borç tek noktada toplanıyor: 14 QML denetleyici sınıfı eşiği aşıyor (en büyüğü 1109 satır dosya) ve 110 fonksiyon eşik dışı. İkinci küme, hataların sessiz yutulması ve şema göçlerinin sürümsüz, elle yönetilmesidir.

| # | Bulgu | Öncelik | Boyut | Efor | Etki |
|---|-------|---------|-------|------|------|
| 1 | Derleme gerçek `data/` klasörünü `.exe`'ye gömüyor | 🟠 | Güvenlik/Üretim | S | Yüksek |
| 2 | 14 denetleyici sınıfı ve 16 Python dosyası eşik dışı | 🟠 | Mimari | XL | Yüksek |
| 3 | Aşırı karmaşık fonksiyonlar (CC 41-43) | 🟠 | Kod kalitesi | L | Orta-yüksek |
| 4 | Sessiz yutulan istisnalar (18 `pass/continue`) | 🟠 | Test/Hata yönetimi | M | Orta |
| 5 | Şema göçü sürümsüz ve tek tabloya özel | 🟠 | Üretim | M | Orta-yüksek |
| 6 | AI yerel yedek motorunda `"al"`/`"sat"` alt dize eşleşmesi | 🟡 | Mantık | S | Orta |
| 7 | BIGINT `max(id)+1` ataması eşzamanlı yazıcıda çakışabilir | 🟡 | Mimari/Veri | M | Orta |
| 8 | 43 yerde naive `datetime.now()` / `date.today()` | 🟡 | Kod kalitesi | M | Orta |
| 9 | Türkçe `lower()` sorunu (`"RİSK".lower() != "risk"`) | 🟡 | Yerel bağlam | S | Düşük-orta |
| 10 | API anahtarları düz metin `.env`'de | 🟡 | Güvenlik | M | Orta |
| 11 | CI: tek Python sürümü, kapsam/lint/CVE taraması yok | 🟡 | Üretim | M | Orta |
| 12 | Testlerde `time.sleep` ve bozuk manuel test | 🟡 | Test | S | Düşük |
| 13 | Global `yfinance_lock` tüm istekleri seri hale getiriyor | 🟡 | Performans | M | Orta |
| 14 | Dev QML görünümleri (5 dosya >1000 satır) | 🟡 | Mimari | L | Orta |
| 15 | 19 fonksiyon >5 parametre, 5 modül >25 import | 🟢 | Kod kalitesi | M | Düşük |
| 16 | Eskimiş betikler, yetkisiz `.gitignore` girdileri, belgesiz `auto_commit.py` | 🟢 | Bakım | S | Düşük |

## Bölüm B — Korunması Gereken İyi Pratikler

1. **Katman koruması testle zorunlu:** `test_architecture_guards.py`, `test_strings_catalog.py`, `test_repo_guards.py`; UI altyapıya doğrudan bağlanamaz, QML metinleri tek katalogda. Refactor sırasında bu testlerin kapsamı daraltılmamalı.
2. **Olay kaynaklı portföy ve `Decimal`:** Türev değerler saklanmıyor; alan katmanında para için `float` yalnızca `financial_goal.py:68` ilerleme oranında (oran, para değil). `Portfolio.from_trades` ve TWR serisi yapısına dokunulmamalı.
3. **Sır ve girdi güvenliği:** Gerçek `.env` izlenmiyor (`git ls-files` yalnızca `.env.example` gösteriyor, geçmişte `.env` yok), loglarda hassas değer maskeleme (`logger_setup.py`), `AI_CORE_API_URL` şema doğrulaması (`_url_env`), AI girdi güvenlik kalıpları, `eval/exec/pickle/shell=True/verify=False` kullanımı yok.
4. **Dış çağrı dayanıklılığı:** `retry.py` (üstel geri çekilme, geçici hata ayrımı), her `requests` çağrısında `timeout`, veri sağlayıcıların birbirinden ayrı hata aileleri.
5. **Test izolasyonu:** Gerçek DB'lere yazmayan oturum başına geçici kopya, ağ çağrısı yapmayan testler, `retry._sleep` yamalama; 1118 testin 42 saniyede koşması.

## Bölüm C — İncelenmedi Listesi

| Kapsam | Neden |
|---|---|
| `data/` (gerçek SQLite ve ~150 MB DuckDB) | Kişisel veri; içerik açılmadı, yalnızca şema ve kod incelendi. |
| QML dosyaları (~26.000 satır) | Satır satır okunmadı; boyut ve bağlama kalıpları `wc`/`grep` ile tarandı. |
| `tests/` içeriği | Yalnızca sayım, `time.sleep` ve yapı taraması; her test okunmadı. |
| Bağımlılık CVE ve lisans taraması | `pip-audit` kurulu değil, çalıştırılmadı. Pinli sürümlerin güvenliği doğrulanmadı. |
| Çalışan uygulama (GUI duman testi, profil) | Bu denetimde uygulama açılmadı; görsel ve etkileşimli davranış, bellek ve gerçek performans doğrulanmadı. |
| `venv/`, `__pycache__`, `logs/`, `reports/`, `scratch/`, `backups/`, `icons/` | Şablondaki hariç tutma kuralı. |
| `.github/` içinde yalnızca `tests.yml` | Başka iş akışı yok. |

## Bölüm D — Detaylı Bulgular

### [🟠] 1. Derleme gerçek veri klasörünü `.exe`'ye gömüyor
- **Persona:** DevSecOps.
- **Dosya/Konum:** `build_nuitka.bat:33`
- **Kategori:** Güvenlik / Üretim
- **Sorun:** `--include-data-dir=data=data` komutu `data/` klasörünü olduğu gibi paketler. `data/` gitignore'dadır ve gerçek `portfolio.db` (işlemler, nakit, hedefler) ile ~150 MB `market_history.duckdb` içerir.
- **Etki:** `.exe` başkasına verilirse kişisel portföy ve hedefler sızar. Ayrıca `onefile` açılışında büyük veri her seferinde geçici dizine çıkarılır.
- **Kanıt:**
```bat
--include-data-dir=src/ui_qml=src/ui_qml --include-data-dir=data=data --disable-console
```
- **Çözüm:** Veri klasörünü gömme; uygulama boş `data/` ile açıldığında tabloları zaten oluşturuyor (`create_all`). Gerekirse yalnızca boş bir şablon klasörü paketle.
- **Düzeltme Eforu:** S
- **Bağımlılık:** İlk çalıştırmada DuckDB'nin boş olması; `sync_bist_to_duckdb.py` veya açılış senkronu doldurur.
- **Durum:** Çözüldü (2026-10-04). `build_nuitka.bat` düzeltildi, preflight'a `bundled data guard` eklendi. Gerçek `onefile` derlemesi denenmedi.

### [🟠] 2. Eşik aşan denetleyici sınıfları ve dosyalar
- **Persona:** Kıdemli Yazılım Mimarı.
- **Dosya/Konum:** `src/ui_qml/controllers/` (14 sınıf)
- **Kategori:** Mimari
- **Sorun:** Ölçümde 14 sınıf >300 satır ve çoğu >20 metot: `ComparisonController` 884 etkin satır / 50 metot, `Stock360Controller` 685 / 84, `OptimizationController` 628, `AiAdvisorController` 614, `DashboardController` 611. 500 satırı aşan 16 `src` Python dosyası var; en büyükleri `comparison_controller.py` 1109, `stock_360_controller.py` 964, `financials_charts.py` 856.
- **Etki:** Aynı sınıfta durum, iş parçacığı yönetimi, biçimlendirme ve servis çağrısı birleşik olduğundan her özellik 3-4 yeri birden değiştirir; çok iş parçacıklı sinyal akışında regresyon riski artar.
- **Kanıt:** `docs/wiki/code_quality_guardrails.md` §3 tablosu (ölçüm JSON'undan).
- **Çözüm:** `Stock360Controller` örneği izlenir: saf hesap (`*_calc.py`), biçimlendirme (`*_formatters.py`) ve HTML üretimi ayrı modüle; arka plan iş akışı ortak bir `BackgroundTask` yardımcısına (ThreadPoolExecutor + Signal örüntüsü her denetleyicide tekrarlanıyor). Önce `ComparisonController` ve `Stock360Controller`.
- **Düzeltme Eforu:** XL
- **Bağımlılık:** `tests/ui_qml` içindeki 14'ten fazla test dosyası; `test_architecture_guards.py`.

### [🟠] 3. Aşırı karmaşık fonksiyonlar
- **Persona:** Kıdemli Yazılım Mimarı.
- **Dosya/Konum:** `isyatirim_provider.py:230 _scrape` (92 satır, CC 43), `chart_controller.py:162 _fetch_and_emit_chart_data` (131 satır, CC 42), `financials/metrics.py:184 _single_period` (140 satır, CC 41), `stock_360_controller.py:608` (CC 34), `stock_360_fallback.py:69` (CC 31)
- **Kategori:** Kod kalitesi
- **Sorun:** Eşik CC 10 iken bu fonksiyonlar 3-4 kat üzerinde; toplam 110 fonksiyon eşik dışı.
- **Etki:** Bir dal eklemek diğer dalları bozar; her biri için ayrı test yazmak pratikte imkansız.
- **Çözüm:** Tablo-güdümlü dallanma (`isyatirim_provider` satır eşlemesi bir sözlüğe), grafik verisi için yükleme/dönüştürme/yayın ayrımı, `_single_period` için kalem başına küçük hesap fonksiyonları.
- **Düzeltme Eforu:** L
- **Bağımlılık:** İlgili testler (`test_financial_*`, `test_chart_*`) önce karakterizasyon testi olarak sabitlenmeli.
- **Durum:** Çözüldü (2026-10-04) listelenen üç fonksiyon için: `_single_period` CC 41 -> 2, `_scrape` CC 43 -> 5, `_fetch_and_emit_chart_data` CC 42 -> ~7. Her biri önce refaktör öncesi koddan üretilen karakterizasyon testiyle sabitlendi. Aynı gün rapordaki kalan dört örnek de çözüldü: `_piotroski` CC 24 -> 2, `ChartController._calculate_indicators` CC 22 -> 1, `get_fallback_financials` CC 31 -> 1, `Stock360Controller._load_local_overview_and_technical` CC 34 -> 6. Eşik dışı toplam 110 -> 104 fonksiyon; kalanlar `code_quality_guardrails.md` §3'te.

### [🟠] 4. Sessiz yutulan istisnalar
- **Persona:** QA / Test Mühendisi.
- **Dosya/Konum:** `dashboard_controller.py:723-730`, `duckdb_optimization_market_data_provider.py:84,112`, `bist_bulk_downloader.py:73`, `ai_advisor_controller.py:507,519,542`, `planning_controller.py:315`, `stock_360_calc.py:188`
- **Kategori:** Test / Hata yönetimi
- **Sorun:** `src` içinde 241 `except Exception` var; 18'inin gövdesi `pass` veya `continue`. Çıplak `except:` yok (olumlu).
- **Etki:** Excel dışa aktarımında tarih biçimi hatalı girilirse sessizce bugüne dönülür; kullanıcı yanlış aralıkta rapor alır ve hata log'da görünmez. DuckDB sağlayıcıda sessiz atlanan seri, optimizasyonda eksik hisseyle sonuç üretir.
- **Kanıt:**
```python
try:
    s_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
except Exception:
    pass
```
- **Çözüm:** `except ValueError` ile daralt ve `logger.warning` ekle; kullanıcıya dönen sonuçta geçersiz girdiyi bildir. Diğer 17 yer için en azından `logger.debug(..., exc_info=True)`.
- **Düzeltme Eforu:** M
- **Bağımlılık:** Log hacmi; `except Exception` toplamı 241 olduğundan hepsi tek seferde değil, 18'lik küme önce.
- **Durum:** Çözüldü (2026-10-04). Düzeltme notu: Excel dışa aktarımında tarih arayüz yuvasında (`exportToExcelFile`) zaten doğrulanıyor; sessiz geri dönüş yalnızca işçi fonksiyonda savunmacı koddu, rapordaki "yanlış aralıkta rapor" senaryosu bu yolla gerçekleşmezdi. İşçi artık `date.fromisoformat` kullanıyor, geçersiz değer dış `except` ile kullanıcıya bildiriliyor. Diğer yerler: `logger.warning`/`debug` eklendi, `except` türleri daraltıldı, DuckDB `ALTER ... ADD COLUMN IF NOT EXISTS`. Bilinçli bırakılan: `stock_360_controller.py:539` (`__del__` temizliği).

### [🟠] 5. Şema göçü sürümsüz ve tek tabloya özel
- **Persona:** SRE / DevOps.
- **Dosya/Konum:** `src/infrastructure/db/sqlalchemy/database_engine.py:41-48`
- **Kategori:** Üretim
- **Sorun:** Göç aracı (Alembic) yok. `_add_missing_columns` yalnızca `cash_movements.stock_id` için yazılmış; şema sürüm tablosu yok. Yeni her sütun için bu metot elle genişletilir.
- **Etki:** Bir sonraki sütun eklemesinde unutulursa mevcut kullanıcı veritabanı `OperationalError: no such column` ile açılışta çöker; yeni kurulum ise `create_all` ile çalıştığından sorun yalnızca eski veride görünür ve testte yakalanmaz.
- **Çözüm:** `schema_version` tablosu + numaralı, idempotent göç listesi; ya da Alembic. En azından göç öncesi otomatik `data/backups/` yedeği (betiklerde var, açılışta yok).
- **Düzeltme Eforu:** M
- **Bağımlılık:** `database_schema_and_orm.md`, testlerdeki geçici DB kopyası.
- **Durum:** Çözüldü (2026-10-04). Kodda rapordan daha kötü bir durum bulundu: tüm `_init_db_schema` bloğu `except Exception` ile sarılıydı, göç hatası yutuluyordu (üç adım da her açılışta yeniden çalışıyordu). `schema_migrations.py` eklendi: sürüm tablosu, göç öncesi yedek, hata yükseltme. Açık nokta: göç hatasında kullanıcı yalnızca çevrimdışı mod görür, hata penceresi yok.

### [🟡] 6. AI yerel motorunda alt dize eşleşmesi
- **Persona:** Kıdemli Yazılım Mimarı.
- **Dosya/Konum:** `src/ui_qml/controllers/ai_advisor_controller.py:532`
- **Kategori:** Mantık hatası
- **Sorun:** Anahtar kelime listesi `"al"` ve `"sat"` içeriyor ve `in lower_q` ile alt dize olarak aranıyor.
- **Etki:** `"maliyet"`, `"analiz"`, `"portföy dağılımı"` gibi neredeyse her soru "optimizasyon" bloğunu tetikler; API anahtarı yokken yerel analiz her soruda gereksiz Markowitz aracı çağırır (yavaşlık + alakasız cevap).
- **Kanıt:**
```python
if any(w in lower_q for w in ["optimizasyon", "rebalance", "dengele", "öneri", "al", "sat"]):
```
- **Çözüm:** Sözcük sınırı: `re.search(r"\b(al|sat)\b", ...)` veya yalnızca belirgin sözcükler ("optimizasyon", "dengele", "öneri").
- **Düzeltme Eforu:** S
- **Bağımlılık:** Yerel analiz testleri.
- **Durum:** Çözüldü (2026-10-04). Yeni `advisor_query_intent.py`: sözcük sınırlı regex ve Türkçe duyarlı küçük harf (Bulgu 9'un bu noktadaki kısmı da kapandı; `planning_controller` isim eşleştirmesi iki tarafta aynı dönüşümü kullandığından dokunulmadı).

### [🟡] 7. BIGINT `max(id)+1` ataması
- **Persona:** Kıdemli Yazılım Mimarı.
- **Dosya/Konum:** `src/infrastructure/db/sqlalchemy/orm_models.py:475-491`
- **Kategori:** Mimari / Veri bütünlüğü
- **Sorun:** SQLite `BIGINT` birincil anahtar otomatik artmadığı için `before_insert` dinleyicisi `SELECT max(id)` ile sonraki değeri hesaplıyor. Okuma ve yazma arasında kilit yok; sayaç yalnızca bağlantı başına tutuluyor.
- **Etki:** Canlı fiyat yenileme iş parçacığı ile arayüzden kayıt yazan ikinci bir bağlantı aynı `max(id)` değerini okursa ikinci ekleme `UNIQUE constraint failed` ile düşer. Tek kullanıcılı masaüstünde nadirdir, ama ikisi de `latest_prices`/`golden_cross_events` gibi sık yazılan tablolarda mümkündür. (Bu dinleyici bu oturumda eklendi; risk bilinçli kabul edilmedi, burada kayda geçirilir.)
- **Çözüm:** Sütunu `BigInteger().with_variant(Integer, "sqlite")` yap (rowid takma adı, gerçek otomatik artış), mevcut tablolar için bir kerelik tablo yeniden oluşturma göçü; ya da yazma işlemini `BEGIN IMMEDIATE` ile başlat.
- **Düzeltme Eforu:** M
- **Bağımlılık:** Bulgu 5 (göç altyapısı).
- **Durum:** Çözüldü (2026-10-04), rapordaki ilk seçenekle (kilit). Çakışma önce `test_bigint_id_concurrency.py` ile yeniden üretildi (`UNIQUE constraint failed: stocks.id`), sonra dinleyiciye `UPDATE ... WHERE 0` ile yazma kilidi eklenerek giderildi. `with_variant(Integer, "sqlite")` seçeneği tablo yeniden kurulumu gerektirdiğinden (gerçek veritabanında üretilmiş sütun, FK ve 42 indeks) ertelendi, `roadmap.md`'de kayıtlı.

### [🟡] 8. Naive tarih/saat kullanımı
- **Persona:** Kıdemli Yazılım Mimarı.
- **Dosya/Konum:** `src` içinde 43 `datetime.now()` / `date.today()` (örn. `chat_session_service.py:43,55`, `screener_service.py:69,86`, `technical_analysis_service.py:90`)
- **Kategori:** Yerel bağlam
- **Sorun:** Saat dilimi bilinçli yönetilen yer yalnızca `live_price_refresh_service.py` ve `shareholder_analysis_service.py` (UTC). BIST seans koruması ve 18:15 zamanlayıcı yerel saate dayanıyor.
- **Etki:** Bilgisayar saat dilimi Türkiye dışındaysa seans penceresi, "bugün" fiyat kontrolü ve zamanlanmış senkron kayar; yaz saati uygulayan bir bölgede hata saatlik olur.
- **Çözüm:** Tek bir `market_clock` yardımcısı (`ZoneInfo("Europe/Istanbul")`) üzerinden "bugün/şimdi" al; servisler `today` parametresi alıyor (ör. `screener_service.py:69`), bu enjeksiyon noktası korunur.
- **Düzeltme Eforu:** M
- **Bağımlılık:** Seans koruması testleri.
- **Durum:** Çözüldü (2026-10-04). `market_clock.py` eklendi, piyasa takvimine bağlı 17 modül dönüştürüldü. Rapordaki "43 yerde" sayısı eksikti (gerçekte ~110 kullanım vardı); yalnızca piyasa saatine bağlı olanlar dönüştürüldü, yerel zamanın doğru olduğu yerler bilinçli bırakıldı.

### [🟡] 9. Türkçe `lower()` sorunu
- **Persona:** Kıdemli Yazılım Mimarı.
- **Dosya/Konum:** `ai_advisor_controller.py:495`; `planning_controller.py:243,259,293,295,312` (isim eşleştirme)
- **Kategori:** Yerel bağlam
- **Sorun:** Python'da `"RİSK".lower()` `"ri̇sk"` (i + birleştirici nokta) üretir ve `"risk"` ile eşit değildir. `"I".lower()` ise `"i"` verir (Türkçe için yanlış).
- **Etki:** Büyük harfle yazılan "RİSK", "ÖNERİ" sorguları anahtar kelimeyle eşleşmez; planlama kalemlerinde pin eşleştirmesi iki taraf da aynı dönüşümü kullandığı için tutarlı kalır (etki yalnızca arama/sorgu tarafında).
- **Kanıt:** `'RİSK'.lower().encode()` -> `b'ri\xcc\x87sk'`.
- **Çözüm:** Karşılaştırma için `casefold()` ve öncesinde `İ->i`, `I->ı` eşlemesi yapan küçük bir `tr_fold()` yardımcısı.
- **Düzeltme Eforu:** S
- **Bağımlılık:** Yok.

### [🟡] 10. API anahtarları düz metin `.env`'de
- **Persona:** DevSecOps.
- **Dosya/Konum:** `config/settings_loader.py:134-158` (`persist_api_keys`)
- **Kategori:** Güvenlik
- **Sorun:** Ayarlar sayfasından girilen Gemini/EVDS anahtarları proje klasöründeki `.env` dosyasına düz metin yazılıyor. Log maskeleme var, depolama şifreli değil.
- **Etki:** Aynı bilgisayardaki başka bir süreç veya yanlışlıkla paylaşılan klasör anahtarı okuyabilir. `.env` gitignore'da olduğundan depo sızıntısı riski düşük.
- **Çözüm:** Windows Kimlik Bilgisi Yöneticisi (`keyring`) ile saklama; `.env` yalnızca geliştirme yedeği olarak kalır.
- **Düzeltme Eforu:** M
- **Bağımlılık:** Yeni bağımlılık (`keyring`) ve Nuitka paketleme.

### [🟡] 11. CI kapsamı dar
- **Persona:** SRE / DevOps.
- **Dosya/Konum:** `.github/workflows/tests.yml`
- **Kategori:** Üretim
- **Sorun:** Yalnızca Python 3.11, tek işletim sistemi (Windows, uygun). README ve preflight Python 3.10+ iddia ediyor ama 3.10 hiç test edilmiyor. Kapsam ölçümü (`pytest-cov` requirements'ta yok), lint (ruff/flake8), `pip-audit`, derleme doğrulaması ve `measure_code_quality.py --fail-on-threshold` kapısı yok. Her `push`'ta tüm paket koşuyor (iyi), ancak QT platform değişkeni (`QT_QPA_PLATFORM=offscreen`) iş akışında ve `conftest.py`'de aranmadı; arayüz testlerinin CI'da nasıl koştuğu bu denetimde doğrulanmadı.
- **Etki:** 3.10'a özgü bir uyumsuzluk veya yeni CVE'li bağımlılık fark edilmeden dağıtılır; kalite eşikleri yalnızca dokümanda kalır.
- **Çözüm:** Matris (3.10, 3.12); `pip-audit` adımı; `--cov` raporu; ihlal sayısının artmasını engelleyen bir kapı (mevcut 14/110 sayısı tavan olarak).
- **Düzeltme Eforu:** M
- **Bağımlılık:** CI süresi.

### [🟡] 12. Test hijyeni
- **Persona:** QA / Test Mühendisi.
- **Dosya/Konum:** `tests/ui_qml/test_market_sync_controller.py:24,57`, `test_comparison_screener_phase7.py:157`, `test_stock_360_phase5.py:43`, `test_stock_detail_and_excel.py:39`; `tests/infrastructure/market_data/test_benchmark_fetch_manual.py:77`
- **Kategori:** Test
- **Sorun:** Beş arayüz testi 0.02-0.05 sn `time.sleep` ile arka plan iş parçacığını bekliyor; bunlar yüklü makinede kırılgan. `test_benchmark_fetch_manual.py` kaldırılmış `_investing_client` alanını kullanıyor (ölü test).
- **Etki:** Aralıklı (flaky) başarısızlık; ölü test yanlış güven verir.
- **Çözüm:** Beklemeyi `qtbot.waitUntil`/sinyal yakalama ile değiştir; manuel testi onar veya sil.
- **Düzeltme Eforu:** S
- **Bağımlılık:** Yok.

### [🟡] 13. Global `yfinance_lock`
- **Persona:** SRE / DevOps.
- **Dosya/Konum:** `src/infrastructure/market_data/yfinance_lock.py:4`, kullanım `yfinance_client.py:51`, `yfinance_price_lookup_provider.py`, `yfinance_optimization_market_data_provider.py:20,52`
- **Kategori:** Performans
- **Sorun:** Tek bir süreç genelinde `threading.Lock` tüm yfinance çağrılarını seri hale getiriyor (yfinance iş parçacığı güvensizliği için bilinçli).
- **Etki:** Toplu BIST senkronu veya canlı fiyat yenilemesi sürerken kullanıcının tek hisse fiyat sorgusu kilidin arkasında bekler; arayüzde "donma" yerine gecikme olarak görünür.
- **Çözüm:** Kullanıcı kaynaklı sorguları (`price_lookup`) toplu iş kilidinden ayır (iki kilit) veya toplu indirmeyi `yf.download(threads=True)` ile tek çağrıda yap.
- **Düzeltme Eforu:** M
- **Bağımlılık:** yfinance sürüm davranışı; testler.

### [🟡] 14. Dev QML görünümleri
- **Persona:** Kıdemli Yazılım Mimarı.
- **Dosya/Konum:** `OptimizationView.qml` 1128, `SettingsView.qml` 1117, `Stock360View.qml` 1113, `StockDetailModal.qml` 1107, `AiAdvisorView.qml` 1080 satır
- **Kategori:** Mimari
- **Sorun:** Birçok görünüm sekme bileşenlerine bölünmüş (Planlama, Ayarlar fiyat sekmesi) ama bu beşi hâlâ tek dosya.
- **Etki:** Gezinme ve birleştirme çatışmaları; değişen her satırda dosyanın tamamı yeniden yükleniyor ve gözle denetlenemiyor.
- **Çözüm:** Sekme/kart başına bileşen; `PlanningBudgetTab` örüntüsü.
- **Düzeltme Eforu:** L
- **Bağımlılık:** `test_strings_catalog.py` tarama kapsamı.

### [🟢] 15. Parametre ve import sayısı
- **Persona:** Kıdemli Yazılım Mimarı.
- **Dosya/Konum:** 19 fonksiyon >5 parametre (`strategy_backtest_controller.py:134,149`, `dashboard_controller.py:504,532`, `corporate_action_controller.py:456`: 7'şer); import >25: `container_parts/services.py` 48 (kompozisyon kökü, kabul edilebilir), `stock_360_controller.py` 37, `ui_qml/app.py` 36, `analysis_service.py` 35, `portfolio_analytics_service.py` 26.
- **Kategori:** Kod kalitesi
- **Etki:** Düşük; QML slot imzaları parametre sayısını zorluyor.
- **Çözüm:** Servis katmanında parametre nesnesi (`StopTakeParams`); `container_parts/services.py` istisna olarak belgelenir.
- **Düzeltme Eforu:** M

### [🟢] 16. Bakım artıkları
- **Persona:** DevOps.
- **Dosya/Konum:** `scripts/import_bist_ohlcv_to_db.py`, `backfill_missing_friday_prices.py`, `fix_technical_analysis.py`; `auto_commit.py` (kök); `.gitignore` (`CLAUDE.md`, `RULES.md` satırları)
- **Kategori:** Bakım
- **Sorun:** Üç eskimiş tek seferlik betik hâlâ duruyor. `auto_commit.py` belgesiz ve kök dizinde. `CLAUDE.md` ve `RULES.md` hem `.gitignore`'da hem izleniyor (ignore etkisiz, yanıltıcı).
- **Çözüm:** Betikleri sil veya `scripts/legacy/`; `.gitignore` satırlarını kaldır; `auto_commit.py` ya belgele ya sil.
- **Düzeltme Eforu:** S

## Metodoloji Uyumu (`AI-Gelistirme-Metodolojisi.md`)

| Madde | Durum | Not |
|---|---|---|
| §1 `index.md` / `log.md` | Uyumlu | Kategorili katalog, en üste eklenen günlük, nav satırları, kırık/öksüz sayfa betikle denetlendi (2026-10-04). |
| §1 `rules.md` adı, `[[link]]` sözdizimi | Sapma | Proje `RULES.md` ve standart Markdown bağlantıları kullanıyor; işlevsel olarak eşdeğer. |
| §1.2 günlük etiketleri `INGEST/REVIEW/LINT` | Sapma | Projede `güncelleme/ekle/düzelt/temizlik` serbest etiketleri var; tutarsız. |
| §1.3 aynı turda wiki güncellemesi | Uyumlu | Her özellik ve temizlik commit'inde wiki + log birlikte. |
| §2-3 inceleme ve mantık analizi akışı | Kısmen | Bu rapor akışı karşılıyor; rapor onaydan önce uygulanmadı. |
| §5.1 `py_compile` | Aşıldı | Tam `pytest` (1118 test) kullanılıyor, daha güçlü. |
| §5.2 GUI duman testi | Eksik | Bu oturumda uygulama açılmadı; `manual_testing_guide.md` var ama yayın öncesi koşulduğuna dair kayıt yok. |
| §6 commit dili ve Türkçe karakter | Kısmen | Türkçe, ancak son commit mesajları ASCII (örn. `kullanilmayan`, `duzeltildi`); metodoloji ı/ğ/ü/ş/ö/ç ister. |
| §6 "AI referansı yok" | Çelişki | Proje `GOVERNANCE.md` ve oturum yönergesi `Co-Authored-By` ekletiyor; iki kaynak çelişiyor, tek kural seçilmeli. |
| §7 silmeden önce referans tara | Uyumlu | Bu oturumdaki silmelerde `grep` ile tarandı. |

## Bölüm E — Aksiyon Planı

### 24 Saat İçinde
1. **Derlemeden `data/` gömmeyi kaldır** (Bulgu 1). Beklenen: `.exe` kişisel veri taşımaz. Bağımlılık: boş veriyle ilk açılış testi. Risk: ilk açılışta DuckDB boş, senkron süresi uzar.
2. **Dışa aktarma tarih hatasını sessiz bırakma** (Bulgu 4, `dashboard_controller.py:723-730`): `ValueError` yakala, uyarı döndür. Bağımlılık: yok. Risk: kullanıcıya yeni hata mesajı görünür.
3. **AI `"al"/"sat"` eşleşmesini düzelt** (Bulgu 6). Bağımlılık: yerel analiz testi. Risk: eski gevşek tetikleme beklentisi olan testler.

### Bu Hafta
1. Kalan 17 sessiz `except`'i `logger.warning` ile görünür yap (Bulgu 4).
2. `schema_version` tablosu ve açılışta otomatik yedek (Bulgu 5).
3. `tr_fold()` yardımcısı (Bulgu 9).
4. CI: Python matrisi, `pip-audit`, kapsam raporu (Bulgu 11).
5. `time.sleep` testlerini sinyal beklemeye çevir, ölü testi sil (Bulgu 12).

### Bu Ay
1. `ComparisonController` ve `Stock360Controller` ayrıştırması (Bulgu 2).
2. Üç en karmaşık fonksiyonun (CC >40) bölünmesi (Bulgu 3).
3. `market_clock` ile saat dilimi yönetimi (Bulgu 8).
4. BIGINT kimlik göçü, `with_variant(Integer, "sqlite")` (Bulgu 7).
5. API anahtarları için `keyring` (Bulgu 10).

## Bölüm F — Sonraki Adımlar

Hangi bulgudan başlamak istersin? Seçtiğin maddenin detaylı refactor planını, etkilenecek dosyaları ve örnek "before/after" kodunu üretebilirim.
