> Ana sayfa: [index.md](index.md) | Değişiklik günlüğü: [log.md](log.md) | Dönüşüm geçmişi: [QML_TRANSFORMATION_HANDOFF.md](../../QML_TRANSFORMATION_HANDOFF.md)

# Yol Haritası ve Fikir Havuzu

Bu sayfa, kodda **henüz olmayan** özellikleri ve bilinen teknik borcu tek yerde toplar. Tamamlanan işler burada tutulmaz; onlar için [log.md](log.md) ve ilgili servis sayfaları esastır. Bu sayfadaki her madde 2026-10-03 tarihinde kod taramasıyla doğrulanmıştır ("Açık" = kodda bulunmuyor).

Durum etiketleri: **Açık** (başlanmadı), **Kısmi** (bir bölümü var).

---

## 1. Teknik Borç

| Konu | Durum | Ayrıntı |
|---|---|---|
| Büyük denetleyici sınıfları | Açık | `scripts/measure_code_quality.py` ölçümünde 14 sınıf ve 77 fonksiyon eşik ihlali vardır; sınıf ihlallerinin tamamı `src/ui_qml/controllers/` altındadır (`ComparisonController` 339 (ayrıştırma başladı), `Stock360Controller` 567 (ayrıştırma başladı), `OptimizationController` 279 (ayrıştırma başladı), `AiAdvisorController` 614, `DashboardController` 611 etkin satır). Eşikler [code_quality_guardrails.md](code_quality_guardrails.md) içindedir. Yeni özellik bu denetleyicilere eklenmeden önce sorumluluk ayrımı yapılmalıdır. |
| SQLite `BIGINT` kimlik tabloları | Açık | `id` sütunları `BIGINT` olduğundan otomatik artmaz; `before_insert` dinleyicisi `max(id)+1` atar (yazma kilidiyle çakışmasız). Kalıcı çözüm: SQLite için `BigInteger().with_variant(Integer, "sqlite")` ve ~19 tablonun yeniden kurulması (üretilmiş sütun `trades.total_amount`, FK ve indeksler korunarak, ayrı numaralı göç). Risk/fayda nedeniyle ertelendi. |
| Kullanılmayan CRUD port/implementasyon çiftleri | Açık | Bazı repository metotları (CRUD tamlığı için yazılmış) hiçbir servis tarafından çağrılmaz. Bilinçli olarak bırakılmıştır. |
| Veritabanı oturum ömrü | İzleme | Uzun oturumlarda SQLite kilitlenmesi görülürse `pool_recycle`/`pool_pre_ping` ayarlarının `.env` ile denetlenmesi planlanmıştı; şu an gözlenen bir sorun yoktur. |

---

## 2. Fikir Havuzu

### 2.1 Finansal Planlama

| Fikir | Durum | Not |
|---|---|---|
| Dinamik hedefler (enflasyon ve yatırım getirisi entegreli) | Açık | Hedefler statiktir (`financial_goals`); hedefe bağlı yatırım aracı ve piyasa simülasyonlu kalan süre yoktur. |
| Nakit akışı tahmini | Açık | Geçmiş bütçelerden gelecek 3 ay tahmini (hareketli ortalama/regresyon) yoktur. |
| Stres testi / what-if | Açık | Gelir/gider şoklarıyla bellek içi senaryo servisi yoktur. |
| Tekrarlayan işlemler | Kısmi | Sabit kalemler "pinlenebilir" (`budget_pinned_items`) ve bütçesi olmayan aylara taslak olarak taşınır; sıklık ve vade tarihli otomatik üretim yoktur. |
| Borç ve tasarruf optimizasyonu (kartopu/çığ) | Açık | `Debt` modeli yoktur. |
| Sankey nakit akışı grafiği | Açık | |

### 2.2 Optimizasyon

| Fikir | Durum | Not |
|---|---|---|
| Dinamik risksiz faiz | Kısmi | Varsayılan %30'dur (`OptimizationPolicy`); kullanıcı arayüzden elle değiştirebilir (`setRiskFreeRate`). TCMB/tahvil verisinden otomatik çekme yoktur. |
| İşlem maliyeti cezası (turnover) | Açık | Amaç fonksiyonunda komisyon yoktur; yalnızca strateji backtest'inde komisyon oranı vardır. |
| Black-Litterman | Açık | Beklenen getiri yalnızca tarihsel ortalamadır (Chopra-Ziemba sınırlaması). |
| Hisse bazlı min/max ağırlık, sektör ve likidite kısıtı | Açık | Yalnızca tek global tek-hisse üst sınırı vardır. |
| Yeniden optimizasyon hatırlatması | Açık | |

