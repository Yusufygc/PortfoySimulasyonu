# 📊 Temel Analiz Filtre Tarama Sistemi — Tartışma Dokümanı

## Mevcut Durum

Sisteminizde **çok güçlü bir finansal analiz motoru** zaten var — ama şu an **tek hisse bazlı, on-demand** çalışıyor:

```
[Kullanıcı ticker girer] → [İş Yatırım API] → [metrics.py: 30+ metrik hesapla] → [Plotly Dashboard]
```

### Zaten Hesaplanabilen Metrikler (Tek Hisse İçin)

| Kategori | Metrikler |
|---|---|
| **Değerleme** | F/K (P/E), PD/DD (P/B), FD/FAVÖK (EV/EBITDA), F/S (P/S), Temettü Verimi |
| **Kârlılık** | Brüt Kar Marjı, FAVÖK Marjı, Net Kar Marjı, FCF Marjı, ROE, ROA |
| **Borç** | Net Borç/FAVÖK, Cari Oran, Finansal Kaldıraç, UV Borç/Varlık |
| **Verimlilik** | DuPont (3-aşamalı), Varlık Devir Hızı, CCC (DSO+DIO-DPO) |
| **Kalite** | Piotroski F-Score (0-9), Accruals Kalitesi |
| **Büyüme** | Satış/Kar YoY%, QoQ%, Reel Büyüme (TÜFE düzeltmeli) |
| **Sermaye** | Bedelsiz Potansiyeli, İhracat Oranı, Capex/Satış |

