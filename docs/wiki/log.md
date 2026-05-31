# Wiki Değişiklik Günlüğü

> Ana katalog: [index.md](index.md) | Mimari: [architecture.md](architecture.md)  
> Bu dosya **yalnızca ekleme** yapılır. Eski girişler hiçbir zaman silinmez veya düzenlenmez.  
> Grep ile son girişler: `grep "^## \[" docs/wiki/log.md | head -10`

---

## [2026-05-30] güncelleme | Modüler QSS sistemi ve design token altyapısı

- `src/ui/styles/base/` silindi; yerine `primitives/` klasörü oluşturuldu
- `src/ui/styles/tokens.py` eklendi: tüm `@TOKEN_ADI` yer tutucuları tek sözlükte toplandı
- `theme_manager.py` `STYLE_MANIFEST` cascade sırası güncellendi (themes → primitives → shared → features)
- `features/ai/`, `features/risk_profile/` alt klasörlerine bölündü; `shared/typography.qss` eklendi
- QSS kapsam kuralı: bileşen-özel `cssState`/`cssClass` kuralları global widget seçicisine taşınmadı
- `ThemeManager.validate_theme_tokens()` ile 0 çözülmemiş token doğrulandı (dark + light)
- 3 ön-var test hatası giderildi: `active_positions` mock attr + `QThreadPool` async zamanlama
- Test sonucu: **238 passed, 0 failed**
- Etkilenen dosyalar: `src/ui/styles/`, `src/ui/theme_manager.py`, `src/ui/styles/tokens.py`, `tests/`
- Bağlantılı sayfa: [architecture.md → Modüler QSS Sistemi](architecture.md#modüler-qss-sistemi-srcuistyles)

---

## [2026-05-31] güncelleme | Finansal planlama ve bütçe modellerinin genişletilmesi

- Bütçe hedefleri için alanlar (budget modeli) detaylandırıldı ve veritabanı yansımaları (`orm_models`) güncellendi
- Planlama servisi ve `sa_planning_repository` yeni özelliklere göre uyarlandı
- Planlama sayfasındaki bütçe form paneli (`budget_form_panel`) ve hedef paneli (`goals_panel`) geliştirildi
- QSS stilleri (planning.qss, shared) UI tasarım sistemiyle uyumlu hale getirildi
- Etkilenen dosyalar: `src/domain/models/`, `src/application/services/planning/`, `src/ui/pages/planning_page.py`, `src/ui/widgets/planning/`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-05-31] lint | Wiki sağlık kontrolü yapıldı

- Silinmiş olan `architecture.md` belgesi git geçmişinden restore edilerek onarıldı
- Yetim kalan `Plans.md` dosyası `index.md` içerik kataloğuna eklendi ve zorunlu navigasyon başlığı eklendi
- Kırık bağlantılar onarıldı ve wiki bütünlüğü sağlandı
- Etkilenen dosyalar: `docs/wiki/architecture.md`, `docs/wiki/index.md`, `docs/wiki/Plans.md`

---

## [2026-05-31] güncelleme | Analiz ve optimizasyon ekranlarında iyileştirmeler

- Analiz servisleri ve grafik motorunda (analysis_chart_engine) güncellemeler yapıldı
- Optimizasyon sayfası ve öneri tablolarında (suggestions_table) stil iyileştirmeleri eklendi
- Etkilenen dosyalar: `src/application/services/analysis/`, `src/ui/pages/`, `src/ui/widgets/optimization/`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-05-31] güncelleme | Tema sistemi modernizasyonu ve UI bileşenleri

- Tema yöneticisi (theme_manager) ve stil tokenleri (tokens.py) modern bir yapıya kavuşturuldu
- Buton, kart, liste ve geri bildirim (toast) gibi paylaşımlı QSS bileşenleri güncellendi/eklendi
- Ayarlar sayfası görünüm paneli (appearance_panel) yeni token altyapısına bağlandı
- Etkilenen dosyalar: `src/ui/theme_manager.py`, `src/ui/styles/`, `src/ui/widgets/shared/`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-05-30] commit | Model portföy geçmiş simülasyonu ve Excel raporu

- Model portföyler için geçmiş simülasyon servisi eklendi
- Excel dışa aktarım (export) fonksiyonları eklendi
- `HistorySimulationService` kod ve test yapısı güçlendirildi
- Etkilenen dosyalar: `src/application/services/simulation/`, `src/application/services/reporting/`, `tests/`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-05-30] commit | BIST piyasa oturum kontrolü ve kullanıcı onayı

- Piyasa saatleri dışı ve tatil günleri için oturum kontrol servisi eklendi
- Kullanıcı işlem yaparken piyasa kapalıysa onay penceresi (`market_session_confirm.py`) gösterilecek
- Etkilenen dosyalar: `src/application/services/market/`, `src/ui/shared/`, `src/infrastructure/calendar/`
- Bağlantılı sayfa: [architecture.md](architecture.md)

