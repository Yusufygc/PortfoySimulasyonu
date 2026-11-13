"""Mesaj kataloğu: Optimizasyon, strateji testi, karşılaştırma, risk profili ve planlama.

Anahtar önekleri: backtest, comparison, comparison_chart, optimization, optimization_input, planning, risk.
"""
from __future__ import annotations

from typing import Dict

MESSAGES: Dict[str, str] = {
    # --- Risk profili ---
    "risk.label.very_conservative": "Çok Muhafazakar",
    "risk.label.conservative": "Muhafazakar",
    "risk.label.balanced": "Dengeli",
    "risk.label.growth": "Büyüme Odaklı",
    "risk.label.aggressive": "Agresif",
    "risk.service_missing": "Risk profili servisi kullanılamıyor.",
    "risk.answer_all": "Lütfen tüm soruları yanıtlayın.",
    "risk.calc_failed": "Profil hesaplanamadı: {error}",
    # --- Planlama ---
    "planning.kalemi_sabitlendi_gelecek_aylara_otomatik_ak": "'{name}' kalemi sabitlendi (gelecek aylara otomatik aktarılacak).",
    "planning.kaleminin_sabitlemesi_kaldirildi": "'{name}' kaleminin sabitlemesi kaldırıldı.",
    "planning.kalem_adi_bos_olamaz_ve_tutar": "Kalem adı boş olamaz ve tutar 0'dan büyük olmalıdır.",
    "planning.gecersiz_kalem_secimi": "Geçersiz kalem seçimi.",
    "planning.kalemi_guncellendi": "'{new_name}' kalemi güncellendi.",
    "planning.butcesi_basariyla_kaydedildi": "{current_month} bütçesi başarıyla kaydedildi.",
    "planning.hedef_tutturuldu_fazlalik": "Hedef tutturuldu! (+{amount} fazlalık)",
    "planning.hedefin_altindasiniz_eksik": "Hedefin altındasınız ({amount} eksik)",
    "planning.net_tasarruf_gucu": "Net tasarruf gücü: {amount}",
    "planning.priority_high": "YÜKSEK",
    "planning.priority_low": "DÜŞÜK",
    "planning.priority_medium": "ORTA",
    "planning.hedefi_guncellendi": "'{name}' hedefi güncellendi.",
    "planning.tarih_bicimi_gecersiz": "Tarih geçersiz. Biçim: GG.AA.YYYY",
    "planning.dca_simulasyon_servisi_bulunamadi": "DCA simülasyon servisi bulunamadı.",
    "planning.dca_simulasyonu_tamamlandi_katki_donemi": "DCA simülasyonu tamamlandı ({contribution_count} katkı dönemi).",
    # --- Strateji testi ---
    "backtest.uyari": "Uyarı",
    "backtest.stop_loss_veya_take_profit_esiklerinden": "Stop-loss veya take-profit eşiklerinden en az birini girin.",
    "backtest.strateji_backtest_servisi_kullanilamiyor": "Strateji backtest servisi kullanılamıyor.",
    "backtest.baslangic_sermayesi_0_dan_buyuk_gecerli": "Başlangıç sermayesi 0'dan büyük geçerli bir sayı olmalıdır.",
    "backtest.tarih_gecersiz_bicim_yyyy_aa_gg": "Tarih geçersiz. Biçim: YYYY-AA-GG",
    "backtest.simulasyon_calistirilamadi": "Simülasyon çalıştırılamadı.",
    "backtest.secilen_tarih_araliginda_tum_hisselerin_fiya": "Seçilen tarih aralığında tüm hisselerin fiyatının bulunduğu işlem günü yok.",
    "backtest.strateji_testi_tamamlandi": "Strateji testi tamamlandı.",
    "backtest.pozisyon_cikisi": "{exit_count} pozisyon çıkışı",
    "backtest.fiyati_olmayan": "fiyatı olmayan: ",
    # --- Karşılaştırma ---
    "comparison.ana_portfoy": "Ana Portföy",
    "comparison.tarih_bicimi_gecersiz_bicim_gg_aa": "Tarih biçimi geçersiz. Biçim: GG.AA.YYYY",
    "comparison.baslangic_tarihi_bitis_tarihinden_once_olmal": "Başlangıç tarihi bitiş tarihinden önce olmalıdır.",
    "comparison.yapay_zeka_servisi_bulunamadi": "Yapay zeka servisi bulunamadı.",
    "comparison.analiz_edilecek_veri_bulunamadi_once_karsila": "Analiz edilecek veri bulunamadı. Önce karşılaştırmayı çalıştırın.",
    "comparison.yapay_zeka_yorumu_uretilemedi": "Yapay zeka yorumu üretilemedi: {error}",
    # --- Karşılaştırma (destek) ---
    "comparison.enflasyondan_arindirilmis_reel": "enflasyondan arındırılmış (reel)",
    # --- Optimizasyon ---
    "optimization.cok_muhafazakar": "Çok Muhafazakar",
    "optimization.buyume_odakli": "Büyüme Odaklı",
    "optimization.ozel_manuel_kisit": "Özel / Manuel Kısıt",
    "optimization.ana_portfoy_canli": "Ana Portföy (Canlı)",
    "optimization.optimizasyon_hesaplaniyor": "Optimizasyon hesaplanıyor...",
    "optimization.optimizasyon_basariyla_tamamlandi": "Optimizasyon başarıyla tamamlandı.",
    "optimization.portfoy_optimizasyonu_basariyla_tamamlandi": "Portföy optimizasyonu başarıyla tamamlandı.",
    # --- Optimizasyon girdisi ---
    "optimization_input.portfolioservice_bulunamadi": "PortfolioService bulunamadı.",
    "optimization_input.optimizasyon_icin_portfoyde_en_az_2": "Optimizasyon için portföyde en az 2 farklı hisse bulunmalıdır.",
    "optimization_input.modelportfolioservice_bulunamadi": "ModelPortfolioService bulunamadı.",
    "optimization_input.optimizasyon_icin_model_portfoyde_en_az": "Optimizasyon için model portföyde en az 2 farklı hisse bulunmalıdır.",
    "optimization_input.optimizationservice_hazir_degil": "OptimizationService hazır değil.",
    # --- Karşılaştırma grafiği ---
    "comparison_chart.fiyat_deger": "Fiyat / Değer",
    "comparison_chart.maksimum_deger_kaybi_drawdown": "Maksimum Değer Kaybı (Drawdown %)",
    # --- Karşılaştırma rozetleri ---
    "comparison.kind_portfolio": "PORTFÖY",
    "comparison.kind_unified": "TÜM VARLIKLAR",
    "comparison.kind_model": "MODEL",
    "comparison.kind_market": "PİYASA",
    # --- Birleşik optimizasyon ---
    "optimization.tum_varliklar_canli": "Tüm Varlıklar (Canlı)",
    "optimization_input.birlesik_optimizasyon_hazir_degil": "Birleşik portföy optimizasyonu hazır değil.",
    # --- Nakit rezervi ---
    "optimization.nakit_etiketi": "NAKİT",
    "optimization.nakit_adi": "Nakit (TL + USD)",
}
