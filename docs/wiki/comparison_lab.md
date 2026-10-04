> Ana sayfa: [index.md](index.md) | Analiz servisleri: [service_analysis.md](service_analysis.md) | Sayfa rehberi: [qml_pages_guide.md](qml_pages_guide.md)

# Karşılaştırma Laboratuvarı

Karşılaştırma Lab (`ComparisonView`, `ComparisonController`), portföyleri, benchmark'ları ve hisseleri aynı eksende getiri, kayıp ve risk açısından kıyaslayan sayfadır. Hesaplar servis katmanındadır ([service_analysis.md](service_analysis.md)); denetleyici seçimi çözer, hesabı arka planda çalıştırır ve grafik HTML'ini üretir.

## 1. Kullanıcı Akışı

1. **Varlık seçimi:** sol panelde çoklu seçim. Seçenekler: Ana Portföy, her model portföy, her biri için sanal **"<Portföy> + Hisseleri"** (`holdings:<kod>`; portföyün kendisi ve içindeki tüm hisseler tek tek kıyaslanır), benchmark'lar (BIST 100, altın, gümüş, USD/TRY, EUR/TRY, mevduat faizi, TÜFE). Başlangıçta ilk iki seçenek seçilir.
2. **Dönem:** `1A`, `3A`, `6A`, `1Y`, `YBB` (yıl başından bugüne), `Tümü` (2022-01-01'den), `ÖZEL` (GG.AA.YYYY veya YYYY-AA-GG). Dönem seçimi hesabı yeniden çalıştırır.
3. **Mod:** `Normal` (fiyat/değer), `Normalize (Baz 100)`, `Rasyo (A / B)` (pay ve payda varlıkları seçilir).
4. **Para birimi:** TL, USD, Reel (TÜFE'den arındırılmış).
5. **Karşılaştır:** `runComparison` arka plan iş parçacığında çalışır; tamamlanınca aktif sekme çizilir.

## 2. Grafik Sekmeleri

| Sekme | İçerik | Çizim |
|---|---|---|
| Kümülatif Getiri | Seçili varlıkların normal/normalize/rasyo eğrileri | TradingView Lightweight Charts |
| Maks. Düşüş (Drawdown) | Tarihsel zirveden düşüş yüzdesi (sıfır çizgisinin altı) | Lightweight Charts |
| Aylık Getiriler | Varlıkların aylık net getirileri yan yana | Chart.js çubuk |
| Risk-Getiri Saçılımı | Yıllık volatilite (x) ve toplam getiri (y) | Chart.js saçılım |
| Getiri Katkı Haritası (Treemap) | Kutu alanı ağırlık, renk getiri; "Portföy Hisseleri" veya "Varlık Kıyaslaması" türü, portföy seçimi | HTML/Canvas |

Altta **risk ve getiri tablosu** (varlık, toplam getiri %, yıllık volatilite %) yer alır. Her grafiğin üstündeki **bilgi kartı** (`ChartInfoCard`, varsayılan kapalı) "Nedir / Nasıl Yorumlanır" açıklamalarını sekme ve moda göre gösterir; metinler `Strings.qml`'dedir.

## 3. Yapay Zekâ Yorumu

"Yapay Zeka Yorumu" düğmesi (`ComparisonAiDialog`) seçili varlıkların toplam getiri ve volatilitesini, dönemi, modu ve para birimini bir istem metnine çevirir ve `AiChatService` ile Gemini'ye gönderir; sonuç diyalogda gösterilir ("Yorumu Yenile" ile tekrar üretilir). İstem yatırım tavsiyesi vermemesini ister; ekranda "kişisel yatırım tavsiyesi değildir" uyarısı bulunur. API anahtarı yoksa hata mesajı gösterilir ([ai_integration.md](ai_integration.md)).

## 4. Veri ve Hizalama Kuralları

- Seriler `ComparisonService.align_financial_series` ile ortak tarih indeksinde hizalanır (tatil farkları ileri doldurma ile kapanır); en az 2 ortak gün yoksa boş durum gösterilir.
- Hesap `AnalysisFilterState` ile `AnalysisService.get_comparison_view` üzerinden yapılır; birden çok portföy seçildiğinde `comparison_portfolio_sources` taşınır, ilk portföy birincil kaynaktır.
- Grafikte kullanılan JS kütüphaneleri uygulamayla birlikte gelir (`assets/js/`); CDN'e yalnızca yerel dosya okunamazsa düşülür.

## 5. Plotly ve Yama Notu

Karşılaştırma grafikleri Plotly kullanmaz. Plotly yalnızca Hisse 360'taki finansal dashboard ve ortaklık HTML'inde kullanılır (`reporting/html/plotly_html.py`, `financials_dashboard.py`). Eski QtWebEngine Chromium'u Plotly'nin `:focus-visible` CSS kuralını ayrıştıramayıp `Plotly is not defined` hatasıyla grafikleri boş bırakabildiği için `plotly_html.py` `CSSStyleSheet.insertRule` yamasını ayrı bir `plotly-shared-patched.min.js` dosyasına yazar ve HTML bu yerel dosyayı kullanır; ağ gerekmez.

## 6. Testler

`tests/ui_qml/test_comparison_screener_phase7.py` (denetleyici ve QML), `tests/ui_qml/test_comparison_info_cards.py` (bilgi kartları), `tests/application/services/test_comparison_service.py` (saf hesaplar).

## 7. Sınırlar

- "Tümü" dönemi sabit 2022 başlangıçlıdır.
- Genişletilmiş risk metrikleri (Sortino, Calmar, Omega, VaR...) servis katmanında hazırdır ama bu ekranda gösterilmez.
- Plandaki işlem analizi, davranışsal analiz ve XIRR yoktur ([roadmap.md](roadmap.md)).

## 4. Kod Yapısı

| Modül | Sorumluluk |
|---|---|
| `controllers/comparison_controller.py` | QML yüzeyi (Property/Slot/Signal), durum, arka plan iş parçacığı ve sinyal akışı |
| `controllers/comparison_support.py` | Saf yardımcılar: seçimi (portföy / benchmark / hisse) ayırma, tarih aralığı, risk-getiri metrikleri, AI istemi, portföy hisse verisi |
| `controllers/comparison_chart_html.py` | Saf HTML üreticileri (Lightweight Charts, Chart.js, treemap şablonları) |

Grafik HTML'i sabit girdilerle üretilip değişmediği doğrulanarak taşınmıştır; yeni grafik eklerken üretici `comparison_chart_html.py`'ye, denetleyiciye yalnızca sekme dağıtımı eklenir.
