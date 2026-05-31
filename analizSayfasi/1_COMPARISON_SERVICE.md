# Aşama 1: Matematiksel Altyapı ve Veri Motoru (AnalysisService ve risk_metrics)

## 📌 Amaç
Bu aşamada, "Karşılaştırma" sekmesinin ihtiyaç duyduğu tüm finansal hesaplamaları, getiri rasyolarını ve risk metriklerini gerçekleştirecek olan `AnalysisService` bileşeni ile `risk_metrics` modülü belgelenmiştir. Sistem, projenin mevcut veri havuzu altyapısını kullanarak UI katmanından tamamen bağımsız (decoupled) çalışmaktadır.

## 📁 Dosya Hedefi
- [analysis_service.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/application/services/analysis/analysis_service.py) (Karşılaştırma verilerinin hazırlandığı ana uygulama servisi)
- [risk_metrics.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/application/services/analysis/risk_metrics.py) (Temel finansal hesaplamalar ve rasyo yardımcı metotları)
- [test_analysis_service.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/tests/application/test_analysis_service.py) (Birim testleri)

## 🏗️ Mimari Gereksinimler ve Kurallar
1. **SOLID Uyumluluğu:** Hesaplama mantığı kesinlikle UI (PyQt) elementleri içermez. Girdi olarak Python temel tipleri, `pandas.DataFrame` veya `pd.Series` alır, çıktı olarak sunuma hazır işlenmiş veriler veya DTO'lar (`ComparisonViewDTO`) döner.
2. **Temiz Kod / Satır Sınırı:** Tek bir metodun veya dosyanın devasa büyümesini engellemek için rasyo, drawdown ve risk metrikleri hesaplamaları `risk_metrics.py` gibi bağımsız helper fonksiyonlarına bölünmüştür.
3. **Eksik Veri (Data Alignment):** Farklı tatil günlerine sahip varlıklar birleştirilirken veya karşılaştırılırken tarihsel indeksler hizalanır.

## 🛠️ Uygulama Adımları ve Teknik Detaylar

### 1. Performans Getirisi Hesaplama (`compute_return_pct`)
- **İşlem:** Belirli bir zaman serisindeki başlangıç ve bitiş değerlerine göre yüzde getiri hesaplanır. Sıfır veya tanımsız başlangıç değerleri için koruma içerir.

### 2. Göreli Fark (Gap) Hesaplama (`compute_relative_gap_pct` / `_build_relative_gap_series`)
- **İşlem:** Portföy getirisi ile seçilen benchmark veya diğer karşılaştırma portföyü arasındaki yüzde farkı ($Fark = Getiri_{portfoy} - Getiri_{benchmark}$) hesaplar.

### 3. Maksimum Drawdown Hesaplama Modülü (`compute_max_drawdown_pct`)
- **İşlem:** Her bir varlık (veya portföy serisi) için tarihsel zirveye göre oluşan maksimum düşüş yüzdesini bulur.
- **Çıktı:** Her zaman $\le 0$ olan yüzdesel düşüş değeri.

### 4. Risk-Getiri ve Volatilite Metrikleri (`compute_volatility_pct`)
- **İşlem:** Günlük yüzdesel getirilerin standart sapması hesapnıp iş günü çarpanıyla yıllıklandırılır: $\sigma_{annual} = \sigma_{daily} \times \sqrt{252} \times 100$.

## 🧪 Örnek Birim Test Senaryosu
Aşağıdaki gibi test senaryoları [test_analysis_service.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/tests/application/test_analysis_service.py) altında işletilmektedir:
```python
def test_comparison_view_builds_deposit_benchmark_series(analysis_service):
    # DTO çıktısı ve karşılaştırma rasyolarının doğruluğu test edilir
    comparison = analysis_service.get_comparison_view(filter_state, ["deposit"])
    assert len(comparison.benchmark_series) == 1
```