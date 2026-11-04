> Ana sayfa: [index.md](index.md) | Kalite: [code_quality_guardrails.md](code_quality_guardrails.md) | Önceki denetim: [system_audit_report_2026-10-04.md](system_audit_report_2026-10-04.md)

# Sistem Denetimi (2026-11-04) ve Uygulama Sonucu

Şablon: `V2-GenelSablon.md`; süreç: `AI-Gelistirme-Metodolojisi.md` (rapor, onay, sıralı düzeltme, doğrulama, wiki kaydı). Bulgular komut çıktısıyla doğrulandı: tam test paketi, kalite ölçümü (`scripts/measure_code_quality.py`), AST taraması, yerel problar. Önceki denetimden (10-04) sonraki durumu ölçer; orada kapanan konuları tekrarlamaz.

**Sonuç:** 15 bulgunun hepsi işlendi. Test paketi 2049 geçti (denetim başında 1973), 4 xfailed, E2E 75 geçti. Kalite kapısı (0 sınıf, 72 fonksiyon, 4 dosya tavanı) yeşil.

| # | Bulgu | Öncelik | Sonuç |
|---|---|---|---|
| 1 | CI kalite kapısı HEAD'de kırıktı (2 sınıf / 73 fonksiyon, tavan 0 / 72) | 🟠 | Çözüldü: `Human` ikiye bölündü, `UnifiedSeriesBuilder`'dan `_PriceBookLoader` ayrıldı, `seed_asset_prices` 5 parametre |
| 2 | Hisse detayı emir düğmesinde çift tıklama koruması yoktu | 🟠 | Çözüldü (kırmızı test önce): `_trade_pending` koruması + QML `enabled` |
| 3 | İşlem girişi iki yoldan; Dashboard emri arayüz iş parçacığında yazıyordu | 🟡 | Çözüldü: Dashboard emri işçide, aynı yeniden giriş koruması. SQLite `timeout` açıkça verilmedi (varsayılan 5 sn değişmedi) |
| 4 | Para sütunları SQLite'ta `REAL` | 🟡 | Kısmen: `ExactNumeric` bozan yazmayı reddeder; depolama biçimi (REAL) aynı |
| 5 | Dosya uzunluğu eşiği ölçülmüyordu, belge "ihlal yok" diyordu | 🟡 | Çözüldü: `file_effective_lines` 500 (üretim); gerçek durum 4 dosya, CI tavanı 4 |
| 6 | Türkçe `lower()`: üç ayrı çözüm, ana yollarda yok | 🟡 | Çözüldü: `src/domain/text.py` (`tr_lower`, `tr_fold`), 5 çağrı noktası |
| 7 | AI güvenlik süzgeci "asset class" ifadesini engelliyordu | 🟡 | Çözüldü (kırmızı test önce) |
| 8 | Konteyner service-locator (60 `getattr`) | 🟡 | Kısmen: yapıcı enjeksiyonuna geçilmedi; ad doğrulama testi eklendi |
| 9 | Geçişli bağımlılıklar pinsizdi | 🟡 | Çözüldü: `constraints.txt` (CI ve derleme kullanır). Hash yok. `google-genai` pin kayması düzeltildi |
| 10 | Geniş `except`; sessiz ve sızdıran yerler | 🟡 | Çözüldü (hedeflenen yerler); toplam `except Exception` sayısı azaltılmadı |
| 11 | Piyasa tarihine bağlı naive `now()`/`today()` | 🟡 | Çözüldü: 4 modül + koruma testi |
| 12 | Özel RSS: boyut sınırı ve özel adres engeli yok | 🟢 | Çözüldü: akışlı okuma, yerel adres reddi |
| 13 | Başka kullanıcının sabit yolu `.bat` ve belgelerde | 🟢 | Çözüldü |
| 14 | `load_project_env` açılışta 3 kez | 🟢 | Çözüldü |
| 15 | Dış çağrı adaptörlerinde düşük kapsam | 🟢 | Çözüldü: 4 adaptör için hata ailesi testleri |

## Bulgu notları

