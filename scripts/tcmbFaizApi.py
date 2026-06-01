"""
TCMB EVDS Faiz Oranları Referans Listesi
TP.KTF10 : 1 Aya Kadar Vadeli (TL) Mevduat Faizi

TP.KTF11 : 3 Aya Kadar Vadeli (TL) Mevduat Faizi

TP.KTF12 : 6 Aya Kadar Vadeli (TL) Mevduat Faizi

TP.KTF17 : Ticari Krediler (TL) Faiz Oranı
"""

import requests
import pandas as pd
from datetime import datetime

# --- AYARLAR ---
API_KEY = "" # Kendi API anahtarını buraya yapıştır
SERI_KODU = "TP.KTF10"          # GERÇEK EVDS KODU: 1 Aya Kadar Vadeli TL Mevduat Faizi

# Tarihleri dinamik olarak ayarlıyoruz: Bugün ve 6 Ay Öncesi
bugun = datetime.now()
alti_ay_once = bugun - pd.DateOffset(months=6)

BASLANGIC = alti_ay_once.strftime("%d-%m-%Y")
BITIS = bugun.strftime("%d-%m-%Y")

# EVDS3 URL
url = f"https://evds3.tcmb.gov.tr/igmevdsms-dis/series={SERI_KODU}&startDate={BASLANGIC}&endDate={BITIS}&type=json"

headers = {
    "key": API_KEY
}

print(f"TL Mevduat Faizi verileri çekiliyor ({BASLANGIC} - {BITIS})...")

response = requests.get(url, headers=headers)

if response.status_code == 200:
    try:
        veri = response.json()
        if "items" in veri:
            df = pd.DataFrame(veri["items"])
            
            # TCMB'nin JSON formatındaki alt çizgi isimlendirmesini çözüyoruz
            json_sutun_adi = SERI_KODU.replace(".", "_")
            
            # Sadece Tarih ve ilgili faiz sütununu çekiyoruz
            if json_sutun_adi in df.columns:
                df = df[['Tarih', json_sutun_adi]]
                
                # Boş gelen verileri temizliyoruz
                df = df.dropna()
                
                # String (metin) olarak gelen veriyi hesaplamalar için Float (sayı) yapıyoruz
                df[json_sutun_adi] = df[json_sutun_adi].astype(float)
                
                # Tablo okunabilirliğini artırmak için sütun adını değiştiriyoruz
                df.rename(columns={json_sutun_adi: '1_Aylik_TL_Mevduat_Faizi'}, inplace=True)
                
                print("\n✅ Mevduat faizi oranları başarıyla çekildi!\n")
                print(df.tail(10)) 
            else:
                print(f"Hata: Gelen veride '{json_sutun_adi}' sütunu bulunamadı. Sütunlar: {df.columns}")
                
        else:
            print("Veri bulunamadı. Gelen JSON:", veri)
            
    except Exception as e:
        print("❌ Hata Oluştu:", e)
else:
    print(f"❌ HATA! HTTP Kodu: {response.status_code}")
    print("Hata Detayı:", response.text)