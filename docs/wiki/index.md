# Wiki — İçerik Kataloğu

> Bu dosya tüm wiki sayfalarının ve teknik tasarım belgelerinin ana dizinidir.  
> Değişiklik günlüğü: [log.md](log.md) | Yol haritası: [Plans.md](Plans.md)

---

## 🏗️ Mimari ve Teknik Belgeler

| Sayfa | Özet |
|-------|------|
| [architecture.md](architecture.md) | Katmanlı mimari (Clean Architecture) özeti ve teknik belgelerin ana yönlendiricisi (Hub) |
| [ai_integration.md](ai_integration.md) | Gemini API asistan entegrasyonu, XAI faktörleri ve prompt yapıları |
| [database_schema_and_orm.md](database_schema_and_orm.md) | SQLAlchemy modelleri, Repo arayüzleri, veritabanı tabloları ve migration |
| [service_analysis.md](service_analysis.md) | Risk/Getiri metrikleri, benchmark hesaplamaları ve fallback veri kuralları |
| [service_planning_optimization.md](service_planning_optimization.md) | Markowitz optimizasyonu, SciPy, ağırlık kısıtları ve risk anketi |
| [service_portfolio_and_market.md](service_portfolio_and_market.md) | Event-sourcing portföy hesaplaması, YFinance veri çekimi ve tatil takvimi |
| [service_simulation.md](service_simulation.md) | Tarihsel backtest (simülasyon) altyapısı, snapshot üretimi ve uç vakalar |
| [ui_architecture_and_events.md](ui_architecture_and_events.md) | PySide6 arayüz mimarisi, Qt compat katmanı, Worker yapıları, Global Event Bus ve QSS Tema Yöneticisi |
| [pyside6_migration_analysis.md](pyside6_migration_analysis.md) | PyQt5 tabanlı masaüstü uygulamasını PySide6'ya taşımak için modüler analiz, risk matrisi ve faz planı |
| [comparison_lab.md](comparison_lab.md) | Karşılaştırma Laboratuvarı mimarisi, görsel bileşenleri, veri entegrasyonu ve Gemini AI asistan yapısı |
| [service_reporting_and_export.md](service_reporting_and_export.md) | OpenPyXL Excel formatter ve dışa aktarım raporlaması |
| [service_corporate_actions.md](service_corporate_actions.md) | Temettü, bölünme işlemleri ve portföy maliyetine etkileri |
| [service_watchlist.md](service_watchlist.md) | İzleme listesi, potansiyel varlıklar ve hedef fiyatlar |
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
| [database_maintenance_and_scripts.md](database_maintenance_and_scripts.md) | DB Bütünlük onarımı, geçersiz trade temizliği, scriptler (purge vb.) |
| [testing_strategy.md](testing_strategy.md) | Birim/Servis ve PySide6 UI testlerinin (pytest) mimarisi ve fixture yapısı |
| [manual_testing_guide.md](manual_testing_guide.md) | Uygulama sayfaları ve kritik akışlar için kapsamlı manuel test yönergesi |
| [project_build_and_deployment.md](project_build_and_deployment.md) | Nuitka ile derleme (.exe), CI commit kancaları ve pip pinleme |
| [log.md](log.md) | Kronolojik, yalnızca ekleme yapılan wiki güncelleme ve commit kaydı |
| [Plans.md](Plans.md) | Gelecek geliştirmeler, teknik borç notları ve code review ihtiyaçları |

---

## 🌐 Proje Genel Bakış

**Portföy Simülasyonu** — PySide6 masaüstü portföy yönetim uygulaması.

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

*Son güncelleme: 2026-06-12 — PySide6 göçü, Qt compat katmanı ve UI test stratejisi dizine işlendi.*
