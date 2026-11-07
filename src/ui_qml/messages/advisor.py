"""Mesaj kataloğu: AI danışman: yerel analiz, sağlık skoru ve sohbet.

Anahtar önekleri: advisor_chat, advisor_health, advisor_local, ai_advisor.
"""
from __future__ import annotations

from typing import Dict

MESSAGES: Dict[str, str] = {
    # --- AI danışman yerel analiz ---
    "advisor_local.portfoy_genel_ozeti": "Portföy Genel Özeti",
    "advisor_local.varlik_dagilimi_ve_risk": "Varlık Dağılımı ve Risk",
    "advisor_local.not_yerel_analiz_motoru_calistirildi_gemini": "*Not: Yerel analiz motoru çalıştırıldı. Gemini API anahtarı ekleyerek çoklu turlu etkileşimli danışmanlığı aktif edebilirsiniz.*",
    "advisor_local.not_yerel_analiz_motoru_calistirildi_gemini_2": "*Not: Yerel analiz motoru çalıştırıldı. Gemini API anahtarı tanımlandığında model ile doğrudan serbest sohbet edebilirsiniz.*",
    "advisor_local.yatirim_tavsiyesi_degildir_ytd": "**Yatırım Tavsiyesi Değildir (YTD).**",
    "advisor_local.modern_portfoy_teorisi_yeniden_dengeleme_ana": "### Modern Portföy Teorisi — Yeniden Dengeleme Analizi",
    "advisor_local.mevcut_portfoyunuzun_toplam_buyuklugu_seviye": "Mevcut portföyünüzün toplam büyüklüğü **{amount}** seviyesindedir. Dengeli risk profili simülasyonuna göre portföyünüzün getiri/risk oranını maksimize etmek için aşağıdaki düzenlemeler önerilmektedir:",
    "advisor_local.hisse_mevcut_pay_hedef_pay_degisim": "| Hisse | Mevcut Pay | Hedef Pay | Değişim | Aksiyon |",
    "advisor_local.stratejik_degerlendirme_portfoyde_agirligi_y": "**Stratejik Değerlendirme:** Portföyde ağırlığı yüksek olan hisselerden kâr realizasyonu yapılarak ağırlığı düşük kalan hisselere pay aktarılması genel portföy volatilitesini düşürecektir.",
    "advisor_local.portfoyunuzde_henuz_yeterli_cesitlilikte_his": "Portföyünüzde henüz yeterli çeşitlilikte hisse senedi bulunmadığından optimizasyon matrisi oluşturulamadı.",
    "advisor_local.danisman_degerlendirmesi": "#### Danışman Değerlendirmesi:",
    "advisor_local.yuksek_yogunlasma_riski_portfoyunuzun_60_ind": "- **Yüksek Yoğunlaşma Riski:** Portföyünüzün %60'ından fazlası ilk 3 hissede toplanmış durumda. Sektörel şoklara karşı dayanıklılığı artırmak için portföyü farklı sektörlere yaymanız önerilir.",
    "advisor_local.dengeli_varlik_dagilimi_hisselerinizin_portf": "- **Dengeli Varlık Dağılımı:** Hisselerinizin portföye dağılımı makul seviyelerde. Tek bir hisseye aşırı bağımlılık riski düşük.",
    "advisor_local.guclu_risk_getiri_dengesi_sharpe_oraniniz": "- **Güçlü Risk-Getiri Dengesi:** Sharpe oranınız 1.0 seviyesinin üzerinde, bu da aldığınız riskin getiri ile iyi dengelendiğini gösteriyor.",
    "advisor_local.getiri_potansiyeli_volatiliteye_oranla_getir": "- **Getiri Potansiyeli:** Volatiliteye oranla getiri marjını yükseltmek için 'Optimizasyon' sekmesindeki rebalance modelini inceleyebilirsiniz.",
    "advisor_local.portfoy_saglik_risk_durumu_raporu": "### Portföy Sağlık & Risk Durumu Raporu",
    "advisor_local.portfoyunuzun_toplam_degeri_olup_piyasa_hare": "Portföyünüzün toplam değeri **{amount}** olup piyasa hareketlerine karşı genel görünümü şöyledir:",
    "advisor_local.donem_getirisi_bist_100_endeksine_gore": "- **Dönem Getirisi:** {period} (BIST 100 Endeksine Göre: {gap})",
    "advisor_local.yillik_volatilite_risk": "- **Yıllık Volatilite (Risk):** {pct}",
    "advisor_local.sharpe_orani_birim_risk_basina_getiri": "- **Sharpe Oranı:** {sharpe} (Birim risk başına getiri kalitesi)",
    "advisor_local.maksimum_geri_cekilme_drawdown": "- **Maksimum Geri Çekilme (Drawdown):** {pct}",
    "advisor_local.en_buyuk_pozisyon": "- **En Büyük Pozisyon:** **{ticker}** ({weight})",
    "advisor_local.ilk_3_hisse_yogunlasmasi": "- **İlk 3 Hisse Yoğunlaşması:** {pct}",
    # --- AI danışman sağlık skoru ---
    "advisor_health.yuksek_cesitlilik": "Yüksek Çeşitlilik",
    "advisor_health.dengeli_dagilim": "Dengeli Dağılım",
    "advisor_health.orta_yogunlasma": "Orta Yoğunlaşma",
    "advisor_health.yuksek_yogunlasma_riski": "Yüksek Yoğunlaşma Riski",
    "advisor_health.dusuk_volatilite": "Düşük Volatilite",
    "advisor_health.piyasa_ortalamasi": "Piyasa Ortalaması",
    "advisor_health.yuksek_dalgalanma": "Yüksek Dalgalanma",
    "advisor_health.asiri_riskli": "Aşırı Riskli",
    "advisor_health.mukemmel_koruma": "Mükemmel Koruma",
    "advisor_health.normal_geri_cekilme": "Normal Geri Çekilme",
    "advisor_health.yuksek_kayip_riski": "Yüksek Kayıp Riski",
    "advisor_health.kritik_dusus_seviyesi": "Kritik Düşüş Seviyesi",
    "advisor_health.mukemmel_getiri_risk": "Mükemmel Getiri/Risk",
    "advisor_health.iyi_performans": "İyi Performans",
    "advisor_health.dusuk_getiri_verimi": "Düşük Getiri Verimi",
    "advisor_health.cok_guclu": "Çok Güçlü",
    "advisor_health.yuksek_risk": "Yüksek Risk",
    "advisor_health.varlik_cesitliligi": "Varlık Çeşitliliği",
    "advisor_health.ilk_3": "%{top3_w} (İlk 3)",
    "advisor_health.maksimum_dusus": "Maksimum Düşüş",
    # --- AI danışman sohbet ---
    "advisor_chat.merhaba_ben_gemini_destekli_yapay_zeka": "**Merhaba! Ben Gemini destekli Yapay Zeka Portföy Danışmanınız.**\n\nPortföyünüzün risk ve varlık dağılımını analiz edebilir, Modern Portföy Teorisi'ne göre yeniden dengeleme (rebalance) önerileri sunabilir ve hisselerinizin teknik/temel verilerini yorumlayabilirim.\n\nAşağıdaki **Hızlı Analiz Soruları**ndan birine tıklayabilir veya aklınızdaki soruyu doğrudan yazabilirsiniz.",
    "advisor_chat.portfoy_risk_analizi": "Portföy Risk Analizi",
    "advisor_chat.portfoyumun_genel_risk_ve_getiri_durumunu": "Portföyümün genel risk ve getiri durumunu, Sharpe oranını ve en büyük risk faktörlerini özetler misin?",
    "advisor_chat.varlik_dagilimi_yogunlasma": "Varlık Dağılımı & Yoğunlaşma",
    "advisor_chat.portfoyumdeki_varlik_dagilimi_ve_hisse_agirl": "Portföyümdeki varlık dağılımı ve hisse ağırlıklarım dengeli mi? Aşırı yoğunlaşma riski taşıyan hissem var mı?",
    "advisor_chat.dengeli_risk_profiline_gore_portfoyumu_optim": "Dengeli risk profiline göre portföyümü optimize ettiğimizde hangi hisseleri artırmalı veya azaltmalıyım?",
    "advisor_chat.hisse_durum_degerlendirmesi": "Hisse Durum Değerlendirmesi",
    "advisor_chat.portfoyumdeki_en_buyuk_pozisyonumun_guncel_f": "Portföyümdeki en büyük pozisyonumun güncel fiyatı, teknik seviyeleri ve 52 haftalık görünümü nedir?",
    # --- AI danışman ---
    "ai_advisor.hazir": "Hazır",
    "ai_advisor.sohbet_sifirlandi": "Sohbet sıfırlandı",
    "ai_advisor.gemini_analiz_ediyor_ve_portfoy_verilerini": "Gemini analiz ediyor ve portföy verilerini inceliyor...",
    "ai_advisor.yanit_alinirken_bir_hata_olustu": "Yanıt alınırken bir hata oluştu: {error_msg}",
    "ai_advisor.hata_olustu": "Hata oluştu",
    "ai_advisor.api_anahtari_kaydedilemedi": "API anahtarı kaydedilemedi: {exc}",
    "ai_advisor.gemini_api_anahtari_kaydedildi": "Gemini API Anahtarı kaydedildi",
    "ai_advisor.google_gemini_api_anahtariniz_basariyla_tani": "Google Gemini API anahtarınız başarıyla tanımlandı. Gemini 2.5 Flash ile tam etkileşimli danışmanlık aktif.",
}
