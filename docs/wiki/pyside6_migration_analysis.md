# PySide6 Göç Analizi

> Ana sayfa: [index.md](index.md) | Değişiklik günlüğü: [log.md](log.md)

Bu rapor, mevcut PyQt5 tabanlı masaüstü uygulamasını PySide6'ya geçirmek için kod tabanını mantıklı parçalara ayırır, göç risklerini değerlendirir ve uygulanabilir faz planı önerir.

## Kısa Sonuç

Göç yapılabilir, fakat tek bir global import değiştirme işi olarak ele alınmamalıdır. Kod tabanında PyQt5 yüzeyi geniştir: 103 üretim dosyası ve 21 test dosyası doğrudan PyQt5 import eder. En riskli alanlar `QWebEngineView` / Plotly entegrasyonu, `sip.isdeleted` kontrolleri, `exec_()` çağrıları, Qt6 enum kapsamları ve test guard'larının PyQt5'e sabitlenmiş olmasıdır.

Önerilen yol: önce bir Qt uyumluluk katmanı oluşturmak, sonra modül modül PySide6'ya taşımak, en sonda PyQt5 geriye dönük alias'larını kaldırmak.

## Analiz Kapsamı

Yerel kaynak kod ve wiki taramasına göre ölçülen yüzey:

| Alan | Değer |
| --- | ---: |
| Toplam Python dosyası | 422 |
| `src/domain` dosyaları | 39 |
| `src/application` dosyaları | 79 |
| `src/infrastructure` dosyaları | 40 |
| `src/ui` dosyaları | 158 |
| Test dosyaları | 90 |
| PyQt5 import eden üretim dosyaları | 103 |
| PyQt5 import eden test dosyaları | 21 |
| QSS dosyaları | 41 |

PyQt5 modül kullanım dağılımı:

| Qt modülü | Dosya sayısı |
| --- | ---: |
| `QtWidgets` | 113 |
| `QtCore` | 104 |
| `QtGui` | 21 |
| `QtWebEngineWidgets` | 2 |
| `QtSvg` | 1 |
| `QtTest` | 3 |

Özel API kullanım sayaçları:

| Kullanım | Adet | Göç notu |
| --- | ---: | --- |
| `pyqtSignal` | 64 | PySide6'da `Signal`; geçişte alias kullanılabilir. |
| `pyqtSlot` | 2 | PySide6'da `Slot`. |
| `QThreadPool` | 38 | Genel model korunabilir; import ve test fixture güncellenir. |
| `QSettings` | 24 | Çalışır, fakat infrastructure katmanındaki Qt bağımlılığı bilinçli tutulmalı. |
| `exec_()` | 20 | Qt6/PySide6 tarafında `exec()` hedeflenmeli. |
| `sip` | 11 | `shiboken6.isValid()` ile değiştirilmeli. |
| `QWebEngineView` | 9 | En yüksek manuel doğrulama riski. |
| `QSvgRenderer` | 2 | `PySide6.QtSvg` ile test edilmeli. |

## Kodun Mantıklı Parçaları

### 1. Saf Domain Katmanı

Konum: `src/domain/`

Bu katman PyQt5'e bağlı görünmüyor. Modeller, portlar ve domain istisnaları PySide6 göçünden doğrudan etkilenmemeli. Bu yüzden ilk doğrulama paketi burada davranış regresyonu olmadığını göstermek için çalıştırılır, ancak üretim değişikliği beklenmez.

Risk: düşük.

Göç işi: yok. Sadece tam testlerde güvenlik ağı olarak korunmalı.

### 2. Application Servisleri ve Event Bus

Konum: `src/application/`

Servislerin çoğu Qt bağımsızdır. Ancak `src/application/events/event_bus.py`, `QObject` ve `pyqtSignal` kullanarak `GlobalEventBus` sağlar. Bu dosya UI ile application sınırı arasında özel bir köprü durumundadır.

Risk: orta.

Göç işi:

- `GlobalEventBus` için `Signal` alias'ı uyumluluk katmanından alınmalı.
- Uzun vadede application katmanının Qt bağımlılığı azaltılmak istenirse iki seçenek var: Qt event bus'ı UI adapter'a taşımak veya domain/application tarafında saf Python pub/sub portu tanımlayıp UI tarafında Qt sinyal adaptörü yazmak.
- Mevcut göç için daha düşük riskli yol, Qt event bus'ı koruyup sadece binding değişimini yapmak.

### 3. Infrastructure Adaptörleri

Konum: `src/infrastructure/`

