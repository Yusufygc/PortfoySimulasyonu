# ARCHITECTURE_GATES.md — Kod Kalitesi ve Teknik Standartlar

Bu dosya, projedeki kod kalitesi, refactor sınırları, test kapıları, dizin konvansiyonları ve teknik operasyon kurallarını tanımlar.

---

## 1. Kod Kalitesi ve Refactor Güvenlik Kapıları

- Bir sınıf 300 satırı veya 20 metodu aşarsa (yorum satırları hariç) yeni özellik eklenmeden önce panel, helper veya servis ayrımı yapılır.
- Bir fonksiyon 50 satırı (yorum satırları hariç), 5 parametreyi veya yaklaşık cyclomatic complexity 10 eşiğini aşarsa yeni davranış eklemek yerine önce küçük helper'lara bölünür.
- UI page sınıfları (dosya limiti: 400 satır, yorumlar hariç) yalnızca layout ve wiring sorumluluğu taşır. Tablo doldurma, rapor formatlama, worker orchestration, tema kartı ve reset onayı gibi alt davranışlar panel/component sınıflarına taşınır.
- Application servisleri doğrudan dış API/client çağırmaz. Dış kaynaklar adapter/provider interface üzerinden kullanılır.
- `except Exception` ancak hata loglandığında, kullanıcıya anlamlı sonuç döndürüldüğünde ve ilgili davranış testle kapatıldığında kabul edilir.
- PyQt global `QApplication` ayarları canlı widget varken yeniden uygulanmaz. Tema değişiminde QSS güvenli kabul edilir; font ve global state değişimi kontrollü yapılır.
- Her production bug fix önce kırmızı testi kanıtlar, sonra fix ve tam test koşumu ile kapanır.
- Kullanıcıya gösterilen arayüz metinlerinde Türkçe karakterlerin doğru kullanımı zorunludur. Arayüz dosyalarındaki sabit metinler doğrudan koda gömülmemeli, `src/ui/shared/locale_tr.py` (`L10N` sınıfı) altından çağrılmalıdır.

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
| [src/ui/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/) | PyQt5 sayfalar ve widget'lar |
| [tests/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/tests/) | Mirror yapı: tests/domain/, tests/application/, tests/ui/ |
| [scripts/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/scripts/) | Tek seferlik migration ve bakım script'leri |
| [docs/wiki/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/docs/wiki/) | Kalıcı bilgi tabanı (bkz. [RULES.md §1](RULES.md)) |
| [.github/workflows/](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/.github/workflows/) | CI/CD pipeline tanımları |

### 3.4 LLM/Ajan İçin Özel Kurallar

- Ajan, push yapmadan önce **mutlaka** `git status` çalıştırarak beklenmeyen dosya olmadığını doğrular.
- Ajan, commit sonrası push yapmadan önce ilgili test setini çalıştırır.
- Ajan, `git add .` kullanmaz; her zaman dosya isimlerini açıkça belirtir.
- Ajan, PowerShell ortamında `&&` operatörü kullanmaz; komutları ayrı ayrı çalıştırır.
- Ajan, `.gitignore`'da listelenen dosyaları (CLAUDE.md, RULES.md, GOVERNANCE.md, ARCHITECTURE_GATES.md, .env vb.) commit'lemez.
- Ajan, geçici debug/test dosyalarını (debug_test.py vb.) işi bitince siler.

---

## 🔗 İlgili Diğer Kurallar ve Kılavuzlar
- Oturum başlangıç, Wiki güncelleme ve LLM operasyon kuralları için: [RULES.md](RULES.md)
- Geliştirme, Branch Yönetimi, Commit ve PR süreçleri için: [GOVERNANCE.md](GOVERNANCE.md)
