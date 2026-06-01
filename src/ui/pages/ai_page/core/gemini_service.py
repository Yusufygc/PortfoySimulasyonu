from PyQt5.QtCore import QThread, pyqtSignal
from config.settings_loader import load_ai_settings
from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole

try:
    from google import genai
    from google.genai import types
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
- Cevabı kısa başlıklarla ve okunabilir paragraflarla yaz.
- Başlıkları düz metin gibi yaz; ###, uzun yıldızlı liste ve tablo kullanma.
- Çok uzun rapor dili kullanma; 5-6 kısa bölüm yeterlidir.
- Her bölümde en fazla 2-3 madde kullan; gereksiz teknik tekrar yapma.
- Sayıları saklama ama yorumunu sadeleştir: "ne anlama geliyor?" sorusunu cevapla.
- XAI bölümünde faktörleri yalnızca listeleme; yukarı/aşağı baskının pratik anlamını açıkla.
- En sonda mutlaka "Gündelik Özet" başlığı aç ve 2-3 cümleyle teknik olmayan, günlük dille özetle.
- Kapanışta yatırım tavsiyesi olmadığını kısa bir cümleyle belirt.

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
        self.api_key = load_ai_settings().gemini_api_key
        
        if self.api_key and HAS_GEMINI:
            self.client = genai.Client(api_key=self.api_key)

    def run(self):
        if not HAS_GEMINI:
            self.error_occurred.emit("google-genai kütüphanesi eksik. Lütfen 'pip install google-genai' çalıştırın.")
            return

        if not self.api_key:
            self.error_occurred.emit("Gemini API key bulunamadı. Lütfen ayarlardan ekleyin.")
            return

        try:
            config = types.GenerateContentConfig(
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
                    
                history.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))
            
            # Son mesajı gönder
            chat = self.client.chats.create(
                model="gemini-3-flash-preview",
                config=config,
                history=history
            )
            
            last_msg = recent_messages[-1]
            last_content = last_msg.content
            if last_msg.role == MessageRole.SYSTEM:
                last_content = "[SİSTEM AKTARIMI]\n" + last_content

            response = chat.send_message(last_content)
            self.response_ready.emit(response.text)

        except Exception as e:
            self.error_occurred.emit(f"Gemini API Hatası: {str(e)}")
