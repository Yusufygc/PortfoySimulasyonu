# Excel Raporlama ve Dışa Aktarım (Export) Servisleri

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, `src/application/services/reporting` dizinindeki Excel üretim ve raporlama süreçlerini detaylandırır. Uygulama, geçmiş portföy verisini ve model portföy analizlerini `openpyxl` kütüphanesi kullanarak Excel (.xlsx) formatında dışa aktarır.

## 1. Raporlama Mimarisi

Raporlama sistemi, birbirine sıkı sıkıya bağlı olmayan, tek sorumluluk prensibine (SRP) uyan bileşenlere ayrılmıştır:

| Sınıf / Modül | Sorumluluk |
| --- | --- |
| `ExcelExportService` | İşlemi başlatan ana servistir. Raporun hazırlanmasını koordine eder. |
| `ExcelDataPreparer` | Portföy ve model portföy verilerini (Snapshot) alır, Excel'e yazılabilecek listeler / tuple'lar haline getirir. |
| `ExcelFormatter` | Hücrelerin veri tiplerini (sayı, yüzde, tarih) ayarlar ve biçimlendirme yapar. |
| `ExcelTheme` | Başlık renkleri, fontlar ve tablo kenarlık (border) ayarlarını (QSS Tokens mantığına benzer şekilde) uygular. |
| `ExcelLayoutManager` | Excel sayfasındaki kolon genişliklerini ve freeze panes (sabit dondurulmuş satırlar) ayarlarını yönetir. |

## 2. Duplicate Günlük Veri Engelleme (Append Mode)

Tarihsel verilerin sürekli olarak Excel dosyasına eklenmesi durumunda aynı tarih satırlarının tekrar etmesini engellemek için "Tarih Normalizasyonu ve Dedup" mantığı uygulanır. 

- Yeni veriler eklendiğinde `Timestamp` ve düz `Date` formatları birbirine karışabilir. 
- Ortak helper fonksiyonlar vasıtasıyla Excel dosyası append (üzerine ekleme) modunda açılır, verilerdeki aynı tarihe ait eski satırlar varsa yenileriyle ezilir ve tek bir temiz tarih listesi oluşturulur.

## 3. Akış Şeması

```mermaid
sequenceDiagram
    UI->>ExcelExportService: Rapor Al (Bugün / Tarih Aralığı)
    ExcelExportService->>SimulationService: Belirtilen tarihler için snapshot al
    ExcelExportService->>ExcelDataPreparer: Snapshot'ı tablo verisine çevir
    ExcelDataPreparer-->>ExcelExportService: Raw Data
    ExcelExportService->>OpenPyXL: Workbook oluştur
    ExcelExportService->>ExcelFormatter: Verileri Formatla
    ExcelExportService->>ExcelTheme: Tablo stillerini uygula
    ExcelExportService->>UI: Başarı Durumu ve Dosya Yolu
```
## Faz 2 Notu (2026-06-02)

- `ExcelReportBuilder._append_to_existing_excel` içindeki silent `except Exception: pass` kaldırıldı.
- Dosya yoksa fresh write yapılır; permission hataları kullanıcıya açık mesajla yükseltilir; corrupt workbook okuma hatasında mevcut backup + yeniden oluşturma davranışı korunur.
- Büyük reporting sınıfları için daha ileri parçalara ayırma adayı devam eder: append/dedup mantığı `ExcelAppendMerger`, dashboard stats ayrı calculator.

## Faz 2D Notu (2026-06-02)

- Append/dedup/backup davranışı `ExcelAppendMerger` sınıfına taşındı; `ExcelReportBuilder` writer orchestration ve formatting akışını yönetir.
- Dashboard KPI metinleri ve top holding hesapları `ExcelDashboardStatsCalculator` içinde tutulur.
- Excel dışa aktarım artık dört çalışma sayfası üretir: `Özet Panel`, `Portföy Özeti`, `Günlük Detaylar`, `Hisse Özeti`.
- Grafik odaklı `Grafikler` ve `Grafik Verileri` sayfaları kaldırıldı; workbook sözleşmesi sadeleştirildi.

## Model Portfoy Rapor Fiyat Sozlesmesi (2026-06-06)

- Model portfoy Excel raporlari tarihsel rapordur ve degerleme icin yalniz `daily_prices` kapanis verisini kullanir; ekranin canli `current_price_map` degerleri rapora overlay edilmez.
- UI export akisi rapor uretmeden once secili `model:<id>` kapsaminda `PriceDataHealthService.analyze(...)` calistirir. Eksik kapanis fiyati varsa dosya secme ve Excel export cagrisi baslamadan kullaniciya hisse/tarih listesi gosterilir.
- Bu kapi, model portfoy ekraninda gorunen gecikmeli/canli fiyat ile Excel raporundaki DB kapanis fiyati arasinda sessiz uyumsuzluk olusmasini engeller.
