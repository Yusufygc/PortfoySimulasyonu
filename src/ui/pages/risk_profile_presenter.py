from __future__ import annotations
from src.ui.shared.locale_tr import L10N

import logging
from typing import Dict

from src.domain.exceptions import DatabaseSchemaError
from src.ui.widgets.shared import Toast

logger = logging.getLogger(__name__)

class RiskProfilePresenter:
    def __init__(self, view, service):
        self.view = view
        self.service = service

    def load_initial_profile(self):
        try:
            profile = self.service.get_current_profile()
            if profile:
                self.view.display_profile(profile)
            else:
                self.view.hide_profile()
        except Exception as exc:
            logger.error(f"Mevcut profil yuklenirken hata: {exc}")
            self.view.hide_profile()

    def calculate_and_save(self, answers: Dict[str, str]):
        try:
            profile = self.service.calculate_and_save_profile(answers=answers)
            self.view.display_profile(profile)
            self.view.show_calculation_success(profile)
        except DatabaseSchemaError:
            error_msg = (
                L10N.RISK_PROFILI_KAYDEDILEMEDI_VERITABANI_SEMASI +
                "scripts/alter_risk_profile_professional.sql dosyasini uygulayin."
            )
            Toast.error(self.view, error_msg)
        except Exception as exc:
            logger.error(f"Profil hesaplanirken hata: {exc}")
            Toast.error(self.view, L10N.PROFIL_HESAPLANAMADI_LUTFEN_YANITLARI_KONTROL)
