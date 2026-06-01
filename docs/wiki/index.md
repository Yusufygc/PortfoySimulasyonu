# Wiki — İçerik Kataloğu

> Bu dosya tüm wiki sayfalarının ve teknik tasarım belgelerinin ana dizinidir.  
> Değişiklik günlüğü: [log.md](log.md) | Yol haritası: [Plans.md](Plans.md)

---

## 🏗️ Mimari ve Teknik Belgeler

| Sayfa | Özet |
|-------|------|
| [architecture.md](architecture.md) | Katmanlı mimari (Clean Architecture), tüm domain modelleri, servisler, DB şeması, veri akışı, optimizasyon motoru |
| [comparison_lab.md](comparison_lab.md) | Karşılaştırma Laboratuvarı mimarisi, görsel bileşenleri, veri entegrasyonu, tarih doğrulama ve Gemini AI asistan yapısı |

---

## 📈 Tasarım Spesifikasyonları (Tarihsel Aşamalar)

Comparison Lab geliştirme sürecinde takip edilen teknik şartnameler ve uygulama blueprints dosyaları:

| Dosya | Açıklama |
|-------|----------|
| [1_COMPARISON_SERVICE.md](../../analizSayfasi/1_COMPARISON_SERVICE.md) | Aşama 1: Matematiksel altyapı ve veri motorunun (`ComparisonService`) teknik gereksinimleri |
| [2_COMPARISON_CHART_FACTORY.md](../../analizSayfasi/2_COMPARISON_CHART_FACTORY.md) | Aşama 2: Plotly grafik üreticisi (`ComparisonChartFactory`) ve JSON şablon tasarımı |
| [3_UI_LAYERS_AND_SIGNALS.md](../../analizSayfasi/3_UI_LAYERS_AND_SIGNALS.md) | Aşama 3: PyQt5 UI bileşenleri, `CheckableComboBox` ve veri güncelleme sinyal ağı |
| [4_NAVIGATION_AND_INTEGRATION.md](../../analizSayfasi/4_NAVIGATION_AND_INTEGRATION.md) | Aşama 4: Sol navigasyon barı, sayfa geçişleri, DI container entegrasyonu ve Gemini analist prompt tasarımı |

---

## 🛠️ Operasyon ve Süreç

| Sayfa | Özet |
|-------|------|
| [log.md](log.md) | Kronolojik, yalnızca ekleme yapılan wiki güncelleme ve commit kaydı |
| [Plans.md](Plans.md) | Gelecek geliştirmeler, teknik borç notları ve code review ihtiyaçları |

---

## 🌐 Proje Genel Bakış

**Portföy Simülasyonu** — PyQt5 masaüstü portföy yönetim uygulaması.

- YFinance ile gerçek zamanlı fiyat takibi
- Markowitz optimizasyonu (SciPy + Ledoit-Wolf)
- BIST ve küresel hisse desteği
- Model/sanal portföy simülasyonu ve backtest
- Risk profili analizi, Excel raporlama, Gemini AI entegrasyonu

Geliştirme komutları ve kurulum için bkz. [../../CLAUDE.md](../../CLAUDE.md).  
Commit ve wiki kuralları için bkz. [../../RULES.md](../../RULES.md).

---

## 📌 Sayfa Ekleme ve Güncelleme Talimatı

Yeni bir wiki sayfası veya teknik doküman eklendiğinde:
1. Bu dizin (`index.md`) tablosuna ilgili satırı ekle.
2. `log.md` dosyasına `yeni-sayfa` veya `güncelleme` türünde kronolojik kaydı işle.
3. Yeni sayfanın en üstüne index ve log sayfalarına kolay erişim sunan yönlendirme satırını ekle (örn. `> Ana sayfa: [index.md](index.md)...`).
4. **Token Tasarrufu**: Belgeleri net, şematik ve yapılandırılmış tutarak gelecekteki LLM oturumlarının hızlıca bağlam kazanmasını ve gereksiz token tüketimini engellemesini sağlayın.

---

*Son güncelleme: 2026-06-01 — Gelişmiş karşılaştırma laboratuvarı ve tasarım spesifikasyonları dizine bağlandı.*