### 1. CI kalite kapısı
Ölçüm CI komutuyla yerelde çıkış kodu 1 verdi. Neden: e2e sürücüsü `Human` 42 metot; `UnifiedSeriesBuilder` 21 metot; yeni e2e `seed_asset_prices` 6 parametre. Düzeltme gerçek sorumluluk ayrımıdır: ekran okuma (`human_screen.py`) ile fare/klavye (`human_input.py`) ayrıldı; fiyat serisi okuma (`_PriceBookLoader`) değerleme ve akış kurmadan ayrıldı. Taşıma davranışı değiştirmedi (mevcut testler karakterizasyon işi gördü).

### 2 ve 3. Çift emir
Hisse detayında `submitTrade` yuvası emir sürerken ikinci çağrıyı `stock_detail.onceki_islem_suruyor` iletisiyle reddeder; `_on_trade_result` bayrağı temizler. `DashboardController` emri arka plana taşıdı (`_asyncTradeFinished`); `ModelPortfolioController.addTrade` arayüz iş parçacığında kalır ve eşzamanlı çağrı üretemez. **Doğrulanmadı:** QML düğme devre dışı bırakma GUI açılarak denenmedi.

### 4. Para depolaması
Prob (geçici SQLite): `Decimal('12345678901234.1234567891')` `REAL` olarak yazılıp `12345678901234.1230468750` okundu. `ExactNumeric` yalnızca "float üzerinden ölçeğe yuvarlanan değer, doğrudan yuvarlanandan farklı" ise yazmayı reddeder; ölçekten fazla basamak taşıyan ama aynı yuvarlanan değeri veren girdiler geçer. DDL değişmedi, göç gerekmedi. Gerçek çözüm (TEXT veya küçük birim tamsayı) tablo yeniden kurulumu gerektirir ve `roadmap.md`'de kalır.

### 5. Dosya eşiği
`file_violations` `[]` döndürüyordu (eşik eski Widgets arayüzüyle kalkmıştı), bu yüzden `violating_files` hep 0'dı. Üretim dosyası eşiği 500 etkin satır; testler muaf. Aşanlar: `price_data_health_service.py` 713, `financials_charts.py` 660, `scripts/measure_code_quality.py` 633, `model_portfolio_trade_service.py` 508. Bunlar kabul edilen borçtur (CI tavanı 4); yalnızca ölçüt için bölünmedi (`ARCHITECTURE_GATES.md` §1.1).

### 6. Türkçe karşılaştırma
`'iş' in 'İŞ BANKASI'.lower()` `False` (`İ.lower()` = `i` + U+0307). `tr_fold` `İ/I/ı/i` farkını yok sayar, ş/ğ/ü/ö/ç'yi korur. Düzeltilen yerler: mali tablo satır filtresi, izleme listesi ad tekrarı, bütçe kalemi ve sabitlenmiş kalem eşleştirmesi. `news_relevance._FOLD` aksan atan farklı bir işlevdir ve bilinçli bırakıldı.

### 7. Süzgeç
`class\s+\w+` yalnızca sınıf tanımı biçimine daraltıldı (`\bclass\s+\w+\s*[:({]`). Süzgeç güvenlik sınırı değildir; gerçek koruma danışman araçlarının salt okunur olmasıdır.

### 8. Konteyner
Denetleyiciler servisi `getattr(container, "ad", None)` ile ister; çevrimdışı mod (konteynersiz demo) bu tasarıma dayanır. Yapıcı enjeksiyonu ürün davranışını (çevrimdışı açılış) ve 20'den fazla denetleyicinin testini değiştirir; yapılmadı. `test_container_service_names.py` kaynaktaki 44 servis adının tamamının `AppContainer` alanı olduğunu doğrular (şu an eksik ad yok).

### 9. Bağımlılıklar
`constraints.txt` Python 3.10.11 / Windows ortamından üretildi (102 satır). Aynı zamanda gerçek bir kayma bulundu: `requirements.txt` `google-genai==1.0.0` pinliyordu, testlerin ve uygulamanın koştuğu ortam 2.27.0 kullanıyordu. Pin 2.27.0'a çekildi. Gemini sağlayıcıları testlerde SDK'sız taklitle koşar; gerçek Gemini çağrısı bu oturumda denenmedi. Nuitka bu ortamda kurulu değil (`build_preflight.py` `nuitka import` adımı düşer, önceden de böyleydi).

### 10. Hata yönetimi
Sızıntı: danışman aracı hataları `str(exc)` olarak Gemini'ye, işlem hataları arayüze gidiyordu. Şimdi `ValueError` (doğrulama iletisi) aynen, diğer istisnalar sabit iletiyle gider ve günlüğe yazılır. `cash_pool_controller.reload` artık günlüğe yazar. `except Exception` toplamı (253) azaltılmadı: çoğu hatayı döndürüyor veya kullanıcıya bildiriyor.

