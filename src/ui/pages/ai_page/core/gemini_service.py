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
- Sadece finans, ekonomi, borsa (BIST), temel analiz, teknik analiz, takas analizi, finansal rasyolar ve indikatörler ile ilgili soruları yanıtlar, bunlara odaklanırsın.

YAPMAMAN GEREKENLER:
- Yatırım tavsiyesi VERME.
- API'de olmayan bilgi uydurma.
- Kendi başına fiyat hedefi üretme.
- AL/SAT emri verme.
- "Kesin yükselir" gibi ifadeler kullanma.
- Model sonucunu garanti gibi sunma.
- XAI çıktısını nedensellik kanıtı gibi anlatma.
- Yazılım geliştirme, programlama yardımı, script/kod yazma veya finans dışı genel kültür/sohbet gibi kapsam dışı konulara kesinlikle yanıt VERME. Kullanıcı bu tür taleplerle gelirse nazikçe reddet ve şu mesajı dön: "Ben Borsa İstanbul odaklı bir yapay zeka finans analiz asistanıyım. Finans, ekonomi, borsa (temel, teknik, takas analizi vb.) dışındaki konularda veya yazılım/kod yazma taleplerinde yardımcı olamam."

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

def generate_gemini_response(messages: list[ChatMessage]) -> str:
    """Synchronous Gemini call intended to be executed inside src.ui.worker.Worker."""
    if not HAS_GEMINI:
        raise RuntimeError("google-genai kütüphanesi eksik. Lütfen 'pip install google-genai' çalıştırın.")

    api_key = load_ai_settings().gemini_api_key
    if not api_key:
        raise RuntimeError("Gemini API key bulunamadı. Lütfen ayarlardan ekleyin.")

    recent_messages = messages[-20:]
    if not recent_messages:
        raise RuntimeError("Gemini isteği için mesaj bulunamadı.")

    try:
        client = genai.Client(api_key=api_key)
        
        # Configure safety settings to block harmful/unsafe content
        safety_settings = [
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
            types.SafetySetting(
                category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                threshold=types.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            ),
        ]
        
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            safety_settings=safety_settings
        )
        history = []

        for msg in recent_messages[:-1]:
            role = "user" if msg.role in (MessageRole.USER, MessageRole.SYSTEM) else "model"
            content = msg.content
            if msg.role == MessageRole.SYSTEM:
                content = "[SİSTEM AKTARIMI]\n" + content
            elif msg.role == MessageRole.USER:
                from src.ui.pages.ai_page.core.safety_guard import wrap_user_message
                content = wrap_user_message(content)
            history.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))

        chat = client.chats.create(
            model="gemini-3-flash-preview",
            config=config,
            history=history,
        )

        last_msg = recent_messages[-1]
        last_content = last_msg.content
        if last_msg.role == MessageRole.SYSTEM:
            last_content = "[SİSTEM AKTARIMI]\n" + last_content
        elif last_msg.role == MessageRole.USER:
            from src.ui.pages.ai_page.core.safety_guard import wrap_user_message
            last_content = wrap_user_message(last_content)

        response = chat.send_message(last_content)
        return response.text
    except Exception as exc:
        raise RuntimeError(f"Gemini API Hatası: {exc}") from exc
