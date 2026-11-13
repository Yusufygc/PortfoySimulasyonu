> Ana sayfa: [index.md](index.md) | Kurumsal aksiyonlar: [service_corporate_actions.md](service_corporate_actions.md) | Önceki denetim: [system_audit_report_2026-11-04.md](system_audit_report_2026-11-04.md)

# Backend Denetimi (2026-11-07): Hesaplamalar, Veri Kaynakları, Bölünme Otomasyonu

Kapsam: servisler ve hesaplamalar (portföy, TWR, risk metrikleri, optimizasyon, backtest, göstergeler, bilanço metrikleri), veri kaynakları (Yahoo, TradingView Scanner, EVDS) ve iki fiyat deposunun (SQLite, DuckDB) tutarlılığı. Bulgular gerçek veri (salt okunur), canlı Yahoo/TradingView karşılaştırması ve küçük deneme betikleriyle doğrulandı. Önceki denetimlerin (10-04, 11-04) yapısal konularını tekrarlamaz.

## Özet

| # | Bulgu | Öncelik | Sonuç |
|---|---|---|---|
| 1 | SDTTR 11:1 bölünme SQLite'ta yok; model portföy 9 (65 lot @242) %-93 sahte zarar. Bölünme tespiti yalnızca DuckDB kırılmasına bakıyordu, DuckDB Yahoo'nun düzelttiği geçmişi tuttuğu için kırılma görünmüyordu | 🔴 | Çözüldü: otomatik bölünme servisi (aşağıda). Gerçek DB'ye uygulanması kullanıcı onayı bekliyor |
| 2 | SQLite `daily_prices` iki tür fiyat karışık: senkron ham, sağlık/backfill temettü-düzeltmeli (`auto_adjust=True`). 56.413 çakışan satırın 6.914'ü DuckDB'den >%0,5 farklı | 🔴 | Çözüldü (kod): yazıcılar ham `Close`. Veri onarımı `scripts/rebuild_sqlite_prices.py` (kopyada 6.914 -> 1.043; betik Plan B2'de kaldırıldı, yerini `PriceProjectionService` aldı) |
| 3 | DuckDB'de 81.294 hayalet bar (bayram, hacimsiz sabit); göstergeleri, kovaryansı ve mumları bozuyordu | 🟠 | Çözüldü (kod): `bar_quality` üç indiriciye bağlı. Temizlik `scripts/clean_ghost_bars.py` (81.154 bar) |
| 4 | TWR: nakitten büyük alımda kırpma (sabit fiyatta TWR 100 -> 600) | 🟠 | Çözüldü: açık dış akış sayılır |
| 5 | Başlangıç nakdinde komisyon yok; değer başlangıç tarihine göre değişiyordu | 🟡 | Çözüldü |
| 6 | Optimizasyon log getiriyi beklenen getiri sayıyordu (σ²/2 kadar düşük) | 🟡 | Çözüldü: basit günlük getiri |
| 7 | Altın/gümüş Yahoo sembolleri 404; USD/TRY yoksa USD verisi TL etiketiyle dönüyordu | 🟡 | Çözüldü: `GC=F`/`SI=F` x `TRY=X`, boş seri + uyarı; mevduat yedeği ayardan |
| 8 | Bilanço: eksik çeyrekte YTD çeyreklik sayılıyordu; ROE/ROA yıl başından bugüne | 🟡 | Çözüldü: ardışık 4 çeyrek, TTM net kâr |
| 9 | Grafik ve göstergeler 2 haneye yuvarlanıyordu (düşük fiyatlı hissede MACD 0,00) | 🟢 | Çözüldü: 10 TL altı 4 hane |
| 10 | Beta/R²/izleme hatası tatil günlerini atlamıyordu (oynaklık atlıyordu) | 🟢 | Çözüldü |
| 11 | TÜFE ayı açıklanmadan uygulanıyordu (ileriye bakma) | 🟢 | Çözüldü: M+1 ayından itibaren |
| 12 | Yedek kapanış zamanı İstanbul'dan UTC'ye dönüştürülmeden etiketleniyordu | 🟢 | Çözüldü |
| 13 | `adjust_prices_before_date` yalnızca kapanışı ölçekliyordu (OHLC ham kalıyordu) | 🟢 | Çözüldü |
| 14 | Kurumsal aksiyon yalnızca ana portföye uygulanıyordu; model portföy hiç düzeltilmiyordu | 🔴 | Çözüldü: manuel bedelsiz de bölünme uygulayıcısını kullanır |
| 15 | BIST takvimi 20.06.2024'ü tatil sayıyordu (553 hisse hacimli işlem görmüş); 2023 deprem kapanışı yoktu | 🟡 | Çözüldü; takvim 2020+ hacim verisiyle karşılaştırıldı |

Doğru bulunanlar: ortalama maliyet ve gerçekleşen K/Z, TWR ana yolu, para birimi (USD/reel) çevrimi, RSI/ATR/ADX/Bollinger/Supertrend (TradingView uyumlu). TradingView Scanner evreni 626, DuckDB 624 (eksik: ALTIN, DMLKT). Yahoo son kapanış ve hacmi TradingView ile 68/68 hissede örtüştü. Uygulama TradingView'den fiyat çekmez; yalnızca hisse listesini alır, grafik Lightweight Charts kütüphanesidir.

## Otomatik bölünme servisi

- **Sinyaller:** Yahoo `Ticker.splits`, KAP bedelsiz adayları, fiyat kırılması (DuckDB ham seride kalıcı kırılma; SQLite ile DuckDB düzeltilmiş geçmişi arasında kalıcı basamak).
- **Uzlaşı:** aynı hisse için 7 takvim günü ve %2 çarpan toleransı tek olay. En az iki kaynak -> otomatik; tek kaynak -> aday. Ex-date önceliği KAP > fiyat kırılması > Yahoo (Yahoo SDTTR'yi 6 gün geç tarihledi); çarpan önceliği KAP > Yahoo > kırılma. Ters bölünme ve bedelli otomatik uygulanmaz.
- **Uygulama:** ana portföy, model portföyler ve Portföyüm (ABD hissesi) işlemleri tek SQLite işleminde; küsurat lot ex-date sonrası ilk kapanışla `FRACTION` nakdi olur (dış akış değil). SQLite fiyat geçmişi yalnızca seri kırılmayı gerçekten gösteriyorsa düzeltilir (çift düzeltme yok). Geri alma tam: işlemler, nakit, fiyatlar, DuckDB kaydı.
- **Tetik ve arayüz:** açılışta günde bir kez; Ayarlar > Kurumsal Aksiyonlar > Hisse Bölünmeleri (otomatik uygula anahtarı, Şimdi Tara, Geri Al).

Kopyada çalıştırma (2026-11-07): SDTTR otomatik uygulandı (model işlem 715 lot @22,0000; 904 eski fiyat ölçeklendi), MERKO zaten uygulanmış tanındı, ADESE/ALTNY/BORSK/CEMZY/OBAMS tek kaynaklı aday.

## Veri onarımı (gerçek veritabanı)

Sıra: (1) uygulamada bölünme taraması (SDTTR) veya kopyadaki aynı çalıştırma, (2) `python scripts/clean_ghost_bars.py --execute`, (3) `python scripts/rebuild_sqlite_prices.py --execute` (2026-11-07'de uygulandı; betik sonra Plan B2'de kaldırıldı, SQLite artık her senkronda DuckDB'den yansıtılır). Betikler varsayılan olarak kuru çalışır ve uygulamada yedek alır. Kopyada sonuç: uyuşmazlık 6.914 -> 1.043, tek günlük >%60 kırılma yok, kalan hacimsiz sabit bar 142.

## Açık kalanlar

- **RUZYE:** SQLite 2019 öncesi geçmişi ~0,76 faktörle düzeltilmiş, DuckDB'deki 2019-03-18 olayı aday (onaysız). Ayarlar > Piyasa Düzeltmeleri'nden onaylanınca yansıtma onu da eşitler; `SinglePriceSourceMigration` 2021 öncesi faktörü içe alamaz (DuckDB'de kırılma yok), raporlar.
- **Takvim 2027 ve 2030 Kurban kayıtları** 2024'teki hatayla aynı kalıbı taşıyabilir (bayram 1. günü Pazar); açıklanınca doğrulanmalı.
- **Tek kaynaklı bölünme adayı onayı** artık ana ve model portföyü düzeltir; varlık defteri (ABD hissesi) adayı yalnızca raporlanır, onay arayüzü yok.
- **Mevduat endeksi** brüt faizle günlük bileşik (stopaj yok); arayüz notu eklenmedi.
- Tam test paketinde aralıklı Windows yerel çökmesi (Qt kaynaklı olası) görüldü; yeniden koşuda geçiyor.