### 2.3 Risk Profili

| Fikir | Durum | Not |
|---|---|---|
| LLM destekli kişisel profil analizi (hibrit: skor yerelde, yorum Gemini'de) | Açık | `RiskProfile` modelinde `ai_analysis` alanı yoktur. |
| Profile uygun model portföy yönlendirmesi | Açık | `recommended_allocation` hesaplanır ama model portföye bağlanmaz. |
| Geçerlilik süresi (yıllık yeniden değerlendirme uyarısı) | Açık | |

### 2.4 Analiz ve Karşılaştırma

| Fikir | Durum | Not |
|---|---|---|
| İşlem analizi (win rate, ortalama elde tutma süresi, erken/geç satış etkisi) | Açık | |
| Davranışsal analiz (aşırı işlem, zarardaki pozisyonu tutma eğilimi) | Açık | |
| Getiri katkısının ağırlık/hisse seçimi olarak ayrıştırılması | Açık | Katkı haritası (treemap) vardır, ayrıştırma yoktur. |
| Para ağırlıklı getiri (XIRR) | Açık | Yalnızca zaman ağırlıklı getiri (TWR) hesaplanır. |
| Drawdown toparlanma süresi | Açık | Drawdown derinliği vardır; toparlanma süresi yoktur. |

### 2.5 Teknik ve Temel Analiz

| Fikir | Durum | Not |
|---|---|---|
| Ichimoku ve Keltner kanalları | Açık | v1 kapsamı dışında bırakılmıştı. |
| Donchian kırılımı, yapısal kırılım (HH/LL) tarayıcısı | Açık | Tasarım notu: [tasarim_notlari/teknik_analiz_tartisma.md](tasarim_notlari/teknik_analiz_tartisma.md). |
| Tüm BIST için toplu temel analiz taraması | Açık | Metrikler tek hisse için hesaplanır; toplu çekim altyapısı yoktur. Tasarım notu: [tasarim_notlari/temel_analiz_filtre_tartisma.md](tasarim_notlari/temel_analiz_filtre_tartisma.md). |
| Mali tablo önbellek tablosu (`cached_financial_statements`) | Açık | Yalnızca dosya tabanlı `data/_cache/financials` ve `kap_*` tabloları vardır. |

### 2.6 Portföy ve Veri

| Fikir | Durum | Not |
|---|---|---|
| Temettü otomatik tespiti, brüt/stopaj hesabı | Açık | Temettü elle ve net tutarla girilir; bkz. [service_corporate_actions.md](service_corporate_actions.md). |
| Model portföy için temettü | Açık | |
| Model portföy fiyatlarının DB merkezli okunması | Açık | Model portföy canlı fiyatı bellekte ve `latest_prices` üzerindedir; tarihsel rapor `daily_prices` kullanır. |
| Rebalance backtest için işlem günü bazlı vergi/komisyon modeli | Açık | Yalnızca tek oranlı komisyon vardır. |

### 2.7 Yapay Zeka

| Fikir | Durum | Not |
|---|---|---|
| AI_Core tahmin servisinin gerçek bağlantısı | Kısmi | İstemci ve ayrıştırıcı hazırdır (`AICoreFastAPIClient`); servis kapalıyken demo sağlayıcıya düşülür. Servis ayrı bir projedir. |
| Yazma yapan araçlar | Reddedildi | Danışman araçları bilerek salt okunurdur; emir/para hareketi aracı eklenmez ([ai_integration.md](ai_integration.md)). |

---

## 3. Belge Bakımı

- Bu sayfa yeni bir özellik tamamlandığında güncellenir: madde silinir ve ilgili servis sayfası ile [log.md](log.md) güncellenir.
- Tarihsel tasarım tartışmaları [tasarim_notlari/](tasarim_notlari/) altında tutulur; eski arayüz dönemine ait oldukları için üstlerinde durum notu vardır.
