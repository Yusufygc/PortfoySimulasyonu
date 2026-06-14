# Refactor Handoff - 2026-06-13

> Ana sayfa: [index.md](index.md) | Guardrail: [code_quality_guardrails.md](code_quality_guardrails.md) | Baseline: [code_quality_baseline_2026-06-13.md](code_quality_baseline_2026-06-13.md)

Bu sayfa, sağlık raporu tabanlı refactor çalışmasının başka bir ajan veya geliştirici tarafından güvenli biçimde sürdürülebilmesi için oluşturuldu.

## Amaç

Production kodunda sağlık baseline raporuyla doğrulanmış sınıf, fonksiyon ve complexity ihlallerini davranış değiştirmeden azaltmak. Refactor kararlarında `PortfoySimulasyonu_saglik_raporu.html` tek kaynak kabul edilmez; `scripts/measure_code_quality.py` çıktısı ve [code_quality_guardrails.md](code_quality_guardrails.md) kuralları esas alınır.

## Güncel Durum

- Branch: `refactor`
- Son önemli commitler:
  - `5d1583b` - Refactor tamamlama notunu wiki ve handoff sayfasına ekle
  - `f0d2768` - Faz 3 application+UI fonksiyon ihlallerini gider; src violations=115→90
  - `75edccd` - Kalan sınıf ihlallerini gider; violating_classes=4→1
- Güncel baseline metrikleri (2026-06-14):
  - **Sınıf ihlali: `2`** (`L10N` + `PortfolioSeriesBuilder` — her ikisi belgeli istisna)
  - **Fonksiyon ihlali toplam: `109`** (src: `90`, tests: `14`, scripts: `5`)
  - src satır ihlali: ≈0 (parse_kap_mkk_disclosure tam sınırda=50, >50 sayılmıyor)
  - **src complexity ihlali: `49`** (cyclomatic > 10)
  - **src parametre ihlali: `44`** (effective_params > 5)
- Kirli worktree notu:
  - `app.py` ve bazı `src/ui/...` dosyalarında önceden var olan unstaged UI değişiklikleri bulunuyor.
  - Bu değişiklikler kullanıcıya ait kabul edilir; geri alınmaz.

## Tamamlananlar

- `scripts/measure_code_quality.py` eklendi.
- `docs/wiki/code_quality_baseline_2026-06-13.md` ve JSON baseline üretildi.
- [code_quality_guardrails.md](code_quality_guardrails.md) eklendi.
- `ModelPortfolioTradeService` builder, sıralama ve zaman filtresi helper'ları sınıf dışına taşındı.
- `ChartRenderer` figure üretimi ve dosya adı helper'ları sınıf dışına taşındı.
- `ChartRenderer` UI whitelist'inden çıkarıldı.
- `ModelPortfolioService` public facade API'si dinamik delegasyon helper'ıyla korunarak method-count ihlalinden çıkarıldı.
- `OptimizationService._optimize` fiyat geçmişi doğrulama, return model, ağırlık optimizasyonu ve öneri üretimi helper'larına ayrıldı.
- `SAModelPortfolioRepository` 6 dönüşüm metodu modül düzeyine taşındı (22→16 metod).
- `CurrencySpinBox` dead code kaldırıldı, 5 metod inlined/modül düzeyine taşındı (27→19 metod).
- `NewStockTradeDialog` static wrapper metod kaldırıldı, no-op signal handler kaldırıldı (23→20 metod).
- `ChatbotPanel` 11 metod azaltıldı (31→20 metod); 6 builder modül düzeyine, 4 metod inlined.
- `WatchlistPage` aksiyon buton bloğu `_make_stock_action_cell()` modül fonksiyonuna taşındı.
- `NewStockTradeDialog._init_page1` ve `_init_page2` widget builderları modül düzeyine taşındı.
- `StockDetailPage` 4 builder metodu modül düzeyine taşındı (20→17 metod).
- **violating_classes: 9 → 1** (L10N belgeli istisna)
- Tam suite son doğrulama: `612 passed`.

## Tamamlanan Fazlar (Faz 1-3)

- **Faz 1** (regresyon): `_build_page2_widgets` (83 sat) → 3 sub-builder
- **Faz 2** (UI _init_ui döngüsü): 12 fonksiyon modül düzeyine taşındı (violating_functions 134→122)
- **Faz 3** (application+UI): 14 fonksiyon helper'lara bölündü (src violations 115→90)
- src satır ihlali: **tümü giderildi** (≈0 kaldı)

## Kalan Fazlar

1. **Complexity ihlalleri (49 adet)** — cyclomatic > 10:
   - `get_overview` (cc=17), `_calc_initial_cash_and_positions` (cc=20), `_run_simulation_loop` (cc=10), `compute_beta` (cc=13) vb.
   - Yaklaşım: dallanma bloklarını alt fonksiyonlara çıkar; match/case yerine dict dispatch.
2. **Parametre sayısı ihlalleri (44 adet)** — effective_params > 5:
   - `_bundle_dict` (p=10), `_run_simulation_loop` (p=12), `compute_portfolio_series` (p=8) vb.
   - Yaklaşım: dataclass/TypedDict parametre grubu oluştur; özellikle `portfolio_series_builder`.
3. **Test ihlalleri (14 adet)** — düşük öncelik, mevcut test mantığı bozulmaz.
4. **False-positive / belgeli istisnalar**:
   - `L10N` (797 sat, sınıf) — locale sabitleri, bölünmez; kalıcı istisna.
   - `PortfolioSeriesBuilder` (307 sat, sınıf) — complexity ve param ihlalleri dallanma yoğun simülasyon döngüsünden kaynaklanıyor; DI bağımlılıkları değiştirilmeden parametre azaltımı kısıtlı.
   - scripts/5 — tek seferlik migration araçları, dokunulmaz.

## Çalışma Kuralları

- `git add .` veya `git add -A` kullanılmaz.
- Commitler Türkçe ve `GOVERNANCE.md` formatına uygun yazılır.
- Python komutlarında yalnız `C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe` kullanılır.
- Kullanıcı değişiklikleri geri alınmaz.
- UI metinleri `L10N` dışına çıkarılmaz.
- Her refactor dilimi sonrası ölçüm script'i ve hedefli testler çalıştırılır.

## Devam Komutları

```bash
C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe scripts\measure_code_quality.py
C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe -m pytest tests/application -q
C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe -m pytest tests/ui/test_refactor_guards.py -q
C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe -m pytest tests -q
```

## Faz 1 Kabul Kriterleri

- Application katmanında yeni eşik ihlali oluşmaz.
- `ModelPortfolioService` sınıf ihlali kalktı.
- `OptimizationService._optimize` eşik altına indi.
- Baseline MD/JSON ve bu handoff sayfası güncel kalır.
