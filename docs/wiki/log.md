# Wiki Değişiklik Günlüğü

> Ana katalog: [index.md](index.md) | Mimari: [architecture.md](architecture.md)  
> Bu dosya **yalnızca ekleme** yapılır. Eski girişler hiçbir zaman silinmez veya düzenlenmez.  
> Grep ile son girişler: `grep "^## \[" docs/wiki/log.md | head -10`

---

## [2026-05-21] güncelleme | Kalite kapıları ve refactor planı belgelendi

- `RULES.md` kod kalitesi, refactor güvenliği, test ve bağımlılık kapılarıyla genişletildi
- `SettingsPage` panel ayrımı ve `HistorySimulationService` helper ayrımı mimari not olarak kaydedildi
- Etkilenen dosyalar: `RULES.md`, `CLAUDE.md`, `docs/wiki/architecture.md`, `docs/wiki/log.md`
- Bağlantılı sayfa: [architecture.md → Kalite Kapıları ve Modülerlik](architecture.md#kalite-kapilari-ve-modulerlik)

---

## [2026-05-09] yeni-sayfa | Wiki sistemi başlatıldı

- `docs/wiki/index.md` içerik kataloğuna dönüştürüldü (LLM Wiki pattern)
- `docs/wiki/log.md` append-only formatına geçirildi (`## [YYYY-AA-GG] işlem | Başlık`)
- `docs/wiki/architecture.md` oluşturuldu: katmanlar, modeller, DB şeması, veri akışı
- `RULES.md` oluşturuldu: wiki güncelleme, commit mesajı ve LLM operasyon kuralları
- `CLAUDE.md` yeniden düzenlendi: wiki kuralları `RULES.md`'ye taşındı, teknik içerik korundu
- Etkilenen dosyalar: `docs/wiki/index.md`, `docs/wiki/log.md`, `docs/wiki/architecture.md`, `RULES.md`, `CLAUDE.md`

---

## [2026-05-09] ingest | Proje ilk incelemesi ve CLAUDE.md oluşturuldu

- Proje yapısı incelendi: Clean Architecture, PyQt5, MySQL, YFinance, SciPy
- `CLAUDE.md` oluşturuldu: tech stack, mimari, kurulum, komutlar belgelendi
- Etkilenen dosyalar: `CLAUDE.md`

---

## Geçmiş Commit Özeti (git log'dan)

Aşağıdaki girişler geçmiş commit'lerden özet olarak alınmıştır.  
Detay için: `git log --oneline`

---

## [2026-05-09] commit | Optimizasyon motorunu Ledoit-Wolf ve ağırlık limitiyle sağlamlaştır

- `b0cb6ff` — SciPy optimize çağrısı büyük portföylerde kararsız sonuç veriyordu
- Ledoit-Wolf kovaryans shrinkage eklendi (scikit-learn)
- Per-hisse min/max ağırlık kısıtı eklendi
- Bkz. [architecture.md → Optimizasyon Motoru](architecture.md#optimizasyon-motoru)

---

## [2026-05-09] commit | Altın ve mevduat benchmark'larını gerçek piyasa verisine bağla

- `e649277` — YFinance + TCMB entegrasyonu ile benchmark verileri gerçek kaynaklara bağlandı

---

## [2026-05-09] commit | Açık tema ve BIST tatil görünümünü ayarlara ekle

- `cbe83fd` — Light mode ve BIST tatil takvimi ayarlar sayfasında kullanılabilir oldu

---

## [2026-05-09] commit | Dashboard getiri oranlarını kalıcılaştır

- `b94863e` — Uygulama kapanıp açıldığında getiri oranları korunuyor

---

## [2026-05-09] commit | Excel geçmiş raporunu günlük özetlerle iyileştir

- `8d1f179` — Excel çıktısı günlük özet sütunlarıyla zenginleştirildi

---

## [2026-05-09] commit | Bedelli ve bedelsiz sermaye artırımı akışını ekle

- `9ba100c` — CorporateAction domain modeli ve akış tamamlandı
- Bkz. [architecture.md → Temel Tablolar](architecture.md#temel-tablolar)

---

## [2026-05-09] commit | Risk Profili analiz sistemi profesyonel seviyeye yükseltildi

- `0da967a` — Detaylı skor hesaplama ve görsel raporlama eklendi

---

## [2026-05-09] commit | Analiz modülü yenilendi, Price Data Health servisi eklendi

- `0f3c62e` — Fiyat veri sağlığı kontrolü ayrı servis olarak çıkarıldı
- `fc665bb` — Ayarlar sayfası modernize edildi, veri sağlığı paneli iyileştirildi

---

## [2026-05-09] commit | QSS stil sistemi modülerleştirildi

- `2212a3c` — Stiller `src/ui/styles/` altında kategorilere ayrıldı
- `4e34e31` — Emoji ikonlar SVG ikonlarla değiştirildi
- Bkz. [architecture.md → UI Katmanı](architecture.md#4-ui-srcui)

---

## [2026-05-09] commit | UI bileşen mimarisi ve servisler modülerleştirildi

- `083cf17` — UI bileşen klasör yapısı yeniden düzenlendi
- `c0a7fc6` — Her domain için ayrı servis klasörü oluşturuldu
- `9f0db4d` — Toast bildirim sistemi, portföy analiz servisi güncellendi
