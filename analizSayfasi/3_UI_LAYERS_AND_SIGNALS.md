# Aşama 3: UI Katmanı ve Sinyal Mekanizması (ComparisonPage)

## 📌 Amaç
Bu aşamada, `ComparisonService` ve `ComparisonChartFactory` modüllerini görsel arayüze bağlayacak olan PyQt tabanlı `ComparisonPage` widget sınıfı yazılacaktır. Sayfa, sağdaki eski filtre panelinden arındırılmış, üstten yatay şeritli (Ribbon Bar) ve TradingView tarzı lokal zaman butonlarına sahip modern bir aracı kurum terminali düzeninde olacaktır.

## 📁 Dosya Hedefi
- [comparison_page.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/comparison/comparison_page.py) (Yeni dosya)
- [ribbon_bar.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/ui/pages/comparison/widgets/ribbon_bar.py) (Yardımcı üst bar bileşeni)

## 🏗️ Mimari Gereksinimler ve Kurallar
1. **Bileşen Tabanlı Tasarım (Component-Based UI):** Satır sınırını (`RULES.md` < 300 satır) aşmamak için üst kontrol şeridi (`RibbonBar`) ayrı bir dosyada widget olarak yazılmalı, ana sayfa sınıfı (`ComparisonPage`) sadece layout orkestrasyonunu ve sinyal-slot yönetimini yapmalıdır.
2. **Dinamik Tema Uyumu:** Tüm arayüz elementleri (QComboBox, QPushButton, QDateEdit) `ThemeManager`'ın dinamik token tabanlı stillerine ve QSS kurallarına göre aktif temayla (koyu/açık) uyumlu olacak şekilde tasarlanacaktır.
3. **QWebEngineView Yönetimi:** Plotly grafiklerini gösterecek olan `QWebEngineView` bileşenleri sayfa yüklendiğinde asenkron olarak beslenmeli ve arayüzü kilitlememelidir.

## 🛠️ Uygulama Adımları ve Bileşen Detayları

### 1. Üst Kontrol Şeridi (`ComparisonRibbonBar`)
Sayfanın en üstünde yatay (`QHBoxLayout`) olarak konumlanacak bileşendir:
- **Multi-Asset Selector (`QComboBox` veya Özel Checkable ComboBox):** Kullanıcının kıyaslamak istediği varlıkları (Portföy, BIST100, Altın vb.) çoklu seçebileceği alan.
- **Grafik Modu Dropdown (`QComboBox`):** "Normal", "Normalize (Baz 100)" ve "Rasyo Modu" seçeneklerini barındırır.
- **Dinamik Rasyo Seçiciler (Pay/Payda `QComboBox`'ları):** Varsayılan olarak gizlidir (`setVisible(False)`). Grafik modu "Rasyo Modu" seçildiğinde sinyal mekanizmasıyla görünür hale gelir.
- **Tarih Aralığı (`QDateEdit`):** Başlangıç ve Bitiş tarihlerinin elle seçilebileceği iki takvim kutusu.

### 2. TradingView Tarzı Lokal Zaman Butonları
Ana grafiğin hemen üst sol köşesine yerleştirilecek yatay buton grubudur:
- **Butonlar:** `[1A]` (1 Ay), `[3A]` (3 Ay), `[6A]` (6 Ay), `[1Y]` (1 Yıl), `[YBB]` (Yıl Başından Beri), `[Tümü]`.
- **Çalışma Mantığı:** Bu butonlardan birine tıklandığında (Örn: `1A`), bir slot fonksiyonu tetiklenir. Fonksiyon, bugünün tarihinden 1 ay gerisini hesaplar, üst bardaki `QDateEdit` başlangıç tarihini otomatik günceller ve grafik yenileme sinyalini (`emit`) tetikler.

### 3. Ekran Düzeni ve Grid Layout (`ComparisonPage`)
Ana sayfa dikey bir `QVBoxLayout` içerir:
1. En üstte `ComparisonRibbonBar`.
2. Altında TradingView Zaman Butonları şeridi.
3. Merkezde `QSplitter` (Yatay bölücü):
   - Sol bölme: Ana Grafik Ekranı (`QWebEngineView`)
   - Sağ bölme: Dönem Sonu Getiri Özeti Tablosu (`QWebEngineView` - `go.Table`)
4. En altta, aşağı doğru kaydırılabilen (`QScrollArea`) ve alt grafikleri içeren 2x2'lik bir `QGridLayout`:
   - Sol Üst: Maksimum Drawdown Grafiği
   - Sağ Üst: Dönemsel Getiri Çubuk Grafiği
   - Sol Alt: Risk-Getiri Dağılımı (Scatter)
   - Sağ Alt: Getiri Katkı Haritası (Treemap)

## 🔀 Sinyal ve Slot Mekanizması (Signals & Slots)
```python
# Ribbon bar veya zaman butonları değiştiğinde tetiklenecek akış:
def on_filter_changed(self):
    # 1. Filtre değerlerini oku (Varlıklar, Tarihler, Grafik Modu)
    # 2. ComparisonService üzerinden hesaplamaları arka planda (Worker/Thread veya hızlıca) yap
    # 3. ComparisonChartFactory metodlarını çağırarak go.Figure nesnelerini üret
    # 4. Çıkan figürleri .to_html() veya JSON olarak QWebEngineView içeriklerine setHtml() ile enjekte et
```