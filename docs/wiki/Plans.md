> Ana sayfa: [index.md](index.md) | Değişiklik günlüğü: [log.md](log.md)

# Yol Haritası ve Teknik Planlar (Plans)

Bu dosya, Portföy Simülasyonu projesindeki gelecek geliştirme planlarını, teknik borçları (technical debt), araştırma başlıklarını ve yapılması planlanan kod incelemelerini (code review) listeler.

---

## 🛠️ Yakın Vadeli Kod İncelemeleri (Code Review Needs)

### 0. Sağlık Raporu Tabanlı Refactor ve Kalite Kapıları
* **Mevcut Durum**: [code_quality_baseline_2026-06-13.md](code_quality_baseline_2026-06-13.md) ile yorum, boş satır ve docstring ayrıştırmalı başlangıç metriği üretildi; sağlık HTML'i artık tek karar kaynağı değil.
* **Sorun/Risk**: Büyük application servisleri ve UI page/widget sınıfları yeni özellik eklerken sorumluluk karışmasına ve regresyon riskine yol açabilir.
* **Geliştirme Planı**: Önce application servis facade'ları, ardından UI page/component ayrımı ve en son doğrulanmış dependency temizliği yapılacak. Her dilimden önce `scripts/measure_code_quality.py`, sonra hedefli testler ve tam `pytest tests -q` çalıştırılacak.
* **Bağlantılı Rehber**: [code_quality_guardrails.md](code_quality_guardrails.md)

### 1. Seans Kapalıyken Otomatik Güncelleme Davranışı
* **Mevcut Durum**: [bist_market_session_service.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/application/services/market/bist_market_session_service.py) seans durumunu (açık, kapalı, tatil) doğru tespit edebiliyor.
* **Sorun/Risk**: Arayüzdeki otomatik fiyat güncelleme zamanlayıcısı seans dışı saatlerde veya resmi tatillerde çalışmaya devam ederek harici API'lere (YFinance, EVDS) gereksiz yük bindirmektedir.
* **Geliştirme Planı**: Fiyat güncelleme tetikleyicisini seans durumuyla ilişkilendirmek. Seans kapalıysa güncelleme sıklığını düşürmek veya tamamen askıya almak.

### 2. SQLAlchemy Oturum Ömrü ve Bağlantı Havuzlaması
* **Sorun/Risk**: Uzun süreli masaüstü uygulaması oturumlarında MySQL bağlantı kopmaları veya SQLite kilitlenmeleri yaşanabilmektedir.
* **Geliştirme Planı**: [orm_schema.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/infrastructure/db/sqlalchemy/orm_models.py) ve repository katmanında session ömrünü izlemek. `pool_recycle` ve `pool_pre_ping` parametrelerinin `.env` yapılandırması üzerinden kontrolünü artırmak.

---

## 🚀 Gelecek Özellikler Yol Haritası (Roadmap)

### 1. Dinamik Risk Profili Optimizasyon Entegrasyonu
* **Hedef**: [risk_profile_service.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/application/services/planning/risk_profile_service.py) çıktısı ile Markowitz optimizasyon motorunu ([optimization_service.py](file:///d:/1KodCalismalari/Projeler/VIBE_CODING_UYGULAMA_DENEMELERI/Merge_PortfoySim/PortfoySimulasyonu/src/application/services/planning/optimization_service.py)) birbirine bağlamak.
* **Senaryo**: Kullanıcının anketteki risk skoru "Muhafazakar" çıkarsa, optimizasyon sayfasındaki maksimum hisse senedi ağırlığı sınırı otomatik olarak %10 ile limitlenecek; "Agresif" kullanıcılar için bu sınır %40'a kadar esnetilecektir.

### 2. Çoklu Pencere (Multi-Window / Docking) Desteği
* **Hedef**: Karşılaştırma Laboratuvarındaki Plotly veya Pyqtgraph grafik panellerinin (`ChartPanel`), ana pencereden ayrılıp (undock) ayrı monitörlerde izlenebilmesini sağlamak.
* **Teknoloji**: PyQt5 `QDockWidget` veya custom alt pencere yönetim mantığı.

---

## 📉 Token ve Okunabilirlik Optimizasyonu
* Gelecekteki LLM oturumlarının bağlam (context) limitini verimli kullanması adına:
  * Gereksiz kod tekrarlarını ve uzun açıklama paragraflarını kaldırın.
  * Tasarımsal kararları ve veri modellerini şematik tablolar ile ifade edin.
  * İlgili kod bileşenlerine doğrudan bağlantı [link formatı](file:///path/to/file) kullanarak hızlı erişim sağlayın.
