# RULES.md — Proje Kuralları

Bu dosya, projedeki wiki bakımı, commit disiplini ve LLM iş akışı için bağlayıcı kuralları tanımlar.  
Gelecekteki Claude oturumları bu kuralları `CLAUDE.md` üzerinden bu dosyaya yönlendirilerek bulur.

---

## 0. Oturum Başlangıç Kuralları

Her ajan/LLM oturumu, kod veya plan üretmeden önce proje kökündeki `AGENTS.md` ve `CLAUDE.md` dosyalarını okur. `AGENTS.md` yerel ajan giriş noktasıdır; `CLAUDE.md` proje bağlamını ve bu `RULES.md` dosyasına yönlendirmeyi taşır.

Dosyalar arasında çelişki olursa en dar kapsamlı ve kullanıcıya en yakın talimat uygulanır; güvenlik, commit ve wiki kuralları için bu dosyadaki bağlayıcı hükümler korunur.

---

## 1. Wiki Güncelleme Kuralları

### 1.1 Temel İlke

`docs/wiki/` bir **kalıcı, biriken bilgi tabanıdır** — sohbet geçmişi değil.  
Ham kaynak (kod, commit, konuşma) değiştiğinde wiki güncellenmeli; wiki hiçbir zaman eskimemelidir.

Her oturumun başında `docs/wiki/index.md` okunur. Sorular bu katalogdan ilgili sayfalar bulunarak yanıtlanır.

### 1.2 Hangi Durumda Wiki Güncellenir?

| Durum | Hangi Dosya(lar) |
|-------|-----------------|
| Yeni özellik eklendi | `architecture.md` (ilgili bölüm) + `log.md` |
| Mimari karar verildi | `architecture.md` + `log.md` |
| Büyük refaktör yapıldı | `architecture.md` + `log.md` |
| Yeni wiki sayfası oluşturuldu | `index.md` (kataloga eklenir) + `log.md` |
| Hata çözümü kalıcı bir ders içeriyorsa | Yeni sayfa veya `architecture.md` notu + `log.md` |
| Planlanan özellik netleşti | `architecture.md` (Roadmap bölümü) + `log.md` |
| Oturum sona eriyor, önemli bilgi konuşuldu | Tüm ilgili sayfalar + `log.md` |

Küçük kod düzeltmeleri, stil değişiklikleri, yazım hatası düzeltmeleri wiki güncellemesi gerektirmez.

### 1.3 `index.md` Kuralları

`index.md` **içerik odaklı katalogdur** — tüm wiki sayfalarını listeler.

- Her sayfa bir satır: `- [Sayfa Adı](sayfa.md) — tek cümle özet`
- Kategorilere göre gruplandırılır (Mimari, Operasyonlar, Kaynaklar vb.)
- Her yeni sayfa oluşturulduğunda veya silindiğinde güncellenir
- LLM, sorguya cevap vermeden önce bu dosyayı okuyarak hangi sayfaların ilgili olduğunu belirler

### 1.4 `log.md` Kuralları

`log.md` **kronolojik, yalnızca ekleme yapılan** kayıttır.

**Format (zorunlu):**
```
## [YYYY-AA-GG] işlem | Konu Başlığı

- Yapılan değişiklik veya kararın kısa açıklaması
- Etkilenen dosyalar (varsa)
- Bağlantılı sayfa (varsa): [architecture.md](architecture.md)
```

**Geçerli işlem türleri:**
- `ingest` — yeni kaynak/bilgi wiki'ye işlendi
- `güncelleme` — mevcut sayfa güncellendi
- `yeni-sayfa` — yeni wiki sayfası oluşturuldu
- `lint` — wiki sağlık kontrolü yapıldı
- `sorgu` — önemli bir soru soruldu ve yanıt wiki'ye kaydedildi
- `commit` — anlamlı bir commit atıldı

Eski girişler **asla silinmez veya düzenlenmez**. Yeni girişler en üste eklenir.

Grep ile log analizi: `grep "^## \[" docs/wiki/log.md | head -10`

### 1.5 `architecture.md` Kuralları

- Katman açıklamaları, veritabanı şeması ve veri akışları burada tutulur
- Modül eklenince/silinince ilgili tablo güncellenir
- Mimari kararların "neden" kısmı mutlaka yazılır
- Diğer wiki sayfalarına anchor link ile referans verilir

