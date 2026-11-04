# Ürün Test Planı ve E2E Otomasyonu

> Ana sayfa: [index.md](index.md) | Test stratejisi: [testing_strategy.md](testing_strategy.md) | Manuel test rehberi: [manual_testing_guide.md](manual_testing_guide.md) | Sayfa rehberi: [qml_pages_guide.md](qml_pages_guide.md)

Bu belge, uygulamayı ürün olarak gerçek bir kullanıcı gibi sınamak için kullanılan planı ve bu planın otomasyonunu (`tests/e2e/`) tanımlar. Birim ve denetleyici testleri "kod doğru mu" sorusunu yanıtlar; bu plan "kullanıcı ekranda gördüğü düğmelere basarak işini bitirebiliyor mu" sorusunu yanıtlar.

---

## 1. Amaç ve Kapsam

| Konu | Karar |
|---|---|
| Sınanan | Ana pencere (`Main.qml`) ve 11 sayfa, gerçek denetleyiciler, gerçek servisler, gerçek SQLite ve DuckDB; yalnızca dış ağ kapalıdır. |
| Sınama biçimi | Fare tıklaması ve klavye olayı ile (denetleyici slotu çağırmadan). Öğeler ekrandaki metinle bulunur. |
| Kapsam dışı | Canlı piyasa/seans davranışı, gerçek Gemini yanıtı, GPU çizimi ve WebEngine grafik içi etkileşimi (bkz. §8). |
| Veri | Kişisel veri yok. Taze, boş şemadan başlayan SQLite + `data/market_history.duckdb` kopyası (kişisel olmayan piyasa geçmişi). Gerçek dosyalara yazılmaz. |

Başarı ölçütü: her yolculuk ekrandan tamamlanır; her hatalı giriş açık Türkçe mesajla reddedilir; hiçbir adımda çökme, donma ya da beklenmeyen QML uyarısı olmaz.

## 2. Test Ortamı ve Test Veritabanı

| Öğe | Uygulama |
|---|---|
| Kabuk | `tests/e2e/shell.py::build_shell`: `AppContainer()` + `build_ui(autostart=False)` + `Main.qml`, 1440x900 pencere. |
| SQLite | Her koşuda taze `portfolio.db` (boş şema; ilk açılışta ORM oluşturur). |
| DuckDB | `data/market_history.duckdb` kopyası (624 BIST hissesi, geçmiş barlar). Dosya yoksa boş DuckDB. |
| Ağ | `network_blocked()`: Python soketleri ve yfinance giriş noktaları kapatılır. Uygulama internetsizmiş gibi davranır. Not: yfinance `curl_cffi` kullanır; soket yaması onu durdurmaz, bu yüzden kütüphane girişleri ayrıca kesilir. |
| Dış kaynak taklidi | Port düzeyinde: `FakeSymbolVerifier`, `seed_fx`, `seed_asset_prices` (`tests/e2e/seed.py`). Uygulama kodu değişmez. |
| Ayar ve sır | `QSettings` test klasöründe INI; API anahtarı bellek içi sır deposunda (kök `conftest.py`). |
| Çizim | `offscreen` + yazılım arka ucu; `QT_QPA_FONTDIR=C:\Windows\Fonts` verilmeden metin kutu çizilir ve yerleşim ölçüleri yanıltıcı olur (yanlış "taşma" bulgusu üretir). |
| Çıktı | `reports/e2e/<zaman>/screens/*.png`: dönüm noktası ve başarısız her test için ekran görüntüsü. |

Tarihli işlemler için kural: arayüzden yatırılan sermaye "bugün" tarihlidir ve geçmiş tarihli işleme yetmez (olay tabanlı nakit). Bu yüzden alım senaryoları için başlangıç sermayesi geçmiş tarihle tohumlanır (`test_02`, `backdated_capital`).

## 3. Strateji ve Test Piramidindeki Yeri

| Katman | Araç | Bu planın payı |
|---|---|---|
| Domain, servis, denetleyici | `pytest tests/` (~1970 test) | Kural doğruluğu burada; E2E tekrarlamaz. |
| Koruma (guard) | Mimari, metin, kalite testleri | Burada. |
| **E2E insan sürücü** | `pytest -m e2e tests/e2e` (~70 test, ~6,5 dk) | Tıklama, yazma, mesaj görünürlüğü, sayfa gezintisi, çapraz sayfa tutarlılığı, kalıcılık. |
| Manuel keşif | [manual_testing_guide.md](manual_testing_guide.md) | Gerçek ağ, canlı seans, GPU, WebEngine, gerçek Gemini. |

