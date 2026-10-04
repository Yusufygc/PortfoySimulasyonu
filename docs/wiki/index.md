# Wiki — İçerik Kataloğu

> Bu dosya tüm wiki sayfalarının ana dizinidir. Değişiklik günlüğü: [log.md](log.md) | Yapılacaklar: [roadmap.md](roadmap.md) | Kurallar: [RULES.md](../../RULES.md)

**Portföy Simülasyonu**, BIST ve küresel hisseleri takip eden bir PySide6 + QML masaüstü uygulamasıdır: olay kaynaklı portföy, SQLite + DuckDB çift veri deposu, tüm BIST için tarayıcı ve sermaye artırımı düzeltmesi, Markowitz optimizasyonu, backtest, Excel raporlama ve Gemini destekli analiz. Geliştirme komutları: [development_guide.md](development_guide.md).

Önce okunacaklar: [architecture.md](architecture.md) -> [project_structure.md](project_structure.md) -> ilgili konu sayfası.

---

## Başlangıç ve Genel Bakış

| Sayfa | Özet |
|---|---|
| [architecture.md](architecture.md) | Katmanlar, katman kuralları ve koruma testleri, DI container, açılış akışı, eşzamanlılık, tasarım kararları ve belge haritası |
| [project_structure.md](project_structure.md) | Kaynak ağacı ve her dizinin/modülün sorumluluğu |
| [development_guide.md](development_guide.md) | Kurulum, `.env` ayarları, komutlar, gerçek veriyi koruma, yeni özellik kalıpları, sık sorunlar |
| [glossary.md](glossary.md) | Finans, risk ve mimari terimler sözlüğü |
| [roadmap.md](roadmap.md) | Kodda olmayan özellikler (fikir havuzu) ve bilinen teknik borç |

## Arayüz

| Sayfa | Özet |
|---|---|
| [ui_architecture_and_events.md](ui_architecture_and_events.md) | QML mimarisi: ince QML + Python denetleyici, gezinme, Theme/Strings/Icons, grafikler, iş parçacığı ve sinyal modeli, denetleyici kuralları |
| [qml_pages_guide.md](qml_pages_guide.md) | 10 sayfanın amacı, denetleyicileri, özellikleri ve denetleyici referansı |
| [comparison_lab.md](comparison_lab.md) | Karşılaştırma Lab: seçim, mod, para birimi, grafik sekmeleri, yapay zekâ yorumu |
| [stock_360.md](stock_360.md) | Hisse 360: genel bakış, teknik seviyeler, finansal analiz, KAP ortaklık yapısı |
| [settings_and_system.md](settings_and_system.md) | Ayarlar sekmeleri, açılış ve zamanlayıcı işleri, canlı fiyat yenileme, `QSettings` |

## Servisler ve Alan Mantığı

| Sayfa | Özet |
|---|---|
| [service_portfolio_and_market.md](service_portfolio_and_market.md) | Olay kaynaklı portföy, işlem girişi ve seans koruması, nakit, iki fiyat akışı, fiyat sağlığı, model portföy nakit kuralları |
| [service_corporate_actions.md](service_corporate_actions.md) | Bedelli/bedelsiz uygulaması, fiyat geçmişi düzeltmesi, KAP/MKK aday akışı, nakit temettü |
| [market_corporate_actions.md](market_corporate_actions.md) | Tüm BIST için DuckDB'de veriden sermaye artırımı tespiti, faktör formülleri, onay, çift düzeltme koruması |
| [service_analysis.md](service_analysis.md) | Analiz servisleri, TWR serisi, risk metrikleri, benchmark kaynakları |
| [technical_analysis_and_screener.md](technical_analysis_and_screener.md) | Göstergeler (ADX, Supertrend dahil), 10 stratejili tarayıcı, Golden/Death Cross |
| [service_planning_optimization.md](service_planning_optimization.md) | Bütçe ve hedefler, Markowitz optimizasyonu, verimli sınır, risk profili ve köprüsü, model portföyler |
| [service_simulation.md](service_simulation.md) | Tarihsel simülasyon, DCA ve strateji backtest (yeniden dengeleme, stop-loss/take-profit) |
| [service_watchlist.md](service_watchlist.md) | İzleme listeleri, kod doğrulama, tablo davranışı |
| [service_reporting_and_export.md](service_reporting_and_export.md) | Excel raporları (ekleme modu, fiyat sözleşmesi) ve HTML üreticileri |
| [ai_integration.md](ai_integration.md) | Portföy Danışmanı (tool-calling), girdi güvenliği, hisse modeli (AI_Core), sohbet geçmişi |

