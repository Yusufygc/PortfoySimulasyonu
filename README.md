# 📈 Portföy Simülasyonu ve Takip Sistemi (V1.0)

Portföy Simülasyonu, BIST (Borsa İstanbul) hisse senedi yatırımlarınızı takip etmenizi, maliyet analizi yapmanızı ve portföyünüzün performansını simüle etmenizi sağlayan kapsamlı bir masaüstü uygulamasıdır.

Bu proje, Clean Architecture prensiplerine sadık kalınarak, sürdürülebilir ve geliştirilebilir bir yapıda tasarlanmıştır.

## 🚀 Özellikler

### 1. İşlem Yönetimi
- **Kolay Ekleme**: Yeni hisse senetleri ekleyebilir veya mevcut hisseleriniz için "Alış" (BUY) / "Satış" (SELL) işlemleri girebilirsiniz.
- **Akıllı Sihirbaz**: Yeni işlem ekleme ekranı, hisse fiyatını otomatik sorgular ve sizi adım adım yönlendirir.
- **Validasyon**: Elde olmayan lotun satılmasını engelleyen iş kuralları mevcuttur.

### 2. Finansal Analiz
- **Maliyet Hesabı**: Portföydeki pozisyonlar Ağırlıklı Ortalama Maliyet (Weighted Average Cost) yöntemine göre dinamik olarak hesaplanır.
- **Getiri Takibi**: Günlük, haftalık ve aylık bazda portföyünüzün getiri oranlarını ve kâr/zarar durumunu anlık takip edebilirsiniz.
- **Görsel Bildirimler**: Kârda olan pozisyonlar yeşil, zararda olanlar kırmızı ile renklendirilerek hızlı analiz imkanı sunar.

### 3. Veri Entegrasyonu
- **Otomatik Fiyat Güncelleme**: yfinance kütüphanesi entegrasyonu sayesinde, tek tuşla tüm portföyünüzün güncel piyasa fiyatlarını çekebilirsiniz.
- **BIST Uyumluluğu**: Borsa İstanbul hisseleri (örn: ASELS, THYAO) için otomatik .IS uzantısı desteği sunar.

### 4. Raporlama ve Dışa Aktarım
- **Excel Export**: Portföyünüzün detaylı tarihçesini, günlük değişimlerini ve hisse bazlı özetlerini Excel formatında dışarı aktarabilirsiniz.
- **Veritabanı**: Tüm veriler güvenli bir şekilde yerel MySQL veritabanında saklanır.

## 🛠️ Kurulum

Projeyi yerel makinenizde çalıştırmak için aşağıdaki adımları izleyin.

### Gereksinimler
- Python 3.9 veya üzeri
- MySQL Veritabanı

### 1. Projeyi Klonlayın

```bash
git clone https://github.com/kullaniciadi/portfoy-simulasyonu.git
cd portfoy-simulasyonu
```

### 2. Sanal Ortamı Kurun (Önerilen)

```bash
# Windows için
python -m venv venv
.\venv\Scripts\activate

# macOS/Linux için
python3 -m venv venv
source venv/bin/activate
```

### 3. Bağımlılıkları Yükleyin

```bash
pip install -r requirements.txt
```

> **Not**: Eğer `requirements.txt` yoksa:
> ```bash
> pip install PyQt5 yfinance pandas openpyxl python-dotenv mysql-connector-python
> ```

### 4. Veritabanı Ayarları

Proje ana dizininde `.env` adında bir dosya oluşturun ve veritabanı bilgilerinizi girin:

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=sifreniz
DB_NAME=portfoy_db
DB_PORT=3306
```

### 5. Uygulamayı Başlatın

```bash
python app.py
```

## 🏗️ Proje Mimarisi

Uygulama, sorumlulukların ayrılığı ilkesine dayanan katmanlı bir mimariye sahiptir:

- **src/domain**: İş kuralları, veri modelleri (Stock, Trade, Portfolio) ve soyut arayüzler (Interfaces).
- **src/infrastructure**: Veritabanı bağlantıları (MySQL), dış servisler (yfinance) ve repository implementasyonları.
- **src/application**: Uygulama mantığı, servisler (PortfolioService, ReturnCalcService) ve kullanım senaryoları.
- **src/ui**: Kullanıcı arayüzü (PyQt5), pencereler ve widget'lar.

## 🔮 Gelecek Planları (Roadmap)

Bu proje şu anda Versiyon 1.0 (MVP) aşamasındadır. İlerleyen dönemlerde eklenmesi planlanan özellikler şunlardır:

- [ ] **Asenkron İşlemler**: Fiyat güncelleme işlemlerinin arka planda (Threading) yapılarak arayüz donmalarının engellenmesi.
- [ ] **Gelişmiş Grafikler**: Portföy dağılımı (Pasta Grafik) ve tarihsel getiri eğrisi (Çizgi Grafik) gibi görsel analiz araçları.
- [ ] **Çoklu Para Birimi**: Sadece TRY değil, USD/EUR bazlı hisse ve varlık takibi.
- [ ] **Temettü Takibi**: Hisselerin temettü ödemelerinin otomatik işlenmesi.
- [ ] **Mobil/Web Arayüzü**: Masaüstü bağımlılığını azaltmak için web tabanlı bir dashboard.
- [ ] **Gelişmiş Hata Yönetimi**: Loglama altyapısının güçlendirilmesi ve kullanıcı dostu hata mesajları.

## 🤝 Katkıda Bulunma

Projeye katkıda bulunmak isterseniz, lütfen bir Fork oluşturun ve değişikliklerinizi Pull Request olarak gönderin. Hata bildirimleri ve önerileriniz için "Issues" bölümünü kullanabilirsiniz.

---

**Geliştirici**: Muhammed Yusuf Yağcı 
**İletişim**: yusufygc118@gmail.com  
**Proje Durumu**: Aktif Geliştirme (v1.0)