# Aşama 4: Uygulama Entegrasyonu ve Sayfa Akışı (AnalysisPage Entegrasyonu)

## 📌 Amaç
Bu aşamada, yeni "Karşılaştırma" bölümünün [analysis_page.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/analysis/analysis_page.py) (Analiz Sayfası) içerisine entegrasyonu ve genel sayfa akışı belgelenmiştir. Sistem, tüm analiz işlevlerini ("Genel Bakış", "Karşılaştırma", "Dağılım & Risk") tek bir sekme yapısında (TabWidget) birleştirerek düzenli bir kokpit arayüzü sunmaktadır.

## 📁 Dosya Hedefi
- [analysis_page.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/analysis/analysis_page.py) (Filtre kontrol ve tab yönetiminin yapıldığı ana sayfa)

## 🏗️ Mimari Gereksinimler ve Kurallar
1. **Tek Noktadan Veri Akışı:** `AnalysisPage` merkezi bir controller görevi üstlenerek sağdaki [analysis_control_panel.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/analysis/analysis_control_panel.py) filtre panelindeki değişimleri dinler, tek bir asenkron Worker çağrısıyla (`get_page_payload`) tüm alt sayfaların verisini çeker ve sekmelere dağıtır.
2. **TabWidget Entegrasyonu:** Sol menüdeki ana "Analiz" sayfa yapısı korunur, böylece sol menünün karmaşıklaşması engellenir. Karşılaştırma modülü sayfa içi sekme olarak konumlandırılır.

## 🛠️ Entegrasyon Adımları ve Sayfa Yapısı

### 1. Sekmelerin (TabWidget) Tanımlanması
`AnalysisPage._init_ui` metodu içerisinde `QTabWidget` oluşturulur ve alt bölümler sekme olarak eklenir:
```python
self.overview_section = AnalysisOverviewSection()
self.comparison_section = AnalysisComparisonSection()
self.risk_section = AnalysisRiskSection()

self.tabs.addTab(self._wrap_scroll(self.overview_section), "Genel Bakış")
self.tabs.addTab(self._wrap_scroll(self.comparison_section), "Karşılaştırma")
self.tabs.addTab(self._wrap_scroll(self.risk_section), "Dağılım & Risk")
```

### 2. Filtre Kontrol Paneli (`AnalysisControlPanel`)
Sayfanın sağ tarafında dikey olarak konumlanan ve 320px-360px genişliğe sahip paneldir:
- **Portföy Kaynağı:** "Dashboard" (Gerçek portföy) veya kayıtlı sanal portföyler seçilebilir.
- **Tarih Aralığı:** Birleşik tarih aralığı kartı üzerinden başlangıç ve bitiş tarihleri.
- **Benchmark Karşılaştırmaları:** BIST100, Altın, Mevduat, Dolar vb. kıyaslanacak benchmark'ların seçilebildiği iki kolonlu çip grubu.
- **Dinamik Portföy Karşılaştırmaları:** Diğer sanal portföylerle performans kıyası için checkbox listesi.
- **Para Birimi Modu:** TL, USD ve REAL (Enflasyondan Arındırılmış) getiri modları.

### 3. Asenkron payload Veri Dağıtımı
Veriler başarıyla yüklendiğinde tetiklenen `_on_payload_ready` metodu, tek bir merkezi veri paketini (payload) parçalayarak ilgili sekmelere dağıtır:
```python
def _on_payload_ready(self, request_id: int, payload: dict) -> None:
    if request_id != self._request_seq:
        return
    self.warning_banner.hide()
    self.overview_section.set_data(payload["overview"])
    self.comparison_section.set_data(payload["comparison"])
    self.risk_section.set_data(payload["risk"])
```

## 🏁 Entegrasyon Sonrası Kontrol Listesi
- [x] Uygulama hatasız olarak ayağa kalkıyor.
- [x] Sol menüden "Analiz" sekmesine geçildiğinde, "Karşılaştırma" sekmesi sorunsuz olarak yükleniyor.
- [x] Sağdaki filtre panelinden benchmark veya tarih değiştirildiğinde arka planda asenkron istek tetiklenip sayfaları yeniliyor.
- [x] Seçilen para birimine göre (USD/REAL) fiyat serileri dönüştürülüyor ve Plotly grafiğinde normalize edilerek gösteriliyor.