Genel DB, market data, AI provider ve logging kodları Qt bağımsızdır. İstisna `src/infrastructure/ai/qsettings_chat_history_repo.py`: `IChatHistoryRepository` portunu `QSettings` ile uygular.

Risk: düşük-orta.

Göç işi:

- `QSettings` importu PySide6'ya taşınmalı.
- Bu adaptör infrastructure içinde kalabilir; çünkü QSettings burada kalıcılık detayıdır.
- Testlerde kullanılan `MemorySettings` benzeri fake'ler korunmalı; böylece QSettings davranışı UI testlerine sızmaz.

### 4. UI Kabuk ve Navigasyon

Konumlar:

- `app.py`
- `src/ui/main_window.py`
- `src/ui/navigation/page_factory.py`
- `src/ui/pages/base_page.py`

Bu kısım uygulama yaşam döngüsünü, `QApplication`, global event filter, tema uygulama, `QStackedWidget` sayfa geçişleri, `QTimer.singleShot` otomatik işler ve navigation sinyallerini yönetir.

Risk: orta.

Göç işi:

- `QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)` Qt6 enum adıyla doğrulanmalı.
- `app.exec_()` yerine `app.exec()` kullanılmalı.
- `pyqtSignal` kullanan base/navigasyon sinyalleri uyumluluk katmanından alınmalı.
- `QAction` gibi Qt6'da modül değiştiren sınıflar için import taraması yapılmalı.

### 5. UI Sayfaları ve Paneller

Konumlar:

- `src/ui/pages/`
- `src/ui/widgets/`
- `src/ui/shared/`

En geniş göç yüzeyi buradadır. `QtWidgets`, `QtCore`, `QtGui`, `QDate`, `QTime`, `QTimer`, `QMessageBox`, `QTableWidget`, `QAbstractTableModel`, `QStyledItemDelegate`, animation sınıfları ve özel widget'lar yaygın kullanılır.

Risk: orta-yüksek.

Özellikle büyük sınıflar:

| Dosya | Satır | Not |
| --- | ---: | --- |
| `src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py` | 561 | Büyük dialog; enum, `QThreadPool`, `QMessageBox`, `QDate/QTime`. |
| `src/ui/pages/comparison/utils/chart_renderer.py` | 530 | WebEngine, Plotly, tempfile, `sip`, async render. |
| `src/ui/pages/watchlist_page.py` | 481 | Sayfa ve worker orchestration birlikte. |
| `src/ui/pages/ai_page/right_panel/chatbot_panel.py` | 476 | Animasyon, `QThreadPool`, chat state. |
| `src/ui/pages/risk_profile_page.py` | 439 | Büyük UI akışı. |
| `src/ui/pages/stock_detail/stock_detail_page.py` | 432 | Trade/form/chart koordinasyonu. |
| `src/ui/pages/stock_detail/stock_chart_widget.py` | 400 | `pyqtgraph`, crosshair, QThreadPool. |

Bu dosyalar `ARCHITECTURE_GATES.md` eşiklerine de yakındır veya whitelist'tedir. PySide6 göçü sırasında yeni davranış eklenmemeli; gerekirse önce küçük adapter/helper ayrımları yapılmalıdır.

### 6. Grafik, WebEngine ve Plotly

Konumlar:

- `src/ui/widgets/shared/controls/silent_web_view.py`
- `src/ui/pages/comparison/utils/chart_view_manager.py`
- `src/ui/pages/comparison/utils/chart_renderer.py`
- `src/ui/pages/comparison/utils/plotly_html.py`

Bu en riskli parça. Mevcut kod PyQt5 `QWebEngineView`, `QWebEnginePage`, `QWebEngineProfile.downloadRequested`, `QUrl.fromLocalFile`, lazy view creation, wheel redirect filter ve Plotly HTML patch'ini birlikte kullanıyor.

Risk: yüksek.

Göç işi:

- PySide6'da `QWebEngineView` `PySide6.QtWebEngineWidgets`, `QWebEnginePage` ve download tipleri `PySide6.QtWebEngineCore` altındadır.
- `download_item.setPath(...)` kullanımı Qt6 tarafında doğrudan taşınmamalı. PySide6 `QWebEngineDownloadRequest` API'sinde hedef klasör ve dosya adı `setDownloadDirectory(...)` ve `setDownloadFileName(...)` ile ayarlanır; sonra `accept()` çağrılır.
- `sip.isdeleted(obj)` kullanımları `shiboken6.isValid(obj)` ile ters mantıkta ele alınmalı: `is_deleted = not shiboken6.isValid(obj)`.
- Plotly geçici HTML dosyalarının yüklenmesi manuel smoke test ister; sadece unit test yeterli değildir.

