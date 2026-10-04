# Kod Kalitesi Guardrail'leri

> Ana sayfa: [index.md](index.md) | Test stratejisi: [testing_strategy.md](testing_strategy.md) | Geliştirme: [development_guide.md](development_guide.md) | Kapılar: [ARCHITECTURE_GATES.md](../../ARCHITECTURE_GATES.md)

Bu sayfa kalıcı kalite kurallarını, ölçüm komutunu ve bilinen eşik ihlallerini tanımlar. Karar kaynağı `scripts/measure_code_quality.py` çıktısı ve mimari kurallardır.

## 1. Ölçüm

**CI kapısı:** `--max-class-violations`, `--max-function-violations`, `--max-file-violations` bayrakları ihlal sayısını tavanla karşılaştırır (aşılırsa çıkış kodu 1). CI mevcut borcu tavan alır (şu an 5 sınıf, 75 fonksiyon, 0 dosya); yeni ihlal eklenemez. Borç azaltıldıkça `.github/workflows/tests.yml` içindeki tavanlar da düşürülmelidir.

```powershell
.\venv\Scripts\python.exe scripts\measure_code_quality.py                    # varsayılan: docs/wiki/ altına yazar
.\venv\Scripts\python.exe scripts\measure_code_quality.py --output-dir C:\temp\cq
.\venv\Scripts\python.exe scripts\measure_code_quality.py --fail-on-threshold   # eşik ihlalinde 1 döner
```

Betik `code_quality_baseline_2026-06-13.md` ve `.json` dosyalarını üretir (dosya adı sabit `BASELINE_DATE` ile belirlenir). Yorum ve boş satırlar eşik kararından çıkarılır; docstring satırları ayrıca raporlanır ve eşikler `effective_code_lines` üzerinden değerlendirilir.

**Not:** Depodaki [code_quality_baseline_2026-06-13.md](code_quality_baseline_2026-06-13.md) ve `.json` dosyaları eski Qt Widgets arayüzü dönemine ait **tarihsel referanstır**; güncel durum için ölçümü yeniden çalıştırın (bir önceki dosyanın üzerine yazmaması için `--output-dir` verin).

## 2. Eşikler

| Yüzey | Eşik | Aksiyon |
|---|---:|---|
| Sınıf satırı | `>300` etkin satır (QML denetleyicileri: `>400`) | Yeni davranış eklemeden önce sorumluluk ayrımı (helper, servis, alt denetleyici). |
| Sınıf metodu | `>20` metot (QML denetleyicileri: `>30`) | Sorumluluk ayrımı veya belgelenmiş geçici istisna. |
| Fonksiyon/metot satırı | `>50` etkin satır | Küçük fonksiyonlara bölünür. |
| Parametre sayısı | `>5` | Parametre nesnesi veya daha dar API. |
| Cyclomatic complexity | `>10` | Dallar ayrıştırılır, hedefli test eklenir. |

**Sayım kuralı:** `@Property(...)` ile QML'e açılan getter'lar sınıfın metot sayısına ve etkin satırına dahil edilmez (saf bağlama yüzeyi; raporda `binding_method_count`). `@Slot` ve diğer metotlar sayılır. `src/ui_qml/controllers/` altındaki sınıflar bağlama yüzeyi nedeniyle 400 satır / 30 metot sınırıyla ölçülür; diğer katmanlar 300 / 20. Neden: getter sayısı QML sözleşmesinden gelir ve sınıf bölünmeden azalmaz; 14 denetleyici bu yüzden eşik dışı görünüyordu.

## 3. Güncel Durum (2026-10-04 ölçümü)

