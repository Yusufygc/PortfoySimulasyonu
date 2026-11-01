# YeniPlan — İçerik Kataloğu

> Bu klasör, "Portföyüm sayfası, çoklu varlık defteri ve Genel Bakış haber akışı" çalışmasının geçici wiki'sidir. `docs/wiki` ile aynı kurallarla yönetilir (bkz. [RULES.md](../RULES.md) §1). İş bitince içerik [08_wiki_entegrasyon.md](08_wiki_entegrasyon.md) kontrol listesine göre `docs/wiki/` içine taşınır ve bu klasör silinir.

Değişiklik günlüğü: [log.md](log.md)

Durum etiketleri: **Taslak** (yazıldı, tartışılabilir), **Onaylı** (kullanıcı kararı alındı), **Uygulandı** (kodda var, wiki'ye taşınmayı bekler).

---

## Sayfalar

| Sayfa | Özet | Durum |
|---|---|---|
| [00_vizyon_ve_kapsam.md](00_vizyon_ve_kapsam.md) | Amaç, hedefler, v1 kapsamı ve v2'ye ertelenenler | Onaylı |
| [01_mimari_kararlar.md](01_mimari_kararlar.md) | Ayrı defter kararı, alternatifler, kabuller, riskler | Onaylı |
| [02_varlik_defteri.md](02_varlik_defteri.md) | Domain modelleri, tablolar, servisler, varlık kataloğu | Uygulandı |
| [03_fiyat_ve_kur_hatti.md](03_fiyat_ve_kur_hatti.md) | Sembol çözümleme, fiyat sağlayıcı, takvim, kur | Aşama 3 Uygulandı |
| [04_portfoyum_sayfasi.md](04_portfoyum_sayfasi.md) | Portföyüm UI, controller'lar, dağılım, sayfa bölünmesi | Aşama 1, 4 ve 5 Uygulandı |
| [05_genel_bakis_ve_haber.md](05_genel_bakis_ve_haber.md) | Genel Bakış yerleşimi, haber mimarisi, spike sonuçları | Aşama 6 Uygulandı |
| [06_ayarlar_haber_kaynaklari.md](06_ayarlar_haber_kaynaklari.md) | Ayarlar > Haber Kaynakları sekmesi, aç/kapa sistemi | Taslak |
| [07_test_ve_kalite.md](07_test_ve_kalite.md) | Test stratejisi, koruma testleri, kalite kapıları | Taslak |
| [08_wiki_entegrasyon.md](08_wiki_entegrasyon.md) | İş bitince wiki'ye taşıma kontrol listesi | Taslak |
| [tasarim_notlari/](tasarim_notlari/) | Spike sonuçları: KAP, yfinance haberi, RSS kaynakları | Spike tamamlandı |

## Aşama Durumu

| Aşama | Konu | Durum |
|---|---|---|
| 0 | YeniPlan iskeleti | Uygulandı |
| 1 | Sayfa bölünmesi (Genel Bakış / Portföyüm) | Uygulandı |
| 2 | Varlık defteri (domain + DB) | Uygulandı |
| 3 | Fiyat ve kur hattı | Uygulandı |
| 4 | Birleşik portföy servisi | Uygulandı |
| 5 | Portföyüm arayüzü | Uygulandı |
| 6 | Genel Bakış + haber akışı (önce spike) | Uygulandı |
| 7 | Ayarlar > Haber Kaynakları | Açık |
| 8 | Ertelenenler (v2) | Açık |
| 9 | Wiki entegrasyonu ve klasörün silinmesi | Açık |

## Bakım Kuralları

- Her iş adımında [log.md](log.md) başına giriş eklenir (yalnızca ekleme, en yeni üstte).
- Yeni sayfa eklenince bu katalog güncellenir; her sayfanın üstünde navigasyon satırı bulunur.
- Kod tamamlanan aşamanın sayfası **Uygulandı** olarak işaretlenir ve gerçek dosya yolları yazılır.
- Tasarım sırasında kesinleşen kararlar [01_mimari_kararlar.md](01_mimari_kararlar.md) içine işlenir.

*Son güncelleme: 2026-11-01*