E2E testleri varsayılan koşudan hariçtir (`pytest.ini` `addopts` içinde `not e2e`): tek süreçte tam kabuk kurmak yavaştır ve diğer QML testleriyle sıraya bağlı çökme riski taşır. Komut: `python -m pytest -m e2e tests/e2e -v`.

## 4. Kişi (Persona) ve Yolculuklar

Tek kullanıcı, tek gün; testler dosya adı sırasıyla çalışır ve durum biriktirir (kasıtlı: gerçek kullanıcının günü).

| Dosya | Yolculuk | Plan kimlikleri |
|---|---|---|
| `test_01_first_launch.py` | Yeni kullanıcı uygulamayı açar, 11 sayfayı gezer, menüyü daraltır, temayı değiştirir, üst kutudan hisse arar, grafik başlığını görür. | ENV-002, GLB-001, GLB-002, GLB-005, DASH-006 |
| `test_02_cash_and_trades.py` | Sermaye yatırır; bakiyeden fazla çekmeyi, sıfır/harfli tutarı dener; THYAO alır, nakitten büyük alımı ve eldekinden fazla satışı dener; kısmi satar; Excel raporu alır. | PF-005..PF-008, PF-012, GLB-004 |
| `test_03_fx_and_assets.py` | Çevrimdışı varlık ekleme hatasını görür; NVDA'yı katalogdan ekler; TL ile USD alır, fazlasını dener; NVDA alır; sınıf sekmelerini ve TRY/USD anahtarını dener; açık pozisyonlu varlığı kaldıramaz. | PF-001..PF-004, PF-010, PF-012 |
| `test_04_watchlist_and_model_portfolio.py` | İzleme listesi kurar, boş adı dener, bilinmeyen ve bilinen hisse ekler, tekrarı dener; model portföy oluşturur. | WL-001, WL-002, MP-001 |
| `test_05_planning.py` | Dört planlama sekmesi, bütçe toplamları, hedef kutusu, DCA ve strateji testi. | FP-BUD-001, FP-GOAL-001, FP-DCA-001, FP-STR-001 |
| `test_06_analysis_pages.py` | Hisse 360 arama ve sekmeler, Karşılaştırma Lab, Hisse Tarayıcı, Optimizasyon (tek hisse), Risk Anketi. | S360-001..003, CMP-001, CMP-003, SCR-001, OPT-002, RISK-001 |
| `test_07_ai_and_settings.py` | AI asistan (anahtarsız, enjeksiyon metni), Ayarlar'ın 10 sekmesi, API anahtarı kaydı ve maskeleme, ücret ayarı, çevrimdışı haber kaynağı testi. | AI-001, AI-002, SET-001..SET-008, NEWS-002 |
| `test_08_persistence_and_reset.py` | Uygulama yeniden açılınca veri kalır; sıfırlama onayı iptal edilir; onaylanınca her şey temizlenir. | GLB-003, SET-007 |

## 5. İzlenebilirlik: Manuel Rehber Kimlikleri ve Otomasyon

Durum: **Otomatik** (E2E), **Kısmi** (E2E bir bölümü doğrular), **Manuel** (otomasyonda yok), **Birim** (alt katmanda var).

