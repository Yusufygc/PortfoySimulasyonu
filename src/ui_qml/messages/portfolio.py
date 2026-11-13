"""Mesaj kataloğu: Ana portföy, Portföyüm, temettü, nakit, ücretler, varlıklar ve izleme listeleri.

Anahtar önekleri: assets, cash_pool, dashboard, dividend, fees, my_portfolio, watchlist.
"""
from __future__ import annotations

from typing import Dict

MESSAGES: Dict[str, str] = {
    # --- Temettü ---
    "dividend.service_missing": "Temettü servisi kullanılamıyor.",
    "dividend.amount_invalid": "Tutar 0'dan büyük geçerli bir sayı olmalıdır.",
    "dividend.date_invalid": "Tarih geçersiz. Biçim: YYYY-AA-GG",
    "dividend.default_note": "{ticker} temettü",
    "dividend.save_failed": "Temettü kaydedilemedi.",
    "dividend.added": "{amount} ₺ temettü nakit bakiyeye eklendi.",
    "dividend.delete_failed": "Temettü silinemedi.",
    "dividend.deleted": "Temettü kaydı silindi.",
    # --- İzleme listeleri ---
    "watchlist.sira_kaydedilemedi": "Sıra kaydedilemedi: {exc}",
    "watchlist.liste_adi_bos_olamaz": "Liste adı boş olamaz!",
    "watchlist.listesi_olusturuldu": "'{name}' listesi oluşturuldu.",
    "watchlist.listesi_basariyla_olusturuldu": "'{name}' listesi başarıyla oluşturuldu.",
    "watchlist.guncellendi": "'{name}' güncellendi.",
    "watchlist.listesi_guncellendi": "'{name}' listesi güncellendi.",
    "watchlist.liste_basariyla_silindi": "Liste başarıyla silindi.",
    "watchlist.hisse_kodu_bos_olamaz": "Hisse kodu boş olamaz!",
    "watchlist.gecersiz_hisse_kodu": "Geçersiz hisse kodu: {ticker}",
    "watchlist.listeye_basariyla_eklendi": "{ticker} listeye başarıyla eklendi.",
    "watchlist.hisse_listeden_cikarildi": "Hisse listeden çıkarıldı.",
    "watchlist.hisse_listeden_basariyla_cikarildi": "Hisse listeden başarıyla çıkarıldı.",
    "watchlist.not_guncellendi": "Not güncellendi.",
    "watchlist.hisse_notu_basariyla_guncellendi": "Hisse notu başarıyla güncellendi.",
    # --- Varlıklar ---
    "assets.islem_yonu_gecersiz": "İşlem yönü geçersiz.",
    "assets.miktar_sifirdan_buyuk_bir_sayi_olmali": "Miktar sıfırdan büyük bir sayı olmalı.",
    "assets.fiyat_sifirdan_buyuk_bir_sayi_olmali": "Fiyat sıfırdan büyük bir sayı olmalı.",
    "assets.tarih_gg_aa_yyyy_biciminde_olmali": "Tarih GG.AA.YYYY biçiminde olmalı.",
    "assets.saat_ss_dd_biciminde_olmali": "Saat SS:DD biçiminde olmalı.",
    "assets.kur_sifirdan_buyuk_bir_sayi_olmali": "Kur sıfırdan büyük bir sayı olmalı.",
    "assets.baska_bir_islem_suruyor_bitmesini_bekleyin": "Başka bir işlem sürüyor, bitmesini bekleyin.",
    "assets.gecmis": "geçmiş",
    "assets.yuklenemedi_daha_sonra_yenilenecek": " ({items} yüklenemedi; daha sonra yenilenecek)",
    "assets.varlik_servisi_kullanilamiyor": "Varlık servisi kullanılamıyor.",
    "assets.varlik_sinifi_gecersiz": "Varlık sınıfı geçersiz.",
    "assets.varlik_fiyati_guncellendi": "{count} varlık fiyatı güncellendi.",
    "assets.islemi_kaydedildi": "{symbol} {label} işlemi kaydedildi.",
    "assets.varlik_kaldirildi": "Varlık kaldırıldı.",
    # --- Ana sayfa ---
    "dashboard.tarih_bicimi_gecersiz_bicim_gg_aa": "Tarih biçimi geçersiz. Biçim: GG.AA.YYYY",
    "dashboard.gelecek_tarihli_islem_girilemez": "Gelecek tarihli işlem girilemez.",
    "dashboard.saat_bicimi_gecersiz_bicim_ss_dd": "Saat biçimi geçersiz. Biçim: SS:DD",
    "dashboard.gecersiz_islem_parametreleri": "Geçersiz işlem parametreleri.",
    "dashboard.islem_kaydedilemedi": "İşlem kaydedilemedi. Ayrıntı günlükte.",
    "dashboard.onceki_islem_suruyor": "Önceki işlem hâlâ sürüyor.",
    "dashboard.adet_islemi_basariyla_kaydedildi": "{quantity} adet {ticker} {side} işlemi başarıyla kaydedildi.",
    "dashboard.islem_servisi_kullanilamiyor": "İşlem servisi kullanılamıyor.",
    "dashboard.tutar_0_dan_buyuk_olmalidir": "Tutar 0'dan büyük olmalıdır.",
    "dashboard.qml_sermaye_girisi": "QML Sermaye Girişi",
    "dashboard.nakit_portfoye_yatirildi": "₺{dec_amount} nakit portföye yatırıldı.",
    "dashboard.qml_sermaye_cikisi": "QML Sermaye Çıkışı",
    "dashboard.nakit_portfoyden_cekildi": "₺{dec_amount} nakit portföyden çekildi.",
    "dashboard.nakit_servisi_kullanilamiyor": "Nakit servisi kullanılamıyor.",
    "dashboard.baslangic_tarihi_bitis_tarihinden_buyuk_olam": "Başlangıç tarihi bitiş tarihinden büyük olamaz.",
    "dashboard.excel_portfoy_raporu_kaydedildi": "Excel portföy raporu kaydedildi:\n{name}",
    "dashboard.excel_rapor_servisi_kullanilamiyor": "Excel rapor servisi kullanılamıyor.",
    "dashboard.excel_raporu_olusturulamadi": "Excel raporu oluşturulamadı: {exc}",
    # --- Ücret ayarları ---
    "fees.service_missing": "Ücret ayarı servisi kullanılamıyor.",
    "fees.invalid_number": "Oranlar sayı olmalıdır (ör. 0,2).",
    "fees.saved": "Ücret oranları kaydedildi.",
    # --- Nakit havuzu ---
    "cash_pool.service_missing": "Döviz servisi kullanılamıyor.",
    "cash_pool.invalid_amount": "USD miktarı sıfırdan büyük bir sayı olmalı.",
    "cash_pool.invalid_rate": "Kur sıfırdan büyük bir sayı olmalı.",
    "cash_pool.invalid_fee": "Ücret negatif olamaz.",
    "cash_pool.buy": "Döviz alımı",
    "cash_pool.sell": "Döviz satımı",
    "cash_pool.row": "{day} - {side}: {usd} USD, kur {rate}",
    "cash_pool.done_buy": "{usd} USD alındı.",
    "cash_pool.done_sell": "{usd} USD satıldı.",
    "cash_pool.deleted": "Döviz işlemi silindi.",
    # --- Portföyüm ---
    "my_portfolio.cash_breakdown": "TL {tl} + USD {usd}",
    # --- Varlık ve döviz tarih doğrulama ---
    "assets.gelecek_tarihli_islem_girilemez": "Gelecek tarihli işlem girilemez.",
    "cash_pool.invalid_date": "Tarih GG.AA.YYYY biçiminde olmalı.",
    "cash_pool.future_date": "Gelecek tarihli döviz işlemi girilemez.",
    "cash_pool.invalid_time": "Saat SS:DD biçiminde olmalı.",
}
