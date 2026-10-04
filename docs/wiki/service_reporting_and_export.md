# Raporlama ve Dışa Aktarım (Excel, HTML)

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md) | Simülasyon: [service_simulation.md](service_simulation.md)

Kod: `src/application/services/reporting/`. İki tür çıktı vardır: tarihsel portföy **Excel** raporları (`openpyxl`) ve arayüzde WebEngine ile gösterilen **HTML** üreticileri (Plotly dashboard'ları).

## 1. Excel Raporlama

### Servisler

| Servis | Görev |
|---|---|
| `ExcelExportService.export_history(start, end, file_path, mode)` | Ana portföy tarihsel raporu: `HistorySimulationService` ile günlük snapshot üretir ve `ExcelReportBuilder`'a verir. |
| `ModelPortfolioExcelExportService` | `export_model_portfolio_history(...)` model portföyün tarihsel raporu; `export_model_portfolio(...)` anlık görüntü. |
| `ExcelReportBuilder` | Çalışma kitabını yazar (`build_and_save`); tarih sütunu normalizasyonu. |
| `ExcelDataPreparer` | Snapshot'ı tablo verisine (liste/tuple) çevirir. |
| `ExcelFormatter`, `ExcelTheme`, `ExcelLayoutManager` | Hücre tipi/biçim, kurumsal renk paleti ve kenarlık, sütun genişliği ve dondurulmuş satırlar. |
| `ExcelDashboardStatsCalculator` | Özet panel KPI metinleri ve en büyük pozisyonlar. |
| `ExcelAppendMerger` | Mevcut dosyaya ekleme: birleştirme, tekrar ayıklama ve yedek. |

### Çalışma kitabı

Dört sayfa: `Özet Panel`, `Portföy Özeti`, `Günlük Detaylar`, `Hisse Özeti`. (Grafik odaklı sayfalar kaldırılmıştır.)

### Ekleme modu ve tekrar engelleme

Arayüzde "mevcut dosyaya ekle" seçilirse yeni günler mevcut dosyaya eklenir; dosya yoksa yeni oluşturulur. `Timestamp` ve düz `date` karışıklığı ortak normalizasyonla giderilir; aynı tarihin eski satırları yenileriyle ezilir, böylece tek temiz tarih listesi kalır. Dosya yoksa taze yazılır, izin hatası kullanıcıya açık mesajla yükseltilir, bozuk çalışma kitabı yedeklenip yeniden oluşturulur; sessiz `except: pass` yoktur.

### Fiyat sözleşmesi

Tarihsel raporlar yalnızca `daily_prices` kapanışını kullanır; canlı fiyat (`latest_prices`, ekrandaki anlık değerler) rapora karışmaz. Model portföy raporu öncesi arayüz seçili `model:<id>` kapsamı için fiyat sağlığı analizi çalıştırır; eksik kapanış varsa dosya seçilmeden kullanıcıya hisse/tarih listesi gösterilir, böylece ekrandaki gecikmeli fiyatla rapordaki DB kapanışı arasında sessiz uyumsuzluk oluşmaz.

### Arayüz girişleri

| Yer | İşlev |
|---|---|
| Genel Bakış > Excel Raporu (`ExcelExportDialog`) | Tarih aralığı (boş = ilk işlemden bugüne), hedef dosya, ekleme modu; `DashboardController.exportToExcelFile`. |
| Model Portföy > Rapor | `ModelPortfolioController.exportHistoryToFile` aynı diyalogla. |
| Hisse Detay > "Hisse Geçmişini Excel'e Aktar" | `StockDetailController.exportStockToExcel`: hisseye özel işlem ve pozisyon raporu. |
| Ayarlar > Dışa Aktarım | Portföy Excel raporu (`exportPortfolioToExcel`) ve JSON yedeği ([database_maintenance_and_scripts.md](database_maintenance_and_scripts.md)). |

Tüm dışa aktarımlar arka plan iş parçacığında çalışır; sonuç sinyalle toast olarak gösterilir.

## 2. HTML Üreticileri (`reporting/html/`)

Arayüzden bağımsız, saf HTML üreten modüller; denetleyici çıktıyı geçici dosyaya yazıp QML `WebEngineView` ile gösterir ([stock_360.md](stock_360.md)).

| Modül | Üretim |
|---|---|
| `financials_dashboard.py` (+ `financials_charts`, `financials_table`, `financials_value_table`) | Hisse 360 finansal dashboard: grafikler, etkileşimli tablo, değer tabloları (koyu tema). |
| `shareholders_dashboard.py` | KAP ortaklık yapısı dashboard'u. |
| `plotly_html.py` | Plotly HTML kapsayıcısı; `ensure_patched_plotly_js` yerel yama uygulanmış Plotly JS'i (`plotly-shared-patched.min.js`) üretir. Eski Chromium'un `:focus-visible` CSS kuralını ayrıştıramaması `Plotly is not defined` hatasına yol açtığından `CSSStyleSheet.insertRule` yaması Plotly paketinden önce uygulanır; ağ kullanılmaz. |

`PriceDataReportFormatter` (market servisleri) fiyat sağlığı raporunu HTML veya düz metne çevirir.

## 3. Testler

`tests/application/test_excel_report_builder.py`, `test_model_portfolio_excel_export_service.py`, `test_friday_excel_export_bug.py` (hafta sonu/cuma düzeltmesi), `tests/application/reporting_html/` (Plotly ve finansal dashboard HTML), `tests/ui_qml/test_stock_detail_and_excel.py`, `test_dashboard_updates.py`.
