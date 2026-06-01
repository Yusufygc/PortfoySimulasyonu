# Aşama 1: Matematiksel Altyapı ve Veri Motoru (ComparisonService)

## 📌 Amaç
Bu aşamada, "Karşılaştırma Laboratuvarı" sayfasının ihtiyaç duyduğu tüm finansal hesaplamaları, veri birleştirmeleri ve rasyo dönüşümlerini gerçekleştirecek olan `ComparisonService` bileşeni yazılacaktır. Sistem, projenin mevcut veri havuzu altyapısını kullanarak UI katmanından tamamen bağımsız (decoupled) çalışmalıdır.

## 📁 Dosya Hedefi
- [comparison_service.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/application/services/analysis/comparison_service.py) (Mevcut analiz servisleri altına entegre edilecek veya yeni alt servis olarak eklenecek)
- [test_comparison_service.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/tests/application/services/test_comparison_service.py) (Birim testleri)

## 🏗️ Mimari Gereksinimler ve Kurallar
1. **SOLID Uyumluluğu:** Hesaplama mantığı kesinlikle UI (PyQt) elementleri içermemelidir. Girdi olarak `pandas.DataFrame` veya `pd.Series` almalı, çıktı olarak sunuma hazır işlenmiş veriler (DataFrame/Dict) dönmelidir.
2. **Temiz Kod / Satır Sınırı:** Tek bir metodun veya dosyanın devasa büyümesini engellemek için rasyo, drawdown ve risk metrikleri hesaplamaları alt fonksiyonlara bölünmelidir.
3. **Eksik Veri (Data Alignment):** Farklı tatil günlerine sahip varlıklar birleştirilirken `outer join` yapılmalı ve eksik günler `ffill()` (Forward Fill) yöntemiyle doldurulmalıdır.

## 🛠️ Uygulama Adımları ve Teknik Detaylar

### 1. Veri Birleştirme ve Hizalama (`align_financial_series`)
- **Girdi:** Farklı varlıklara ait tarih indeksli `pd.Series` listesi veya sözlüğü.
- **İşlem:** Tüm seriler ortak bir tarih indeksinde `pandas.concat(axis=1, join='outer')` ile birleştirilir. Hafta sonu veya resmi tatil kesişimsizlikleri `.ffill()` ile çözülür. İlk günlerde oluşabilecek `NaN` değerleri `.bfill()` ile temizlenir.

### 2. Gelişmiş Rasyo Hesaplama Motoru (`calculate_asset_ratio`)
- **Girdi:** `series_a` (Pay), `series_b` (Payda).
- **İşlem:** İki seri tarihsel olarak hizalandıktan sonra her satır için $Rasyo = Seri_a / Seri_b$ hesaplaması yapılır. 
- **İstisna Yönetimi:** Sıfıra bölünme (`ZeroDivisionError`) kontrolü yapılmalı, tanımsız veya sonsuz (`inf`) değerler `NaN` olarak işaretlenip temizlenmelidir.

### 3. Maksimum Drawdown Hesaplama Modülü (`calculate_drawdowns`)
- **Girdi:** Hizalanmış fiyat veya getiri DataFrame'i.
- **İşlem:** Her bir varlık (kolon) için tarihsel zirve (`rolling(window=len(df), min_periods=1).max()`) veya `.cummax()` serisi bulunur. Düşüş yüzdesi şu formülle hesaplanır:
  $$DD = \frac{Fiyat - Tarihsel Zirve}{Tarihsel Zirve} \times 100$$
- **Çıktı:** Her zaman $\le 0$ olan yüzdesel düşüş serisi.

### 4. Risk-Getiri ve Volatilite Metrikleri (`calculate_risk_return_metrics`)
- **Girdi:** Tarihsel fiyat DataFrame'i ve seçilen periyod.
- **İşlem:** - Günlük yüzdesel getiriler hesaplanır (`.pct_change()`).
  - **Yıllıklandırılmış Volatilite (Risk):** Günlük getirilerin standart sapması hesaplanıp iş günü çarpanıyla yıllıklandırılır: $\sigma_{annual} = \sigma_{daily} \times \sqrt{252} \times 100$.
  - **Toplam Dönem Getirisi:** Seçilen periyodun başındaki ve sonundaki değerler üzerinden toplam getiri hesaplanır.

### 5. Dönemsel Getiri Kıyaslama Mantığı (`calculate_periodic_returns`)
- **Girdi:** Fiyat veri seti.
- **İşlem:** Veriler aylık (`'ME'`) veya yıllık (`'YE'`) frekanslara resample edilerek, her periyodun kendi içindeki net getiri yüzdesi hesaplanır ve bar grafiğine uygun matris formatına getirilir.

## 🧪 Örnek Birim Test Senaryosu (TDD)
```python
def test_calculate_asset_ratio():
    # Arrange
    dates = pd.date_range(start="2026-01-01", periods=3)
    portfoy = pd.Series([100, 120, 150], index=dates)
    altin = pd.Series([50, 50, 75], index=dates)
    
    # Act
    ratio = ComparisonService.calculate_asset_ratio(portfoy, altin)
    
    # Assert
    assert ratio.iloc[0] == 2.0  # 100 / 50
    assert ratio.iloc[1] == 2.4  # 120 / 50
    assert ratio.iloc[2] == 2.0  # 150 / 75
```