### 1.6 Yeni Wiki Sayfası Oluşturma

1. `docs/wiki/<konu>.md` dosyası oluşturulur
2. Dosyanın üstüne navigation satırı eklenir: `> Ana sayfa: [index.md](index.md) | ...`
3. `index.md` kataloğuna eklenir
4. `log.md`'ye `yeni-sayfa` girişi eklenir
5. İlgili mevcut sayfalara cross-reference eklenir

### 1.7 Lint (Sağlık Kontrolü)

Periyodik olarak aşağıdaki soruları sor ve düzelt:

- Gelen linki olmayan (orphan) sayfa var mı?
- Eski bilgi içeren bölüm var mı (kodla çelişiyor mu)?
- `index.md`'de olmayan ama `docs/wiki/`'de var olan sayfa var mı?
- Önemli bir kavram bahsediliyor ama kendi sayfası yok mu?
- Cross-reference eksik mi?

---

## 2. Commit Mesajı Kuralları

### 2.1 Dil ve Ton

Tüm commit mesajları **Türkçe** yazılır.  
Teknik terimler (API, ORM, QSS, DI vb.) Türkçe cümle içinde orijinal haliyle kullanılabilir.

### 2.2 Format

```
<fiil>: <ne yapıldığı, tek satır, 72 karakter sınırı>

<gövde — neyin neden yapıldığını açıklar, boş satırla ayrılır>
- Madde 1
- Madde 2

Etkilenen modüller: src/application/services/..., docs/wiki/...
```

**Başlık fiilleri (küçük harf):**

| Fiil | Ne zaman |
|------|----------|
| `ekle:` | Yeni özellik, dosya, sayfa |
| `güncelle:` | Mevcut bir şeyi geliştir |
| `düzelt:` | Hata giderme |
| `refaktör:` | Davranış değişmeden yapı değişimi |
| `sil:` | Dosya veya kod bloğu kaldırıldı |
| `belge:` | Yalnızca dokümantasyon değişikliği |
| `test:` | Test ekleme veya güncelleme |
| `yapılandır:` | Config, .env, build dosyaları |

### 2.3 İyi Commit Mesajı Kriterleri

- Başlık "ne yapıldı"yı söyler; gövde "neden yapıldı"yı açıklar
- Commit başlığı tek başına okunduğunda anlaşılır olmalı
- Tek bir commit tek bir mantıksal değişikliği kapsamalı
- Wiki güncellemesi içeren commit'lerde `docs/wiki/` etkilenen modüller listesinde belirtilir

### 2.4 Örnekler

```
güncelle: Optimizasyon motoruna Ledoit-Wolf kovaryans ve ağırlık limiti ekle

SciPy minimize() çağrısı büyük portföylerde kararsız sonuç veriyordu.
Ledoit-Wolf shrinkage ile kovaryans matrisi stabilize edildi.
Her hisse için min/max ağırlık kısıtı eklendi.

Etkilenen modüller: src/application/services/planning/optimization_service.py
```

```
belge: Wiki sistemi başlatıldı ve LLM Wiki pattern'ine uyarlandı

docs/wiki/index.md içerik kataloğuna dönüştürüldü.
docs/wiki/log.md append-only format'a geçirildi (## [YYYY-AA-GG] prefix).
RULES.md oluşturuldu: wiki bakım ve commit kuralları belgelendi.

Etkilenen modüller: docs/wiki/index.md, docs/wiki/log.md, RULES.md, CLAUDE.md
```

---

## 3. LLM Wiki Operasyon Protokolü

Bu proje **LLM Wiki** pattern'ini uygular: ham kaynak değişmez, LLM wiki'yi yazar ve bakımını yapar, insan yönlendirir ve soru sorar.

### 3.1 Ingest (Yeni Bilgi Ekleme)

Yeni bir kaynak (kod kararı, harici makale, toplantı notu vb.) bilgi tabanına eklenecekse:

1. Kaynak okunur / tartışılır
2. Önemli kararlar ve öğrenilenler çıkarılır
3. İlgili wiki sayfaları güncellenir (10-15 sayfaya dokunabilir)
4. Gerekirse yeni sayfa açılır
5. `index.md` güncellenir
6. `log.md`'ye `ingest` girişi eklenir

