# RULES.md — Proje Kuralları

Bu dosya, projedeki wiki bakımı, commit disiplini ve LLM iş akışı için bağlayıcı kuralları tanımlar.  
Gelecekteki Claude oturumları bu kuralları `CLAUDE.md` üzerinden bu dosyaya yönlendirilerek bulur.

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

- Bir sınıf 300 satırı veya 20 metodu aşarsa yeni özellik eklenmeden önce panel, helper veya servis ayrımı yapılır.
- Bir fonksiyon 50 satırı, 5 parametreyi veya yaklaşık cyclomatic complexity 10 eşiğini aşarsa yeni davranış eklemek yerine önce küçük helper'lara bölünür.
- UI page sınıfları yalnızca layout ve wiring sorumluluğu taşır. Tablo doldurma, rapor formatlama, worker orchestration, tema kartı ve reset onayı gibi alt davranışlar panel/component sınıflarına taşınır.
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

## 5. Kapsam Dışı

Bu kurallar aşağıdakiler için geçerli **değildir**:

- Küçük kod düzeltmeleri (yazım hatası, tek satır fix)
- Test çalıştırma çıktıları
- Geçici araştırma sohbetleri (wiki'ye işlenmedikçe)
