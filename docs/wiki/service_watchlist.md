# İzleme Listesi (Watchlist) Servisi

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, `src/application/services/watchlist` dizinini ve izleme listesi yeteneklerini açıklar.

## 1. Amacı ve Modelleri

Kullanıcıların henüz portföylerine (gerçek parayla) eklemedikleri ancak radarında tutmak istedikleri hisseleri listeledikleri yapıdır. 

Modeller:
- `Watchlist`: Listenin kendisi (İsim, Oluşturulma tarihi vb.)
- `WatchlistItem`: Liste altındaki her bir hisse kaydı. Hisse bazlı açıklama notu (`notes`) ve eklendiği tarih bilgilerini içerir.

## 2. Portföyle Entegrasyon

Watchlist verisi, `analysis` ekranında (özellikle Comparison Lab tarafında) benchmark veya "Potansiyel Hisseler" olarak gösterilebilir. 
İlerleyen aşamalarda `WatchlistService` asenkron `GlobalEventBus` sinyallerini dinleyerek, "prices_updated" event'i tetiklendiğinde hedef fiyata (Target Price) ulaşan hisseler için Toast/Notification üretme yeteneğine sahiptir.

## 3. UI Entegrasyonu

Dashboard veya ayrı bir İzleme Listesi sekmesi üzerinden `WatchlistService` çağrılarak hisseler eklenir/çıkarılır. Fiyat sağlığı (Price Health) paneli, kullanıcının Watchlist'inde olan hisseleri de dikkate alarak YFinance API üzerinden eksik gün tamamlaması yapar. 
Yani Watchlist'e eklenen bir hissenin geçmiş verisi arka planda sistem tarafından otomatik çekilmeye başlanır.

Ayrıca, liste içerisindeki her bir hissenin eylem sütununda (silme butonunun solunda) yer alan kalem ikonu üzerinden hisse notları `EditStockInWatchlistDialog` penceresi aracılığıyla düzenlenebilir.
