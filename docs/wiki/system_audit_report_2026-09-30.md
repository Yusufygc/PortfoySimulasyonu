# Sistem Denetim ve Mimari İnceleme Raporu (2026-09-30)

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md)

---

## 1. Yönetici Özeti

Portföy Simülasyonu projesi; **Domain** katmanında saf Python nesneleri ve zengin matematiksel finansal modeller (Markowitz, Ledoit-Wolf kovaryans büzüşmesi, event-sourced portföy türetimi) ile güçlü bir mimari temele sahiptir. SQLite göçü ve modern QML/Qt Quick (`src/ui_qml`) dönüşümü, donanım hızlandırmalı modern bir yatırım terminali oluşturma yolunda doğru bir adımdır.

Ancak projenin mevcut durumunda; **QML katmanında WebEngine üzerinden ham string birleştirme ile yapılan JavaScript enjeksiyon açığı (XSS)**, **Dashboard fiyat yenilemesinde (`refreshMetrics`) canlı servis yerine sahte `np.random.normal` üretimi yapılması**, **1.421 satırlık ve 96 metotlu God-Object `Stock360Controller` sınıfı**, **UI Controller'larının doğrudan SQL Repository'lerine sızması (Clean Architecture katman delinmesi)**, **derleme betiğinin (`build_nuitka.bat`) halen PyQt5 bayraklarıyla çalışıp QML kaynaklarını paketlememesi** ve **SQLite göçü sonrası izole edilmeyen ortam değişkenleri nedeniyle 9 testin patlamış olması** acil müdahale gerektiren yüksek riskli teknik borçlar olarak tespit edilmiştir.

### Yönetici Özeti Tablosu

| # | Bulgu | Öncelik | Boyut | Efor | Etki | Durum |
|---|-------|:-------:|-------|:----:|------|:-----:|
| 1 | QtWebEngine XSS ve Ham JS Enjeksiyon Açığı | 🔴 | Güvenlik | S | Yüksek | ✅ Çözüldü |
| 2 | Dashboard Fiyat Yenilemesinde Canlı Servis Yerine Sahte Sayı (`np.random`) Üretimi | 🔴 | Mimari / Kod | S | Yüksek | ✅ Çözüldü |
| 3 | SQLite Göçü Sonrası `test_settings_loader.py` Çöküşü (7 Test Fail) | 🔴 | Test | S | Yüksek | ✅ Çözüldü |
| 4 | Nuitka Build Betiğinde Eski PyQt5 Plugin'i ve Sabit Geliştirici Yolu | 🔴 | Production | M | Yüksek | ✅ Çözüldü |
| 5 | God Object Patlaması: `Stock360Controller` (1.421 Satır, 96 Metot, CC=54) | 🟠 | Mimari / Kalite | L | Yüksek | ✅ Çözüldü |
| 6 | Katman İhlali: UI Controller'larının Doğrudan SQL Repository'lerine Erişmesi | 🟠 | Mimari | M | Yüksek | ✅ Çözüldü |
| 7 | DRY İhlali: Teknik İndikatör Hesaplamalarının UI Katmanında Yeniden Yazılması | 🟠 | Mimari / Kalite | M | Orta | ✅ Çözüldü |
| 8 | UI Thread'de N+1 Senkron DB Sorgusu ve Arayüz Donma Riski | 🟠 | Performans | M | Yüksek | ✅ Çözüldü |
| 9 | `time.sleep(1.5)` ile Bekletilen Flaky UI Testleri | 🟠 | Test | S | Orta | ✅ Çözüldü |
| 10 | `requirements.txt` ile Sanal Ortam Paket ve Sürüm Ayrışması | 🟠 | DevSecOps / SRE | S | Yüksek | ✅ Çözüldü |
| 11 | `test_isyatirim_provider.py` Veri Dönem Uyuşmazlığı Nedeniyle Test Hatası | 🟠 | Test | S | Düşük | ✅ Çözüldü |
| 12 | UI Tablo Modellerinde Kâr/Zarar İçin `float` Matematik Kullanımı | 🟠 | Kod Kalitesi | M | Orta | ✅ Çözüldü |
| 13 | 9 Ayrı Noktada Sessiz Hata Yutma (`except Exception: pass`) | 🟡 | Kod Kalitesi | S | Orta | ✅ Çözüldü |
| 14 | QML Dosyalarında 49 Adet Hardcoded Arayüz Metni (`RULES.md §2.3` İhlali) | 🟡 | Standartlar | M | Düşük | ✅ Çözüldü |
| 15 | `_write_temp_html` Tarafından Üretilen Geçici Dosyaların Asla Temizlenmemesi | 🟡 | Production / SRE | S | Orta | ✅ Çözüldü |
| 16 | Preflight Kontrolünde Python Sürüm Uyuşmazlığı (3.10 vs 3.11) | 🟡 | Production | S | Düşük | ✅ Çözüldü |
| 17 | Naive ve Aware Datetime Karışımı ile Deprecated `datetime.utcnow()` | 🟡 | Kod Kalitesi | M | Orta | ✅ Çözüldü |
| 18 | `FintechShareholderTimeline.qml` İçinde Ham Unicode Ok Karakteri (`\u2794`) | 🟢 | Standartlar | S | Düşük | ✅ Çözüldü |
| 19 | Sayı ve Para Birimi Formatlarında Dil/Kısaltma Uyuşmazlığı ("Mr" vs "B") | 🟢 | Yerel Bağlam | S | Düşük | ✅ Çözüldü |
| 20 | `auto_commit.py` Scriptinin Hassas Kod ve .env İçeriklerini Dış API'ye Göndermesi | 🟢 | DevSecOps | S | Düşük | ✅ Çözüldü |

