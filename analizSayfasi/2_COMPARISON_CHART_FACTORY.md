# Aşama 2: Görselleştirme Motoru (chart_builder)

## 📌 Amaç
Bu aşamada, analiz servisleri tarafından üretilen finansal metrikleri ve zaman serilerini grafiklere dönüştüren [chart_builder.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/analysis/chart_builder.py) modülü belgelenmiştir. Tüm grafikler Plotly (`plotly.graph_objects`) mimarisiyle üretilmekte ve PyQt tarafında `QWebEngineView` içinde render edilmeye hazır HTML/JSON çıktısı vermektedir.

## 📁 Dosya Hedefi
- [chart_builder.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/analysis/chart_builder.py) (Görselleştirme fonksiyonlarını içeren modül)

## 🏗️ Mimari Gereksinimler ve Kurallar
1. **Saf Fonksiyon Yapısı:** Grafik çizim fonksiyonları bağımsız saf fonksiyonlar (pure functions) mantığıyla çalışmalı, state tutmamalıdır.
2. **Dinamik Tema Uyumu:** Grafik tasarımları uygulamanın dinamik tema yöneticisine (`ThemeManager` ve `@COLOR` token'ları) ve varsayılan olarak Plotly'nin koyu tema şablonuna (`template="plotly_dark"`) uyumlu olacak şekilde yapılandırılmıştır.
3. **Chromium Uyumluluğu (`patch_plotly_html`):** Eski Chromium motorları barındıran PyQt QWebEngineView üzerinde Plotly'nin fırlatabileceği `:focus-visible` CSS insertRule hataları bir maymuncuk (monkeypatch) script'i ile onarılmıştır.

## 🛠️ Uygulama Adımları ve Grafik Metodları

### 1. Normalize Performans Grafiği (`build_performance_line_chart_v2`)
- **Grafik Türü:** `go.Scatter`
- **Tasarım:** Varlıklar ve portföy normalize edilmiş getiri (Başlangıç=100) bazında çizgi grafiği olarak karşılaştırılır. Range selector butonları (`1A`, `3A`, `6A`, `YBB`, `1Y`, `Tümü`) ve bir range slider (mini zaman çubuğu) içerir.

### 2. Yuvarlanan Getiri Analizi Grafiği (`build_rolling_returns_chart`)
- **Grafik Türü:** `make_subplots` (go.Scatter)
- **Tasarım:** Farklı pencere boyutlarında (örn. 30 ve 90 günlük) yuvarlanan kümülatif getiri yüzdelerini alt alta alt-grafikler (subplots) halinde çizer.

### 3. Maksimum Drawdown Grafiği (`build_drawdown_chart`)
- **Grafik Türü:** `go.Scatter` (Line + Area)
- **Tasarım:** Tepe noktasından yüzde düşüşleri (drawdown) gösterir. Portföy çizgisinin altı yarı saydam kırmızı (`rgba(230,57,70,0.12)`) dolguyla (`fill='tozeroy'`) vurgulanır.

### 4. Varlık Getiri Korelasyon Grafiği (`build_correlation_heatmap`)
- **Grafik Türü:** `go.Heatmap`
- **Tasarım:** Varlık getirilerinin günlük bazda korelasyon matrisini çizer. Renk skalası olarak kırmızı (-1) → nötr/koyu gri (0) → yeşil (+1) skalası uygulanır.

### 5. Dönemsel Getiri Çubuk Grafiği (`build_period_bar_chart`)
- **Grafik Türü:** `go.Bar`
- **Tasarım:** Aylık (`ME`) veya çeyreklik bazda periyodik getiri yüzdelerini yan yana sütunlar halinde kıyaslar (`barmode='group'`).

### 6. Kar/Zarar Katkı Haritası (`build_treemap`)
- **Grafik Türü:** `go.Treemap`
- **Tasarım:** Varlıkların portföy içindeki ağırlıklarına göre kutu boyutlarını ayarlar, getiri oranlarına göre ise kırmızıdan yeşile renk tonu vererek kâr/zarar katkısını görselleştirir.

### 7. Risk-Getiri Dağılımı Grafiği (`build_risk_return_scatter`)
- **Grafik Türü:** `go.Scatter` (Markers + Text)
- **Tasarım:** X ekseninde yıllık volatilite (%), Y ekseninde toplam dönem getiri (%) olacak şekilde varlıkların dağılımını gösterir. Portföy bir yıldız marker sembolüyle öne çıkarılır.

## ⚙️ Layout Yapılandırma Mantığı
Grafiklerin layout ayarlarında Türkçe ay isimleri ve dinamik tema tokenlerine uyumlu koyu renkler (`#1e1e2e` arka plan, `#cdd6f4` metin renkleri) tercih edilir:
```python
fig.update_layout(
    xaxis=dict(
        rangeselector=dict(
            bgcolor="#313244",
            activecolor="#585b70",
            font=dict(color="#cdd6f4", size=11)
        ),
        rangeslider=dict(visible=True, bgcolor="#1e1e2e")
    ),
    template="plotly_dark"
)
```