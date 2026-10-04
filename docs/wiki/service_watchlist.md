# İzleme Listesi (Watchlist)

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Sayfa: [qml_pages_guide.md](qml_pages_guide.md)

Kullanıcının portföyüne henüz eklemediği ama takip ettiği hisseler için birden çok liste. Kod: `src/application/services/watchlist/watchlist_service.py`, `src/domain/models/watchlist.py`, `src/ui_qml/controllers/watchlist_controller.py`.

## 1. Modeller ve Tablolar

| Tablo | Alanlar |
|---|---|
| `watchlists` | `name`, `description`, `sort_order`, zaman damgaları |
| `watchlist_items` | `watchlist_id`, `stock_id`, `notes`, `added_at`; `(watchlist_id, stock_id)` benzersiz |

Liste silinince öğeleri de silinir (CASCADE).

## 2. Servis (`WatchlistService`)

Liste CRUD (`get_all_watchlists`, `create_watchlist`, `update_watchlist`, `delete_watchlist`), sıralama (`reorder_watchlists(ids)`), hisse işlemleri (`get_watchlist_stocks`, `add_stock_to_watchlist`, `add_stock_by_ticker`, `remove_stock_from_watchlist`, `update_watchlist_item_notes`, `get_watchlist_item_count`). `add_stock_by_ticker` kodu kanonik biçime çevirir (`THYAO.IS` -> `THYAO`), 15 karakterden uzun kodu reddeder ve hisse `stocks`'ta yoksa oluşturur.

## 3. Arayüz Davranışı

- **Listeler:** sol panelde liste kartları, sürükle-bırak sıralama, oluşturma/düzenleme/silme (`ManageWatchlistModal`). Başlıkta yükselen/düşen hisse sayısı.
- **Hisse ekleme** (`AddStockModal`): kod doğrulanır. SQLite'ta kayıtlı veya DuckDB kataloğunda (tüm BIST) bilinen kod doğrudan eklenir; bilinmeyen kod arka planda çevrimiçi doğrulanır (`StockLookupService.verify_ticker_online`); geçersizse "Geçersiz hisse kodu: X" gösterilir ve kayıt oluşmaz.
- **Tablo** (`WatchlistTableModel`): son fiyat ve günlük değişim, son ~10 kapanışlık mini sparkline (`MiniSparkline`, Canvas), hisse notu (`EditStockNoteModal`). Fiyat ve seriler `StockLookupService` toplu okumasıyla gelir (DuckDB/SQLite); canlı fiyat önbelleği (`latest_prices`), Ana Sayfa ile aynı kuralla (`CurrentPriceResolver.live_applies`) uygulanıyorsa `watchlist_pricing.py` ile günlük barların üzerine bindirilir (denetleyicinin kendisi ağ çağrısı yapmaz; canlı fiyatı `LivePriceRefreshService` yazar). Başlık ve satırlar aynı sabit sütun genişliklerini kullanır.
- **Fiyat yenileme:** `refreshPrices` yalnızca DB'den yeniden okur (ağ yok); `PriceRefreshController.pricesChanged` ile her fiyat yazımından (canlı yenileme, kapanış senkronu, açılış tamamlama) sonra kendiliğinden çalışır. Ekranda ayrı yenile düğmesi yoktur; başlıktaki `PriceStatusChip` ortak son güncellemeyi ve küçük yenile ikonunu gösterir. Sistem sıfırlanınca listeler yeniden yüklenir.
- Satırdan **hızlı işlem** (`QuickTradeModal`) ve hisse detayı açılabilir.

## 4. Sınırlar

Hedef fiyat takibi ve hedef fiyata ulaşınca bildirim yoktur. Watchlist hisseleri fiyat sağlığı (eksik gün tamamlama) kapsamına girmez ama canlı fiyat yenilemesine dahildir (varsayılan sağlık kapsamı açık pozisyonlardır; bkz. [service_portfolio_and_market.md](service_portfolio_and_market.md)); izleme listesi hisselerinin fiyatı DuckDB'deki tüm BIST verisinden gelir.

## 5. Testler

`tests/application/test_watchlist_service.py`, `tests/ui_qml/test_watchlist_phase4.py`, `test_watchlist_ticker_validation.py`, `test_reorder.py`.
