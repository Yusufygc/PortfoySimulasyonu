# Refactor Handoff - 2026-06-13

> Ana sayfa: [index.md](index.md) | Guardrail: [code_quality_guardrails.md](code_quality_guardrails.md) | Baseline: [code_quality_baseline_2026-06-13.md](code_quality_baseline_2026-06-13.md)

Bu sayfa, sağlık raporu tabanlı refactor çalışmasının başka bir ajan veya geliştirici tarafından güvenli biçimde sürdürülebilmesi için oluşturuldu.

## Amaç

Production kodunda sağlık baseline raporuyla doğrulanmış sınıf, fonksiyon ve complexity ihlallerini davranış değiştirmeden azaltmak. Refactor kararlarında `PortfoySimulasyonu_saglik_raporu.html` tek kaynak kabul edilmez; `scripts/measure_code_quality.py` çıktısı ve [code_quality_guardrails.md](code_quality_guardrails.md) kuralları esas alınır.

## Güncel Durum

- Branch: `refactor`
- Son önemli commitler:
  - `b6d8bf8` - İlk kalite baseline ihlali azaltımı
  - `b9dd891` - Refactor handoff ve devam notu
  - `75edccd` - Kalan sınıf ihlallerini gider; violating_classes=4→1
- Güncel baseline metrikleri (2026-06-14):
  - **Sınıf ihlali: `1`** (yalnızca `L10N` — belgeli istisna)
  - Fonksiyon/metot ihlali: `134`
  - Health report crosswalk: `84/84`
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

## Kalan Fazlar

1. Application servisleri (opsiyonel — sınıf ihlali kalmadı):
   - `CorporateActionService` bedelli/bedelsiz hesaplarını calculator/builder helper'larına ayır.
   - `PriceDataHealthService` DTO, scope resolver, analyzer ve updater yüzeylerini modül bazında ayır.
   - `OptimizationService.__init__` parametre sayısı guard ihlali mevcut davranış ve DI sözleşmesi nedeniyle ayrıca değerlendirilmeli.
2. Fonksiyon/metot ihlalleri (134 adet, ikincil öncelik):
   - >50 satır fonksiyonlar; en büyükleri: UI page load metodları, AI yanıt işleyiciler.
3. False-positive değerlendirmeleri:
   - `L10N` kalıcı istisna olarak belgeli kalır.
   - Repository method-count uyarıları interface yüzeyi nedeniyle ayrıca değerlendirilmeli.

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