## Veri ve Altyapı

| Sayfa | Özet |
|---|---|
| [data_architecture.md](data_architecture.md) | SQLite ve DuckDB sahipliği, DuckDB şeması, ticker biçimi, yazma/okuma kuralları, bilinen sınırlar |
| [database_schema_and_orm.md](database_schema_and_orm.md) | 23 tablo, repository deseni, açılış göçleri, BIGINT id atama |
| [service_market_data_providers.md](service_market_data_providers.md) | Dış veri kaynakları, önbellekler, ağ yeniden denemesi, hata aileleri, seans ve takvim |
| [database_maintenance_and_scripts.md](database_maintenance_and_scripts.md) | `DatabaseMaintenanceService`, betikler, güvenli çalışma pratikleri |

## Test, Kalite ve Yayın

| Sayfa | Özet |
|---|---|
| [testing_strategy.md](testing_strategy.md) | Test piramidi, koruma testleri, fixture ve gerçek veri izolasyonu, komutlar, CI |
| [manual_testing_guide.md](manual_testing_guide.md) | 10 sayfa ve arka plan davranışı için yayın öncesi manuel test listesi |
| [code_quality_guardrails.md](code_quality_guardrails.md) | Eşikler, ölçüm komutu, güncel eşik ihlalleri, istisna protokolü |
| [code_quality_baseline_2026-06-13.md](code_quality_baseline_2026-06-13.md) | Tarihsel kod kalitesi baseline raporu (eski arayüz dönemi) |
| [project_build_and_deployment.md](project_build_and_deployment.md) | Nuitka derlemesi, preflight, pinli bağımlılıklar, CI, `auto_commit.py` |

## Tarihsel ve Proje Kök Belgeleri

| Belge | Özet |
|---|---|
| [QML_TRANSFORMATION_HANDOFF.md](../../QML_TRANSFORMATION_HANDOFF.md) | QML dönüşümünün tamamlanan fazları, Faz 11 sonrası eklemeler ve devralma kılavuzu |
| [TRANSFORMATION_PLAN.md](../../TRANSFORMATION_PLAN.md) | Tarihsel dönüşüm planı (üstündeki durum notu ve §9.13 güncel durumu belirtir) |
| [tasarim_notlari/teknik_analiz_tartisma.md](tasarim_notlari/teknik_analiz_tartisma.md) | Trend kırılım tarayıcısı tasarım tartışması (kısmen uygulanmadı) |
| [tasarim_notlari/temel_analiz_filtre_tartisma.md](tasarim_notlari/temel_analiz_filtre_tartisma.md) | Toplu temel analiz taraması tasarım tartışması (uygulanmadı) |
| [log.md](log.md) | Kronolojik, yalnızca ekleme yapılan değişiklik günlüğü |

---

## Sayfa Ekleme ve Güncelleme Talimatı

1. Yeni sayfanın en üstüne navigasyon satırı koy (`> Ana sayfa: [index.md](index.md) | ...`).
2. Bu tabloya ilgili satırı ekle; silinen sayfayı kataloğdan çıkar.
3. `log.md`'ye (en üste) giriş ekle.
4. Mimari karar, yeni özellik veya önemli hata çözümünde ilgili servis sayfasını ve `architecture.md`'yi güncelle; tamamlanan özelliği `roadmap.md`'den sil.
5. Belgeleri net, şematik ve doğrulanabilir tut; bir iddia kodla çelişiyorsa kod esastır.

*Son güncelleme: 2026-10-04 — wiki kod tabanına göre baştan doğrulanıp yenilendi (bkz. [log.md](log.md)).*