> [!IMPORTANT]
> **Kritik Sorun:** Bu metriklerin hepsi tek hisse için çalışıyor. 500+ hisseyi toplu taramak için **yeni bir batch altyapısı** gerekiyor. Çünkü her hisse için ayrı İş Yatırım API çağrısı yapılması gerekiyor (cache'lenmiş olsa bile ilk çalıştırmada ~500 HTTP isteği demek).

---

## 🎯 Hangi Filtreler En Verimli? — Kategori Bazlı Analiz

### Kategori 1: Değerleme Çarpanları (Ucuzluk Taraması)

Bu filtrelerin amacı: **temel değerlerine göre ucuz kalan hisseleri bulmak**.

| Filtre | Eşik Değer | Neden Verimli? | Dikkat |
|---|---|---|---|
| **PD/DD ≤ 2.0** | `Piyasa Değeri / Özkaynaklar ≤ 2` | Defter değerine göre makul fiyat. Buffett klasiği. | Bankalarda her zaman düşük — sektörel karşılaştırma şart |
| **F/K ≤ 15** | `Piyasa Değeri / Net Kar TTM ≤ 15` | Kazanca göre makul fiyat | Negatif karlı şirketlerde anlamsız. Döngüsel sektörlerde yanıltıcı |
| **FD/FAVÖK ≤ 8** | `Enterprise Value / FAVÖK TTM ≤ 8` | Borç yapısını da dikkate alır, F/K'dan daha güvenilir | Bankalar ve finansallarda FAVÖK yok |
| **F/S ≤ 1.5** | `Piyasa Değeri / Satışlar TTM ≤ 1.5` | Düşük marjlı ama büyüyen şirketler için güzel | Tek başına yetmez, marj bilgisi gerekir |
| **Temettü Verimi ≥ 5%** | `Temettü / Piyasa Değeri` | Nakit akışı güçlü, hissedarını düşünen | Geçmiş temettü gelecek garantisi değil |

> [!TIP]
> **En pratik başlangıç seti:** PD/DD + F/K + FD/FAVÖK üçlüsü. Bu üçü birlikte "ucuz" hisseleri yüksek doğrulukla bulur.

---

### Kategori 2: Kârlılık & Verimlilik (Kaliteli Şirket Taraması)

Bu filtrelerin amacı: **operasyonel olarak güçlü, iyi yönetilen şirketleri bulmak**.

| Filtre | Eşik Değer | Neden Verimli? | Dikkat |
|---|---|---|---|
| **ROE ≥ 15%** | `Net Kar / Özkaynak` | Özsermaye verimliliği yüksek | Aşırı kaldıraçlı şirketlerde şişirilmiş olabilir |
| **Net Kar Marjı ≥ 10%** | `Net Kar / Satışlar` | Fiyatlama gücü yüksek | Sektörler arası çok farklı — perakende vs yazılım |
| **FAVÖK Marjı ≥ 15%** | `FAVÖK / Satışlar` | Operasyonel verimlilik | — |
| **FCF Marjı > 0%** | `Serbest Nakit / Satışlar` | Gerçek nakit üretimi | Yatırım dönemindeki şirketlerde negatif olabilir |
| **Piotroski F-Score ≥ 7** | 9 üzerinden 7+ | Kapsamlı kalite filtresi — kârlılık + borç + verimlilik | Zaten hesaplanıyor, çok güçlü |
| **Varlık Devir Hızı ≥ 0.5** | `Satışlar / Toplam Varlıklar` | Varlıkları verimli kullanan | Holding ve yatırım şirketlerinde düşük |

> [!TIP]
> **"Kaliteli ve ucuz" birleşik filtre:** PD/DD ≤ 2 **VE** ROE ≥ 15% **VE** Piotroski ≥ 6. Bu kombinasyon "value trap"ları elemine eder.

---

### Kategori 3: Borç & Finansal Sağlık (Risk Filtresi)

Bu filtrelerin amacı: **finansal riski yüksek, borç batağındaki şirketleri elemek**.

| Filtre | Eşik Değer | Neden Verimli? | Dikkat |
|---|---|---|---|
| **Net Borç/FAVÖK ≤ 3.0** | `Net Borç / FAVÖK TTM` | Borç ödeme kapasitesi | Negatif FAVÖK'te anlamsız |
| **Cari Oran ≥ 1.5** | `Dönen Varlıklar / KVY` | Kısa vadeli ödeme gücü | Çok yüksek = verimsiz nakit yönetimi |
| **Finansal Kaldıraç ≤ 3.0** | `Toplam Varlıklar / Özkaynak` | Özkaynak ağırlıklı bilanço | Bankalar doğal olarak yüksek |
| **Nakit > 0** | Nakit ve Benzerleri | Temel hayatta kalma | — |

> [!TIP]
> **Negatif filtre olarak kullanımı:** Net Borç/FAVÖK > 5 olan şirketleri **dışla**. Bu, diğer filtrelerin kalitesini artırır.

---

### Kategori 4: Büyüme & Momentum (Büyüyen Şirket Taraması)

Bu filtrelerin amacı: **hızla büyüyen, ivme kazanan şirketleri bulmak**.

| Filtre | Eşik Değer | Neden Verimli? | Dikkat |
|---|---|---|---|
| **Satış Büyümesi (YoY) ≥ %20** | Reel satış artışı (TÜFE düzeltmeli) | Organik büyüme | Enflasyonist ortamda reel büyüme çok önemli |
| **Net Kar Büyümesi (YoY) ≥ %15** | Reel net kar artışı | Kârlı büyüme | Düşük bazdan gelen yüksek büyüme yanıltıcı |
| **İhracat Oranı ≥ %30** | Yurtdışı Satışlar / Toplam | Döviz geliri → TL devalüasyondan korunma | — |
| **Bedelsiz Potansiyeli ≥ %100** | (Özkaynak/Sermaye - 1) × 100 | Kısa vadeli katalizör | Gerçekleşmesi yönetim kararına bağlı |

---

## 🏆 Önerilen Hazır Filtre Setleri (Presets)

Kullanıcıya hazır filtre kombinasyonları sunmak pratikliği artırır:

### 1. 💎 "Değerli ve Kaliteli" (Value + Quality)
```
PD/DD ≤ 2.0 VE F/K ≤ 12 VE ROE ≥ 15% VE Piotroski ≥ 6 VE Net Borç/FAVÖK ≤ 3
```
> Graham + Greenblatt stili. Ucuz AMA kaliteli şirketler.

### 2. 📈 "Büyüme Makinesi" (Growth)
```
Satış Büyümesi YoY ≥ %25 (reel) VE Net Kar Marjı ≥ 8% VE FAVÖK Marjı ≥ 12% VE Cari Oran ≥ 1.2
```
> Hızla büyüyen ama kârlılığını koruyan şirketler.

### 3. 🛡️ "Savunma Kalkanı" (Defensive)
```
Temettü Verimi ≥ 4% VE Net Borç/FAVÖK ≤ 2 VE Cari Oran ≥ 2.0 VE Piotroski ≥ 7
```
> Düşük riskli, nakit akışı güçlü, temettü ödeyen.

### 4. 🔥 "Ucuz ve Büyüyen" (GARP - Growth At Reasonable Price)
```
F/K ≤ 15 VE Satış Büyümesi YoY ≥ %15 (reel) VE ROE ≥ 12% VE Net Borç/FAVÖK ≤ 4
```
> PEG yaklaşımı benzeri — büyümeye makul fiyat ödeyen.

### 5. 💰 "Bedelsiz Avcısı"
```
Bedelsiz Potansiyeli ≥ %200 VE Net Kar > 0 VE Cari Oran ≥ 1.5
```
> Yüksek bedelsiz sermaye artırımı potansiyeli olan karlı şirketler.

---

## 🏗️ Mimari — Toplu Tarama Nasıl Çalışır?

### Ana Zorluk

```
Mevcut: 1 hisse → 1 API çağrısı → ~2 sn → metrik hesapla → göster
Hedef:  500+ hisse → 500+ API çağrısı → ??? → metrikleri hesapla → filtrele
```

Her hisse için İş Yatırım API'sine istek atılması gerekiyor. Bu da 500× ~2 sn = **~15-20 dakika** ilk tam tarama demek.

### Yaklaşım A: Full On-Demand Tarama

```
[Kullanıcı "Tara" butonuna basar]
  → 500 hisse × (İş Yatırım API + YFinance) → paralel/sıralı
  → Her hisse için metrics.py hesapla
  → Filtreleri uygula → Sonuçları tabloda göster
```

| ✅ Avantaj | ❌ Dezavantaj |
|---|---|
| En güncel veri | İlk tarama 15-20 dk (rate limit riski) |
| Ekstra DB tablosu gerektirmez | Her taramada tekrar API çağrısı |
| Basit implementasyon | UX kötü — kullanıcı çok bekler |

---

### Yaklaşım B: Pre-Computed Snapshot Tablosu ⭐ ÖNERİLEN

```
[Arka Plan Güncelleme (günde 1x veya kullanıcı tetikli)]
  → 500 hisse × İş Yatırım → metrics hesapla
  → "fundamental_snapshots" tablosuna yaz (MySQL)
  → Progress bar ile ilerleme göster

[Kullanıcı Filtreleme (anlık)]
  → SQL sorgusunda WHERE fk <= 15 AND pddd <= 2.0
  → Milisaniyede sonuç → Tablo + sıralama
```

| ✅ Avantaj | ❌ Dezavantaj |
|---|---|
| Filtreleme anlık (SQL) | İlk güncelleme yavaş (~15-20 dk) |
| Sıralama, gruplama, istatistik kolay | Veri güncelliği snapshot anına bağlı |
| Geçmiş snapshot'lar saklanabilir | Yeni DB tablosu + migration gerekli |
| Progress bar ile UX iyi | — |

#### Önerilen Tablo Yapısı

```sql
CREATE TABLE fundamental_snapshots (
    id            BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_id      BIGINT NOT NULL,
    snapshot_date DATE NOT NULL,
    
    -- Değerleme
    fk            DECIMAL(12,2),    -- F/K (P/E)
    pddd          DECIMAL(12,2),    -- PD/DD (P/B)
    fd_favok      DECIMAL(12,2),    -- FD/FAVÖK (EV/EBITDA)
    fs            DECIMAL(12,2),    -- F/S (P/S)
    temttu_verimi DECIMAL(8,2),     -- %
    piyasa_degeri DECIMAL(18,2),    -- TL
    
    -- Kârlılık
    roe           DECIMAL(8,2),     -- %
    roa           DECIMAL(8,2),     -- %
    brut_kar_marji    DECIMAL(8,2), -- %
    favok_marji       DECIMAL(8,2), -- %
    net_kar_marji     DECIMAL(8,2), -- %
    fcf_marji         DECIMAL(8,2), -- %
    
    -- Borç & Likidite
    net_borc_favok    DECIMAL(12,2),
    cari_oran         DECIMAL(8,2),
    finansal_kaldirac DECIMAL(8,2),
    
    -- Büyüme (reel, TÜFE düzeltmeli)
    satis_buyume_yoy  DECIMAL(8,2),   -- %
    kar_buyume_yoy    DECIMAL(8,2),   -- %
    
    -- Kalite & Diğer
    piotroski_score   TINYINT,         -- 0-9
    ihracat_orani     DECIMAL(8,2),    -- %
    bedelsiz_potansiyeli DECIMAL(12,2), -- %
    nakit_donusum_suresi INT,           -- gün (CCC)
    
    -- Meta
    son_bilanço_donemi VARCHAR(10),     -- "2025/9" gibi
    updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE KEY uq_stock_snapshot (stock_id, snapshot_date),
    INDEX idx_snapshot_date (snapshot_date),
    FOREIGN KEY (stock_id) REFERENCES stocks(id)
);
```

---

### Yaklaşım C: Hibrit (Hafif Snapshot + On-Demand Detay)

```
Hafif Snapshot (hızlı):
  → YFinance'den piyasa değeri + hisse adedi (batch alınabilir)
  → İş Yatırım'dan SADECE son çeyrek bilanço özeti
  → Temel 5-6 metrik hesapla (F/K, PD/DD, Cari Oran)
  → ~5 dk'da tüm BIST taranır

Detay Görüntüleme:
  → Kullanıcı bir hisseye tıklayınca → tam metrics.py analizi
```

| ✅ Avantaj | ❌ Dezavantaj |
|---|---|
| İlk tarama daha hızlı (~5 dk) | Piotroski, CCC gibi ileri metrikler eksik |
| Basit metrikler yeterli çoğu filtre için | İki aşamalı karmaşıklık |

---

## ⚠️ Kritik Mimari Kararlar

### 1. Sektör/Endüstri Verisi

Mevcut `stocks` tablosunda **sektör bilgisi yok**. Bu önemli bir eksiklik çünkü:
- PD/DD bankalar için doğal olarak düşük — banka mı üretim mi ayırt etmek lazım
- F/K sektörden sektöre çok farklı — teknoloji vs enerji
- Bazı metrikler finans sektöründe anlamsız (FAVÖK, Stok, CCC)

**Seçenekler:**
1. İş Yatırım veya KAP'tan sektör bilgisini çekip `stocks` tablosuna `sector` kolonu ekle
2. BIST sektör endekslerinden hisse-sektör eşleştirme tablosu oluştur
3. Manuel sektör sınıflandırması (JSON/CSV dosyası)

> [!WARNING]
> **Banka/finans şirketleri** için FAVÖK, Net Borç/FAVÖK, CCC gibi metrikler hesaplanamaz. Tarayıcıda bu şirketler ya ayrı tutulmalı ya da bu filtreler "N/A" olarak işaretlenmelidir.

### 2. Rate Limiting

İş Yatırım API'si rate limit uygulayabilir. 500 istek atılırsa:
- **Throttling**: İstekler arası 1-2 sn beklemek gerekebilir
- **Batch boyutu**: 10-20 paralel istek → toplam ~5-10 dk
- **Cache akıllı kullanım**: 12 saatlik TTL'i tarama sırasında "geçerli" sayan strateji

### 3. Veri Güncelliği

BIST şirketleri çeyreklik bilanço yayınlar (Mart, Haziran, Eylül, Aralık sonrası ~2 ay). Yani:
- **Değerleme çarpanları**: Piyasa fiyatı değiştiği için her gün güncellenebilir
- **Bilanço metrikleri**: Çeyreklik değişir — 3 ayda bir tam güncelleme yeterli
- **Pratik yaklaşım**: Piyasa değeri günlük, bilanço verisi haftalık/çeyreklik güncelle

---

## 🔗 Teknik Analiz ile Birleştirme Vizyonu

Asıl güç, temel ve teknik analizi **birleştirdiğimizde** ortaya çıkar:

```
[Temel Filtre: PD/DD ≤ 2, ROE ≥ 15%, Piotroski ≥ 6]
  → 30-40 hisse geçer
    → [Teknik Filtre: Son 30 günde Golden Cross VEYA Donchian Kırılımı]
      → 5-8 hisse → ✨ HEM ucuz HEM de momentum kazanmış
```

Bu birleşik tarama, "değerli ama piyasanın henüz fark etmediği, teknik olarak dönüş sinyali veren" hisseleri bulmak için son derece güçlü bir araç olur.

### Olası Birleşik Presetler

| Preset | Temel Filtre | Teknik Filtre |
|---|---|---|
| **"Uyanan Dev"** | PD/DD ≤ 1.5, F/K ≤ 10, Piotroski ≥ 7 | Son 30 gün Golden Cross |
| **"Momentum + Kalite"** | ROE ≥ 20%, Net Kar Marjı ≥ 12% | MACD yukarı kesişim + Donchian(20) kırılım |
| **"Temettü + Teknik Dip"** | Temettü Verimi ≥ 5%, Cari Oran ≥ 2 | RSI < 35 (aşırı satım bölgesi) |

---

## 🤔 Tartışma Soruları

1. **Filtre Önceliği:** Değerleme çarpanları mı (PD/DD, F/K), kârlılık mı (ROE, marjlar), yoksa kalite skoru mu (Piotroski) önce gelsin? Hangi filtreler sizin için en değerli?

2. **Tarama Mimarisi:** Pre-computed snapshot tablosu (Yaklaşım B) uygun mu? İlk taramanın 15-20 dk sürmesi kabul edilebilir mi?

3. **Hazır Preset Setleri:** "Değerli ve Kaliteli", "Büyüme Makinesi" gibi hazır filtre kombinasyonları ister misiniz?

4. **Sektör Bilgisi:** Sektör bazlı filtreleme ve karşılaştırma ne kadar önemli? Sektör verisini nereden almak istersiniz?

5. **Banka/Finans Ayrımı:** Finansal kuruluşlar için ayrı bir filtre seti mi olsun, yoksa sadece uygulanamayan metrikler "N/A" mı gösterilsin?

6. **Teknik + Temel Birleşim:** İlk aşamada temel analiz tarayıcısını bağımsız mı yapalım, yoksa teknik analiz tarayıcısı ile entegre bir "Birleşik Tarayıcı" mı?

7. **Güncelleme Sıklığı:** Snapshot tablosu ne sıklıkla güncellensin? (Günlük otomatik? Kullanıcı tetikli? Haftalık?)

8. **UI Tercihi:** Filtre arayüzü nasıl olsun? Slider'lar + input alanları mı, yoksa daha basit bir dropdown/preset sistemi mi?
