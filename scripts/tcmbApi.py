import requests
import pandas as pd

# --- AYARLAR ---
API_KEY = "" # Kendi API anahtarın
SERI_KODU = "TP.DK.USD.A"       # Dolar/TL Alış Kuru
BASLANGIC = "01-01-2024"
BITIS = "31-05-2024"

# EVDS3 URL
url = f"https://evds3.tcmb.gov.tr/igmevdsms-dis/series={SERI_KODU}&startDate={BASLANGIC}&endDate={BITIS}&type=json"

headers = {
    "key": API_KEY
}

print("Veriler TCMB EVDS3'ten çekiliyor, lütfen bekleyin...")

response = requests.get(url, headers=headers)

if response.status_code == 200:
    try:
        veri = response.json()
        if "items" in veri:
            df = pd.DataFrame(veri["items"])
            
            # 🎯 KRİTİK GÜNCELLEME: TCMB'nin nokta (.) yerine alt çizgi (_) kullanma huyunu çözüyoruz
            json_sutun_adi = SERI_KODU.replace(".", "_")
            
            # Tablodan sadece Tarih ve ilgili kur sütununu çekiyoruz
            df = df[['Tarih', json_sutun_adi]]
            
            # Hafta sonu gibi boş (null) gelen verileri temizliyoruz
            df = df.dropna()
            
            print("\n✅ Veri başarıyla çekildi!\n")
            print(df.head(10))
            
        else:
            print("Veri bulunamadı. Gelen JSON:", veri)
            
    except Exception as e:
        print("❌ Hata Oluştu:", e)
else:
    print(f"❌ HATA! HTTP Kodu: {response.status_code}")
    print("Hata Detayı:", response.text)