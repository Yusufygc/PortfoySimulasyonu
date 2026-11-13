"""Model portföy tarihsel Excel dışa aktarımı (Qt'siz): tarih aralığı doğrulama ve dosyaya yazma."""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path
from typing import Optional, Tuple

from src.ui_qml.controllers.date_input import parse_date_text
from src.ui_qml.messages import msg

logger = logging.getLogger(__name__)


def resolve_range(start_text: str, end_text: str, first_trade: Optional[date]) -> Tuple[Optional[date], Optional[date], str]:
    """(başlangıç, bitiş, hata metni); hata boşsa aralık geçerlidir. Boş başlangıç ilk işlem gününe, boş bitiş bugüne düşer."""
    start = parse_date_text(start_text) or first_trade
    end = parse_date_text(end_text) or date.today()
    if (start_text.strip() and parse_date_text(start_text) is None) or (end_text.strip() and parse_date_text(end_text) is None):
        return None, None, msg("model_portfolio.tarih_bicimi_gecersiz_bicim_gg_aa")
    if start is None:
        return None, None, msg("model_portfolio.bu_model_portfoyde_islem_bulunamadi")
    if start > end:
        return None, None, msg("model_portfolio.baslangic_tarihi_bitis_tarihinden_buyuk_olam")
    return start, end, ""


def run_history_export(excel_service, portfolio_id: int, start: date, end: date, file_path: str, append: bool) -> Tuple[bool, str]:
    """Raporu yazar; (başarı, kullanıcı mesajı) döner. Arka plan iş parçacığından çağrılır."""
    from src.application.services.reporting.daily_history_models import ExportMode

    if excel_service is None:
        return False, msg("model_portfolio.excel_disa_aktarim_servisi_yapilandirilmamis")
    try:
        target = Path(file_path) if file_path else Path.home() / "Desktop" / f"Model_Portfoy_{portfolio_id}.xlsx"
        if target.suffix.lower() != ".xlsx":
            target = target.with_suffix(".xlsx")
        target.parent.mkdir(parents=True, exist_ok=True)
        excel_service.export_model_portfolio_history(
            portfolio_id=portfolio_id, start_date=start, end_date=end, file_path=target,
            mode=ExportMode.APPEND if append else ExportMode.OVERWRITE,
        )
        return True, msg("model_portfolio.model_portfoy_raporu_olusturuldu", name=target.name)
    except Exception as exc:
        logger.exception("Model portföy tarihsel Excel export hatası: %s", exc)
        return False, msg("model_portfolio.excel_raporu_olusturulamadi", exc=exc)
