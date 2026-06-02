from __future__ import annotations

import logging
from datetime import date

logger = logging.getLogger(__name__)


class ComparisonWarningBuilder:
    def __init__(self, page, analysis_service) -> None:
        self.page = page
        self.analysis_service = analysis_service

    def check_date_warnings(self) -> list[str]:
        warnings: list[str] = []
        start_date, end_date = self.page.ribbon_bar.date_range()

        if start_date > end_date:
            warnings.append("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
            return warnings

        if end_date > date.today():
            warnings.append("Bitiş tarihi bugünden ileri bir tarih olamaz.")

        selected_codes = self.page.ribbon_bar.selected_assets()
        for code in selected_codes:
            if not (code == "dashboard" or code.startswith("portfolio:") or code.startswith("model:")):
                continue
            try:
                first_trade_dt = self.analysis_service.get_first_trade_date_for_source(code)
                if first_trade_dt and start_date < first_trade_dt:
                    label = getattr(self.page, "_asset_labels", {}).get(code, code)
                    warnings.append(
                        f"Seçilen başlangıç tarihi ({start_date.strftime('%d.%m.%Y')}), "
                        f"<b>{label}</b> varlığının ilk işlem tarihinden "
                        f"({first_trade_dt.strftime('%d.%m.%Y')}) öncedir. "
                        "Bu dönemde portföy değeri 0 veya sabit nakit olarak "
                        "görüneceğinden kıyaslama yanıltıcı olabilir."
                    )
            except Exception as exc:
                logger.debug("Failed to get first trade date for %s: %s", code, exc)

        if (end_date - start_date).days < 7:
            warnings.append(
                "Seçilen tarih aralığı çok kısa (7 günden az). "
                "Yıllıklandırılmış volatilite ve drawdown hesaplamaları kararsız olabilir."
            )
        return warnings
