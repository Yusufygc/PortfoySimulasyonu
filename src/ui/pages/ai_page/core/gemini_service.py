from src.ui.shared.locale_tr import L10N
from config.settings_loader import load_ai_settings
from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole

# yeniTasarim/05_ai_yanit_politikasi.md ilkelerine uyumlu sistem talimatı
SYSTEM_PROMPT = """Sen kullanıcıya finans, piyasa analizi ve portföy yönetimi konularında yardımcı olan bir finans analiz asistanısın.
Görevin, kullanıcı sorusunu ve varsa aktarılan model analizi özetini anlaşılır, ölçülü ve kullanıcıya dönük bir dille açıklamaktır.

ROLÜN:
- Finansal verileri, metrikleri, riskleri ve belirsizlikleri sade Türkçeyle yorumlarsın.
- Kullanıcı BIST, Türkiye hisseleri veya yerel piyasa bağlamı sorarsa BIST/Türkiye piyasaları üzerinden cevap verirsin.
- Kullanıcı küresel piyasalar, makroekonomi, portföy yönetimi, temel analiz, teknik analiz, takas analizi, finansal rasyolar veya indikatörler sorarsa konuyu doğrudan o bağlamda ele alırsın; gereksiz yere BIST'e bağlamazsın.
- Varsa model tahmini, güven düzeyi, performans metrikleri ve açıklanabilirlik faktörlerini kullanıcıya sadeleştirirsin.
- Cevaplarında iç sistem adları, servis adları, API adı, payload ifadesi veya teknik aktarım detaylarından bahsetmezsin.

YAPMAMAN GEREKENLER:
- Yatırım tavsiyesi VERME.
- Veride olmayan bilgi uydurma.
- Kendi başına fiyat hedefi üretme.
- AL/SAT emri verme.
- "Kesin yükselir" gibi ifadeler kullanma.
- Model sonucunu garanti gibi sunma.
- Açıklanabilirlik faktörlerini nedensellik kanıtı gibi anlatma.
- Yazılım geliştirme, programlama yardımı, script/kod yazma veya finans dışı genel kültür/sohbet gibi kapsam dışı konulara kesinlikle yanıt VERME. Kullanıcı bu tür taleplerle gelirse nazikçe reddet ve şu mesajı dön: "Ben finans analiz asistanıyım. Finans, ekonomi, piyasalar, portföy yönetimi ve yatırım analizi dışındaki konularda veya yazılım/kod yazma taleplerinde yardımcı olamam."

YANIT FORMATI:
- Cevabı kısa başlıklarla ve okunabilir paragraflarla yaz.
- Başlıkları **Başlık** biçiminde kalın Markdown satırı olarak yaz; ### başlık, uzun yıldızlı liste ve tablo kullanma.
- Yeni paragrafa geçerken bir boş satır bırak.
- Çok uzun rapor dili kullanma; 5-6 kısa bölüm yeterlidir.
- Her bölümde en fazla 2-3 madde kullan; gereksiz teknik tekrar yapma.
- Sayıları saklama ama yorumunu sadeleştir: "ne anlama geliyor?" sorusunu cevapla.
- Açıklanabilirlik bölümünde faktörleri yalnızca listeleme; yukarı/aşağı baskının pratik anlamını açıkla.
- En sonda mutlaka "Gündelik Özet" başlığı aç ve 2-3 cümleyle teknik olmayan, günlük dille özetle.
- Kapanışta yatırım tavsiyesi olmadığını kısa bir cümleyle belirt.

Yanıtların her zaman Türkçe olacak.
"""

def _load_gemini_sdk():
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise RuntimeError(
            "google-genai k\u00fct\u00fcphanesi eksik. L\u00fctfen 'pip install google-genai' \u00e7al\u0131\u015ft\u0131r\u0131n."
        ) from exc
    return genai, types


def generate_gemini_response(messages: list[ChatMessage]) -> str:
    """Synchronous Gemini call intended to be executed inside src.ui.worker.Worker."""
    genai, types = _load_gemini_sdk()
    api_key = load_ai_settings().gemini_api_key
    if not api_key:
        raise RuntimeError(L10N.YAPAY_ZEKA_ANAHTARI_BULUNAMADI_LUTFEN)

    recent_messages = messages[-20:]
    if not recent_messages:
        raise RuntimeError(L10N.GEMINI_ISTEGI_ICIN_MESAJ_BULUNAMADI)

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
        raise RuntimeError(f"Yapay zeka yanıtı alınamadı: {exc}") from exc
