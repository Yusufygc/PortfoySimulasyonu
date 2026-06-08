"""AI sayfası için kullanıcıya dönük Türkçe etiketler.

Domain modelleri (`src/domain/models/ai_analysis.py`) saf kalır ve L10N
içermez; semantic enum/alanların Türkçe gösterimi burada üretilir.
"""

from __future__ import annotations

from src.domain.models.ai_analysis import ModelOutlook
from src.ui.shared.locale_tr import L10N


DEFAULT_INVESTMENT_DISCLAIMER = (
    L10N.BU_CIKTI_KISISEL_YATIRIM_TAVSIYESI
    + L10N.MODEL_GECMIS_VERILERDEN_URETILMIS_ANALITIK
    + L10N.NIHAI_KARAR_KULLANICIYA_AITTIR
)

WELCOME_MESSAGE = L10N.MERHABA_FINANS_PIYASA_ANALIZI_VE
EMPTY_CHAT_TITLE = L10N.YENI_SOHBET

_OUTLOOK_LABELS = {
    ModelOutlook.UP: L10N.YUKSELIS_EGILIMI,
    ModelOutlook.DOWN: L10N.DUSUS_EGILIMI,
    ModelOutlook.NEUTRAL: L10N.YATAY_NOTR_GORUNUM,
}


def outlook_label(outlook: ModelOutlook) -> str:
    """Yön beklentisini kullanıcıya dönük Türkçe etikete çevirir."""
    return _OUTLOOK_LABELS.get(outlook, _OUTLOOK_LABELS[ModelOutlook.NEUTRAL])
