"""Mesaj kataloğu: Model portföy ve model analizi.

Anahtar önekleri: model_analysis, model_portfolio.
"""
from __future__ import annotations

from typing import Dict

MESSAGES: Dict[str, str] = {
    # --- Model portföy ---
    "model_portfolio.sira_kaydedilemedi": "Sıra kaydedilemedi: {exc}",
    "model_portfolio.veri_yukleme_hatasi": "Veri yükleme hatası: {exc}",
    "model_portfolio.portfoy_adi_bos_olamaz": "Portföy adı boş olamaz",
    "model_portfolio.portfoyu_olusturuldu": "'{name}' portföyü oluşturuldu",
    "model_portfolio.portfoy_olusturulamadi": "Portföy oluşturulamadı: {exc}",
    "model_portfolio.portfoy_guncellendi": "Portföy güncellendi",
    "model_portfolio.portfoy_guncellenemedi": "Portföy güncellenemedi: {exc}",
    "model_portfolio.portfoy_silindi": "Portföy silindi",
    "model_portfolio.portfoy_silinemedi": "Portföy silinemedi: {exc}",
    "model_portfolio.portfoy_secili_degil": "Portföy seçili değil",
    "model_portfolio.alindi": "alındı",
    "model_portfolio.satildi": "satıldı",
    "model_portfolio.islem_gerceklestirilemedi": "İşlem gerçekleştirilemedi: {exc}",
    "model_portfolio.yatirildi": "yatırıldı",
    "model_portfolio.cekildi": "çekildi",
    "model_portfolio.disa_aktarmak_icin_bir_model_portfoy": "Dışa aktarmak için bir model portföy seçilmelidir.",
    "model_portfolio.tarih_bicimi_gecersiz_bicim_gg_aa": "Tarih biçimi geçersiz. Biçim: GG.AA.YYYY",
    "model_portfolio.bu_model_portfoyde_islem_bulunamadi": "Bu model portföyde işlem bulunamadı.",
    "model_portfolio.baslangic_tarihi_bitis_tarihinden_buyuk_olam": "Başlangıç tarihi bitiş tarihinden büyük olamaz.",
    "model_portfolio.excel_disa_aktarim_servisi_yapilandirilmamis": "Excel dışa aktarım servisi yapılandırılmamış.",
    "model_portfolio.model_portfoy_raporu_olusturuldu": "Model portföy raporu oluşturuldu:\n{name}",
    "model_portfolio.excel_raporu_olusturulamadi": "Excel raporu oluşturulamadı: {exc}",
    # --- Model analizi ---
    "model_analysis.bu_cikti_kisisel_yatirim_tavsiyesi_degildir": "Bu çıktı kişisel yatırım tavsiyesi değildir. Model geçmiş verilerden üretilmiş analitik bir görünümdür; nihai karar kullanıcıya aittir.",
    "model_analysis.yukselis_egilimi": "Yükseliş eğilimi",
    "model_analysis.dusus_egilimi": "Düşüş eğilimi",
    "model_analysis.yatay_notr_gorunum": "Yatay / nötr görünüm",
    "model_analysis.dusuk": "Düşük",
    "model_analysis.yuksek": "Yüksek",
    "model_analysis.yukselis_trendi": "Yükseliş trendi",
    "model_analysis.dusus_trendi": "Düşüş trendi",
    "model_analysis.akranlarina_gore_guclu": "Akranlarına göre güçlü",
    "model_analysis.akranlariyla_paralel": "Akranlarıyla paralel",
    "model_analysis.akranlarina_gore_zayif": "Akranlarına göre zayıf",
    "model_analysis.analiz_basarili_veriler_guncel": "Analiz başarılı, veriler güncel.",
    "model_analysis.dikkat_piyasa_verisi_eski_tahminler_guncel": "Dikkat: piyasa verisi eski, tahminler güncel olmayabilir.",
    "model_analysis.bu_hisse_icin_kayitli_model_bulunamadi": "Bu hisse için kayıtlı model bulunamadı.",
    "model_analysis.model_mevcut_ama_tahmin_uretilmemis": "Model mevcut ama tahmin üretilmemiş.",
    "model_analysis.sonuc_mevcut_ancak_guven_duzeyi_dusuk": "Sonuç mevcut ancak güven düzeyi düşük.",
    "model_analysis.tahmin_mevcut_ama_aciklanabilirlik_xai_veris": "Tahmin mevcut ama açıklanabilirlik (XAI) verisi yok.",
    "model_analysis.beklenmeyen_bir_hata_olustu": "Beklenmeyen bir hata oluştu.",
    "model_analysis.bilesik_skor": "Bileşik skor",
    "model_analysis.yon_dogrulugu": "Yön doğruluğu",
    "model_analysis.isabet_orani": "İsabet oranı",
    "model_analysis.kararlilik": "Kararlılık",
    "model_analysis.gun": "{horizon_days} gün",
    "model_analysis.islem_gunu_geride": " ({staleness_days} işlem günü geride)",
    "model_analysis.icin_model_analizi_sonucu_tahmin_son": "{ticker} için model analizi sonucu: tahmin {predicted} (son kapanış {last_close}, {change}), yön beklentisi: {outlook}, güven: {confidence}. Bu sonucu portföyüm bağlamında yorumlar mısın?",
    "model_analysis.yapay_zeka_motoruna_baglaniliyor": "Yapay zeka motoruna bağlanılıyor...",
    "model_analysis.ai_core_modeli_bagli": "AI_Core modeli bağlı.",
    "model_analysis.model_henuz_bagli_degil_sonuclar_demo": "Model henüz bağlı değil: sonuçlar DEMO verisidir, gerçek tahmin değildir.",
    "model_analysis.analiz_hatasi": "Analiz hatası: {value}",
    "model_analysis.demo_verisi_model_bagli_degil": "DEMO verisi (model bağlı değil): ",
    # --- Model analizi (ek) ---
    "model_analysis.no_result": "sonuç alınamadı",
}
