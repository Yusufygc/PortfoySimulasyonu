# Aşama 2: Görselleştirme Motoru (ComparisonChartFactory)

## 📌 Amaç
Bu aşamada, `ComparisonService` tarafından üretilen finansal metrikleri ve zaman serilerini, üst düzey aracı kurum terminalleri standartlarında grafiklere ve veri tablolarına dönüştürecek olan `ComparisonChartFactory` modülü yazılacaktır. Tüm grafikler Plotly (`plotly.graph_objects`) mimarisiyle üretilecek ve PyQt tarafında `QWebEngineView` içinde render edilmeye hazır HTML/JSON çıktısı verecektir.

## 📁 Dosya Hedefi
- [chart_factory.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/comparison/chart_factory.py) (Yeni dosya)

## 🏗️ Mimari Gereksinimler ve Kurallar
1. **Statik Fabrika Tasarım Kalıbı (Factory Pattern):** Sınıf içindeki tüm grafik çizim fonksiyonları `@staticmethod` olarak tanımlanmalıdır. Sınıf state tutmamalı, saf fonksiyon (pure function) mantığıyla çalışmalıdır.
2. **Dinamik Tema Uyumu:** Grafik tasarımları uygulamanın dinamik tema sistemine (`ThemeManager` ve `@COLOR` token'ları) ve varsayılan koyu/açık tema şablonlarına (`plotly_dark` veya özelleştirilmiş açık tema standartları) tamamen uyumlu ve dinamik olacak şekilde tasarlanmalıdır.
3. **Temiz Kod / Satır Sınırı:** Her grafik fonksiyonu kendi layout yapılandırmasını içermeli, kod tekrarını önlemek için ortak eksen ayarları yardımcı bir iç metoda (`_apply_theme_layout`) delege edilmelidir. Dosya boyutu 300 satırı aşmamalıdır.

## 🎨 Dinamik Renk Paleti ve Tema Ayarları
Grafiklerde kullanılacak renk paletleri ve stiller `ThemeManager` üzerinden okunmalı ve uygulanmalıdır:
- **Arka Plan (Paper/Plot Background):** Aktif temaya göre dinamik (koyu modda koyu gri/siyah, açık modda saf beyaz veya açık gri).
- **Metin / Grid Renkleri:** Metinler için tema metin rengi (örn. `@COLOR_TEXT_PRIMARY`), kılavuz çizgileri (Grid) için tema sınır rengi.
- **Performans Renk Skalası:** Pozitif/Kâr için yeşil tonları (örn. `#2DC653` veya `@COLOR_ACCENT`), Negatif/Zarar için kırmızı/gül tonları (örn. `#E63946`).

## 🛠️ Uygulama Adımları ve Grafik Metodları

### 1. Dönem Sonu Getiri Özeti Tablosu (`build_summary_table`)
- **Grafik Türü:** `go.Table`
- **Girdi:** `df_summary` (Kolonlar: Varlık Adı, Başlangıç Değeri [Baz 100], Dönem Sonu Değeri, Toplam Getiri %)
- **Tasarım:** Veriler toplam getiri yüzdesine göre büyükten küçüğe sıralanmalıdır. Hücre içi renkler, getirinin pozitif veya negatif olmasına göre yeşil/kırmızı tonlarında koşullu renklendirilmelidir. Header alanı tema renklerine uygun olmalıdır.

### 2. Maksimum Drawdown Grafiği (`build_drawdown_chart`)
- **Grafik Türü:** `go.Scatter` (Line + Area)
- **Girdi:** `df_drawdowns` (Zaman indeksli, her varlığın $\le 0$ olan yüzdesel drawdown serisi)
- **Tasarım:** Çizgi altındaki alanlar sıfır çizgisine doğru doldurulmalıdır (`fill='tozeroy'`). Modülün sarsıcı etkisini göstermek adına alan dolgu renkleri şeffaf kırmızı tonlarında seçilmelidir.

### 3. Dönemsel Getiri Çubuk Grafiği (`build_period_bar_chart`)
- **Grafik Türü:** `go.Bar` (Grouped Bar Chart)
- **Girdi:** `df_periodic` (Satırlar: Ay/Yıl periyotları, Kolonlar: Varlıkların o dönemdeki getiri %'leri)
- **Tasarım:** Her periyot grubu altında varlıklar yan yana sütunlar (barchart) halinde yarışmalıdır. `barmode='group'` ayarı kullanılmalıdır.

### 4. Risk-Getiri Dağılımı Grafiği (`build_risk_return_scatter`)
- **Grafik Türü:** `go.Scatter` (Markers + Text)
- **Girdi:** `df_risk_return` (Her varlık için hesaplanmış 'Yıllıklandırılmış Volatilite' ve 'Toplam Getiri' değerleri)
- **Tasarım:** X ekseni "Yıllık Volatilite (%)", Y ekseni "Toplam Getiri (%)" olmalıdır. Her varlık grafik üzerinde bir nokta (marker) olarak konumlanmalı, varlığın adı noktanın hemen üstünde (`textposition='top center'`) kalıcı olarak yazmalıdır.

### 5. Getiri Katkı Haritası (`build_treemap`)
- **Grafik Türü:** `go.Treemap`
- **Girdi:** `df_portfolio_weights` (Portföydeki varlıkların güncel ağırlıkları ve dönem içi bireysel getiri %'leri)
- **Tasarım:** Kutuların büyüklükleri (büyüklük parametresi) varlıkların portföy içerisindeki ağırlığını temsil etmelidir. Kutuların renkleri (color parametresi) ise varlığın getiri yüzdesine göre sürekli bir renk skalasında dağılmalıdır.

## ⚙️ Örnek Fonksiyon İmzası Taslağı
```python
import plotly.graph_objects as go
import pandas as pd

class ComparisonChartFactory:
    @staticmethod
    def _apply_theme_layout(fig: go.Figure, title: str, theme_colors: dict) -> go.Figure:
        """Tüm grafiklere aktif temaya uygun layout standartlarını uygular."""
        fig.update_layout(
            title={"text": title, "font": {"size": 16, "color": theme_colors["text"]}},
            paper_bgcolor=theme_colors["paper_bg"],
            plot_bgcolor=theme_colors["plot_bg"],
            font={"family": "Segoe UI, Arial", "color": theme_colors["text"]},
            margin={"l": 40, "r": 40, "t": 60, "b": 40},
            xaxis={"gridcolor": theme_colors["grid"], "zerolinecolor": theme_colors["zeroline"]},
            yaxis={"gridcolor": theme_colors["grid"], "zerolinecolor": theme_colors["zeroline"]}
        )
        return fig

    @staticmethod
    def build_drawdown_chart(df_drawdowns: pd.DataFrame, theme_colors: dict) -> go.Figure:
        fig = go.Figure()
        for column in df_drawdowns.columns:
            fig.add_trace(go.Scatter(
                x=df_drawdowns.index,
                y=df_drawdowns[column],
                mode='lines',
                name=column,
                fill='tozeroy',
                line={"width": 2}
            ))
        return ComparisonChartFactory._apply_theme_layout(fig, "Maksimum Drawdown Analizi (%)", theme_colors)
```