### 11. Zaman
`chart_candle_sources`, `stock_360_fallback`, `planning_controller`, `isyatirim_provider` `market_today()` kullanır. `tests/test_repo_guards.py` bu dört modülde `datetime.now()`/`date.today()` yasaklar. `src` genelinde kalan kullanımlar yerel zamanın doğru olduğu yerlerdir (dosya adı damgası, göç kaydı vb.); toplu dönüşüm yapılmadı.

### 12-15
RSS akışı `MAX_BODY_BYTES` sınırında kesilir ve bağlantı kapatılır; `localhost`, `.local`, `.internal`, özel ve link-local IP sabitleri reddedilir (DNS çözümlemesi yapılmaz, bu yüzden alan adı ile iç ağa çözülen adresler yine geçer). `.bat` dosyaları `venv`, `.venv`, `PATH` sırasını kullanır. `load_app_settings` `.env` ve sır deposunu bir kez okur. Yeni testler: `test_ai_core_client_errors.py`, `test_yfinance_adapters_failure_modes.py`, `test_scraped_benchmark_provider.py` (eklemeler), `test_news_http_limits.py`.

## İlk GitHub Actions koşusu ve düzeltmeleri (2026-11-04)

Push sonrası CI kırmızı çıktı. **CI bu denetimden önce de kırmızıydı** (2026-10-04 koşusunda aynı 17 test düşüyordu); ilk denetimdeki "CI var" tespiti koşu sonucuna bakılmadan yapılmıştı. Nedenler ve düzeltmeler:

| Sorun | Neden | Düzeltme |
|---|---|---|
| 3 test işi: 17 test düşüyor | Testler gerçek `data/portfolio.db` ve `market_history.duckdb` kopyasına dayanıyor (git dışı, kişisel veri); CI'da veritabanı boş | `real_data` işareti (`pytest.ini`); dosyalar yoksa `tests/conftest.py` testleri atlar (CI'da 18 atlama, yerelde 0). CI'ı gerçek veri olmadan taklit eden bir kopyada 2033 geçti, kapsam %87 |
| `test_parse_trade_moment_rejects_future_time_today` | Test yerel saati, kod piyasa saatini (Europe/Istanbul) kullanıyor; CI UTC'de çalışıyor | Test `market_now()`/`market_today()` kullanır; aynısı `test_dashboard_submit_trade_keeps_default_now` için |
| Dependency audit: 19 açık | `constraints.txt` `pip freeze` ile üretilmişti: `certifi` 2026.7.22, `pyasn1` 0.6.4 eski; `filelock` 4.0.10 `pip-audit`'in kendi bağımlılığıydı (projeye ait değil) ve pinlenmesi CI'da eski sürümde kalmasına yol açtı | Kilit artık yalnızca `requirements.txt` kapanışı (77 paket); `certifi` 2026.10.23, `pyasn1` 0.6.5. `filelock` kilitten çıktı. Yerelde `pip_audit`: proje paketlerinde açık yok; kalanlar `filelock` (CI'da güncellenir) ve `setuptools` (CI adımı yükseltir) |
| Test (3.12): `pip check` | Runner'daki `pipx` kendi bağımlılığından şikayet ediyor | Adım `pipx` satırını yok sayar |

Not: ilk denetim raporunda "`pip-audit` kurulu değil" yazmıştım; kurulu olduğu doğrulanmadan yazılmıştı (yerel `venv`'de 2.10.1 vardı).

## Açık kalanlar
- `ExactNumeric` bozan yazmayı engeller ama değeri `REAL` saklar (Bulgu 4).
- Yapıcı enjeksiyonu yapılmadı (Bulgu 8).
- Bağımlılık hash doğrulaması yok (Bulgu 9).
- Dosya borcu: 4 üretim dosyası 500 satırın üstünde.
- GUI, Nuitka derlemesi ve GitHub Actions koşusu bu denetimde doğrulanmadı.
- `ScrapedBenchmarkProvider` başarısız ay/yıl isteklerini örnek ömrü boyunca boş önbellekte tutar (yeniden deneme yok); davranış testle kayda geçti, değiştirilmedi.
