# Kod Kalitesi Guardrail'leri

> Ana sayfa: [index.md](index.md) | Test stratejisi: [testing_strategy.md](testing_strategy.md) | Geliştirme: [development_guide.md](development_guide.md) | Kapılar: [ARCHITECTURE_GATES.md](../../ARCHITECTURE_GATES.md)

Bu sayfa kalıcı kalite kurallarını, ölçüm komutunu ve bilinen eşik ihlallerini tanımlar. Karar kaynağı `scripts/measure_code_quality.py` çıktısı ve mimari kurallardır.

## 1. Ölçüm

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
| Sınıf satırı | `>300` etkin satır | Yeni davranış eklemeden önce sorumluluk ayrımı (helper, servis, alt denetleyici). |
| Sınıf metodu | `>20` metot | Sorumluluk ayrımı veya belgelenmiş geçici istisna. |
| Fonksiyon/metot satırı | `>50` etkin satır | Küçük fonksiyonlara bölünür. |
| Parametre sayısı | `>5` | Parametre nesnesi veya daha dar API. |
| Cyclomatic complexity | `>10` | Dallar ayrıştırılır, hedefli test eklenir. |

## 3. Güncel Durum (2026-10-04 ölçümü)

Python dosyası eşiği (400 satır) ihlali yoktur. **14 sınıf** ve **107 fonksiyon** eşik dışıdır; sınıf ihlallerinin tamamı QML denetleyicileridir:

| Denetleyici | Etkin satır | Metot |
|---|---:|---:|
| `ComparisonController` | 884 | 50 |
| `Stock360Controller` | 685 | 84 |
| `OptimizationController` | 628 | 36 |
| `AiAdvisorController` | 614 | 44 |
| `DashboardController` | 611 | 44 |
| `StockDetailController` | 558 | 43 |
| `ModelPortfolioController` | 518 | 41 |
| `PlanningController` | 489 | 39 |
| `WatchlistController` | 405 | 29 |
| `CorporateActionController` | 394 | 29 |
| `ChartController` | 199 | 22 |
| `SettingsController` | 304 | 38 |
| `PriceDataController` | 288 | 37 |
| `StrategyBacktestController` | 170 | 21 |

Fonksiyon ihlallerinin çoğu `stock_detail_controller.py` (8), `stock_360_calc.py` (6), `comparison_controller.py`, `corporate_action_controller.py`, `dashboard_controller.py` (5'er) dosyalarındadır. Bunlar geçici ve bilinen teknik borçtur ([roadmap.md](roadmap.md)); **yeni ihlal eklenmez**: bu denetleyicilere özellik eklemeden önce ilgili parça ayrı modüle (hesap yardımcısı, alt denetleyici) çıkarılır. `Stock360Controller` bu ayrımın örneğidir (`stock_360_calc/fallback/formatters/html`).

## 4. Denetleyici ve QML Standardı

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