### 7. Tema, QSS ve İkon Sistemi

Konumlar:

- `src/ui/theme_manager.py`
- `src/ui/styles/`
- `src/ui/core/icon_manager.py`

QSS dosyaları binding'den bağımsızdır, fakat Qt6 style engine bazı selector/property davranışlarında PyQt5/Qt5'ten farklı sonuç verebilir. `IconManager`, `QSvgRenderer`, `QPixmap`, `QPainter` ile SVG renklendirir ve QSS için `.icon_cache` üretir.

Risk: orta.

Göç işi:

- QSS token çözümleme testleri korunmalı.
- `QSvgRenderer(byte_data)` PySide6 ile doğrulanmalı.
- Tema değiştirme sırasında `QApplication.setFont` ve `setStyleSheet` sırası mevcut kalite kuralına uygun kalmalı.

### 8. Async Worker Modeli

Konumlar:

- `src/ui/worker.py`
- `src/ui/shared/live_price_refresh_controller.py`
- UI sayfalarındaki `Worker + QThreadPool` kullanımları

Mevcut mimari özel `QThread` sınıflarından kaçınıyor ve `QRunnable + QThreadPool` standardına dayanıyor. Bu PySide6 için iyi bir başlangıçtır.

Risk: orta.

Göç işi:

- `pyqtSignal` / `pyqtSlot` importları `Signal` / `Slot` ile uyumlanmalı.
- `QThreadPool.globalInstance().waitForDone(...)` test fixture'ları PySide6 altında doğrulanmalı.
- Worker signal tipleri (`object`, `tuple`) korunabilir.

### 9. Test ve Kalite Kapıları

Konumlar:

- `tests/conftest.py`
- `tests/ui/`
- `tests/ui/test_refactor_guards.py`

Testler doğrudan PyQt5'e sabitlenmiş durumda. `pytest.importorskip("PyQt5")`, `from PyQt5...` importları ve AST guard'larında `PyQt5.QtCore` string araması var.

Risk: yüksek, çünkü göç sonrası testler koddan önce kırılabilir.

Göç işi:

- Testlerde doğrudan binding importu yerine ortak test helper kullanılmalı.
- Guard testleri `PyQt5` yerine uyumluluk katmanını veya `PySide6` importlarını denetlemeli.
- `QtTest.QTest` kullanan testler PySide6 ile tekrar doğrulanmalı.
- UI testleri için `QT_QPA_PLATFORM=offscreen` ve WebEngine için Chromium runtime davranışı CI üzerinde ayrıca denenmeli.

## Bağımlılık ve Paketleme Etkisi

Mevcut bağımlılıklar:

```text
PyQt5==5.15.11
PyQtWebEngine==5.15.7
pyqtgraph==0.14.0
plotly==6.7.0
nuitka==2.7.14
```

Hedef:

- `PyQt5` ve `PyQtWebEngine` kaldırılır.
- `PySide6` pinlenir.
- WebEngine gerekiyorsa PySide6 dağıtımının ilgili WebEngine modülleri ve Nuitka plugin davranışı ayrıca doğrulanır.
- `sip` kaldırılır, `shiboken6` PySide6 ile gelir.
- `pyqtgraph` aynı kalabilir, fakat PySide6 backend seçimi ve import sırası test edilmelidir.

Nuitka tarafında risk orta-yüksek. Qt6 plugin, platform, WebEngine, translations, resources ve SSL/Chromium dosyaları paketleme çıktısında PyQt5'e göre farklılaşabilir. Bu yüzden göçün son fazı yalnız unit test değil, Windows `.exe` smoke test ile kapanmalıdır.

## Kritik API Farkları

| PyQt5 / Qt5 kullanımı | PySide6 / Qt6 hedefi | Etkilenen yer |
| --- | --- | --- |
| `from PyQt5...` | `from PySide6...` veya compat import | 103 üretim dosyası |
| `pyqtSignal` | `Signal` | event bus, base page, paneller |
| `pyqtSlot` | `Slot` | `src/ui/worker.py` |
| `app.exec_()` / `dialog.exec_()` | `exec()` | app ve dialog akışları |
| `sip.isdeleted(obj)` | `not shiboken6.isValid(obj)` | comparison chart lifecycle |
| `Qt.AlignCenter` vb. | `Qt.AlignmentFlag.AlignCenter` hedeflenmeli | yaygın UI kodu |
| `Qt.UserRole` | `Qt.ItemDataRole.UserRole` hedeflenmeli | tablo item data |
| `QAction` from `QtWidgets` | `QAction` from `QtGui` | shared controls |
| `download_item.setPath(...)` | `setDownloadDirectory(...)` + `setDownloadFileName(...)` | WebEngine download |

