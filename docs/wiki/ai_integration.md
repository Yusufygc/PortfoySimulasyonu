# Yapay Zeka (Gemini AI) Entegrasyonu

> Ana sayfa: [index.md](index.md) | Mimari: [architecture.md](architecture.md)

Bu belge, `src/ui/pages/ai_page/` ve ilgili servisler altındaki yapay zeka asistanı entegrasyonunu kapsar.

## 1. Temel İşlev ve AI Core

Portföy Simülasyonu, kullanıcının portföyündeki analiz metriklerini, rasyoları veya bir hissenin durumunu düz matematiksel sayılar olmaktan çıkarıp, Gemini API kullanarak yorumlar. 

*Not: Uygulama güncel `google.genai` SDK'sını kullanır. Gemini API anahtarı `config/settings_loader.py` içindeki merkezi ayar yükleyici üzerinden okunur.*

## 2. Açıklanabilirlik ve "Yatırım Tavsiyesi Değildir" Politikası

Projedeki en önemli yapısal kural, yapay zekanın **Yatırım Tavsiyesi** (Al/Sat sinyali) **VERMEMESİDİR**.
Prompt mimarisi şu şekilde kurgulanmıştır:

- **Veri Sağlama:** LLM'e sadece saf finansal veriler, teknik göstergeler (örn. Sharpe, Drawdown) verilir.
- **XAI (Explainable AI - Açıklanabilir Yapay Zeka) Faktörleri:** LLM'den yanıt dönerken, modelin bu yorumu yapmasına neyin sebep olduğunu gösteren "Faktörler" listesi (Örn: "Artan volatilite ve yüksek drawdown oranına dayanarak riskli görünmektedir") istenmektedir.
- Kullanıcıya model görünümü, performans kartı ve XAI faktörleri olarak ayrıştırılmış modüler bir panelle sunum yapılır.

## 3. Sohbet Bağlamı (Context) Aktarımı

Sohbet panelindeki geçmiş konuşmalar sırayla tutulur ve LLM'e (Gemini) beslenir. Bu şekilde kullanıcı, "Bu hissenin grafiğini göster" dediğinde ardından "Peki bu riske değer mi?" diye sorarsa LLM önceki hisseyi hatırlayarak bağlamsal (context-aware) cevap verebilir. Hatalar log dosyasına ayrıntılı yazılırken, kullanıcı arayüzüne (UI) olabildiğince basitleştirilmiş ve kibar bir formatta yansıtılır.
