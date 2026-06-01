# Aşama 4: Navigasyon ve Uygulama Entegrasyonu (MainWindow Refactor)

## 📌 Amaç
Bu aşamada, yazılan yeni "Karşılaştırma Laboratuvarı" sayfasını uygulamanın ana penceresine (`MainWindow`) entegre edeceğiz. Sol menüye (Sidebar) yeni sayfa için dinamik temaya uygun bir buton ekleyecek, sayfa indekslerini güncelleyecek ve eski analiz sayfasındaki ("PAGE_ANALYSIS") kalabalık tab yapısını temizleyerek sistemi ayağa kaldıracağız.

## 📁 Dosya Hedefi
- [main_window.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/main_window.py) (Mevcut dosya güncellenecek)
- [analysis_page.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/analysis/analysis_page.py) (Mevcut dosyadaki karşılaştırma tabı kaldırılacak)

## 🏗️ Mimari Gereksinimler ve Kurallar
1. **Gevşek Bağlılık (Loose Coupling):** `MainWindow`, yeni sayfanın iç mantığını veya filtre süreçlerini bilmemelidir. Sadece sayfayı `QStackedWidget` içerisine eklemeli ve menüden tıklandığında ilgili indekse geçişi (Router görevi) sağlamalıdır.
2. **Temiz Kod / Satır Sınırı:** `MainWindow` içerisindeki sayfa ekleme ve buton bağlama mantığı sade tutulmalı, `RULES.md` uyarınca dosya büyümesinin önüne geçilmelidir.
3. **Dinamik Tema Uyumu:** Sol menüye eklenecek yeni butonun normal, hover ve active durumlarındaki QSS tasarımları, dinamik tema sistemine (`ThemeManager` ve `@COLOR` token'ları) tamamen uyumlu olacak şekilde tasarlanacaktır.

## 🛠️ Uygulama Adımları ve Entegrasyon Detayları

### 1. Sayfa İndekslerinin ve StackedWidget Yapısının Güncellenmesi
- `src/ui/main_window.py` dosyasındaki sayfa sabitlerine (Constants) yeni bir indeks eklenmelidir:
  ```python
  PAGE_DASHBOARD = 0
  PAGE_PORTFOLIO = 1
  PAGE_ANALYSIS = 2
  PAGE_COMPARISON = 3  # Yeni eklenen Karşılaştırma Laboratuvarı sayfası
  ```

- `MainWindow.__init__` veya `setup_ui` metodu içerisinde, `QStackedWidget` bileşenine yeni sayfamızın örneği (Instance) eklenmelidir:
  ```python
  from src.ui.pages.comparison.comparison_page import ComparisonPage

  self.comparison_page = ComparisonPage()
  self.stacked_widget.addWidget(self.comparison_page)
  ```

### 2. Sol Menü (Sidebar) Güncellemesi ve Buton Tasarımı
Sol menü şeridine "Analiz" butonunun hemen altına gelecek şekilde "Karşılaştırma" (veya "Kıyaslama Lab") butonu eklenmelidir.
- **İkon seçimi:** Kurumsal yapıyı destekleyen, çizgi grafikleri veya üst üste binen katmanları temsil eden bir ikon (layers, bar-chart-2 veya sliders türevi) seçilmelidir.
- Butona tıklandığında `self.stacked_widget.setCurrentIndex(PAGE_COMPARISON)` slotu tetiklenmelidir.
- Sayfa geçişlerinde sol menüdeki aktif buton vurgusunun (Highlight) yeni butona da hatasız uygulanması sağlanmalıdır.

### 3. Eski Analiz Sayfasının (AnalysisPage) Hafifletilmesi
- `src/ui/pages/analysis/analysis_page.py` içerisindeki `QTabWidget` yapısı veya "Karşılaştırma" sekmesi (Tab) tamamen koddan kaldırılmalıdır.
- Eski sayfadaki sağ dikey filtre paneli temizlenmeli, analiz sayfası da kendi içinde yatay üst şerit (Ribbon Bar) düzenine geçirilerek sadeleştirilmelidir.
- Böylece eski sayfa sadece portföy içi performans, varlık dağılımı ve risk metriklerine (Sharpe, Drawdown vb.) odaklanan temiz bir "Portföy Analiz Kokpiti" haline gelecektir.

## 🏁 Entegrasyon Sonrası Kontrol Listesi (Checklist)
- [ ] Uygulama hatasız ayağa kalkıyor mu?
- [ ] Sol menüden "Karşılaştırma" butonuna basıldığında yeni sayfa tam ekran ve ferah bir şekilde yükleniyor mu?
- [ ] Grafik modundan "Rasyo Modu" seçildiğinde Pay/Payda combo-box'ları dinamik olarak beliriyor mu?
- [ ] TradingView tarzı hızlı tarih butonlarına (1A, 3A vb.) tıklandığında grafikler asenkron olarak ve donma olmadan güncelleniyor mu?
- [ ] Tüm arayüz elemanları dinamik tema (ThemeManager) standartlarına uyuyor mu?