| Kimlik | Durum | Not |
|---|---|---|
| ENV-001..003 | Otomatik | Test veritabanı ve kabuk kurulumu kendisi. |
| GLB-001..005 | Otomatik | GLB-004 yalnızca tutar, boş ad, bilinmeyen kod, yetersiz bakiye/pozisyon. |
| DASH-001, DASH-006 | Kısmi | Grafik başlığı ve arama; WebEngine içi çizim manuel. |
| DASH-005 | Manuel | Canlı seans gerekir. |
| NEWS-001 | Manuel | Gerçek ağ. NEWS-002 çevrimdışı yön Otomatik. |
| PF-001..PF-008, PF-010, PF-012 | Otomatik | |
| PF-009 | Manuel | Fiyat yenileme ağ ister. |
| PF-011 | Kısmi | Tek hisseyle uyarı doğrulanır; tam optimizasyon sonucu manuel. |
| SD-001..004 | Manuel | Hisse detay penceresi; temettü ve sermaye artırımı akışı E2E dışında. |
| WL-001, WL-002 | Otomatik | WL-003 (tablo sıralama, mini grafik) manuel. |
| MP-001 | Otomatik | MP-002 (işlem ve sermaye), MP-003 manuel. |
| S360-001..003 | Kısmi | KAP sekmesi çevrimdışı geçiş doğrulanır; veri içeriği manuel. |
| CMP-001, CMP-003 | Kısmi | CMP-002 (modlar, para birimi), CMP-004 (AI yorumu) manuel. |
| SCR-001 | Otomatik | SCR-002 (Golden Cross sonuç içeriği) Kısmi. |
| FP-BUD-001, FP-GOAL-001, FP-DCA-001, FP-STR-001 | Kısmi | Hedef ekleme ve katkı akışı manuel. |
| OPT-001, OPT-002, RISK-001 | Kısmi | |
| AI-001, AI-002 | Otomatik (anahtarsız) | Gerçek model yanıtı manuel. AI-003, AI-004 manuel. |
| SET-001, SET-007, SET-008 | Otomatik | SET-002..SET-006 sekmeler açılır (Kısmi). |
| BG-001, BG-002 | Kısmi | Açılışta çevrimdışı davranış doğrulanır; zamanlayıcılı arka plan işleri manuel. |

## 6. Test Tasarım Teknikleri

- **Mutlu yol + hata yolu çiftleri:** her iş akışı için başarılı sonuç ve reddedilen sonuç (yetersiz nakit, fazla satış, geçersiz kod, çevrimdışı doğrulama).
- **Çifte doğrulama (oracle):** arayüz metni ve servis/veritabanı değeri birlikte denetlenir (örn. nakit kartı ve `get_cash_balance()`).
- **Sınır ve biçim:** sıfır, harf, eksi işareti, çok büyük tutar, Türkçe karakter girişi.
- **Çapraz sayfa tutarlılığı:** işlem sonrası Portföyüm, nakit, sınıf sekmesi sayacı, dağılım dilimi.
- **Kalıcılık:** yeni `AppContainer` aynı veritabanını açar.
- **Yıkıcı eylem:** sıfırlama önce iptal, sonra onayla sınanır; test veritabanında güvenle yapılır.
- **Ekran kanıtı:** her yolculuk için görüntü; başarısızlıkta otomatik.

## 7. Çıkış Ölçütleri

1. `pytest -m e2e tests/e2e` yeşil (xfail/atlanan yok).
2. `pytest tests/` yeşil; kalite kapıları ihlal sayısını artırmaz ([ARCHITECTURE_GATES.md](../../ARCHITECTURE_GATES.md)).
3. `test_01` sonundaki QML uyarı denetimi: bilinen uyarı listesi dışında uyarı yok.
4. Açık "Yüksek" ve "Orta" kusur yok ya da bilinçli kabul kaydı var (§9). Şu an açık Orta kusur yok.

## 8. Otomasyonun Sınırları (Manuel Kalanlar)

| Sınır | Neden | Önlem |
|---|---|---|
| Canlı fiyat ve seans | Seans dışında koşulur, ağ kapalıdır. | DASH-005 ve PF-009 manuel. |
| Gerçek Gemini | Anahtar ve ağ gerekir. | AI-001'de yerel analiz motoru yolu sınanır. |
| GPU ve gerçek yazı tipi | Yazılım çizimi; `QT_QPA_FONTDIR` ile ölçüler yaklaşıktır. | Görsel inceleme manuel; kontrast `test_theme_contrast.py`. |
| WebEngine grafik içi | `QTest` Chromium içeriğine olay gönderemez. | Grafik verisi ve başlığı sınanır; çizim manuel. |
| Dosya diyalogları | Yerel diyalog açılmaz. | Excel yolu alana yazılır. |
| Simge (metinsiz) düğmeler | Metin yok. | `ModernButton` ve bütçe `+` düğmeleri `tooltip`/`Accessible.name` taşır; sürücü `click_icon(ad)` ile adından tıklar (koordinat yok). Yeni simge düğmesine ad verilmezse otomasyon bulamaz. |

