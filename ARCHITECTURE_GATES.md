# ARCHITECTURE_GATES.md — Kod Kalitesi ve Teknik Standartlar

Bu dosya, projedeki kod kalitesi, refactor sınırları, test kapıları, dizin konvansiyonları ve teknik operasyon kurallarını tanımlar.

---

## 1. Kod Kalitesi ve Refactor Güvenlik Kapıları

- Bir sınıf 300 satırı veya 20 metodu aşarsa (yorum satırları hariç) yeni özellik eklenmeden önce panel, helper veya servis ayrımı yapılır. **Sayım:** `@Property` getter'ları (QML bağlama yüzeyi) metot sayısına ve satıra dahil edilmez; `src/ui_qml/controllers/` sınıfları için sınır 400 satır / 30 metottur (`scripts/measure_code_quality.py`). Kalan eşik dışı denetleyiciler kabul edilen borçtur (denetim Bulgu 2); sırf eşik için ayrıştırılmaz.
- Bir fonksiyon 50 satırı (yorum satırları hariç), 5 parametreyi veya yaklaşık cyclomatic complexity 10 eşiğini aşarsa yeni davranış eklemek yerine önce küçük helper'lara bölünür.
- **Parametre azaltma yöntemi — öncelik sırası:** (1) fonksiyonu daha küçük helper'lara böl; (2) yalnızca helper bölme mümkün değilse veya parametreler gerçek bir domain kavramı / cross-module contract oluşturuyorsa `NamedTuple`/`dataclass` kullanılır.
- **NamedTuple kabul koşulları (üçünden biri sağlanmalı):** domain value object (iş kuralı taşır, 2+ modülde kullanılır); DI dependency grouping (`__init__` için bağımlılık kümesi); cross-module context (2+ farklı dosyada oluşturulan ve tüketilen veri transfer objesi).
- **NamedTuple metric gaming (yasak):** tek bir private metodun param sayısını düşürmek için yaratılan NamedTuple; yalnızca 1 yerde kullanılan dosya-içi NamedTuple; tüm field'ları `object` tipli NamedTuple (tip güvenliği yoksa değeri de yoktur).
- UI page sınıfları (dosya limiti: 400 satır, yorumlar hariç) yalnızca layout ve wiring sorumluluğu taşır. Tablo doldurma, rapor formatlama, worker orchestration, tema kartı ve reset onayı gibi alt davranışlar panel/component sınıflarına taşınır.
- Application servisleri doğrudan dış API/client çağırmaz. Dış kaynaklar adapter/provider interface üzerinden kullanılır.
- `except Exception` ancak hata loglandığında, kullanıcıya anlamlı sonuç döndürüldüğünde ve ilgili davranış testle kapatıldığında kabul edilir.
- PySide6 global `QApplication` ayarları çalışan arayüz varken yeniden uygulanmaz. Tema değişimi `Theme.qml` singleton'ı üzerinden yapılır; font ve global state değişimi kontrollü yapılır.
- Her production bug fix önce kırmızı testi kanıtlar, sonra fix ve tam test koşumu ile kapanır.
- Kullanıcıya gösterilen arayüz metinlerinde Türkçe karakterlerin doğru kullanımı zorunludur. Arayüz dosyalarındaki sabit metinler doğrudan QML'e gömülmemeli, `src/ui_qml/qml/theme/Strings.qml` (`Strings` singleton) altından çağrılmalıdır. `tests/ui_qml/test_strings_catalog.py` bunu denetler.

### 1.1 Refaktör Disiplini

- **Değer şartı:** Refaktör okunabilirlik, hata riski veya test edilebilirlik kazandırmalıdır. Yalnızca ölçüt sayısını düşürmek için yeni modül/sarmalayıcı açmak yasaktır (metric gaming). Ölçüt gerçek sorunu yansıtmıyorsa kod yerine ölçüt düzeltilir ve gerekçesi `docs/wiki/log.md`'ye yazılır.
- **Karakterizasyon önce:** Davranışı koruyan taşıma/bölme öncesi mevcut kodun çıktısı sabit girdilerle (hata dalları dahil) kaydedilir; refaktör sonrası aynı girdilerle karşılaştırılır. Eşdeğerlik kanıtlanmadan commit atılmaz.
- **Ölçülü kapsam:** Birden çok benzer sınıfı ayrıştırma işinde ilk örnekten sonra kazanç/maliyet raporlanır; devam kararı kullanıcıdadır. Kullanıcı görünür fayda üretmeyen işe sınırsız devam edilmez.
- **Davranış değişikliği ayrı commit:** Refaktör sırasında bulunan hata aynı commit'te sessizce düzeltilmez; ayrı commit ve kırmızı testle düzeltilir (§1 bug-fix kuralı).
- **Yüzde/oran formülleri:** Türev yüzde/oran değerleri (ROE, marj, büyüme) için elle hesaplanmış beklenen değerli birim test zorunludur; yalnızca biçim doğrulayan test yetmez.
- **Zaman bağımlılığı:** Testler gerçek saate/tarihe bağlı olamaz. Piyasa zamanı `market_clock` (`market_now`, `market_today`) üzerinden alınır ve testte yamalanır. Koddan bir bağımlılık veya yama hedefi kalktığında o hedefi yamalayan testler `grep` ile taranıp güncellenir.

