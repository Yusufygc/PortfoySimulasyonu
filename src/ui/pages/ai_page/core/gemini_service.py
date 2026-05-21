import os
from PyQt5.QtCore import QThread, pyqtSignal
from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole

try:
    import google.generativeai as genai
    from google.generativeai.types import HarmCategory, HarmBlockThreshold
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

# yeniTasarim/05_ai_yanit_politikasi.md ilkelerine uyumlu sistem talimatı
SYSTEM_PROMPT = """Sen BIST (Borsa İstanbul) odaklı bir yapay zeka finans analiz tercümanısın.
Görevin, AI_Core tahmin modelinden gelen yapılandırılmış analiz sonuçlarını kullanıcıya anlaşılır bir dille açıklamaktır.

ROLÜN:
- Analiz tercümanı ve risk açıklayıcısısın.
- API payload'undaki metrik ve bulguları sade Türkçeye çevirirsin.
- Modelin ne beklediğini açıklarsın.
- Performans metriklerini (Composite Score, Yön İsabeti, Sharpe vb.) yorumlarsın.
- XAI faktörlerini anlaşılır hale getirirsin.
- Belirsizlikleri ve riskleri belirtirsin.
- Veri tazeliği uyarısı verirsin.

YAPMAMAN GEREKENLER:
- Yatırım tavsiyesi VERME.
- API'de olmayan bilgi uydurma.
- Kendi başına fiyat hedefi üretme.
- AL/SAT emri verme.
- "Kesin yükselir" gibi ifadeler kullanma.
- Model sonucunu garanti gibi sunma.
- XAI çıktısını nedensellik kanıtı gibi anlatma.

YANIT FORMATI:
1. Kısa özet (1-2 cümle)
2. Model görünümü (hangi model, eğitim tarihi, doğrulama modu)
3. Tahmin ve yön (trend, beklenen getiri, horizon)
4. Güven seviyesi (etiket, nedenleri, uyarılar)
5. Model performansı (öne çıkan metrikler)
6. Öne çıkan XAI faktörleri (yukarı çeken/aşağı iten)
7. Riskler ve belirsizlikler
8. "Bu çıktı kişisel yatırım tavsiyesi değildir" uyarısı

Yanıtların her zaman Türkçe olacak.
"""

class GeminiWorker(QThread):
    response_ready = pyqtSignal(str)
    error_occurred = pyqtSignal(str)

    def __init__(self, messages: list[ChatMessage]):
        super().__init__()
        self.messages = messages
        self._setup_api()

    def _setup_api(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            try:
                from dotenv import load_dotenv
                load_dotenv()
                self.api_key = os.environ.get("GEMINI_API_KEY")
            except ImportError:
                pass
        
        if self.api_key and HAS_GEMINI:
            genai.configure(api_key=self.api_key)

    def run(self):
        if not HAS_GEMINI:
            self.error_occurred.emit("google-generativeai kütüphanesi eksik. Lütfen 'pip install google-generativeai' çalıştırın.")
            return

        if not self.api_key:
            self.error_occurred.emit("Gemini API key bulunamadı. Lütfen ayarlardan ekleyin.")
            return

        try:
            model = genai.GenerativeModel(
                model_name="gemini-3-flash-preview",
                system_instruction=SYSTEM_PROMPT
            )
            
            # Geçmişi Gemini formatına çevir (Sadece son 20 mesajı al)
            recent_messages = self.messages[-20:]
            history = []
            
            for msg in recent_messages[:-1]:
                # Sistem aktarımlarını 'user' olarak gönderelim ama belirtelim
                role = "user" if msg.role in (MessageRole.USER, MessageRole.SYSTEM) else "model"
                content = msg.content
                if msg.role == MessageRole.SYSTEM:
                    content = "[SİSTEM AKTARIMI]\n" + content
                    
                history.append({"role": role, "parts": [content]})
            
            # Son mesajı gönder
            chat = model.start_chat(history=history)
            
            last_msg = recent_messages[-1]
            last_content = last_msg.content
            if last_msg.role == MessageRole.SYSTEM:
                last_content = "[SİSTEM AKTARIMI]\n" + last_content

            response = chat.send_message(last_content)
            self.response_ready.emit(response.text)

        except Exception as e:
            self.error_occurred.emit(f"Gemini API Hatası: {str(e)}")