---

## 2. Korunması Gereken İyi Pratikler (Pozitif Bulgular)

1. **Domain Katmanı Saflığı (Clean Architecture Zero-Dependency):**
   `src/domain/` altındaki modellerde PySide6, SQLAlchemy veya harici kütüphane bağımlılığı bulunmamaktadır.
2. **Sıfır `print()` Disiplini:**
   Tüm `src/` ağacında (eski UI hariç) tek bir `print()` dahi yoktur; merkezi yapılandırılmış loglama (`logger_setup.py`) kullanılmaktadır.
3. **Event-Sourced Portföy Durum Hesabı:**
   Portföy değerleri durağan saklanmayıp her seferinde işlem geçmişi loglarından (`Portfolio.from_trades()`) deterministik olarak yeniden üretilmektedir.
4. **Merkezi SVG İkon Sistemi (`Icons.qml` & `ModernIcon.qml`):**
   QML tarafında Unicode emojiler yerine 52 adet Lucide vektörel SVG ikonu ve `ColorOverlay` renklendirmesi kullanılmıştır.
5. **SQLite WAL Modu ve Hızlı Yerel Veri Tabanı:**
   `SQLiteConfig` üzerinde `journal_mode = WAL` ve `synchronous = NORMAL` optimizasyonları ile hızlı yerel veri akışı sağlanmıştır.

---

## 3. Detaylı 20 Bulgu Listesi

Detaylı teknik açıklamalar, etki analizleri, kanıt kod blokları ve çözüm adımları denetim çıktısında listelenmiştir.

---

## 4. Aksiyon Planı ve Kriz Yönetimi

- **24 Saat İçinde:** Bulgu 1 (QtWebEngine XSS), Bulgu 2 (Dashboard Fiyat Yenileme), Bulgu 3 (test_settings_loader fail).
- **Bu Hafta İçinde:** Bulgu 4 (Nuitka build), Bulgu 6 (Katman ihlalleri), Bulgu 8 (N+1 sorgular), Bulgu 9 (Flaky testler), Bulgu 10 (requirements.txt).
- **Bu Ay İçinde:** Bulgu 5 (Stock360Controller refactor), Bulgu 7 (DRY indikatörler), Bulgu 14 (QML Strings), Bulgu 15 (Geçici dosya temizliği).
