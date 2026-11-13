"""AI Danışman sohbet yardımcıları: sistem istemi, karşılama, hızlı sorular, oturum dönüşümleri ve Gemini çağrısı.

Denetleyici durumundan bağımsız saf fonksiyonlardır.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.domain.models.ai_analysis import ChatMessage, ChatSession, MessageRole
from src.ui_qml.controllers.advisor_local_analysis import TOOL_LABELS
from src.ui_qml.messages import msg

logger = logging.getLogger(__name__)

# metin-muaf: yapay zeka sistem istemi, arayüz metni değil
ADVISOR_SYSTEM_PROMPT = """Sen Borsa İstanbul (BIST) ve modern portföy yönetimi konusunda uzmanlaşmış, analitik, rasyonel ve yardımsever bir Kıdemli Portföy Danışmanısın.
Kullanıcının portföyü yalnızca BIST hisselerinden oluşmaz: altın/gümüş/platin (kıymetli maden), kripto, ABD (NASDAQ) hisseleri ve TL/USD nakit de içerir.
Sana kullanıcının portföyünü, risk metriklerini ve hisse detaylarını inceleyebilmen için özel analiz araçları (tools) sağlanmıştır:
- get_portfolio_overview: Kullanıcının toplam portföy büyüklüğü, dönem getirisi, BIST100 farkı ve en iyi/kötü katkı sağlayan varlıklarını döner (varsayılan kapsam tüm varlıklar, scope=bist yalnızca BIST).
- get_allocation_and_risk: Varlık dağılımı (ağırlık %), volatilite, maksimum düşüş (drawdown), beta, Sharpe ve yoğunlaşma durumunu döner (varsayılan kapsam tüm varlıklar).
- get_assets_overview: Sınıf (BIST, ABD hissesi, kripto, kıymetli maden, nakit) ve pozisyon bazında güncel TL değer, maliyet, kâr/zarar, ağırlık ve nakit bakiyelerini döner.
- suggest_optimization: Modern Portföy Teorisi (Markowitz SLSQP) ile BIST hisse portföyü için hedef ağırlıklar ve AL/SAT/TUT yeniden dengeleme önerileri döner (varlık defterindeki diğer varlıkları kapsamaz; bunu kullanıcıya belirt).
- get_stock_overview: Tek bir hissenin güncel fiyatı, 52 haftalık aralığı ve teknik indikatörlerini (RSI, MACD, SMA) döner.

TEMEL İLKELERİN:
1. Kullanıcı portföyü, hisseleri veya piyasa hakkında bir şey sorduğunda ilgili aracı ÇAĞIR ve gerçek verilere dayanarak konuş.
2. Spekülatif, temelsiz veya kesinlik bildiren ("kesin yükselecektir", "tavan yapacak") ifadelerden kaçın.
3. Rakamları ve oranları Türkiye finans standartlarında ifade et (örn: ₺150.450,20 ve %14,25).
4. Yanıtlarında Markdown kalın metin, liste ve net paragraflar kullan. Aşırı uzun ve boğucu rapor dilinden kaçın; pratik ve uygulanabilir içgörüler sun.
5. Cevabın sonunda mutlaka 1-2 cümlelik "Özet / Aksiyon Önerisi" ve yasal uyarı ("Yatırım tavsiyesi niteliğinde değildir.") ekle.
"""

_WELCOME_TEXT = (
    msg("advisor_chat.merhaba_ben_gemini_destekli_yapay_zeka")
)


def default_quick_prompts() -> List[Dict[str, Any]]:
    return [
        {
            "title": msg("advisor_chat.portfoy_risk_analizi"),
            "prompt": msg("advisor_chat.portfoyumun_genel_risk_ve_getiri_durumunu"),
            "icon": "shield-check",
        },
        {
            "title": msg("advisor_chat.varlik_dagilimi_yogunlasma"),
            "prompt": msg("advisor_chat.portfoyumdeki_varlik_dagilimi_ve_hisse_agirl"),
            "icon": "pie-chart",
        },
        {
            "title": "Rebalance (Yeniden Dengeleme)",
            "prompt": msg("advisor_chat.dengeli_risk_profiline_gore_portfoyumu_optim"),
            "icon": "scale",
        },
        {
            "title": msg("advisor_chat.hisse_durum_degerlendirmesi"),
            "prompt": msg("advisor_chat.portfoyumdeki_en_buyuk_pozisyonumun_guncel_f"),
            "icon": "trending-up",
        },
    ]


def build_welcome_message() -> Dict[str, Any]:
    return {
        "id": "msg-0",
        "role": "ai",
        "content": _WELCOME_TEXT,
        "timestamp": datetime.now().strftime("%H:%M"),
        "toolCalls": [],
        "isWelcome": True,
    }


def message_to_dict(index: int, message: ChatMessage) -> Dict[str, Any]:
    return {
        "id": f"msg-{index}",
        "role": message.role.value,
        "content": message.content,
        "timestamp": message.timestamp.strftime("%H:%M"),
        "toolCalls": [],
    }


def messages_to_persist(entries: Iterable[Dict[str, Any]]) -> List[ChatMessage]:
    """Karşılama ve sistem mesajlarını atlayarak kalıcı kaydedilecek sohbet mesajlarını üretir."""
    persisted = []
    for entry in entries:
        if entry.get("isWelcome") or entry["role"] == "system":
            continue
        try:
            role = MessageRole(entry["role"])
        except ValueError:
            continue
        persisted.append(ChatMessage(role=role, content=entry["content"]))
    return persisted


def session_list_item(session: ChatSession) -> Dict[str, Any]:
    return {
        "id": session.id,
        "title": session.title or "Yeni Sohbet",
        "updatedText": session.updated_at.strftime("%d.%m.%Y %H:%M"),
        "messageCount": sum(1 for m in session.messages if m.role == MessageRole.USER),
    }


def try_gemini_chat(advisor_service: Any, api_key: str, history: List[Tuple[str, str]]) -> Optional[Dict[str, Any]]:
    """Gemini + Function Calling denemesi; hata olursa None döner (yerel analize geçilir)."""
    try:
        # Gemini 'user' ve 'model' rolleri bekler
        turns = [("user" if role == "user" else "model", content) for role, content in history]
        chat_result = advisor_service.chat(api_key, ADVISOR_SYSTEM_PROMPT, turns)
        return {
            "content": chat_result.text,
            "toolCalls": [{"name": tc.name, "label": TOOL_LABELS.get(tc.name, tc.name)} for tc in chat_result.tool_calls],
        }
    except Exception as exc:
        logger.warning("Gemini API çağrısı başarısız, yerel analiz motoruna geçiliyor: %s", exc)
        return None