Python dosyası eşiği (400 satır) ihlali yoktur. **5 sınıf** ve **75 fonksiyon** eşik dışıdır; sınıf ihlallerinin tamamı QML denetleyicileridir (`@Property` getter'ları hariç; eşik 400 satır / 30 metot):

| Denetleyici | Etkin satır | Metot |
|---|---:|---:|
| `DashboardController` | 504 | 23 |
| `ModelPortfolioController` | 518 | 41 |
| `PlanningController` | 445 | 17 |
| `Stock360Controller` | 455 | 39 |
| `StockDetailController` | 507 | 19 |

Bunlar **kabul edilen borçtur** (denetim Bulgu 2, 2026-10-04): sırf eşik için ayrıştırılmaz; yeni davranış eklenen denetleyicide önce ilgili parça çıkarılır (bkz. §6). Karar gerekçesi için [log.md](log.md) "Bulgu 2 Kabul Edilen Borç" girdisine bakın.

Fonksiyon ihlallerinin çoğu `stock_detail_controller.py` (8), `corporate_action_controller.py` ve `dashboard_controller.py` (5'er) dosyalarındadır. Bunlar geçici ve bilinen teknik borçtur ([roadmap.md](roadmap.md)); **yeni ihlal eklenmez**: bu denetleyicilere özellik eklemeden önce ilgili parça ayrı modüle (hesap yardımcısı, alt denetleyici) çıkarılır. `Stock360Controller` (`stock_360_calc/fallback/formatters/html/overview/remote`) `ComparisonController` (`comparison_chart_html`, `comparison_support`) `OptimizationController` (`optimization_pipeline`, `optimization_chart_html`) ve `AiAdvisorController` (`advisor_health`, `advisor_local_analysis`, `advisor_chat_support`) bu ayrımın örnekleridir. `@Property` getter'ları ölçümde sayılmadığı için kalan ihlaller gerçek mantık satırlarıdır.

## 4. Denetleyici ve QML Standardı

**QML dosya tavanı:** `Strings.qml` hariç hiçbir QML dosyası 900 satırı aşmaz (`tests/ui_qml/test_qml_file_size_guard.py`); aşan görünüm sekme/bölüm bileşenlerine bölünür ([qml_pages_guide.md](qml_pages_guide.md)).

Denetleyici yalnızca durum, sinyal ve servis çağrısı bağlamasından sorumludur. Büyümemesi gerekenler: uzun hesap blokları, biçimlendirme, HTML/grafik üretimi, çok adımlı iş akışları. Bunlar saf yardımcı modüllere (`*_calc.py`, `*_formatters.py`, `lw_chart_html.py`, `number_input.py`) veya application servislerine taşınır. QML sayfaları iskelet ve bağlama kodudur; büyük sayfalar sekme bileşenlerine bölünür (`PlanningBudgetTab`, `SettingsPriceDataTab`...). Kullanıcı metinleri `Strings.qml`'dedir.

## 5. Application Servis Standardı

Servisler public API'yi koruyan ince facade olarak kalır; büyüyen servislerden şunlar ayrılır: kapsam çözümleme, doğrulama, dış sağlayıcı/repository çağrısı, hesaplama algoritması, persistence ve DTO üretimi. Örnekler: `PriceDataHealthService` (analyzer/updater/scope resolver), `ModelPortfolioService` (admin/trade/snapshot), `OptimizationService` (+ `frontier_simulation`), saf backtest motorları ve servis ayrımı.

## 6. İstisna Protokolü

- Yeni istisna yalnızca geçici ve gerekçeli kabul edilir; ölçüm JSON'unda görünür olmalı ve bu sayfada refactor hedefiyle açıklanmalıdır.
- Production dosyalarında yeni eşik ihlali oluşturulmaz; zorunluysa aynı değişiklikte refactor planı ve test kapsamı eklenir.
- Repository arayüzlerindeki "God Object" uyarıları yanlış pozitif olabilir; yalnızca farklı iş alanlarını karıştırıyorsa bölünür.

## 7. Yeni Özellik Öncesi Kontrol

1. Ölçüm betiğini çalıştır.
2. Değişecek dosyada mevcut ihlal varsa önce ayrıştırma dilimini planla.
3. Yeni kullanıcı metinlerini `Strings.qml`'e ekle.
4. Katman sınırlarını koru; denetleyici HTTP/SDK/repository import etmez.
5. Hedefli testleri ve sonunda tam `pytest tests -q` komutunu çalıştır.

## 8. Refaktör Disiplini (alınan dersler)

Kurallar [ARCHITECTURE_GATES.md](../../ARCHITECTURE_GATES.md) §1.1'dedir; özeti:

- **Değer şartı:** refaktör okunabilirlik, hata riski veya test edilebilirlik kazandırmalıdır. Yalnızca ölçüt sayısını düşürmek (yeni modül, yeni sarmalayıcı) gerekçe değildir; ölçüt gerçek sorunu yansıtmıyorsa ölçüt düzeltilir (§2 sayım kuralı).
- **Karakterizasyon önce:** davranışı koruyan taşıma/bölmeden önce mevcut kodun çıktısı sabit girdilerle kaydedilir, sonra karşılaştırılır; geçici betik yerine kalıcı test tercih edilir.
- **Küçük adım, ölçülü kapsam:** bir oturumda çok sayıda benzer sınıfa girişmeden önce ilk örnekten kazanç/maliyet raporlanır ve devam kararı kullanıcıdan alınır.
