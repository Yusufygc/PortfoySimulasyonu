# Veritabanı Bakımı ve Scriptler

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, `src/application/services/database/db_integrity_service.py` ve projedeki `scripts/` klasörünün operasyonel işlevlerini belgeler. 

Bir uygulamanın zamanla kirlenen verilerini (bozuk trade'ler, yanlış girilmiş nakit bakiye) onarmak ve sistemi kararlı tutmak için bakım (maintenance) scriptlerine ihtiyaç vardır.

## 1. Veritabanı Bütünlük Servisi (`DbIntegrityService`)

Event-Sourced sistemlerde işlem zinciri birbirine bağlıdır. Eğer bir hissede elde yeterli lot olmadan "Satış" (SELL) girilmişse veya nakit eksiye inmişse, bu ilerideki kâr/zarar hesaplamalarını patlatır.

`DbIntegrityService` şunları kontrol eder:
- **Eksik veya Hatalı Trade'ler:** Orijinali olmayan bir hissenin satılıp satılmadığı.
- **Nakit ve Lot Yetersizliği:** Trade_Entry_Service tarafından normalde engellenen ama bir şekilde (örneğin SQL ile manuel) veritabanına sızmış geçersiz kayıtlar.
- **Bütünlük Raporu Üretimi:** Sorunlu kayıtları listeler. UI üzerinden "Bozuk kayıtları yoksayarak güvenli portföy kur" seçeneğini destekleyerek uygulamanın çökmesini engeller.

## 2. Operasyonel Scriptler (`scripts/`)

| Script Adı | İşlevi |
| --- | --- |
| `purge_stock.py` | Belirli bir hissenin (örn. ismi değişmiş veya delist olmuş) tüm işlemlerini, watchlist kayıtlarını, fiyat geçmişini ve model portföy bağlantılarını kalıcı olarak temizler. Çok dikkatli kullanılmalıdır. |
| `clean_db_prices.py` | Eksik fiyat veya 0 değerine inmiş hatalı fiyatları silerek YFinance'in yeniden indirmesini tetiklemek için temizlik yapar. |
| `manual_backfill.py` | Eksik verileri veya özel bir geçmiş aralığı API sınırlamalarına takılmadan (chunking ile) parça parça indirmeye yarar. |
| `dbOlusturmak.sql` vb. | İlk kurulumda otomatik SQL oluşturmaların manuel yedeğidir. |

Uygulamanın uzun süreli sağlığı için, büyük versiyon atlamalarında `db_integrity_service` raporu incelenmeli ve gerekirse bakım scriptleri ile temizlik yapılmalıdır.