### 3.2 Sorgu (Query)

Bir soru sorulduğunda:

1. `index.md` okunur → ilgili sayfalar belirlenir
2. İlgili sayfalar okunur
3. Yanıt bu bilgilerden sentezlenir
4. Eğer yanıt anlamlı ve kalıcıysa `log.md`'ye `sorgu` girişi eklenir; gerekirse yeni sayfa açılır

### 3.3 Lint (Sağlık Kontrolü)

Periyodik olarak (yaklaşık 10 ingest'te bir) wiki sağlık kontrolü yapılır.  
Sonuçlar `log.md`'ye `lint` girişi olarak kaydedilir.

---

## 4. Kod Kalitesi, Refactor ve Test Kapıları

Bu bölüm, aynı tür üretim hatalarının ve kontrolsüz büyüyen sınıf/metod yapılarının tekrarlanmaması için bağlayıcı kapıları tanımlar.

### 4.1 Kod Kalitesi ve Refactor Güvenlik Kapıları

- Bir sınıf 300 satırı veya 20 metodu aşarsa (yorum satırları hariç) yeni özellik eklenmeden önce panel, helper veya servis ayrımı yapılır.
- Bir fonksiyon 50 satırı (yorum satırları hariç), 5 parametreyi veya yaklaşık cyclomatic complexity 10 eşiğini aşarsa yeni davranış eklemek yerine önce küçük helper'lara bölünür.
- UI page sınıfları (dosya limiti: 400 satır, yorumlar hariç) yalnızca layout ve wiring sorumluluğu taşır. Tablo doldurma, rapor formatlama, worker orchestration, tema kartı ve reset onayı gibi alt davranışlar panel/component sınıflarına taşınır.
- Application servisleri doğrudan dış API/client çağırmaz. Dış kaynaklar adapter/provider interface üzerinden kullanılır.
- `except Exception` ancak hata loglandığında, kullanıcıya anlamlı sonuç döndürüldüğünde ve ilgili davranış testle kapatıldığında kabul edilir.
- PyQt global `QApplication` ayarları canlı widget varken yeniden uygulanmaz. Tema değişiminde QSS güvenli kabul edilir; font ve global state değişimi kontrollü yapılır.
- Her production bug fix önce kırmızı testi kanıtlar, sonra fix ve tam test koşumu ile kapanır.

### 4.2 Test ve Bağımlılık Kapıları

- Her refactor sonrası minimum komut: `C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe -m pytest tests`.
- UI-only değişiklikte `tests/ui`, servis değişikliğinde `tests/domain tests/application`, infrastructure değişikliğinde `tests/infrastructure` ayrıca hedefli çalıştırılır.
- `requirements.txt` doğrudan kullanılan bağımlılıklar için pinli kalır. Yeni paket eklenirse test ortamındaki sürümle pinlenir.
- Gerçek `.env` değerleri asla dokümana, loga veya test çıktısına yazılmaz. Ortam anahtarı değişirse `.env.example` güncellenir.

---

---


## 5. GitHub, Git CLI ve Genel Operasyon Kuralları

Bu bölüm, projedeki Git/GitHub kullanımı, branch yönetimi, CI/CD akışı ve günlük geliştirme operasyonlarını standartlaştırır.

### 5.1 Branch Stratejisi

| Branch | Amaç | Koruma |
|--------|-------|--------|
| `main` | Kararlı sürüm. Doğrudan commit **yasak**. | PR + CI yeşil zorunlu |
| `Refactor` | Aktif geliştirme branch'i. Günlük çalışma burada yapılır. | CI yeşil önerilir |
| Özellik branch'leri | Büyük özellik/deney için açılır, bitince silinir. | — |

**Kurallar:**
- `main`'e doğrudan `git push` yapılmaz. Her zaman PR üzerinden merge edilir.
- Feature branch isimlendirme: `kebab-case` veya `PascalCase` (örn. `AnalizSayfasi`, `UIupdate`).
- Tamamlanmış ve merge edilmiş remote branch'ler silinir: `git push origin --delete <branch>`.
- Yerel branch temizliği: `git fetch --prune` ile ölü remote referansları düzenli temizlenir.

### 5.2 Git CLI Standartları

#### Temel İş Akışı

```bash
# 1. Güncel branch'i çek
git pull --rebase origin Refactor

# 2. Değişiklikleri stage et (ilgili dosyaları seç, toplu değil)
git add <ilgili_dosyalar>

# 3. Commit at (RULES.md §2 formatında)
git commit -m "fiil: Başlık (72 karakter)

Gövde açıklaması.

Etkilenen modüller: src/..."

# 4. Push et
git push origin Refactor
```

#### Kesinlikle Yapılmaması Gerekenler

| Yasak | Neden |
|-------|-------|
| `git add .` veya `git add -A` | İlgisiz/geçici dosyalar (debug_test.py, __pycache__ vb.) commit'e girer |
| `git push --force` (main'e) | Takım geçmişi bozulur, CI güvensizleşir |
| `git commit --amend` (push'lanmış commit) | Remote geçmişi bozar |
| `git merge` (main → feature, gereksiz yere) | Geçmiş karmaşıklaşır; `rebase` tercih edilir |
| Büyük binary dosyaları commit'lemek | Repo şişer; `.gitignore`'da engellenmelidir |

#### Faydalı Komutlar

```bash
# Branch arasındaki farkı gör
git log --oneline main..Refactor

# Son commit'i incele
git show HEAD

# Staged değişiklikleri gör
git diff --staged

# Belirli dosyanın geçmişi
git log --follow -p <dosya>

# Ölü remote branch referanslarını temizle
git fetch --prune

# Worktree listele
git worktree list
```

### 5.3 Commit Hijyeni

- Her commit **tek bir mantıksal değişikliği** kapsar. Birden fazla bağımsız düzeltme aynı commit'e konmaz.
- Commit'lemeden **önce** ilgili testler çalıştırılır (bkz. §4.2).
- Geçici dosyalar (`debug_test.py`, `temp_*.py`, `*.pyc`) commit'e dahil edilmez.
- `.env`, veritabanı şifreleri, API anahtarları **asla** commit'lenmez (`.gitignore`'da engellidir).
- Commit mesajları RULES.md §2 formatına uyar; İngilizce commit mesajı **kabul edilmez**.

### 5.4 Pull Request (PR) Kuralları

#### PR Açma

```bash
# GitHub CLI ile PR aç
gh pr create --base main --head Refactor --title "PR başlığı" --body "Açıklama"
```

#### PR Şablonu

PR açıklama gövdesi aşağıdaki yapıyı takip eder:

```markdown
## Ne Yapıldı
- Madde 1
- Madde 2

## Neden Yapıldı
- Kısa gerekçe

## Test
- [ ] Tüm testler geçiyor (`python -m pytest tests`)
- [ ] CI yeşil
- [ ] Manuel doğrulama yapıldı (gerekiyorsa)

## Etkilenen Modüller
- src/...
- tests/...
```

#### PR Merge Kuralları

- CI (GitHub Actions) **yeşil** olmadan merge yapılmaz.
- Squash merge tercih edilir: `gh pr merge --squash`.
- Merge sonrası feature branch silinir.

### 5.5 GitHub Actions / CI Kuralları

CI workflow dosyası: [`.github/workflows/tests.yml`](.github/workflows/tests.yml)

#### CI Pipeline Akışı

```
Push/PR → Checkout → Python 3.11 Kurulum → pip install -r requirements.txt → pip check → pytest --collect-only → pytest tests
```

#### CI Kırmızı Olduğunda

1. **Kök neden belirlenir:** Hata çıktısı okunur (collection error ≠ test failure).
2. **Yerel ortamda tekrarlanır:** `python -m pytest --collect-only -q` + `python -m pytest tests`.
3. **Düzeltme yapılır ve push'lanır.**
4. CI tekrar yeşil olana kadar yeni özellik commit'lenmez (acil durum hariç).

#### Bağımlılık Güvenliği

- `requirements.txt`'e eklenen her paket **pinli sürümle** (örn. `plotly==6.7.0`) kaydedilir.
- Yeni bir `import` eklendiğinde, ilgili paketin `requirements.txt`'te olup olmadığı kontrol edilir.
- Top-level import'lar CI'da çalışmayan bir paket kullanıyorsa, ya `requirements.txt`'e eklenir ya da import lazy yapılır.
- `pip check` adımı bağımlılık çakışmalarını yakalar; bu adım kırmızıysa bağımlılık sürümleri uyumlanır.

### 5.6 .gitignore Yönetimi

Mevcut `.gitignore` dosyasındaki proje-özel kurallar:

| Pattern | Neden |
|---------|-------|
| `CLAUDE.md`, `RULES.md` | Ajan konfigürasyonu, her branch'te farklı olabilir |
| `.env` | Veritabanı şifreleri ve API anahtarları |
| `backups/` | Yerel yedekler |
| `*.sql` (istisna: scripts/) | Yerel veritabanı dump'ları |
| `*.xlsx` | Oluşturulan Excel raporları |
| `logs/` | Uygulama log dosyaları |
| `__pycache__/`, `*.py[codz]` | Python bytecode |
| `.icon_cache/` | Tema ikonları önbelleği |

**Kurallar:**
- Yeni bir dosya türü veya dizin kalıcı olarak takipten çıkarılacaksa `.gitignore`'a eklenir ve commit mesajında belirtilir.
- `.gitignore`'dan çıkartılan dosyalar (ör. `!scripts/*.sql`) açıkça yorum satırı ile belgelenir.
- Geçici dosyalar (test script'leri, debug çıktıları) `.gitignore`'a değil, silme alışkanlığına dayanır.

### 5.7 Release ve Tag Kuralları

```bash
# Sürüm etiketi oluştur (semantic versioning)
git tag -a v1.2.0 -m "v1.2.0: Kurumsal aksiyon ve analiz iyileştirmeleri"

# Tag'i push et
git push origin v1.2.0
```

- Tag formatı: `v<major>.<minor>.<patch>` (Semantic Versioning).
- Tag mesajı Türkçe, değişikliklerin kısa özetini içerir.
- Tag yalnızca `main` branch üzerinde atılır.

### 5.8 Genel Operasyon Kuralları

#### Ortam Yönetimi

| Ortam | Python | Amaç |
|-------|--------|------|
| Fintech (conda) | 3.11.x | Geliştirme ve çalıştırma |
| GitHub Actions | 3.11.x | CI/CD |

- Yerel geliştirme komutu: `C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe -m pytest tests`
- CI komutu: `python -m pytest tests -q`
- İki ortam arasındaki paket uyumsuzlukları `requirements.txt` pinleriyle önlenir.

#### Veritabanı Güvenliği

- Canlı veritabanına yönelik migration script'leri `scripts/` altında tutulur.
- `ALTER TABLE` veya `DROP` içeren script'ler yedek alınmadan çalıştırılmaz.
- ORM şema değişiklikleri ilk olarak yerel ortamda test edilir, ardından production'a uygulanır.

#### Dosya ve Dizin Konvansiyonları

| Konum | İçerik |
|-------|--------|
| `src/domain/` | Saf domain modelleri, dış bağımlılık yasak |
| `src/application/services/` | İş mantığı servisleri |
| `src/infrastructure/` | DB, API adaptörleri |
| `src/ui/` | PyQt5 sayfalar ve widget'lar |
| `tests/` | Mirror yapı: `tests/domain/`, `tests/application/`, `tests/ui/` |
| `scripts/` | Tek seferlik migration ve bakım script'leri |
| `docs/wiki/` | Kalıcı bilgi tabanı (bkz. §1) |
| `.github/workflows/` | CI/CD pipeline tanımları |

#### LLM/Ajan İçin Özel Kurallar

- Ajan, push yapmadan önce **mutlaka** `git status` çalıştırarak beklenmeyen dosya olmadığını doğrular.
- Ajan, commit sonrası push yapmadan önce ilgili test setini çalıştırır.
- Ajan, `git add .` kullanmaz; her zaman dosya isimlerini açıkça belirtir.
- Ajan, PowerShell ortamında `&&` operatörü kullanmaz; komutları ayrı ayrı çalıştırır.
- Ajan, `.gitignore`'da listelenen dosyaları (CLAUDE.md, RULES.md, .env vb.) commit'lemez.
- Ajan, geçici debug/test dosyalarını (debug_test.py vb.) işi bitince siler.

---


## 6. Kapsam Dışı

Bu kurallar aşağıdakiler için geçerli **değildir**:

- Küçük kod düzeltmeleri (yazım hatası, tek satır fix)
- Test çalıştırma çıktıları
- Geçici araştırma sohbetleri (wiki'ye işlenmedikçe)