## 9. Bulgular (Bu Koşuda Çıkan)

Önem: Yüksek (veri/para yanlış), Orta (yanıltıcı/işlev eksik), Düşük (kullanılabilirlik).

| Kod | Önem | Bulgu | Durum |
|---|---|---|---|
| D-01 | Orta | Karşılaştırma Lab, seçili varlıklar için veri yokken "Karşılaştırmak için en az bir varlık seçin" diyordu. | **Düzeltildi:** `ComparisonController.noData` + "karşılaştırılacak veri bulunamadı" metni; birim testi `test_comparison_no_data_flag_...`. E2E'de verisiz durum dizili koşuda kararsız (önbellek/başka testlerin verisi), bu yüzden yalnızca birim testi ve koşullu e2e denetimi var. |
| D-02 | Orta | AI danışman toplam değeri, kapanış fiyatı olmayan BIST pozisyonunu sessizce dışlıyordu (Portföyüm maliyetle değerleyip uyarıyordu): 244.346,80 ₺ ≠ 259.946,80 ₺. | **Düzeltildi:** `UnifiedSeriesBuilder` fiyat yoksa ortalama maliyetle değerler ve uyarı üretir (varlıklardaki kuralla aynı). Birim testleri `TestUnpricedBistPosition`; e2e `test_ai_advisor_total_matches_my_portfolio_total...`. |
| D-03 | Düşük | Modal kutular (`Rectangle` karartma) Escape tuşuna yanıt vermiyordu. | **Düzeltildi:** 17 kutuya `Shortcut { sequence: "Escape" }` eklendi; e2e `test_escape_closes_modal_dialogs` (5 kutu). |
| D-04 | Düşük | Varlık Ekle kutusu pencereden uzundur; "Sembolle Ekle" alanı kaydırmayla görünür. | Bilinen |
| D-05 | Bilgi | Tutar alanları eksi işaretini sessizce atar ("-50" yazınca "50" kalır). Para yatırma yönünden güvenli; kullanıcıya geri bildirim yok. | Kabul edilebilir |
| T-01 | Test altyapısı | Python soket yaması yfinance'i (curl_cffi) durdurmaz; ilk sürümde "ağ kapalı" test canlı Yahoo'ya çıkıyordu. Giriş noktaları kesilerek çözüldü. Aynı tuzak başka ağ-yasaklı testlerde de olabilir. | Çözüldü |
| T-02 | Test altyapısı | Offscreen platformda yazı tipi yok: metin kutu çizilir, satır genişlikleri ~2 kat ölçülür ve sahte "yatay taşma" bulguları çıkar. `QT_QPA_FONTDIR` ile çözüldü. | Çözüldü |

## 10. Bakım Kuralları

- Yeni sayfa, modal veya akış: ilgili `test_0X` dosyasına yolculuk adımı ve §4/§5 satırı eklenir; kimlik [manual_testing_guide.md](manual_testing_guide.md) ile aynı tutulur.
- Etiket değişikliği: testler görünen metni bulur; `Strings.qml` değişince testteki metin güncellenir (kırılan test bunu bildirir).
- Yeni dış ağ bağımlılığı: `tests/e2e/shell.py::_block_native_http_libraries` kapsamı gözden geçirilir.
- Bulgu kapatılınca §9 satırı güncellenir ve ilgili testte regresyon doğrulaması bırakılır.
- E2E testleri `Human` sürücüsünün (`tests/e2e/human.py`; ekran okuma `human_screen.py`, fare/klavye `human_input.py`) yardımcılarını kullanır; yeni yardımcı gerekiyorsa orada genelleştirilir: `click`, `fill`, `click_beside`, `cancel`, `wait_sees`, `screenshot`.

## 11. Çalıştırma

```powershell
.\venv\Scripts\python.exe -m pytest -m e2e tests/e2e -v           # tüm yolculuklar (~6,5 dk)
.\venv\Scripts\python.exe -m pytest -m e2e tests/e2e/test_03_fx_and_assets.py   # tek dosya (önceki dosyaların verisine bağlıysa önce onlar çalışmalı)
```

Çıktı: `reports/e2e/<zaman>/screens/`. `reports/e2e/` sürüm denetimi dışındadır.
