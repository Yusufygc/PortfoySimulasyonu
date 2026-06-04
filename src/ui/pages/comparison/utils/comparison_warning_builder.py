from __future__ import annotations
from src.ui.shared.locale_tr import L10N

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
            warnings.append(L10N.BASLANGIC_TARIHI_BITIS_TARIHINDEN_SONRA)
            return warnings

        if end_date > date.today():
            warnings.append(L10N.BITIS_TARIHI_BUGUNDEN_ILERI_BIR)

        selected_codes = self.page.ribbon_bar.selected_assets()
        for code in selected_codes:
            if not (code == "dashboard" or code.startswith("portfolio:") or code.startswith("model:")):
                continue
            try:
                first_trade_dt = self.analysis_service.get_first_trade_date_for_source(code)
                if first_trade_dt and start_date < first_trade_dt:
                    label = getattr(self.page, "_asset_labels", {}).get(code, code)
                    warnings.append(
                        f"Seçilen başlangıç tarihi ({start_date.strftime('%d.%m.%Y')}), " +
                        f"<b>{label}</b> varlığının ilk işlem tarihinden " +
                        f"({first_trade_dt.strftime('%d.%m.%Y')}) öncedir. " +
                        L10N.BU_DONEMDE_PORTFOY_DEGERI_0 +
                        L10N.GORUNECEGINDEN_KIYASLAMA_YANILTICI_OLABILIR
                    )
            except Exception as exc:
                logger.debug("Failed to get first trade date for %s: %s", code, exc)

        if (end_date - start_date).days < 7:
            warnings.append(
                L10N.SECILEN_TARIH_ARALIGI_COK_KISA +
                L10N.YILLIKLANDIRILMIS_VOLATILITE_VE_DRAWDOWN_HESAPLAMALARI
            )
        return warnings
