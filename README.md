# 📈 Portföy Simülasyonu (Portfolio Simulation)

**Portföy Simülasyonu**, yatırımcıların portföylerini gerçek zamanlı piyasa verileriyle takip etmelerini, geçmiş performanslarını analiz etmelerini ve farklı yatırım senaryolarını test etmelerini sağlayan kapsamlı bir masaüstü uygulamasıdır. Modern ve kullanıcı dostu arayüzü, güçlü veritabanı altyapısı ve detaylı analiz araçlarıyla profesyonel bir deneyim sunar.

---

## 🚀 Özellikler

### 📊 Kapsamlı Dashboard
*   **Genel Bakış:** Toplam portföy değeri, günlük değişimler, kar/zarar durumu ve nakit dengesini tek bir ekranda görüntüleyin.
*   **Görsel Grafikler:** Varlık dağılımı ve performans grafiklerini inceleyin.

### 💼 Portföy Yönetimi
*   **İşlem Kaydı:** Hisse senedi alım/satım işlemlerinizi kolayca kaydedin.
*   **Pozisyon Takibi:** Açık pozisyonlarınızın maliyet, adet ve güncel değerlerini anlık olarak izleyin.
*   **Tarihsel Veri:** Geçmiş işlemlerinizi ve portföy değişimlerinizi analiz edin.

### 🔍 Detaylı Hisse Analizi
*   **Teknik & Temel Veriler:** Seçtiğiniz hisse senedinin detaylı piyasa verilerine, grafiklerine ve temel analiz rasyolarına ulaşın.
*   **Dinamik Grafikler:** Fiyat hareketlerini etkileşimli grafikler üzerinde inceleyin.

### 📋 Takip Listeleri (Watchlists)
*   **Özel Listeler:** İlgilendiğiniz hisseleri kategorize ederek kendi takip listelerinizi oluşturun.
*   **Hızlı Erişim:** Piyasa hareketlerini yakından izlemek için listeler arasında hızlıca geçiş yapın.

### 🧪 Model Portföyler
*   **Senaryo Analizi:** Gerçek portföyünüzü etkilemeden sanal portföyler oluşturun ve stratejilerinizi test edin.
*   **Performans Karşılaştırma:** Farklı yatırım stratejilerinin potansiyel getirilerini karşılaştırın.

### 📉 Excel Dışa Aktarım
*   **Raporlama:** Portföy durumunuzu, işlem geçmişinizi ve analizlerinizi Excel formatında dışa aktararak harici analizler yapın.

---

## 🛠️ Teknoloji Yığını ve Mimari

Bu proje, **Clean Architecture** (Temiz Mimari) ve **Domain-Driven Design** (DDD) prensiplerine sadık kalarak geliştirilmiştir. Bu sayede sürdürülebilir, test edilebilir ve genişletilebilir bir kod tabanı sunar.

*   **Dil:** Python 3.x
*   **Arayüz (GUI):** PyQt5 (Modern, responsive tasarım)
*   **Veritabanı:** MySQL (Güvenilir veri saklama)
*   **Veri Sağlayıcı:** yfinance (Yahoo Finance API)
*   **Veri Analizi:** Pandas, OpenPyXL
*   **ORM/Veri Erişimi:** Custom Repository Pattern

---

## � Proje Yapısı

```
PortfoySimulasyonu/
├── app.py                  # Uygulama giriş noktası
├── config/                 # Konfigürasyon dosyaları
├── src/
│   ├── application/        # İş mantığı ve servisler (Use Cases)
│   ├── domain/             # Temel iş varlıkları (Entity layer)
│   ├── infrastructure/     # Veritabanı ve dış servis entegrasyonları
│   └── ui/                 # Kullanıcı arayüzü (Pages, Widgets, Styles)
├── icons/                  # Uygulama ikonları
└── requirements.txt        # Bağımlılıklar
```

---

## ⚙️ Kurulum ve Çalıştırma

### Gereksinimler
*   Python 3.8 veya üzeri
*   MySQL Server

### Adım 1: Depoyu Klonlayın
```bash
git clone https://github.com/Yusufygc/PortfoySimulasyonu.git
cd PortfoySimulasyonu
```

### Adım 2: Sanal Ortam Oluşturun (Önerilen)
```bash
python -m venv venv
# Windows için:
venv\Scripts\activate
# macOS/Linux için:
source venv/bin/activate
```

### Adım 3: Bağımlılıkları Yükleyin
```bash
pip install -r requirements.txt
```

### Adım 4: Veritabanı Yapılandırması
Projenin çalışması için bir MySQL veritabanına ihtiyacı vardır. `.env` dosyası veya `config` klasörü içerisindeki ayarları kendi veritabanı bilgilerinize göre düzenleyin.

### Adım 5: Uygulamayı Başlatın
python app.py