---

## 2. Test ve Bağımlılık Kapıları

- Her refactor sonrası minimum komut: `C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe -m pytest tests`.
- UI-only değişiklikte `tests/ui`, servis değişikliğinde `tests/domain tests/application`, infrastructure değişikliğinde `tests/infrastructure` ayrıca hedefli çalıştırılır.
- `requirements.txt` doğrudan kullanılan bağımlılıklar için pinli kalır. Yeni paket eklenirse test ortamındaki sürümle pinlenir.
- Gerçek `.env` değerleri asla dokümana, loga veya test çıktısına yazılmaz. Ortam anahtarı değişirse `.env.example` güncellenir.

---

## 3. Genel Operasyon Kuralları

### 3.1 Ortam Yönetimi

| Ortam | Python | Amaç |
|-------|--------|------|
| Fintech (conda) | 3.11.x | Geliştirme ve çalıştırma |
| GitHub Actions | 3.11.x | CI/CD |

- Yerel geliştirme komutu: `C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe -m pytest tests`
- CI komutu: `python -m pytest tests -q`
- İki ortam arasındaki paket uyumsuzlukları `requirements.txt` pinleriyle önlenir.

### 3.2 Veritabanı Güvenliği

- Canlı veritabanına yönelik migration script'leri `scripts/` altında tutulur.
- `ALTER TABLE` veya `DROP` içeren script'ler yedek alınmadan çalıştırılmaz.
- ORM şema değişiklikleri ilk olarak yerel ortamda test edilir, ardından production'a uygulanır.

### 3.3 Dosya ve Dizin Konvansiyonları

| Konum | İçerik |
|-------|--------|
| [src/domain/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/domain/) | Saf domain modelleri, dış bağımlılık yasak |
| [src/application/services/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/application/services/) | İş mantığı servisleri |
| [src/infrastructure/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/infrastructure/) | DB, API adaptörleri |
| [src/ui_qml/](src/ui_qml/) | QML görünümleri ve Python denetleyiciler |
| [tests/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/tests/) | Mirror yapı: tests/domain/, tests/application/, tests/ui/ |
| [scripts/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/scripts/) | Tek seferlik migration ve bakım script'leri |
| [docs/wiki/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/docs/wiki/) | Kalıcı bilgi tabanı (bkz. [RULES.md §1](RULES.md)) |
| [.github/workflows/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/.github/workflows/) | CI/CD pipeline tanımları |

### 3.4 LLM/Ajan İçin Özel Kurallar

- Ajan, push yapmadan önce **mutlaka** `git status` çalıştırarak beklenmeyen dosya olmadığını doğrular.
- Ajan, commit sonrası push yapmadan önce ilgili test setini çalıştırır.
- Ajan, `git add .` kullanmaz; her zaman dosya isimlerini açıkça belirtir.
- Ajan, PowerShell ortamında `&&` operatörü kullanmaz; komutları ayrı ayrı çalıştırır.
- Ajan, `.gitignore`'da listelenen dosyaları (`.env`, `data/`, `logs/`, `backups/` vb.) commit'lemez. Kural dosyaları (AGENTS.md, CLAUDE.md, RULES.md, GOVERNANCE.md, ARCHITECTURE_GATES.md) izlenir; ajan bunları düzenleyebilir ve değişikliği diğer dosyalarla aynı kurallarla (§GOVERNANCE) commit'ler.
- Ajan, geçici debug/test dosyalarını (debug_test.py vb.) işi bitince siler.
- Ajan, denetim/analiz raporuna yazdığı sayı ve iddiaları (kullanım sayısı, "yok/belgesiz", "bekler") koda bakarak doğrular; doğrulanmayan iddia raporda "doğrulanmadı" diye işaretlenir. (Dersler: Bulgu 4/13/16 düzeltmeleri; "43 yer" iddiası gerçekte ~110 kullanımdı.)
- Ajan, kalite ölçütünü hedef alan bir iş önermeden önce işin kullanıcıya ne kazandırdığını ve ölçütün gerçek sorunu yansıtıp yansıtmadığını söyler; belirsizse işe başlamadan sorar.

---

## 🔗 İlgili Diğer Kurallar ve Kılavuzlar
- Oturum başlangıç, Wiki güncelleme ve LLM operasyon kuralları için: [RULES.md](RULES.md)
- Geliştirme, Branch Yönetimi, Commit ve PR süreçleri için: [GOVERNANCE.md](GOVERNANCE.md)