---

## [2026-05-27] güncelleme | Yeni işlem sihirbazında şirket adı ve fiyat kaynağı temizlendi

- `PriceLookupService` sonucu şirket adı, normalize ticker ve anlık/son kapanış kaynak bilgisini taşıyacak şekilde genişletildi
- Yeni işlem sihirbazında şirket adı manuel girişten çıkarıldı; lookup sonucu otomatik gösteriliyor
- İşlem detay başlığındaki inline HTML/CSS kaldırıldı, ticker ve şirket adı ayrı QSS sınıflı label'lara ayrıldı
- Etkilenen dosyalar: `src/application/services/market/price_lookup_service.py`, `src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py`, `src/ui/styles/shared/dialogs.qss`, `tests/`
- Bağlantılı sayfa: [architecture.md → Application](architecture.md#2-application-srcapplication)

---

## [2026-05-27] güncelleme | Nakit gösterimi sıfır tabanlı yapıldı ve THYAO temizleme servisi eklendi

- Nakit hesaplama negatif borç üretmeyecek şekilde olay akışında `0` tabanına sabitlendi
- Dashboard nakit kartı ve seçili hisse hızlı işlem paneli negatif kalan nakit göstermeyecek şekilde güncellendi
- THYAO/THYAO.IS kayıtlarını gerçek portföy, fiyat, watchlist, model portföy ve kurumsal aksiyon tablolarından temizlemek için bakım servisi ve script eklendi
- Etkilenen dosyalar: `src/application/services/portfolio/`, `src/infrastructure/db/sqlalchemy/repositories/`, `src/ui/pages/`, `scripts/purge_stock.py`, `docs/wiki/architecture.md`
- Bağlantılı sayfa: [architecture.md → Portföy Hesaplama Mantığı](architecture.md#portföy-hesaplama-mantığı)

---

## [2026-05-27] güncelleme | Dashboard nakit doğrulaması ve güvenli trade replay eklendi

- Gerçek portföy için kalıcı `cash_movements` tablosu, nakit hareket servisi ve al/sat doğrulaması eklendi
- Nakit yetersizse alım, eldeki lot yetersizse satış kaydı engellenecek şekilde merkezi `TradeEntryService` doğrulaması güncellendi
- Eski geçersiz satış kayıtları hesaplamadan hariç tutulup DB bütünlük raporunda listelenecek şekilde güvenli portföy kurucu eklendi
- Etkilenen dosyalar: `src/domain/`, `src/application/services/portfolio/`, `src/infrastructure/db/sqlalchemy/`, `src/ui/pages/dashboard/`, `docs/wiki/architecture.md`
- Bağlantılı sayfa: [architecture.md → Portföy Hesaplama Mantığı](architecture.md#portföy-hesaplama-mantığı)

---

## [2026-05-26] commit | Seçili hisse ekranı ve tablo seçim davranışı iyileştirildi

- Seçili hisse detay grafiği pyqtgraph ile responsive hale getirildi; referans çizgi açıklamaları çakışmayacak legend alanına taşındı
- Hızlı işlem paneli sabit yerleşime alındı; splitter resize handle kaldırıldı ve onay butonu işlem etkisi kartının altında konumlandı
- Pasif tablolarda seçim/focus kapatıldı; dashboard ana tablo dahil renkli hücrelerin seçim tarafından ezilmesi engellendi
- Stok detay kartları emoji yerine tema duyarlı SVG ikonlara geçti; kâr/zarar kartı pozitif/negatif duruma göre ikon ve renk değiştiriyor
- Etkilenen dosyalar: `src/ui/`, `tests/ui/`, `docs/wiki/architecture.md`, `docs/wiki/log.md`
- Bağlantılı sayfa: [architecture.md → UI](architecture.md#4-ui-srcui)

---

## [2026-05-26] commit | UI tema modernizasyonu ve dashboard rapor akışı güncellendi

- Component token tabanlı light/dark tema kontrastları güçlendirildi; dashboard kartları ve butonları modernize edildi
- `QStackedWidget` seviyesindeki fade/graphics effect kaldırılarak hover sırasında buton kaybolması ve QPainter uyarıları giderildi
- UI gösteriminde BIST `.IS` suffix'i gizlendi, Türkçe metin standardizasyonu yapıldı
- Dashboard rapor üretimi tek `Rapor Al` menüsünde `Bugün` ve `Tarih Aralığı` seçeneklerine indirildi
- Etkilenen dosyalar: `src/ui/`, `tests/ui/`, `docs/wiki/architecture.md`, `docs/wiki/log.md`
- Bağlantılı sayfa: [architecture.md → UI](architecture.md#4-ui-srcui)

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
