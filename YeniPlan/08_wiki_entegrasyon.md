# 08 — Wiki Entegrasyonu

> Ana sayfa: [index.md](index.md) | Günlük: [log.md](log.md) | Önceki: [07_test_ve_kalite.md](07_test_ve_kalite.md)

Durum: **Taslak** (Aşama 9)

Tüm aşamalar tamamlanıp testler yeşil olunca bu klasörün içeriği `docs/wiki/` içine taşınır; sonra `YeniPlan/` silinir (git geçmişinde kalır). Bu sayfa taşıma kontrol listesidir.

## 1. Yeni Wiki Sayfaları

| Kaynak (YeniPlan) | Hedef (`docs/wiki/`) | İçerik |
|---|---|---|
| [02](02_varlik_defteri.md) | `service_asset_ledger.md` | Domain, tablolar, servis, katalog (gerçek dosya yollarıyla) |
| [03](03_fiyat_ve_kur_hatti.md) | `service_asset_prices_fx.md` | Sembol çözümleme, sağlayıcı, takvim, kur |
| [05](05_genel_bakis_ve_haber.md) + [06](06_ayarlar_haber_kaynaklari.md) | `service_news.md` | Haber mimarisi, kaynaklar, önbellek, ayarlar |
| [04](04_portfoyum_sayfasi.md) | `qml_pages_guide.md` içine bölüm | Portföyüm ve Genel Bakış sayfa rehberi |

Yeni sayfa kuralı ([RULES.md](../RULES.md) §1.6): üstte navigasyon satırı, `index.md` kataloğuna ekleme, `log.md`'ye `yeni-sayfa` girişi, çapraz bağlantılar.

## 2. Güncellenecek Mevcut Sayfalar

| Sayfa | Güncelleme |
|---|---|
| `docs/wiki/qml_pages_guide.md` | 10 sayfa → 11 sayfa tablosu; Genel Bakış ve Portföyüm açıklamaları; Ayarlar'a Haber Kaynakları sekmesi |
| `docs/wiki/ui_architecture_and_events.md` | Yeni controller'lar, Signal akışı, `pricesChanged` bağlantıları |
| `docs/wiki/database_schema_and_orm.md` | `assets`, `asset_trades`, `asset_prices`, `asset_latest_prices`, `fx_rates`, `news_source_settings` |
| `docs/wiki/data_architecture.md` | Varlık fiyatları SQLite'ta; DuckDB yalnızca BIST |
| `docs/wiki/service_market_data_providers.md` | Yeni fiyat ve haber sağlayıcıları, "Yeni Kaynak Eklerken" kontrol listesi uyumu |
| `docs/wiki/project_structure.md` | Yeni dizinler (`services/assets`, `services/news`, `infrastructure/news`) |
| `docs/wiki/roadmap.md` | v2 maddeleri (bkz. [00](00_vizyon_ve_kapsam.md) §4) açık maddeler olarak |
| `docs/wiki/testing_strategy.md` | Yeni test alanları |
| `docs/wiki/code_quality_guardrails.md` | Eşik ihlal sayısı değişmişse güncel sayı |
| `docs/wiki/index.md` | Yeni sayfalar kataloğa |
| `docs/wiki/log.md` | Tek bir entegrasyon girişi + her büyük aşama için `yeni-sayfa` / `güncelleme` kayıtları |
| `CLAUDE.md` | Veritabanı şeması özetine yeni tablolar; sayfa sayısı |
| `README.md` | Özellik özeti (Portföyüm, haber akışı, çoklu varlık) |

## 3. Taşıma Sırasında

- Taslak etiketleri ve "Aşama N" ifadeleri kaldırılır; metin kalıcı bilgi tabanı diline çevrilir.
- Planlanıp yapılmayan her madde `roadmap.md` içine "Açık" olarak taşınır; sessizce düşürülmez.
- Spike sonuçları ([tasarim_notlari/](tasarim_notlari/)) ilgili servis sayfasına "Bilinen sınırlar" bölümü olarak işlenir; kalıcı değeri olan tartışmalar `docs/wiki/tasarim_notlari/` altına taşınır.
- Çapraz bağlantılar `YeniPlan/` yollarına işaret etmez.

## 4. Kapanış Kontrolü

- [ ] Tüm aşamalar index'te **Uygulandı**.
- [ ] Yukarıdaki yeni ve güncellenen wiki sayfaları yazıldı.
- [ ] `grep -r "YeniPlan" .` repoda kalıntı bulmuyor (bu klasör dışında).
- [ ] Tam test paketi yeşil.
- [ ] `YeniPlan/` silindi, wiki `log.md`'ye kapanış girişi eklendi.
