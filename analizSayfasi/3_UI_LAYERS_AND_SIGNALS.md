# Aşama 3: UI Katmanı ve Sinyal Mekanizması (AnalysisComparisonSection)

## 📌 Amaç
Bu aşamada, `AnalysisService` tarafından sağlanan verileri ve `chart_builder` grafiklerini arayüze bağlayan [analysis_comparison_section.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/analysis/analysis_comparison_section.py) widget sınıfı belgelenmiştir. Karşılaştırma arayüzü, sağdaki filtre paneliyle eşgüdümlü çalışan ve TradingView benzeri grafik modlarına sahip modern bir finansal analiz paneli düzenindedir.

## 📁 Dosya Hedefi
- [analysis_comparison_section.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/analysis/analysis_comparison_section.py) (Arayüz bileşeni)

## 🏗️ Mimari Gereksinimler ve Kurallar
1. **Filtre ve Görünüm Ayrımı:** Sayfa tasarımı filtre seçimlerini sağdaki [analysis_control_panel.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/analysis/analysis_control_panel.py) bileşenine devrederken, sol ana içerik alanı sadece verilerin sunulması ve grafik modunun yönetilmesine odaklanır.
2. **Dinamik QSS Tema Entegrasyonu:** Tüm butonlar, açılır kutular (combo box) ve kart bileşenleri, `ThemeManager`'ın dinamik token tabanlı stillerine (`primaryButton`, `secondaryButton`, `customComboBox`, `warningBanner`) uygun şekilde tasarlanmıştır.
3. **Asenkron Grafik Güncelleme:** Sayfadaki Plotly grafikleri `QWebEngineView` aracılığıyla, ana arayüz iş parçacığını kilitlemeyecek şekilde asenkron yüklenir.

## 🛠️ Arayüz Bileşenleri ve Düzeni

### 1. Üst Grafik Mod Kontrol Paneli
Bölümün en üstünde yatay (`QHBoxLayout`) bir çerçeve (`panelFramePadded`) yer alır:
- **Grafik Modu Seçici (`QComboBox`):** Kullanıcıya 5 farklı karşılaştırma modu sunar:
  - *Portföy vs Benchmark:* Portföy ile seçili benchmark'ların zaman serisi grafiği.
  - *Portföyler Arası:* Portföy ile seçili diğer sanal/model portföylerin karşılaştırması.
  - *Hisseler vs Portföy:* Seçili hisselerin performanslarının portföy ile kıyası.
  - *Hisseler Arası:* Sadece seçilen hisselerin kendi aralarındaki performans kıyası.
  - *Göreli Fark:* Portföyün benchmark'lara ve diğer portföylere göre relatif fark grafiği ($Getiri_{portfoy} - Getiri_{karsilastirma}$).
- **Grafiği Kaydet Butonu (`AnimatedButton`):** Mevcut grafik görünümünü PNG/PDF/SVG formatında kaydeder.

### 2. Metrik Kartları Yatay Şeridi (InfoCard Carousel)
Grafiğin hemen üstünde yatay kaydırma çubuğuna (`QScrollArea`) sahip `metrics_container` yer alır:
- **MetricCard:** Karşılaştırılan her bir varlık/benchmark için yan yana kartlar oluşturulur.
- **İçerik:** Portföy getirisi, benchmark getirisi ve aralarındaki göreli fark (delta) dinamik olarak güncellenerek gösterilir.

### 3. Grafik Gösterim Ekranı (`QWebEngineView`)
Sayfanın merkezinde Plotly grafiklerinin interaktif olarak render edildiği `chart_engine` alanı yer alır. Seçilen grafik moduna göre ilgili Plotly figürü buraya yüklenir.

## 🔀 Sinyal ve Slot Mekanizması
Sağ filtre panelindeki tarihler, hisseler veya benchmark seçimleri değiştiğinde `filter_changed` sinyali ana sayfa slotunu tetikler:
1. `AnalysisPage` arka planda asenkron `Worker` (QThreadPool) başlatarak güncel DTO verilerini çeker.
2. Gelen veri `set_data()` metodu üzerinden `AnalysisComparisonSection`'a aktarılır.
3. `_rebuild_metric_cards()` ile metrik kartları yenilenir, `_redraw_chart()` ile de Plotly grafiği güncel mod seçimine göre yeniden çizilir.