Not: PySide6 bazı eski adları uyumluluk için kabul edebilir; ancak bu göçün amacı Qt6 uyumlu ve sürdürülebilir kod olmalı. Bu yüzden rapor, nihai hedefte scoped enum ve yeni API adlarını önerir.

## Önerilen Göç Stratejisi

### Faz 0: Baseline ve Envanter

Amaç: PyQt5 mevcut davranışını sabitlemek.

Yapılacaklar:

- Tam test: `C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe -m pytest tests`
- UI hedefli test: `...\python.exe -m pytest tests/ui`
- WebEngine manuel smoke: Comparison sayfasında beş grafik, download, scroll wheel yönlendirme.
- Build smoke: mevcut Nuitka build'in kırık olup olmadığı.

Çıkış kriteri: PyQt5 ana branch davranışı ölçülmüş ve bilinen kırıklar ayrı not edilmiş olmalı.

### Faz 1: Qt Uyumluluk Katmanı

Amaç: 103 dosyada doğrudan binding değişimi yerine kontrollü geçiş noktası yaratmak.

Önerilen dosya:

```text
src/qt_compat.py
```

İlk içerik fikri:

```python
from PySide6.QtCore import *  # veya seçili explicit export
from PySide6.QtGui import *
from PySide6.QtWidgets import *
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import Signal as pyqtSignal, Slot as pyqtSlot
from shiboken6 import isValid

def is_qobject_deleted(obj) -> bool:
    try:
        return not isValid(obj)
    except RuntimeError:
        return True
```

Üretim kodu bu katmana taşınırken iki aşamalı yaklaşım daha güvenli:

1. Kısa vadede `pyqtSignal` / `pyqtSlot` alias'ları korunur.
2. Göç stabilize olduktan sonra adlar `Signal` / `Slot` olarak temizlenir.

### Faz 2: Mekanik Import Göçü

Amaç: doğrudan `PyQt5` importlarını kaldırmak.

Sıra:

1. `app.py`, `src/ui/worker.py`, `src/application/events/event_bus.py`.
2. `src/infrastructure/ai/qsettings_chat_history_repo.py`.
3. `src/ui/shared`, `src/ui/core`, `src/ui/widgets/shared`.
4. Sayfalar ve feature widget'ları.
5. Testler.

Çıkış kriteri:

- `rg "PyQt5" src app.py` boş veya yalnız geçici compatibility notlarında geçiyor.
- PySide6 altında import collection geçiyor.

### Faz 3: API Kırıklarını Düzeltme

Amaç: PySide6 çalıştırma zamanı kırıklarını düzeltmek.

Öncelik sırası:

1. `exec_()` -> `exec()`.
2. `sip` -> `shiboken6`.
3. `QAction` importları.
4. WebEngine download API'si.
5. Scoped enum dönüşümleri.
6. `QMouseEvent`, `QWheelEvent`, `QTest` constructor farkları.
7. `QHeaderView`, `QFrame`, `QMessageBox` enumları.

Bu fazda en iyi taktik, her alt paket için hedefli test çalıştırmaktır.

### Faz 4: WebEngine ve Grafik Doğrulaması

Amaç: Plotly, WebEngine ve lazy chart lifecycle davranışını stabil hale getirmek.

Doğrulama listesi:

- Comparison sayfası açılıyor.
- Boş state HTML gösteriliyor.
- Main, drawdown, periodic, scatter, treemap grafiklerinin lazy init'i çalışıyor.
- Scroll wheel ana `QScrollArea`'ya yönleniyor.
- Plotly patched JS temp dosyası yükleniyor.
- Download isteği `Downloads` klasörüne doğru dosya adıyla gidiyor.
- Sayfadan çıkışta pending temp dosyaları ve timer kuyruğu temizleniyor.

### Faz 5: Test Guard'larını PySide6'ya Taşıma

Amaç: kalite kapıları yeni binding'i denetlesin.

Yapılacaklar:

- `tests/conftest.py` içindeki `pytest.importorskip("PyQt5")` PySide6 veya compat helper'a taşınır.
- `tests/ui/test_refactor_guards.py`, `PyQt5.QtCore` string'i yerine `src.qt_compat` veya `PySide6.QtCore` bekler.
- `QThread` yasağı aynı kalır.
- UI içinde backend SDK import yasağı aynı kalır.
- L10N hardcoded metin guard'ı aynı kalır.

