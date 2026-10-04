# Kurumsal Aksiyonlar ve Nakit Temettü

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Piyasa geneli düzeltme: [market_corporate_actions.md](market_corporate_actions.md)

Kod: `src/application/services/corporate_actions/` ve `portfolio/cash_movement_service.py`. Bu sayfa **portföye uygulanan** bedelli/bedelsiz sermaye artırımını, KAP/MKK aday akışını ve nakit temettü kaydını anlatır. Tüm BIST için veriden tespit edilen fiyat düzeltmesi ayrı bir mekanizmadır: [market_corporate_actions.md](market_corporate_actions.md).

## 1. Türler

| Tür | Model | Etki |
|---|---|---|
| Bedelsiz sermaye artırımı | `ActionType.BEDELSIZ` | Lot oranla artar, toplam maliyet sabit kalır, ortalama maliyet düşer. |
| Bedelli sermaye artırımı | `ActionType.BEDELLI` | Lot artar; kullanım fiyatı x yeni lot kadar sermaye toplam maliyete eklenir (nakit tutarı), ortalama maliyet yeniden hesaplanır. |
| Nakit temettü | `CashMovementType.DIVIDEND` | `CorporateAction` **değildir**; lot ve maliyeti değiştirmez, nakde girer (bölüm 5). |

`ActionType` yalnızca bedelli ve bedelsizi kapsar; bölünme (split) portföy aksiyonu olarak modellenmez (piyasa geneli düzeltmede birleştirme/bölünme faktörü vardır).

## 2. Sermaye Artırımı Uygulaması (`CorporateActionService`)

Akış: `register_bedelsiz` / `register_bedelli` aksiyonu kaydeder (`corporate_actions`) -> `apply_action(action_id, current_price)` portföye uygular.

- Uygulama için ex-date'te **açık pozisyon** gerekir; aksiyon daha önce uygulanmışsa veya hesaplanan yeni lot sıfırsa `ValueError` fırlatılır.
- **Yeni pay hesabı** (BIST kuralı): `int(mevcut_lot x oran)` (aşağı yuvarlama). **Teorik baz fiyat** `CorporateAction.theoretical_price(güncel_fiyat)` ile hesaplanır.
- **Geriye dönük düzeltme modeli:** ex-date öncesi işlemlerin lot ve fiyatı faktörle ayarlanır; `trades.original_quantity` ve `original_price` özgün değerleri korur, her değişiklik `trade_adjustments` tablosuna (faktör, önceki/sonraki lot ve fiyat) denetim izi olarak yazılır. Bedelsiz lot katsayısı `1 + oran`, fiyat katsayısı `1 / (1 + oran)`.
- **Sıra güvenliği:** işlem düzeltmesi başarısız olursa aksiyon "uygulandı" işaretlenmez (testle sabitlenmiştir).
- **Fiyat geçmişi düzeltmesi** (`CorporateActionPriceAdjustmentService`): uygulanan aksiyondan sonra SQLite `daily_prices`'ta yalnızca `price_date < ex_date` kayıtları düzeltilir. Bedelsiz katsayısı `1 / (1 + r)`; bedelli katsayısı `(P0 + r*K) / ((1 + r) * P0)` (P0: ex-date öncesi ham kapanış, K: kullanım fiyatı). `corporate_actions` satırında `prices_adjusted`, `prices_adjusted_at`, `price_adjustment_factor`, `price_adjustment_count` alanları **idempotency** sağlar: aynı aksiyon iki kez uygulanmaz. Geçiş günü `_find_price_transition_date` ile gerçek kırılmadan bulunur. Uygulanan olay aynı faktörle DuckDB `market_corporate_actions`'a ONAYLI olarak da kaydedilir (başarısız olursa SQLite düzeltmesi geri alınmaz, yalnızca loglanır).
- Fiyat yeniden indirmelerinde (backfill, sağlık güncellemesi) uygulanmış aksiyonlar dikkate alınarak ham piyasa fiyatı düzeltilmiş yazılır (`adjust_downloaded_series`).

Arayüz: Hisse Detay modalı > **Sermaye Artırımı** (yalnızca ana portföy, açık pozisyon): tür (bedelsiz/bedelli), oran, ex-date, kullanım fiyatı, not; canlı ön izleme (yeni lot, yeni ortalama maliyet, sermaye tutarı, teorik baz fiyat) `compute_preview` ile hesaplanır. Uygulama arka planda çalışır; başarısızsa kaydedilen bekleyen aksiyon silinir. Başarıdan sonra Dashboard ve Model Portföy yenilenir.

