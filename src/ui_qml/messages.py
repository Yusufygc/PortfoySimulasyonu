"""Python tarafından üretilen kullanıcı metinleri için tek katalog.

Denetleyiciler Türkçe metin yazmaz; `msg("anahtar", ad=değer)` çağırır. QML'in kendi metinleri `Strings.qml`'de kalır.
Anahtar adı: `<alan>.<olay>` (ör. `dividend.added`). Parametreler `str.format` ile doldurulur.
`tests/ui_qml/test_message_catalog.py` tanımsız ve kullanılmayan anahtarı yakalar.
"""
from __future__ import annotations

from typing import Dict

MESSAGES: Dict[str, str] = {
    # --- Temettü ---
    "dividend.service_missing": "Temettü servisi kullanılamıyor.",
    "dividend.amount_invalid": "Tutar 0'dan büyük geçerli bir sayı olmalıdır.",
    "dividend.date_invalid": "Tarih geçersiz. Biçim: YYYY-AA-GG",
    "dividend.default_note": "{ticker} temettü",
    "dividend.save_failed": "Temettü kaydedilemedi.",
    "dividend.added": "{amount} ₺ temettü nakit bakiyeye eklendi.",
    "dividend.delete_failed": "Temettü silinemedi.",
    "dividend.deleted": "Temettü kaydı silindi.",
    # --- Haber ayarları ---
    "news_settings.never_fetched": "Henüz çekilmedi",
    "news_settings.from_cache_suffix": " (önbellekteki haberler gösteriliyor)",
    "news_settings.error": "Hata: {error}{suffix}",
    "news_settings.last_fetch": "Son çekim {when}, {count} haber",
    "news_settings.count_only": "{count} haber",
    "news_settings.operation_failed": "İşlem başarısız: {error}",
    "news_settings.test_ok": "Bağlantı başarılı: {count} haber alındı",
    "news_settings.test_failed": "Bağlantı başarısız: {error}",
    # --- Sistem ---
    "system.auto_refresh_failed": "Otomatik fiyat yenileme çalıştırılamadı: {error}",
    "system.reset_service_missing": "Sıfırlama servisi bulunamadı.",
    "system.reset_done": "Sistem başarıyla sıfırlandı.",
    "system.reset_failed": "Sistem sıfırlanamadı: {error}",
    # --- Piyasa verisi senkronu ---
    "market_sync.ready": "Piyasa verisi hazır",
    "market_sync.syncing": "Borsa kapanış verileri senkronize ediliyor...",
    "market_sync.updated": "Borsa verileri güncellendi: {stocks} hisse için {bars} yeni bar eklendi.",
    "market_sync.status_failed": "Güncelleme hatası: {error}",
    "market_sync.notify_failed": "Piyasa verisi güncellenemedi: {error}",
    # --- Risk profili ---
    "risk.label.very_conservative": "Çok Muhafazakar",
    "risk.label.conservative": "Muhafazakar",
    "risk.label.balanced": "Dengeli",
    "risk.label.growth": "Büyüme Odaklı",
    "risk.label.aggressive": "Agresif",
    "risk.service_missing": "Risk profili servisi kullanılamıyor.",
    "risk.answer_all": "Lütfen tüm soruları yanıtlayın.",
    "risk.calc_failed": "Profil hesaplanamadı: {error}",
    # --- Tarayıcı ---
    "screener.ready": "Taramaya hazır",
    "screener.service_missing": "Tarayıcı servisi bulunamadı",
    "screener.running": "Piyasa taranıyor, lütfen bekleyin...",
    "screener.all_strategies": "Tüm Stratejiler",
    "screener.done_empty": "Tarama tamamlandı: Kriterlere uyan hisse bulunamadı",
    "screener.done_count": "Tarama tamamlandı: {count} hisse sinyal verdi",
    # --- Kabuk (sayfa başlıkları, seans) ---
    "page.dashboard": "Ana Sayfa",
    "page.watchlists": "Listelerim",
    "page.model_portfolios": "Model Portföyler",
    "page.stock_360": "Hisse 360",
    "page.comparison": "Karşılaştırma Laboratuvarı",
    "page.screener": "BIST Tarama",
    "page.planning": "Finansal Planlama",
    "page.optimization": "Optimizasyon",
    "page.ai_advisor": "AI Asistan",
    "page.settings": "Ayarlar",
    "page.my_portfolio": "Portföyüm",
    "page.app_title": "Portföy Simülasyonu",
    "session.market_closed": "Piyasa Kapalı",
    "session.bist_open": "BIST: Canlı Seans Açık",
    "session.bist_closed": "BIST: Seans Kapalı",
    # --- Haber akışı ---
    "news.time.now": "şimdi",
    "news.time.minutes": "{n} dk önce",
    "news.time.hours": "{n} sa önce",
    "news.time.days": "{n} gün önce",
}


def msg(key: str, **params: object) -> str:
    """Anahtarın metnini döner; parametreler `{ad}` yer tutucularına yazılır."""
    template = MESSAGES[key]
    return template.format(**params) if params else template
