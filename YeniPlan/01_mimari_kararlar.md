# 01 — Mimari Kararlar

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md) | Önceki: [00_vizyon_ve_kapsam.md](00_vizyon_ve_kapsam.md) | Sonraki: [02_varlik_defteri.md](02_varlik_defteri.md)

Durum: **Onaylı**

## 1. Kullanıcı Kararları

| Konu | Karar | Gerekçe |
|---|---|---|
| Saklama | **Ayrı defter** (model portföy örüntüsü) | Mevcut `trades`/`stocks` hattı BIST + TRY + tam sayı lot varsayıyor; ona dokunmak TWR, nakit, optimizasyon, Excel, AI araçları ve senkronizasyonu etkiler |
| Portföyüm görünümü | **Tek toplam + sınıf sekmeleri** | Tümü / BIST / ABD Hisse / Kripto / Emtia sekmeleri; üstte birleşik toplam |
| Para birimi | **TRY ana + USD anahtarı** | Varlık kendi para biriminde de gösterilir |
| Haber kaynakları | **KAP + yfinance + Türkçe RSS**, Ayarlar'da kaynak bazlı aç/kapa | Her kaynağın kapsamı ve güvenilirliği farklı |

## 2. Varsayılan Kabuller

İtiraz edilmezse bu kabullerle ilerlenir.

1. **Sayfa indeksi:** Portföyüm, `Main.qml` StackLayout'ta sona (indeks 10) eklenir; Sidebar'da 2. sıraya konur. Bu sayede kod tabanındaki 9 adet `navigateTo(0)` çağrısı kaymaz (grafik Genel Bakış'ta kaldığı için hedef hâlâ geçerli).
2. **Nakit bağı yok:** Varlık defteri BIST TRY nakit defterine bağlanmaz; alım BIST nakdini düşürmez. Tek TRY nakit defteri varken USD varlık alımının finansmanı ayrı bir soru açar. İleride "varlık nakdi" ayrı eklenebilir.
3. **v1 analiz sınırı:** Birleşik TWR, risk, optimizasyon, Excel ve AI araçları yalnızca BIST portföyünde kalır.
4. **Grafik:** Genel Bakış grafiği global sembolleri de çizer; BIST veri yolu bozulmaz, sınıf bazlı ikinci veri yolu eklenir.
5. **Vadeli kontrat notu:** `GC=F`, `SI=F`, `PL=F` vadeli kontrat fiyatıdır; spot'tan küçük sapma gösterebilir. Arayüzde not düşülür.

## 3. Değerlendirilen Alternatif

**A. Mevcut `stocks`/`trades` hattını genişletmek** (`asset_class`, `currency_code`, kesirli `quantity`, çok para birimli nakit): Tek defter olur ama şunlar kırılır veya değişir:

- Ticker/sembol: `to_yf_symbol` her şeye `.IS` ekler; `AAPL` → `AAPL.IS`, `BTC-USD` → `BTC-USD.IS`.
- `uq_stocks_ticker`: aynı sembol iki sınıfta kullanılamaz (BIST'te `LINK`, `SILVR` gibi kodlar var).
- `trades.quantity` `BigInteger` ve `total_amount` üretilmiş sütun; SQLite'ta ALTER ile değişmez, tablo yeniden kurulumu gerekir.
- `PortfolioService` tek TRY nakit defteri; `TradeEntryService` BIST doğrulaması ve BIST seans kuralı zorunlu kılar.
- `PriceDataHealthService`, `LivePriceRefreshService`, `MarketDataSyncService` yeni sınıfları BIST kurallarıyla işler.

**Seçilen: B. Ayrı defter.** Ana BIST portföyüne dokunmaz. `AnalysisSourceResolver` zaten "dashboard" ve "model:N" kaynak kodlarıyla çoklu kaynağı destekler; v2'de yeni kaynak kodu eklenebilir.

## 4. Mimari İlkeler

- Clean Architecture bağımlılık yönü korunur: UI → Application → Infrastructure → Domain.
- Controller'lar yalnızca application/domain katmanına bağlanır (`tests/ui_qml/test_architecture_guards.py`).
- Parasal hesaplar `Decimal` ile yapılır.
- Türev değerler (K/Z, getiri) veritabanında saklanmaz; defter işlem geçmişinden yeniden hesaplanır (event-sourced).
- Ağ çağrıları ana UI iş parçacığında yapılmaz; `ThreadPoolExecutor` + Qt Signal kalıbı kullanılır.
- Yeni davranış `DashboardController` içine eklenmez (zaten kalite eşiğinin üstünde); yeni controller'lar ayrıdır.
- Kullanıcıya görünen metinler `Strings.qml` içinde, emoji yok, ikonlar `Icons.qml` + SVG.

## 5. Riskler

| Risk | Önlem |
|---|---|
| KAP şirket bazlı bildirim uç noktası çalışmayabilir | Aşama 6 öncesi spike; best-effort geri düşüş; kullanıcıya açık bildirim |
| yfinance haberi İngilizce ağırlıklı, BIST kapsamı zayıf olabilir | Kaynak etiketi ve dil rozeti; Ayarlar'dan kapatılabilir |
| Yahoo oran sınırı | `YFinanceGate` + `retry_call`, TTL önbellek, tek işçi |
| `DashboardController` eşik üstü | Yeni davranış oraya eklenmez |
| Sayfa bölünmesinde regresyon | Aşama 1 salt taşıma; mevcut testler + görsel anlık görüntü |
| Kur veya fiyat eksikliğinde yanlış toplam | Eksik veri açıkça işaretlenir, toplam "kısmi" etiketli |
| Vadeli kontrat spot'a eşit değil | Arayüz notu; ileride spot sembol alternatifi |
| Sembol çakışması (BIST kodu ile yabancı sembol) | `(asset_class, symbol)` benzersizliği |

## 6. Açık Sorular

Şu an açık soru yok. Aşama 6 spike'ı sonucunda KAP ve RSS kaynak seçimi için karar notu eklenecek (bkz. [05](05_genel_bakis_ve_haber.md)).