## 3. KAP/MKK Aday Akışı

Bedelli/bedelsiz duyuruları önce **aday** olarak kaydedilir; kullanıcı onayı olmadan portföy veya fiyat geçmişi değişmez.

- `CorporateActionDiscoveryService.discover(tickers, start, end)`: `kap_mkk_provider` ile KAP'ın kamuya açık duyuru listesini ve bildirim sayfalarını tarar; hedef ticker'lar portföy, izleme listesi ve model portföy hisseleridir. Uygulanmış bir aksiyonla çakışan adaylar kaydedilmez. Resmi API aboneliği gerekmez (best-effort); kaynak 404/zaman aşımı verirse sonuç `source_unavailable` ve `errors` ile döner, açılış işi iz veya toast üretmez.
- `CorporateActionCandidateReviewService`: yalnızca `READY`/`APPROVED` adaylar `approve_and_apply` ile mevcut `CorporateActionService` üzerinden uygulanır (sentetik düzeltme ve fiyat düzeltme idempotency aynı hattan korunur); `ignore` ve `update_candidate` ile yoksayma/düzenleme.
- Aday tablosu: `corporate_action_candidates` (benzersiz: kaynak, duyuru kimliği, tür, ticker). Eski kayıtların `ticker`'ı `.IS` uzantılı olabilir; aramalar iki biçimi de tolere eder.
- Arayüz: Ayarlar > Kurumsal Aksiyonlar (liste, "KAP/MKK Yenile", kaynak açma, düzenleme, yoksayma, onayla ve uygula). Açılışta günde bir kez otomatik tarama çalışır ([settings_and_system.md](settings_and_system.md)); manuel yenileme, kaynak okunamazsa kısa uyarı gösterir.

## 4. Eksik Veri ve MERKO Örneği

Bedelli artırımda ham fiyat geçmişi düzeltme olmadan grafikte sahte düşüş üretir; bu yüzden fiyat düzeltmesi uygulamanın zorunlu parçasıdır. MERKO için onarım betiği artık yoktur; benzer durumlarda aksiyon Hisse Detay'dan girilir veya Piyasa Düzeltmeleri sekmesindeki aday onaylanır.

## 5. Nakit Temettü Kaydı

- **Model:** `CashMovementType.DIVIDEND`; `cash_movements.stock_id` temettüyü hisseye bağlar (mevcut veritabanlarında açılışta idempotent `ALTER TABLE` ile eklenir). Temettü kaydı bir hisse içermek zorundadır.
- **Nakit ve getiri:** net tutar nakit bakiyeye girer (`adds_cash`) ama **dış sermaye akışı sayılmaz** (`is_external_flow` yanlış). `PortfolioSeriesBuilder` zaman ağırlıklı getiriyi (TWR) temettü kadar yükseltir; aynı tutarda "Nakit Yatır" getiri üretmez. Zaman çizelgesi doğrulayıcısı temettüyü nakit girişi sayar.
- **Servis:** `CashMovementService.add_dividend(stock_id, tutar, tarih, not)`, `get_dividends`, `get_total_dividends`, `delete_dividend`. Kayıt için hissenin o tarihte portföyde pozisyonu olmalı ve tarih gelecekte olmamalıdır. Silme, sonraki alım/çekimi yetersiz nakde düşürüyorsa reddedilir (`PortfolioService.validate_cash_removal`).
- **Arayüz:** Hisse Detay modalı > **Temettü** (yalnızca ana portföy, açık pozisyon): `DividendDialog` ve `DividendController`; net tutar (`1.234,5`, `50.000` biçimleri), tarih, not ve geçmiş listesi/silme. Kayıt veya silme sonrası Dashboard yenilenir. Girilen metin Türkçe sayı ayrıştırıcısıyla okunur.
- **Sınırlar:** Brüt/stopaj hesabı ve otomatik temettü tespiti yoktur; tutar kullanıcıdan net alınır. Model portföy için temettü yoktur. Dashboard "Toplam K/Z" kartı yalnızca pozisyon kâr/zararıdır; temettü getiri grafiklerine ve nakit bakiyeye yansır ([roadmap.md](roadmap.md)).

## 6. Testler

`tests/domain/test_corporate_action.py`, `tests/application/test_corporate_action_service.py`, `test_corporate_action_candidate_services.py`, `test_cash_movement_service.py`, `test_dividend_cash_flow.py`; `tests/infrastructure/db/test_cash_movement_dividend_repository.py`; `tests/ui_qml/test_group2_corporate_price_startup.py`, `test_dividend_controller.py`.
