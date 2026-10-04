# Piyasa Geçmişi (DuckDB) Sermaye Artırımı Düzeltmesi

> Ana sayfa: [index.md](index.md) | Portföy aksiyonları: [service_corporate_actions.md](service_corporate_actions.md) | Veri: [data_architecture.md](data_architecture.md) | Arayüz: [settings_and_system.md](settings_and_system.md)

Tüm BIST için (portföyde olsun olmasın) bölünme/bedelsiz/bedelli kaynaklı fiyat kırılmalarının düzeltilmesi.
Kod: `src/domain/models/market_corporate_action.py`, `src/application/services/corporate_actions/market_action_service.py`,
`src/infrastructure/market_data/duckdb_corporate_action_store.py`, `duckdb_market_history_repo.py`.

## İlke

- **Ham barlar değişmez.** yfinance `auto_adjust=False` ile gelen barlar olduğu gibi tutulur; düzeltme `market_corporate_actions`
  tablosundaki faktörlerle okuma anında uygulanır. Geri alınabilir, tekrar indirmeye dayanıklı ve denetlenebilir.
- Düzeltilmiş fiyat = ham fiyat x (kendinden sonraki ONAYLI olayların faktör çarpımı). Etkin gün (`effective_date`) yeni baz fiyattaki ilk bardır.
- Hacim düzeltilmez; yalnızca OHLC.
- Tablo: `ticker, effective_date (PK), factor, action_type, status, source, ex_date, ratio, rights_price, observed_ratio, confidence, note`.
  Durumlar: `CANDIDATE` (onay bekler), `CONFIRMED` (düzeltmeye dahil), `IGNORED`, `NO_BREAK` (ham veride kırılma yok, düzeltmeye dahil değil).

## Faktör formülleri

| Tür | Faktör |
|---|---|
| Bedelsiz (oran r, 1.0 = %100) | `1 / (1 + r)` |
| Bedelli (oran r, kullanım fiyatı K, ex-date öncesi HAM kapanış P0) | `(P0 + r*K) / ((1 + r) * P0)` (TERP/P0) |
| Birleştirme (ters bölünme) | `> 1` (gözlenen oran) |
| Veriden tespit (kaynak belirsiz) | `(yeni kapanış / önceki kapanış) x aynı günkü piyasa medyanı` |

## Veri güdümlü tespit (`MarketCorporateActionService.scan`)

1. `DuckDBMarketHistoryRepository.find_price_breaks`: tek SQL taramasıyla (pencere fonksiyonları) ham seride günlük `önceki/yeni >= 1,25`
   (BIST günlük limiti %10; üstü piyasa hareketi değildir) veya `<= 0,5` (birleştirme) kırılmalar. 2006 öncesi (TL redenominasyonu, bozuk Yahoo geçmişi) taranmaz.
2. **Veri hatası ayıklama:** fiyat sonraki 3 barda önceki seviyeye dönüyorsa (veya önceki bar tek barlık sıçramaysa) aday olmaz.
3. **Piyasa hareketi ayıklama:** aynı gün tüm hisselerin medyan `önceki/yeni` oranı hesaplanır; hisseye özgü oran `>= 1,2` değilse (kriz günleri: Mart 2020, Ağustos 2018) aday olmaz. Faktör piyasa hareketinden arındırılarak yazılır.
4. Hayalet (hacim 0) bar dahil ilk yeni bazlı bar etkin gün olur (MERKO: Yahoo 2026-05-01 tatil gününe yeni bazlı bar yazmış; faktör `0,1354` birebir eşleşti).
5. Güven puanı: iki bar da hacimli +0,2, bar aralığı <= 5 gün +0,2, piyasa medyanı yok -0,2, küçük kırılma -0,2.
6. Adaylar kullanıcı onayına kadar düzeltmeye girmez. Kullanıcı faktörü düzenleyebilir.

Gerçek veri üzerinde: ~8 sn, 289 aday, 194 veri hatası/piyasa hareketi elendi.

## Çift düzeltme koruması (`verify_actions`)

Kaynak sonradan geçmişi düzeltirse (Yahoo gecikmeli bölünme düzeltmesi) ham seride kırılma kaybolur. Her senkronda ONAYLI olaylar
ham veriye karşı doğrulanır; beklenen kırılmanın en az yarısı yoksa olay `NO_BREAK` yapılır ve düzeltmeye dahil edilmez.

## Kaynaklar

- **Ham bar:** yfinance (`auto_adjust=False`). TradingView (`tvdatafeed`) yalnızca ikincil doğrulama adayıydı (istemci ve bağımlılık kullanılmadığı için 2026-10-03'te kaldırıldı; git geçmişinden geri alınabilir): split-düzeltmeli ama temettü-düzeltmesiz, yalnızca kapanış, anonim ve kırılgan; 624 hissede denenmedi.
- **Olay kaynağı:** (1) veri güdümlü tarama, (2) portföy kurumsal aksiyon akışı (`CorporateActionPriceAdjustmentService` uygulanan olayı DuckDB'ye de kaydeder; etkin gün `locate_effective_date` ile ham veriden bulunur), (3) SQLite geçmişinden göç (aşağıda), (4) KAP/MKK adayı onayı.

## SQLite göçü (2026-10-03)

`scripts/migrate_market_universe_to_duckdb.py` (varsayılan kuru çalıştırma, `--execute` yedek alır): kullanıcı verisine bağlı olmayan 133 hissenin
SQLite fiyatları ve kayıtları silindi (305.692 satır; yedek `data/backups/portfolio_pre_universe_migration_*.db`). Silmeden önce SQLite'ın
düzeltilmiş geçmişi ile DuckDB ham geçmişinin farkından, **yalnızca DuckDB ham serisinin kendisi de aynı kırılmayı gösteriyorsa**, 10 geçmiş olay
(`source=MIGRATION`) türetildi. Ham seri zaten sürekliyse (ör. SDTTR, INFO: kaynak Yahoo düzeltmiş, bozuk olan SQLite'tı) olay üretilmez.
