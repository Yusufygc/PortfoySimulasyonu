# Veritabanı Şeması ve SQLAlchemy ORM

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, uygulamanın `src/infrastructure/db/sqlalchemy` dizini altındaki veritabanı yapısını detaylandırır.

## 1. Veritabanı Yaklaşımı ve Repository Pattern

Uygulamanın çekirdek kodları (Domain) SQL veya MySQL teknolojisinden tamamen bağımsızdır. `src/domain/ports/repositories` altında tanımlı soyut arayüzler (Interfaces), SQLAlchemy Repository'leri tarafından `src/infrastructure` içinde somutlaştırılır.

Bu sayede, ileride veritabanı SQLite veya PostgreSQL ile değiştirilmek istenirse sadece Infrastructure katmanında değişiklik yapılması yeterli olacaktır.

## 2. Tablo Şeması Özetleri (`orm_models.py`)

Aşağıda SQLAlchemy Declarative Base ile oluşturulan ana tablolar listelenmiştir:

| Tablo Adı | İçerik ve İşlev |
| --- | --- |
| `stocks` | Hisselerin (Varlıkların) ana kimlik bilgilerini (Ticker, İsim, Para Birimi) tutar. |
| `trades` | Alım/Satım işlemleri. Miktar, fiyat, tarih ve varlık referansını içerir. |
| `daily_prices` | Zaman serisi fiyatları. Hissenin günlük kapanış değerini tutar. |
| `latest_prices` | Hisse başına tek satır intraday/latest fiyat cache'i. UI güncel değerlemeleri içindir; tarihsel rapor ve backtest kaynağı değildir. |
| `model_portfolios` | Gerçek portföy dışında, sanal (test) amaçlı hedef ağırlıkları saklar. |
| `risk_profiles` | Risk anketindeki kullanıcı yanıtlarını ve finansal profilleri barındırır. |
| `corporate_actions` | Temettü veya bölünme gibi işlemleri tutar. |
| `budgets` | Tasarruf ve hedef bütçelerini tanımlar. |
| `budget_items` | Aylık bütçeye bağlı gelir/gider kalemlerini tutar. |
| `budget_pinned_items` | Boş aylara otomatik taşınan tekrar eden gelir/gider başlıklarını ve varsayılan tutarlarını saklar. |
| `watchlists` | Kullanıcının ana portföyde olmadığı halde takip etmek istediği hisse listeleridir. |

## 3. İlklendirme ve Migration

İlk çalıştırmada `database_engine.py` üzerinden MySQL/SQLite motoruna bağlanılır ve ORM modelleri otomatik olarak tabloları oluşturur (`metadata.create_all()`). Alembic veya benzeri ağır migration toollarından ziyade, uygulamanın esnek yapısı gereği modeller kendi tablolarını doğrudan oluşturacak şekilde yapılandırılmıştır. (Gelecekteki ölçeklenme planlarında Alembic eklenebilir).

## Faz 3 Notu (2026-06-02)

- SQLAlchemy repository yazma yollarında tekrar eden `commit/rollback/refresh` blokları `commit_or_rollback` ve `commit_refresh_or_rollback` helper'larına taşındı.
- Repository tarafında kontrolsüz `except Exception` kullanılmıyor; DB transaction rollback davranışı `SQLAlchemyError` ailesiyle sınırlandı.
- `SQLAlchemyModelPortfolioRepository` içindeki ulaşılamayan ORM mapper kodu gerçek `_to_orm_portfolio` metoduna taşındı ve regression testi eklendi.
- `SQLAlchemyRiskProfileRepository` legacy schema fallback'i bilinçli istisna olarak korunur; raw SQL yalnız eski `risk_profiles` şeması uyumluluğu için kullanılır.

## Bütçe Pinleme Notu (2026-06-03)

- `budget_pinned_items`, `item_type + name` benzersizliğiyle tekrar eden gelir/gider şablonlarını saklar.
- Aylık kayıtlar yine `budgets` ve `budget_items` üzerinde kalır; pinli şablonlar yalnız bütçesi olmayan aylar için form taslağı üretir.
- Repository başlangıcında tablo `checkfirst=True` ile oluşturulur; mevcut bütçe kayıtları migrate edilmez veya değiştirilmez.

## Kurumsal İşlemler ve İşlem Düzeltme Notu (2026-06-04)

- `trades` tablosuna `original_quantity` ve `original_price` kolonları eklendi.
- Kurumsal işlemler uygulandığında düzeltme geçmişini (factor, pre_quantity, post_quantity, pre_price, post_price) denetim izli olarak saklayan `trade_adjustments` tablosu oluşturuldu.
- Düzeltilen işlemler için `trades.quantity` ve `trades.price` kolonları bölünmüş değerleri tutarken, orijinal işlem bilgileri `trades.original_quantity` ve `trades.original_price` kolonlarında salt-okunur şekilde korunur.

## Latest Fiyat Cache Notu (2026-06-06)

- `latest_prices` tablosu `stock_id` üzerinde unique constraint ve `stocks.id` FK ile tanımlanır; bir hisse için yalnız son canlı/latest fiyat saklanır.
- Alanlar: `price`, `as_of`, `source`, `provider`, `fetched_at`, `updated_at`. `updated_at` upsert sırasında DB tarafında yenilenir.
- `SQLAlchemyLatestPriceRepository`, `ILatestPriceRepository` portunu uygular ve 15 dakikalık canlı yenileme ile model portföy manuel fiyat güncellemelerinin kalıcı cache yazma yoludur.
- Migration için `scripts/apply_latest_prices_schema.py` vardır; mevcut `daily_prices` kapanış verisi migrate edilmez veya değiştirilmez.

