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
| `model_portfolios` | Gerçek portföy dışında, sanal (test) amaçlı hedef ağırlıkları saklar. |
| `risk_profiles` | Risk anketindeki kullanıcı yanıtlarını ve finansal profilleri barındırır. |
| `corporate_actions` | Temettü veya bölünme gibi işlemleri tutar. |
| `budgets` | Tasarruf ve hedef bütçelerini tanımlar. |
| `watchlists` | Kullanıcının ana portföyde olmadığı halde takip etmek istediği hisse listeleridir. |

## 3. İlklendirme ve Migration

İlk çalıştırmada `database_engine.py` üzerinden MySQL/SQLite motoruna bağlanılır ve ORM modelleri otomatik olarak tabloları oluşturur (`metadata.create_all()`). Alembic veya benzeri ağır migration toollarından ziyade, uygulamanın esnek yapısı gereği modeller kendi tablolarını doğrudan oluşturacak şekilde yapılandırılmıştır. (Gelecekteki ölçeklenme planlarında Alembic eklenebilir).

## Faz 3 Notu (2026-06-02)

- SQLAlchemy repository yazma yollarında tekrar eden `commit/rollback/refresh` blokları `commit_or_rollback` ve `commit_refresh_or_rollback` helper'larına taşındı.
- Repository tarafında kontrolsüz `except Exception` kullanılmıyor; DB transaction rollback davranışı `SQLAlchemyError` ailesiyle sınırlandı.
- `SQLAlchemyModelPortfolioRepository` içindeki ulaşılamayan ORM mapper kodu gerçek `_to_orm_portfolio` metoduna taşındı ve regression testi eklendi.
- `SQLAlchemyRiskProfileRepository` legacy schema fallback'i bilinçli istisna olarak korunur; raw SQL yalnız eski `risk_profiles` şeması uyumluluğu için kullanılır.
