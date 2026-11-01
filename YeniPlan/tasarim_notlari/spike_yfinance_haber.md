# Spike: yfinance haberleri ve Yahoo / Google News alternatifleri

> Ana sayfa: [../index.md](../index.md) | Günlük: [../log.md](../log.md) | Not dizini: [README.md](README.md)

Durum: **Tamamlandı** (2026-11-01). Sonuç: **`yfinance` haber API'si çalışmıyor**; yerine sembol bazlı RSS kullanılacak.

## 1. Soru

Plan §05: `yfinance.Ticker.get_news` / `Search.news` ile `.IS` hisseleri, ABD hisseleri, kripto ve emtia için haber alınabilir mi?

## 2. Sonuç: yfinance haber çağrıları boş dönüyor

`yfinance==1.7.0`: `THYAO.IS`, `GARAN.IS`, `AAPL`, `BTC-USD`, `GC=F`, `^XU100`, `TRY=X` için `get_news()` her seferinde **0 haber** döndü; `Search("THYAO").news` de boş. Hata fırlatılmıyor. Ayrıntı günlüğünde sebep görünüyor: kütüphanenin kullandığı `https://finance.yahoo.com/xhr/ncp?queryRef=latestNews&serviceKey=ncp_fin` adresi **HTTP 404** veriyor (tüm sekmeler: `news`, `all`, `press releases`). Yahoo bu uç noktayı kaldırmış; kütüphane 404'ü sessizce boş listeye çeviriyor.

Çıkarım: `YFinanceNewsProvider` (plan §05) **yazılmayacak**. Sessiz boş dönüş nedeniyle "kaynak açık ama haber yok" ile "kaynak bozuk" ayırt edilemez; yeni sağlayıcılar HTTP durumunu açıkça denetlemeli.

## 3. Alternatif 1: Yahoo Finance sembol RSS

`https://feeds.finance.yahoo.com/rss/2.0/headline?s={SEMBOL}&region={US|TR}&lang={en-US|tr-TR}` çalışıyor:

| Sembol | Öğe | En yeni | Dil |
|---|---|---|---|
| `AAPL` | 18 | gün içi | İngilizce |
| `BTC-USD` | 19 | gün içi | İngilizce |
| `GC=F` | 17 | gün içi | İngilizce |
| `THYAO.IS` | 14 | 3 gün önce | İngilizce (dünya basını kaynaklı) |

Yorum: ABD hisseleri, kripto ve emtia için iyi bir şirket/varlık haberi kaynağı. BIST için seyrek ve İngilizce; BIST için KAP ve Google News daha uygun. Resmî olarak belgelenmemiş bir adres; kapanabilir.

## 4. Alternatif 2: Google News RSS (arama)

`https://news.google.com/rss/search?q={SORGU}&hl=tr&gl=TR&ceid=TR:tr`:

| Sorgu | Öğe | Not |
|---|---|---|
| `THYAO` | 100 | Türkçe, hisse analizi ve haber karışık |
| `gram altın` | 92 | Türkçe |
| `bitcoin` | 92 | Türkçe |

Yorum: Türkçe ve varlık bazlı tek geniş kaynak; her öğenin başlığında yayıncı adı geliyor, bağlantı Google yönlendirmesi. Sorgu kalitesi sembole göre değişir (`THYAO` yerine `"Türk Hava Yolları" OR THYAO` daha iyi olabilir; BIST kodları bazen alakasız eşleşir). **Dikkat:** Google News RSS kişisel/ticari olmayan okuyucu kullanımına yöneliktir; bu uygulama kişisel masaüstü aracı olsa da koşullar ve olası hız sınırı Ayarlar'da açıklanmalı, varsayılan açık/kapalı kararı kullanıcıya bırakılmalı (bkz. [../01_mimari_kararlar.md](../01_mimari_kararlar.md) §6).

## 5. Tasarım Kararları (öneri)

- `YFinanceNewsProvider` yerine `YahooRssNewsProvider` (sembol bazlı, İngilizce) ve `GoogleNewsRssProvider` (arama, Türkçe).
- Sembol → sorgu eşlemesi sağlayıcıda: ABD hissesi/kripto/emtia için Yahoo sembolü (`Asset.yf_symbol`), BIST için Google News sorgusu (kod + şirket adı).
- Her sağlayıcı HTTP durumunu denetler; 4xx/5xx ve boş gövde "kaynak hatası" olarak raporlanır (sessiz boş dönüş yok).
- Haber başlıkları dilleriyle etiketlenir (`tr` / `en`).
