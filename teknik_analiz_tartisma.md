# 📊 Teknik Analiz — Trend Kırılım Tespit Sistemi Tartışma Dokümanı

## Mevcut Durum

Şu an [technical_analysis_page.py](file:///D:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/technical/technical_analysis_page.py) sayfasında **tek bir sinyal türü** var:

| Mevcut | Detay |
|---|---|
| **EMA50 / EMA200 Golden Cross** | Boğa sinyali — EMA(50) yukarı keser |
| **EMA50 / EMA200 Death Cross** | Ayı sinyali — EMA(50) aşağı keser |

Bu çok iyi bir başlangıç noktası. Mevcut altyapı ([golden_cross.py](file:///D:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/application/services/analysis/technical/golden_cross.py), [TechnicalAnalysisService](file:///D:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/application/services/analysis/technical/technical_analysis_service.py), IGoldenCrossRepository) sağlam bir Clean Architecture deseni üzerine kurulu. Ancak **yalnızca uzun vadeli MA cross** tespiti yapıyor — bir "trend kırılım tarayıcı" için çok daha zengin bir mekanizma seti gerekiyor.

---

## 🎯 Trend Kırılımı Nedir? — Konsept Çerçeve

"Trend kırılımı" şu durumları kapsar:

```
1. Yatay Kırılım   → Fiyat, belirli bir destek/direnç seviyesini kırar
2. Trend Çizgisi   → Fiyat, çizilen bir trend çizgisini aşar
3. Kanal Kırılımı   → Fiyat, bir fiyat kanalından çıkar (Donchian, Bollinger vb.)
4. Momentum Kırılımı → İndikatör bazlı sinyal (MACD cross, RSI divergence vb.)
5. Yapısal Kırılım  → Higher-High / Lower-Low yapısının bozulması (Market Structure Break)
```

Her birinin karmaşıklığı, güvenilirliği ve hesaplama maliyeti farklıdır.

---

## 🔧 Kullanılabilecek Trend Tespit Mekanizmaları

### Tier 1 — Hızlı & Güvenilir (İlk Aşama İçin Önerilen)

#### 1. 🟢 Donchian Channel Kırılımı (N-Gün Yüksek/Düşük)
```
Fiyat > Son N günün en yüksek kapanışı → YUKARI KIRILIM
Fiyat < Son N günün en düşük kapanışı → AŞAĞI KIRILIM
```

| Avantaj | Dezavantaj |
|---|---|
| Çok basit, vektörel hesaplanır | Dar bantta çok sinyal üretir (whipsaw) |
| Turtle Trading sistemi — kanıtlanmış | N parametresi seçimi kritik |
| Mevcut `daily_prices` verisi yeterli | Tek başına yeterli değil, filtre gerekir |

> **Öneri:** N=20 (kısa vade) ve N=55 (orta vade) ikili tarama. Volume filtresi eklenirse kalite artar.

---

#### 2. 🟢 Çoklu Hareketli Ortalama Hizalanması (MA Alignment)
```
EMA(20) > EMA(50) > EMA(200) → GÜÇLÜ YÜKSELIŞ TRENDİ
EMA(20) < EMA(50) < EMA(200) → GÜÇLÜ DÜŞÜŞ TRENDİ
Geçiş anları → TREND DEĞİŞİMİ
```

| Avantaj | Dezavantaj |
|---|---|
| Mevcut EMA altyapısına (`_ema_tv`) doğrudan bağlanır | Gecikme inherent (lagging) |
| Çok güvenilir trend doğrulaması | Yatay piyasada çok geç sinyal |
| 3-MA alignment = piyasa yapısı özeti | — |

> **Öneri:** Mevcut `detect_crosses` mantığını genişleterek EMA(20) eklenip 3'lü alignment skoru hesaplanabilir.

---

#### 3. 🟢 MACD Sinyal Kesişimleri
```
MACD = EMA(12) - EMA(26)
Signal = EMA(9) of MACD
Histogram = MACD - Signal

MACD > Signal → ALIM SİNYALİ
MACD < Signal → SATIM SİNYALİ
Sıfır çizgisi geçişleri → TREND TEYİDİ
```

| Avantaj | Dezavantaj |
|---|---|
| Endüstri standardı, herkes bilir | Tek başına false positive yüksek |
| Mevcut `_ema_tv` ile kolayca hesaplanır | Histogram divergence daha karmaşık |
| Momentum + trend birleşimi | — |

> **Öneri:** MACD sıfır çizgisi geçişi + sinyal kesişimi = 2 ayrı sinyal türü.

---

#### 4. 🟢 RSI Aşırı Bölge + Divergence
```
RSI(14) < 30 → AŞIRI SATIM (olası dönüş)
RSI(14) > 70 → AŞIRI ALIM (olası dönüş)
Fiyat yeni dip + RSI yükselen dip → BULLISH DIVERGENCE
Fiyat yeni zirve + RSI düşen zirve → BEARISH DIVERGENCE
```

| Avantaj | Dezavantaj |
|---|---|
| Dönüş sinyallerinde çok etkili | Divergence tespiti algoritmik olarak zor |
| Trend teyidi olarak kullanılabilir | Güçlü trendlerde yanıltıcı |
| Basit RSI hesabı kolay | Swing high/low tespiti gerektirir |

> **Öneri:** İlk aşamada RSI aşırı bölge, ikinci aşamada divergence.

---

### Tier 2 — Orta Karmaşıklık (İkinci Aşama)

#### 5. 🟡 Bollinger Band Kırılımı
```
Fiyat > Üst Band (SMA20 + 2σ) → Volatilite kırılımı (trend başlangıcı veya aşırı alım)
Band genişliği daralma sonrası genişleme → SQUEEZE BREAKOUT
```

| Avantaj | Dezavantaj |
|---|---|
| Volatilite + trend birleşimi | Squeeze sonrası yön belirsiz |
| Bollinger Squeeze çok güçlü sinyal | Tek başına trend yönü söylemez |

---

#### 6. 🟡 Destek / Direnç Seviye Kırılımı
```
Fiyat yoğunluğu algoritması ile yatay seviyeleri tespit et
Fiyat > direnç seviyesi → DIRENÇ KIRILIMI
Fiyat < destek seviyesi → DESTEK KIRILIMI
```

| Avantaj | Dezavantaj |
|---|---|
| Trader'ların en çok izlediği kavram | Seviye tespiti subjektif |
| Pratik ve anlaşılır | Algoritmik tespit: pivot, fractal veya kernel density |
| Volume teyidi ile çok güçlü | Parametre hassasiyeti yüksek |

> **Yaklaşımlar:** Fractal pivot noktaları (N-bar pattern), fiyat yoğunluk kümeleme, veya sabit dönemsel Pivot Points (günlük/haftalık).

---

#### 7. 🟡 ADX (Average Directional Index) — Trend Gücü
```
ADX > 25 → GÜÇLÜ TREND VAR
ADX < 20 → YATAY PİYASA
+DI > -DI → YUKARI TREND
+DI < -DI → AŞAĞI TREND
```

| Avantaj | Dezavantaj |
|---|---|
| Trend gücünü ölçer (yön + güç ayrı) | Tek başına zamanlama vermez |
| Filtre olarak mükemmel | Hesaplama biraz daha karmaşık |

> **Öneri:** Tek başına sinyal değil, diğer sinyallerin **kalite filtresi** olarak kullanılmalı.

---

### Tier 3 — İleri Seviye (Üçüncü Aşama / Opsiyonel)

#### 8. 🔴 Programatik Trend Çizgisi Kırılımı
```
Swing High/Low noktalarını tespit et
Art arda yükselen dipleri birleştir → Yükselen Trend Çizgisi
Art arda alçalan zirveleri birleştir → Düşen Trend Çizgisi
Fiyat bu çizgiyi kırdığında → TREND KIRILIMI
```

| Avantaj | Dezavantaj |
|---|---|
| En "gerçek" teknik analiz yöntemi | Algoritmik olarak EN ZOR |
| Grafik deseni tespitine yakın | Hangi pivot noktaları? Parametre çok |
| Trader'ların gözüyle uyumlu | Regression line fitting gerekir |

> **Yaklaşım:** Zigzag indikatörü ile swing tespiti → Son N swing'i birleştiren OLS/Theil-Sen regresyon çizgisi → Fiyat çizgiyi kırınca sinyal.

---

#### 9. 🔴 Market Structure Break (MSB / BOS)
```
Higher-High, Higher-Low yapısı → Yükselen trend
Bu yapının bozulması (Lower-Low oluşması) → YAPISAL KIRILIM
```

| Avantaj | Dezavantaj |
|---|---|
| Smart Money konseptleri ile uyumlu | Swing tespit algoritması kritik |
| Çok güçlü trend dönüş sinyali | Timeframe bağımlılığı yüksek |

---

#### 10. 🔴 Ichimoku Bulutu Kırılımı
```
Fiyat > Kumo (Bulut) → YUKARI KIRILIM
Tenkan > Kijun → ALIM
Chikou > Fiyat(26 bar önce) → TEYİT
```

| Avantaj | Dezavantaj |
|---|---|
| 5 bileşenli kapsamlı sistem | Parametre seti büyük |
| Kendi kendine yeten strateji | BIST'e uygunluğu tartışmalı |

---

## 🏗️ Mimari Yaklaşım — Nasıl Entegre Edelim?

### Seçenek A: Mevcut Yapıyı Genişlet (Golden Cross Pattern'i Kopyala)

Her yeni sinyal türü için ayrı:
- Domain Model (ör. `TrendSignalEvent`)
- Repository Interface + Implementation
- DB tablosu
- Service sınıfı
- Saf hesaplama fonksiyonu

```
✅ Mevcut pattern'e sadık kalır
✅ Her sinyal bağımsız test edilir
❌ Çok fazla boilerplate (her sinyal için ~5 dosya)
❌ UI tarafında her sinyal için ayrı tablo/sekme
❌ Sinyalleri birleştirmek zor
```

---

### Seçenek B: Generic Signal Engine (Strategy Pattern) ⭐ ÖNERİLEN

Tek bir **genel sinyal modeli** ve **strateji arayüzü** ile tüm sinyal türlerini birleştirilmiş bir yapıda yönet:

```python
# Domain Model
@dataclass(frozen=True)
class TrendSignal:
    stock_id: int
    ticker: str
    signal_date: date
    signal_type: SignalType        # DONCHIAN_BREAKOUT, MACD_CROSS, RSI_DIVERGENCE, ...
    direction: SignalDirection     # BULLISH, BEARISH
    strength: SignalStrength       # WEAK, MODERATE, STRONG
    indicator_values: dict         # {"ema20": 45.2, "ema50": 43.1, ...}
    description: str               # "20 günlük Donchian kanalı yukarı kırıldı"

# Strategy Interface (Port)
class ITrendDetectionStrategy(ABC):
    @abstractmethod
    def detect(self, closes: pd.Series, ...) -> list[TrendSignal]: ...
    
    @property
    @abstractmethod
    def strategy_name(self) -> str: ...

# Concrete Strategies
class DonchianBreakoutStrategy(ITrendDetectionStrategy): ...
class MACDCrossStrategy(ITrendDetectionStrategy): ...
class RSIExtremeStrategy(ITrendDetectionStrategy): ...
class MAAlignmentStrategy(ITrendDetectionStrategy): ...
```

```
✅ Tek DB tablosu (trend_signals), tek repository
✅ Yeni strateji eklemek = 1 dosya + container'a kayıt
✅ Sinyalleri birleştirme / skorlama kolay (Composite Score)
✅ UI'da tek tablo, filtreleme ile sinyal türü seçimi
✅ Clean Architecture'a uygun (Strategy = Domain Port)
❌ Generic model bazı sinyal türleri için "gevşek" olabilir
❌ indicator_values dict'i schema-free — type safety zayıf
```

---

### Seçenek C: Hibrit (Mevcut Golden Cross + Yeni Generic Engine)

Mevcut `golden_cross_events` tablosunu ve servisini olduğu gibi bırak, **yeni sinyaller için** Seçenek B'yi uygula:

```
✅ Geriye uyumlu — mevcut kodu bozmaz
✅ Yeni sinyaller esnek yapıda
❌ İki farklı sinyal sistemi — UI'da birleştirmek gerekir
❌ Uzun vadede bakım yükü artar
```

---

## ⚡ Performans ve Veri Kaynağı Değerlendirmesi

### Mevcut Veri Altyapısı
- **~500+ BIST hissesi** × **10 yıl günlük veri** = ~1.25M satır (`daily_prices`)
- Tüm veri **MySQL'de** zaten mevcut — ek API çağrısı gerekmez
- TradingView backfill mekanizması (`tv_backfill_service`) eksik verileri tamamlar

### Performans Tahmini
| İşlem | Tahmini Süre | Notlar |
|---|---|---|
| 500 hisse × EMA hesabı | ~2-5 sn | NumPy vektörel, hızlı |
| 500 hisse × MACD + RSI + Donchian | ~5-10 sn | Her hisse için ~4 indikatör |
| 500 hisse × Bollinger + ADX | ~3-5 sn | Ek olarak |
| 500 hisse × Trend Çizgisi (ZigZag + Regression) | ~15-30 sn | Swing tespiti maliyetli |
| **Toplam (Tier 1 + 2)** | **~15-25 sn** | Arka planda `QThreadPool` |

> [!TIP]
> Tüm Tier 1 + Tier 2 indikatörleri, mevcut `QThreadPool` + `Worker` altyapısı ile arka planda rahatlıkla çalışır. Kullanıcı tarama başlattığında UI donmaz.

### Kütüphane Seçenekleri

| Kütüphane | Avantaj | Dezavantaj | Önerim |
|---|---|---|---|
| **Custom (mevcut `_ema_tv` gibi)** | TV uyumlu, tam kontrol | Her indikatörü elle yazmak gerekir | ✅ EMA/MACD için |
| **pandas_ta** | 130+ indikatör, pip ile kolay | Büyük bağımlılık, bazı edge case'ler | ✅ RSI, Bollinger, ADX, Stoch için |
| **ta (by bukosabino)** | Daha hafif, pandas uyumlu | pandas_ta kadar kapsamlı değil | 🔸 Alternatif |
| **TA-Lib (C binding)** | Endüstri standardı, çok hızlı | Windows'ta kurulumu zor (C derlemesi) | ❌ Kurulum riski |

> [!IMPORTANT]
> **Önerim:** EMA/MACD gibi temel hesaplamalar için mevcut custom `_ema_tv` altyapısını genişlet (TradingView uyumluluğu korunsun). RSI, Bollinger, ADX gibi daha karmaşık indikatörler için `pandas_ta` kütüphanesini ekle. Bu hibrit yaklaşım hem tutarlılık hem de geliştirme hızı sağlar.

---

## 📋 Önerilen Yol Haritası

### Faz 1 — Temel Tarayıcı Motoru (Öncelikli)
1. Generic `TrendSignal` domain modeli + `trend_signals` DB tablosu
2. `ITrendDetectionStrategy` strateji arayüzü
3. **Donchian Channel Breakout** stratejisi (en basit, en güvenilir)
4. **MACD Cross** stratejisi (mevcut EMA altyapısını kullanır)
5. **MA Alignment** (EMA20/50/200 hizalanma skoru)
6. Birleşik tarayıcı servisi (`TrendScannerService`)
7. UI: Mevcut teknik analiz sayfasına yeni sekmeler veya tamamen yeni sayfa

### Faz 2 — Zenginleştirme
8. **RSI** aşırı bölge tespiti
9. **Bollinger Squeeze** breakout
10. **ADX** trend gücü filtresi
11. **Composite Score** — birden fazla sinyalin ağırlıklı puanlaması
12. Sinyal kalite filtreleme (hacim, ADX eşik, vb.)

### Faz 3 — İleri Seviye
13. **Destek/Direnç seviye** tespiti ve kırılımı
14. **Programatik Trend Çizgisi** kırılımı (ZigZag + regresyon)
15. **Market Structure Break** (Higher-High/Lower-Low analizi)
16. Sinyal geçmişi backtesting (sinyalden sonraki N gün getiri analizi)

---

## 🤔 Tartışma Soruları

1. **Sinyal Önceliği:** Hangi sinyal türleri sizin için en değerli? Donchian, MACD, RSI veya başka bir şey mi önce olsun?

2. **Mimari Tercih:** Generic Signal Engine (Seçenek B) mi, yoksa mevcut Golden Cross pattern'ini kopyalama (Seçenek A) mı tercih edersiniz?

3. **UI Yerleşimi:** Yeni trend sinyalleri mevcut Teknik Analiz sayfasına (Sayfa 13) ek sekmeler olarak mı eklensin, yoksa tamamen ayrı bir "Trend Tarayıcı" sayfası mı açılsın?

4. **Composite Score:** Birden fazla sinyali birleştiren bir "trend gücü skoru" (ör. 0-100 arası) ister misiniz?

5. **Alert / Bildirim:** Yeni trend kırılımı tespit edildiğinde uygulama içi bildirim/alert sistemi gerekli mi?

6. **Kütüphane Tercihi:** `pandas_ta` eklemek uygun mu, yoksa her şeyi custom mı yazalım?

7. **Golden Cross Entegrasyonu:** Mevcut EMA50/200 cross sistemi yeni generic yapıya taşınsın mı, yoksa ayrı kalsın mı?
