# Refactor Handoff - 2026-06-13

> Ana sayfa: [index.md](index.md) | Guardrail: [code_quality_guardrails.md](code_quality_guardrails.md) | Baseline: [code_quality_baseline_2026-06-13.md](code_quality_baseline_2026-06-13.md)

Bu sayfa, sağlık raporu tabanlı refactor çalışmasının başka bir ajan veya geliştirici tarafından güvenli biçimde sürdürülebilmesi için oluşturuldu.

## Amaç

Production kodunda sağlık baseline raporuyla doğrulanmış sınıf, fonksiyon ve complexity ihlallerini davranış değiştirmeden azaltmak. Refactor kararlarında `PortfoySimulasyonu_saglik_raporu.html` tek kaynak kabul edilmez; `scripts/measure_code_quality.py` çıktısı ve [code_quality_guardrails.md](code_quality_guardrails.md) kuralları esas alınır.

## Güncel Durum

- Branch: `refactor`
- Son önemli commitler:
  - `9974b61` - Kod kalitesi baseline ve guardrail ölçümü
  - `b6d8bf8` - İlk kalite baseline ihlali azaltımı
- Güncel baseline metrikleri:
  - Sınıf ihlali: `10`
  - Fonksiyon/metot ihlali: `154`
  - Health report crosswalk: `84/84`
- Kirli worktree notu:
  - `app.py` ve bazı `src/ui/...` dosyalarında önceden var olan unstaged UI değişiklikleri bulunuyor.
  - Bu değişiklikler kullanıcıya ait kabul edilir; geri alınmaz ve application Faz 1 commitlerine dahil edilmez.

## Tamamlananlar

- `scripts/measure_code_quality.py` eklendi.
- `docs/wiki/code_quality_baseline_2026-06-13.md` ve JSON baseline üretildi.
- [code_quality_guardrails.md](code_quality_guardrails.md) eklendi.
- `ModelPortfolioTradeService` builder, sıralama ve zaman filtresi helper'ları sınıf dışına taşındı.
- `ChartRenderer` figure üretimi ve dosya adı helper'ları sınıf dışına taşındı.
- `ChartRenderer` UI whitelist'inden çıkarıldı.
- Tam suite son doğrulama: `612 passed`.

## Kalan Fazlar

1. Application servisleri:
   - `ModelPortfolioService` method-count ihlalini kaldır.
   - `OptimizationService._optimize` algoritmasını helper'a taşı.
   - `CorporateActionService` bedelli/bedelsiz hesaplarını calculator/builder helper'larına ayır.
   - `PriceDataHealthService` DTO, scope resolver, analyzer ve updater yüzeylerini modül bazında ayır.
2. Büyük UI sayfaları ve dialoglar:
   - `StockDetailPage`, `WatchlistPage`, `RiskProfilePage`, `NewStockTradeDialog`, `PriceDataPanel`.
3. AI ve analysis karmaşıklıkları:
   - `ChatbotPanel`, `PeerCard`, `PredictionCard`, `AnalysisComparisonSection`, `ai_core_fastapi_client`.
4. False-positive değerlendirmeleri:
   - `L10N` kalıcı istisna olarak belgeli kalabilir.
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
- `ModelPortfolioService` sınıf ihlali kalkar.
- En az `OptimizationService._optimize` veya `CorporateActionService` apply fonksiyonlarından biri eşik altına iner.
- Baseline MD/JSON ve bu handoff sayfası güncel kalır.
