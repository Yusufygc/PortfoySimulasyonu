# Spike: KAP şirket bazlı bildirimler

> Ana sayfa: [../index.md](../index.md) | Günlük: [../log.md](../log.md) | Not dizini: [README.md](README.md)

Durum: **Tamamlandı** (2026-11-01). Sonuç: **kullanılabilir**; iki ön koşul var (kimlik haritası hatası, gürültü süzgeci).

## 1. Soru

Plan §05: KAP'ın şirket bazlı bildirim listesi uç noktası depoda doğrulanmamıştı. Şirket haberi olarak KAP bildirimleri çekilebilir mi?

## 2. Yöntem

KAP sitesi Next.js ile yazılmış. Ana sayfanın JS paketlerinde rota listesi arandı (`api/company-detail/disclosures`, `api/disclosure/members/byCriteria`, `api/disclosure/subjects` ...), ardından aday uç noktalar THYAO KAP kimliğiyle denendi. Betik: [scripts/probe_news_sources.py](../../scripts/probe_news_sources.py) (`kap` bölümü).

## 3. Sonuç

| Uç nokta | Sonuç |
|---|---|
| `POST https://www.kap.org.tr/tr/api/disclosure/members/byCriteria` | **200, çalışıyor.** JSON liste döner |
| `GET /tr/api/company-detail/disclosures/{oid}` | 500 hata sayfası (kullanılamaz) |
| `GET /tr/api/disclosure/subjects` | 404 |
| `https://www.kap.org.tr/tr/rss/bildirim` | 404 (KAP RSS yok) |

**İstek gövdesi** (tarihler **ISO** `YYYY-AA-GG` olmalı; `GG.AA.YYYY` verilirse 500 döner):

```json
{"fromDate": "2026-10-18", "toDate": "2026-11-01", "memberType": "IGS",
 "mkkMemberOidList": ["<KAP kimliği>", "..."], "inactiveMkkMemberOidList": [],
 "disclosureClass": "", "subjectList": [], "isLate": "", "mainSector": "", "sector": "", "subSector": "",
 "marketOidList": [], "index": "", "bdkReview": "", "bdkMemberOidList": [], "year": "", "term": "",
 "ruleType": "", "period": "", "fromSrc": false, "srcCategory": "", "disclosureIndexList": []}
```

Tarih aralığı dışındaki alanlar boş bırakılabilir; yalnızca tarih verilirse tüm piyasanın bildirimleri döner. Gerekli başlıklar: tarayıcı `User-Agent`, `Referer: https://www.kap.org.tr/tr/bildirim-sorgu`.

**Yanıt alanları:** `publishDate` (`GG.AA.YYYY SS:DD:SS`, İstanbul saati), `stockCodes` (şirketin kendi bildirimi ise dolu), `relatedStocks` (kurum/ortak bildirimlerde ilgili hisseler, virgüllü), `kapTitle`, `subject`, `summary`, `disclosureClass` (`ODA` özel durum, `FR` finansal rapor, `DKB` diğer kurum bildirimi, `DG` genel bilgi), `disclosureType`, `disclosureIndex`, `attachmentCount`, `isLate`.

**Bağlantı:** `https://www.kap.org.tr/tr/Bildirim/{disclosureIndex}` (200, doğrulandı).

**Performans:** 5 şirket / 14 gün ≈ 0,2-1,2 sn, ~17 KB; tek şirket / 365 gün = 98 bildirim, 0,5 sn. Tek istekte birden çok `mkkMemberOidList` çalışıyor (portföy + izleme listesi tek çağrıda sorgulanabilir). Sayfalama gerekmedi.

## 4. Bulunan Sorunlar

1. **Kimlik haritası hatası (mevcut kod):** `kap_shareholder_provider._parse_bist_companies` birden fazla borsa kodu olan şirketleri atlıyor: KAP listesinde `"stockCode":"GARAN, TGB"` gibi 45 girdi var ve `_TICK_PATTERN` (`[A-Z0-9]+` + kapanış tırnağı) bunları eşleştiremiyor. Sonuç: **GARAN** dahil 45 şirketin KAP kimliği çözülemiyor; bu yalnızca haber değil, mevcut Hisse 360 ortaklık yapısı sekmesini de etkiliyor (`GARAN: KAP'ta bulunamadı`). Haber sağlayıcısı yazılmadan önce düzeltilmeli (virgüllü kodlar ayrıştırılıp her kod aynı kimliğe eşlenir) ve test eklenmeli.
2. **Gürültü:** Şirket filtresi uygulansa da sonuçların yaklaşık üçte biri `stockCodes` boş kurum bildirimidir (MKK "SPK İşlem Yasağı Nedeniyle Pay Duyurusu" gibi); bir bildirimde 106'ya kadar hisse listelenebiliyor. Ayrıca finansal rapor dönemlerinde aynı anda 3-4 `FR` kaydı geliyor (Finansal Rapor, Faaliyet Raporu, Sorumluluk Beyanı ×2).

## 5. Tasarım Kararları (öneri)

- Kimlik çözümü mevcut `resolve_member_oid` ile; önce yukarıdaki hata düzeltilir.
- **Şirket haberi** için bildirim, `stockCodes` takip ettiğimiz koda eşitse veya `relatedStocks` en çok ~5 hisse içeriyorsa alınır; çok hisseli kurum bildirimleri (genel duyuru) varsayılan olarak elenir.
- Aynı anda yayımlanan `FR` kayıtları tek satırda gruplanır veya yalnızca "Finansal Rapor" gösterilir; "Sorumluluk Beyanı" gibi alt belgeler gizlenir.
- Başlık: `subject` (özet varsa `summary` ikinci satır); kaynak etiketi "KAP"; dil Türkçe; zaman İstanbul saati.
- `isLate` doluysa rozet gösterilebilir (v2).
- Önbellek TTL ~10 dakika; tek istek, yeniden deneme `retry_call` ile.
- Yalnızca portföy ve izleme listesindeki BIST sembolleri sorgulanır (≤ ~50 kimlik).

## 6. Riskler

- Resmî olmayan, belgesiz bir iç API; KAP istediği zaman değiştirebilir. Sağlayıcı hata verirse kaynak "ulaşılamıyor" durumuna düşer, diğer kaynaklar etkilenmez; Ayarlar'dan kapatılabilir.
- Kullanım koşulları: yalnızca başlık, özet ve bağlantı gösterilir; bildirim metni kopyalanmaz.
