"""Mesaj kataloğu: Uygulama kabuğu: sayfa başlıkları, seans, açılış işleri, sistem ve ayarlar.

Anahtar önekleri: page, session, settings, startup, system.
"""
from __future__ import annotations

from typing import Dict

MESSAGES: Dict[str, str] = {
    # --- Sistem ---
    "system.auto_refresh_failed": "Otomatik fiyat yenileme çalıştırılamadı: {error}",
    "system.reset_service_missing": "Sıfırlama servisi bulunamadı.",
    "system.reset_done": "Sistem başarıyla sıfırlandı.",
    "system.reset_failed": "Sistem sıfırlanamadı: {error}",
    # --- Kabuk (sayfa başlıkları, seans) ---
    "page.dashboard": "Ana Sayfa",
    "page.watchlists": "Listelerim",
    "page.model_portfolios": "Model Portföyler",
    "page.stock_360": "Hisse 360",
    "page.comparison": "Karşılaştırma Laboratuvarı",
    "page.screener": "BIST Tarama",
    "page.planning": "Finansal Planlama",
    "page.optimization": "Optimizasyon",
    "page.ai_advisor": "AI Asistan",
    "page.settings": "Ayarlar",
    "page.my_portfolio": "Portföyüm",
    "page.app_title": "Portföy Yönetimi",
    "session.market_closed": "Piyasa Kapalı",
    "session.bist_open": "BIST: Canlı Seans Açık",
    "session.bist_closed": "BIST: Seans Kapalı",
    # --- Açılış işleri ---
    "startup.otomatik_veri_guncelleme_calistirilamadi": "Otomatik veri güncelleme çalıştırılamadı",
    "startup.kurumsal_aksiyon_taramasi_calistirilamadi": "Kurumsal aksiyon taraması çalıştırılamadı",
    "startup.otomatik_golden_cross_taramasi_calistirilama": "Otomatik Golden Cross taraması çalıştırılamadı",
    "startup.otomatik_veri_guncelleme": "Otomatik veri güncelleme",
    "startup.yeni_kurumsal_aksiyon_adayi_bulundu_ayarlar": "{saved} yeni kurumsal aksiyon adayı bulundu. Ayarlar > Kurumsal Aksiyonlar'dan inceleyin.",
    "startup.bolunme_taramasi_calistirilamadi": "Hisse bölünmesi taraması çalıştırılamadı",
    "startup.bolunme_otomatik_uygulandi": "Hisse bölünmesi otomatik uygulandı: {summary}. İşlemler ve fiyat geçmişi düzeltildi; Ayarlar > Kurumsal Aksiyonlar'dan geri alabilirsiniz.",
    "startup.bolunme_adayi_onay_bekliyor": "{count} hisse bölünmesi adayı tek kaynakla bulundu ve onay bekliyor. Ayarlar > Kurumsal Aksiyonlar'dan inceleyin.",
    "startup.golden_cross_taramasi_tamamlandi_yeni_sinyal": "Golden Cross taraması tamamlandı: {new_events} yeni sinyal.",
    "startup.tamamlandi_fiyat_kaydi_eklendi": "{label} tamamlandı: {updated} fiyat kaydı eklendi.",
    "startup.sirasinda_hata_olustu": "{label} sırasında {errors} hata oluştu.",
    # --- Ayarlar ---
    "settings.hazir": "Hazır",
    "settings.acik_tema": "Açık Tema",
    "settings.basariyla_etkinlestirildi": "{theme_name} başarıyla etkinleştirildi.",
    "settings.api_anahtarlari_kaydedilemedi": "API anahtarları kaydedilemedi: {exc}",
    "settings.api_anahtarlari_kaydedilemedi_2": "API anahtarları kaydedilemedi",
    "settings.api_anahtarlari_kaydedildi_evds_anahtari_bir": "API anahtarları kaydedildi. EVDS anahtarı bir sonraki açılışta etkin olur.",
    "settings.api_anahtarlari_kaydedildi": "API anahtarları kaydedildi",
    "settings.lutfen_once_gecerli_bir_api_anahtari": "Lütfen önce geçerli bir API anahtarı girin.",
    "settings.google_gemini_sunucularina_baglaniliyor": "Google Gemini sunucularına bağlanılıyor...",
    "settings.baglanti_basarili_gemini_2_5_flash": "Bağlantı Başarılı! Gemini 2.5 Flash erişilebilir durumda.",
    "settings.sunucu_yanit_vermedi": "Sunucu yanıt vermedi.",
    "settings.baglanti_hatasi": "Bağlantı Hatası: {exc}",
    "settings.veritabani_metrikleri_taraniyor": "Veritabanı metrikleri taranıyor...",
    "settings.veritabani_metrikleri_guncellendi": "Veritabanı metrikleri güncellendi",
    "settings.piyasa_senkron_servisi_kullanilamiyor": "Piyasa senkron servisi kullanılamıyor.",
    "settings.senkronizasyon_hatasi": "Senkronizasyon hatası: {e}",
    "settings.tamamlandi": "Tamamlandı",
    "settings.veritabani_butunluk_kontrolu_yurutuluyor": "Veritabanı bütünlük kontrolü yürütülüyor...",
    "settings.veritabani_servisi_kullanilamiyor": "Veritabanı servisi kullanılamıyor.",
    "settings.mukemmel_sqlite_oltp_ve_duckdb_olap": "Mükemmel! SQLite (OLTP) ve DuckDB (OLAP) veritabanı bütünlüğü doğrulandı (OK).",
    "settings.excel_raporu_hazirlaniyor": "Excel raporu hazırlanıyor...",
    "settings.kapsamli_portfoy_excel_raporu_olusturuldu": "Kapsamlı portföy Excel raporu oluşturuldu:\n{name}",
    "settings.excel_raporu_olusturuldu": "Excel raporu oluşturuldu:\n{name}",
    "settings.excel_disa_aktarim_hatasi": "Excel dışa aktarım hatası: {e}",
    "settings.json_yedegi_aliniyor": "JSON yedeği alınıyor...",
    "settings.json_yedegi_kaydedildi": "JSON yedeği kaydedildi:\n{name}",
    "settings.json_yedekleme_hatasi": "JSON yedekleme hatası: {e}",
    "settings.disa_aktarim_tamamlandi": "Dışa aktarım tamamlandı",
    # --- Ayarlar (tema) ---
    "settings.dark_theme": "Koyu Tema",
}
