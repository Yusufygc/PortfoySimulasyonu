# Kurumsal Aksiyonlar (Corporate Actions) Servisi

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, `src/application/services/corporate_actions` dizini altındaki temettü (dividend), bedelli ve bedelsiz sermaye artırımı gibi varlık tabanlı şirket olaylarını açıklar.

## 1. Temel İşlev

Kurumsal aksiyonlar, bir hissenin portföydeki lot miktarını veya maliyetini doğrudan etkiler. Event-Sourcing (işlem geçmişi) tabanlı portföy modelinde, bu aksiyonların portföy hesaplanırken dikkate alınması hayati önem taşır. Eğer dikkate alınmazsa kullanıcının Kâr/Zarar metrikleri devasa oranda hatalı gözükür (Örn: Hissenin %500 bedelsiz bölünüp fiyatının 6'ya düşmesi).

## 2. Türler ve Hesaplama Mantığı

| Aksiyon Türü | Veritabanı (Type) | Sisteme Etkisi |
| --- | --- | --- |
| **Bedelsiz Sermaye Artırımı** | `STOCK_SPLIT` / `BONUS` | Yatırımcının portföyündeki hisse adedi çarpılır, yeni bir "0 maliyetli" alım (veya ayarlama) gibi sisteme yansıtılır. Toplam maliyet değişmez ama birim ortalama maliyet düşer. |
| **Temettü (Dividend)** | `DIVIDEND` | Hisse başına verilen net nakit temettü, yatırımcının elindeki lot sayısıyla çarpılır ve sisteme "Nakit Girişi" (Cash Inflow) olarak yansıtılır. İstenirse hisse maliyetinden düşülerek de hesaplanabilir. |
| **Bedelli Sermaye Artırımı** | `RIGHTS_ISSUE` | Hisse sayısını artırırken sistemde rüçhan hakkı kullanımı nedeniyle bir "Nakit Çıkışı" (Cash Outflow) üretir. Toplam maliyete eklenir. |

## 3. Mimari Entegrasyon

Kurumsal aksiyonlar doğrudan `CorporateActionService` vasıtasıyla veritabanına (`corporate_actions` tablosuna) kaydedilir. Portföy simülasyonu çalıştırılırken (veya `Portfolio.from_trades` anında), işlemlerin yapıldığı günlerde kurumsal aksiyon olup olmadığı kontrol edilir. Varsa bu matematiksel ayarlamalar pozisyon nesnesinin (`Position`) adet ve maliyet hesaplamalarına "Event" olarak dahil edilir.

```mermaid
graph TD
    A[Trade Geçmişi] --> B(Portföy Hesaplama)
    C[Corporate Actions] --> B
    B --> D{Pozisyon Değerlemesi}
    D -->|Lot Çarpımı| E[Bölünme Ayarı]
    D -->|Maliyet Düşümü| F[Temettü Ayarı]
```
## Faz 2 Notu (2026-06-02)

- `CorporateActionService.apply_action` failure-safe sıraya alındı: action okunur, pozisyon etkisi hesaplanır, sentetik trade insert edilir ve sadece insert başarılı olursa action `applied` işaretlenir.
- Trade insert exception durumunda action applied kalmaması regression testiyle sabitlendi.

## Faz 2D Notu (2026-06-02)

- Bedelli/bedelsiz description ve `CorporateActionResult` üretimi pure helper function'lara taşındı.
- `CorporateActionService` kayıt, sorgu ve action application orchestration sorumluluğunda kalır; public API değişmedi.
