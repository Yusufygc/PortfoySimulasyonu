# GOVERNANCE.md — Git, Commit ve Süreç Yönetimi

Bu dosya, projedeki geliştirme süreçlerini, branch stratejisini, commit disiplinini, PR kurallarını ve genel sürüm yönetimi operasyonlarını tanımlar.

---

## 1. Commit Mesajı Kuralları

### 1.1 Dil ve Ton

Tüm commit mesajları **Türkçe** yazılır.  
Teknik terimler (API, ORM, QSS, DI vb.) Türkçe cümle içinde orijinal haliyle kullanılabilir.

### 1.2 Format

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

### 1.3 İyi Commit Mesajı Kriterleri

- Başlık "ne yapıldı"yı söyler; gövde "neden yapıldı"yı açıklar
- Commit başlığı tek başına okunduğunda anlaşılır olmalı
- Tek bir commit tek bir mantıksal değişikliği kapsamalı
- Wiki güncellemesi içeren commit'lerde `docs/wiki/` etkilenen modüller listesinde belirtilir

### 1.4 Örnekler

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

## 2. GitHub, Git CLI ve Genel Operasyon Kuralları

Bu bölüm, projedeki Git/GitHub kullanımı, branch yönetimi, CI/CD akışı ve günlük geliştirme operasyonlarını standartlaştırır.

### 2.1 Branch Stratejisi

| Branch | Amaç | Koruma |
|--------|-------|--------|
| `main` | Kararlı sürüm. Doğrudan commit **yasak**. | PR + CI yeşil zorunlu |
| `development` | Aktif geliştirme branch'i. Günlük çalışma burada yapılır. | CI yeşil önerilir |
| Özellik branch'leri | Büyük özellik/deney için açılır, bitince silinir. | — |

**Kurallar:**
- `main`'e doğrudan `git push` yapılmaz. Her zaman PR üzerinden merge edilir.
- Feature branch isimlendirme: `kebab-case` veya `PascalCase` (örn. `AnalizSayfasi`, `UIupdate`).
- Tamamlanmış ve merge edilmiş remote branch'ler silinir: `git push origin --delete <branch>`.
- Yerel branch temizliği: `git fetch --prune` ile ölü remote referansları düzenli temizlenir.

### 2.2 Git CLI Standartları

#### Temel İş Akışı

```bash
# 1. Güncel branch'i çek
git pull --rebase origin development

# 2. Değişiklikleri stage et (ilgili dosyaları seç, toplu değil)
git add <ilgili_dosyalar>

# 3. Commit at (GOVERNANCE.md §1 formatında)
git commit -m "fiil: Başlık (72 karakter)

Gövde açıklaması.

Etkilenen modüller: src/..."

# 4. Push et
git push origin development
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
git log --oneline main..development

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

### 2.3 Commit Hijyeni

- Her commit **tek bir mantıksal değişikliği** kapsar. Birden fazla bağımsız düzeltme aynı commit'e konmaz.
- Commit'lemeden **önce** ilgili testler çalıştırılır (bkz. [ARCHITECTURE_GATES.md §2](ARCHITECTURE_GATES.md)).
- Geçici dosyalar (`debug_test.py`, `temp_*.py`, `*.pyc`) commit'e dahil edilmez.
- Ajan/LLM tarafından geçici/debug/test amaçlı oluşturulan dosyaların işi bittiğinde kullanıcıya silinip silinmeyeceği sorulmalı, onay alındıktan sonra bu geçici dosyalar repodan temizlenmelidir.
- `.env`, veritabanı şifreleri, API anahtarları **asla** commit'lenmez (`.gitignore`'da engellidir).
- Commit mesajları [GOVERNANCE.md §1](#1-commit-mesaji-kurallari) formatına uyar; İngilizce commit mesajı **kabul edilmez**.

### 2.4 Pull Request (PR) Kuralları

#### PR Açma

```bash
# GitHub CLI ile PR aç
gh pr create --base main --head development --title "PR başlığı" --body "Açıklama"
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

### 2.5 GitHub Actions / CI Kuralları

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

### 2.6 .gitignore Yönetimi

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

### 2.7 Release ve Tag Kuralları

```bash
# Sürüm etiketi oluştur (semantic versioning)
git tag -a v1.2.0 -m "v1.2.0: Kurumsal aksiyon ve analiz iyileştirmeleri"

# Tag'i push et
git push origin v1.2.0
```

- Tag formatı: `v<major>.<minor>.<patch>` (Semantic Versioning).
- Tag mesajı Türkçe, değişikliklerin kısa özetini içerir.
- Tag yalnızca `main` branch üzerinde atılır.

---

## 🔗 İlgili Diğer Kurallar ve Kılavuzlar
- Oturum başlangıç, Wiki güncelleme ve LLM operasyon kuralları için: [RULES.md](RULES.md)
- Kod kalitesi, refactor limitleri, dizin konvansiyonları ve test kapıları için: [ARCHITECTURE_GATES.md](ARCHITECTURE_GATES.md)