### Faz 6: Bağımlılık ve Build

Amaç: proje PySide6 ile kurulabilir ve paketlenebilir hale gelsin.

Yapılacaklar:

- `requirements.txt` güncellenir.
- `pip check` çalıştırılır.
- Nuitka build komutu PySide6/Qt6 plugin ve WebEngine kaynaklarıyla denenir.
- `.exe` açılış, tema, ikon, WebEngine ve DB bağlantısı smoke test edilir.

## Risk Matrisi

| Risk | Olasılık | Etki | Azaltma |
| --- | --- | --- | --- |
| WebEngine download API kırılması | yüksek | yüksek | `QWebEngineDownloadRequest` için özel adapter + test |
| `sip.isdeleted` eşdeğeri yanlış çevrilir | yüksek | yüksek | tek `is_qobject_deleted` helper'ı |
| Testler PyQt5 importunda skip/fail olur | yüksek | orta | önce test compat helper |
| Qt6 scoped enum uyumsuzluğu | orta | yüksek | AST/rg tabanlı enum dönüşüm listesi |
| Nuitka paketinde WebEngine kaynakları eksik kalır | orta | yüksek | ayrı build smoke fazı |
| QSS görsel farkları | orta | orta | ana sayfalar için manuel görsel kontrol |
| pyqtgraph backend farkı | düşük-orta | orta | StockChartWidget hedefli test + manuel chart kontrolü |
| Infrastructure'da QSettings bağımlılığı unutulur | orta | düşük | `qsettings_chat_history_repo` hedefli test |

## Parça Parça Uygulama Planı

Önerilen PR/commit bölünmesi:

1. `belge:` Bu analiz raporu.
2. `yapılandır:` PySide6 deney branch'i ve dependency spike.
3. `refaktör:` `src/qt_compat.py` ekle, `Worker` ve `EventBus` uyumla.
4. `refaktör:` app shell, theme, icon, shared controls importlarını taşı.
5. `refaktör:` dashboard, stock detail, model portfolio, planning sayfalarını taşı.
6. `refaktör:` analysis/comparison sayfaları ve WebEngine adapter'ını taşı.
7. `test:` UI test fixture ve guard'ları PySide6'ya taşı.
8. `yapılandır:` requirements ve Nuitka build ayarlarını güncelle.
9. `test:` tam test ve manuel smoke bulgularını kapat.

## Kabul Kriterleri

Kod göçü tamamlandı sayılmadan önce:

- `rg "PyQt5|PyQtWebEngine|import sip|sip\\.isdeleted" src tests app.py` temiz olmalı.
- `C:\Users\ysfygc\anaconda3\envs\Fintech\python.exe -m pytest tests` geçmeli.
- `tests/ui/test_refactor_guards.py` PySide6 uyumlu hale gelmeli.
- `app.py` PySide6 ile uygulamayı açmalı.
- Dashboard, Stock Detail, Analysis, Comparison, Model Portfolio, AI Page ve Settings manuel smoke edilmeli.
- Comparison WebEngine grafikleri ve Plotly download davranışı doğrulanmalı.
- Nuitka build çıktısı Windows üzerinde açılmalı.

## Resmi Kaynak Notları

- Qt for Python ana dokümantasyonu PySide6 modüllerini ve desteklenen API yüzeyini listeler: https://doc.qt.io/qtforpython-6/
- PySide6 sinyal/slot modeli `Signal` ve `Slot` sınıflarıyla belgelenir: https://doc.qt.io/qtforpython-6/tutorials/basictutorial/signals_and_slots.html
- `QWebEngineView` PySide6 tarafında `PySide6.QtWebEngineWidgets` altındadır: https://doc.qt.io/qtforpython-6/PySide6/QtWebEngineWidgets/QWebEngineView.html
- Qt6 WebEngine download modeli `QWebEngineDownloadRequest` kullanır; dosya hedefi için `setDownloadDirectory` ve `setDownloadFileName` bulunur: https://doc.qt.io/qtforpython-6/PySide6/QtWebEngineCore/QWebEngineDownloadRequest.html

## Son Karar Önerisi

Bu proje için en güvenli göç modeli "compat-first, page-by-page" modelidir. Doğrudan toplu `PyQt5` -> `PySide6` değiştirme, özellikle WebEngine, `sip`, enumlar ve test guard'ları nedeniyle yüksek kırılma riski taşır. Önce `src/qt_compat.py` ile binding sınırı daraltılmalı; sonra UI parçaları mevcut test katmanlarına göre küçük paketler halinde taşınmalıdır.
