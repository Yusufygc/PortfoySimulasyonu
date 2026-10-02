"""
RiskProfileController — Risk profili anketi (soru bölümleri, puanlama, kayıtlı profil) QML controller'ı.

`RiskProfileService` üzerinden anket sorularını sunar, yanıtları puanlayıp kaydeder ve kayıtlı
profili özetler. Optimizasyon ekranı kaydedilen profili `profileSaved` sinyaliyle takip eder.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.application.services.planning.risk_profile_service import DIMENSION_LABELS
from src.domain.models.risk_profile import RiskLabel, RiskProfile

logger = logging.getLogger(__name__)

LABEL_NAMES = {
    RiskLabel.COK_MUHAFAZAKAR: "Çok Muhafazakar",
    RiskLabel.MUHAFAZAKAR: "Muhafazakar",
    RiskLabel.DENGELI: "Dengeli",
    RiskLabel.BUYUME_ODAKLI: "Büyüme Odaklı",
    RiskLabel.AGRESIF: "Agresif",
}
# Eski veritabanı şeması uyarıları kullanıcıya gösterilmez
_HIDDEN_NOTE_MARKER = "eski şema"


def _empty_profile() -> Dict[str, Any]:
    """Kayıtlı profil yokken QML bağlamalarının undefined üretmemesi için tam alanlı boş profil."""
    return {
        "exists": False, "score": 0, "label": "", "labelText": "", "description": "",
        "dimensions": [], "allocation": [], "notes": [], "answers": {},
    }


class RiskProfileController(QObject):
    """QML context property: riskProfileController"""

    profileChanged = Signal()
    busyChanged = Signal()
    # (success, message) — Anket diyaloğu durum satırı
    notification = Signal(bool, str, arguments=["success", "message"])
    # Yeni profil kaydedildi; Optimizasyon ekranı profil seçimini güncellemeli
    profileSaved = Signal()

    def __init__(self, container=None, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._service = getattr(container, "risk_profile_service", None) if container else None
        self._is_busy = False
        self._sections: List[Dict[str, Any]] = self._build_sections()
        self._profile: Dict[str, Any] = _empty_profile()
        self.reload()

    # ------------------------------------------------------------------ properties

    @Property(bool, constant=True)
    def serviceAvailable(self) -> bool:
        return self._service is not None

    @Property(bool, notify=busyChanged)
    def isBusy(self) -> bool:
        return self._is_busy

    @Property("QVariantList", constant=True)
    def sections(self) -> list:
        return self._sections

    @Property("QVariantMap", notify=profileChanged)
    def profile(self) -> dict:
        return self._profile

    # ------------------------------------------------------------------ slots

    @Slot()
    def reload(self) -> None:
        if self._service is None:
            self._profile = _empty_profile()
            self.profileChanged.emit()
            return
        try:
            profile = self._service.get_current_profile()
        except Exception as exc:
            logger.warning("Kayıtlı risk profili okunamadı: %s", exc)
            profile = None
        self._profile = self._profile_to_dict(profile) if profile else _empty_profile()
        self.profileChanged.emit()

    @Slot("QVariantMap", result=bool)
    def calculate(self, answers: dict) -> bool:
        """Anket yanıtlarını puanlar ve kaydeder. Başarılıysa True döner."""
        if self._service is None:
            self.notification.emit(False, "Risk profili servisi kullanılamıyor.")
            return False
        clean = {str(k): str(v) for k, v in (answers or {}).items()}
        missing = [q["id"] for s in self._sections for q in s["questions"] if q["id"] not in clean]
        if missing:
            self.notification.emit(False, "Lütfen tüm soruları yanıtlayın.")
            return False
        self._is_busy = True
        self.busyChanged.emit()
        try:
            profile = self._service.calculate_and_save_profile(answers=clean)
        except Exception as exc:
            logger.exception("Risk profili hesaplanamadı: %s", exc)
            self.notification.emit(False, f"Profil hesaplanamadı: {exc}")
            return False
        finally:
            self._is_busy = False
            self.busyChanged.emit()
        self._profile = self._profile_to_dict(profile)
        self.profileChanged.emit()
        self.profileSaved.emit()
        self.notification.emit(
            True, f"Risk skorunuz: {profile.risk_score}/100 — Profiliniz: {LABEL_NAMES.get(profile.risk_label, profile.risk_label)}"
        )
        return True

    # ------------------------------------------------------------------ yardımcılar

    def _build_sections(self) -> List[Dict[str, Any]]:
        if self._service is None:
            return []
        try:
            raw_sections = self._service.get_questionnaire()
        except Exception as exc:
            logger.warning("Risk anketi okunamadı: %s", exc)
            return []
        sections = []
        for section in raw_sections:
            sections.append({
                "title": section.title,
                "questions": [
                    {
                        "id": q.id,
                        "title": q.title,
                        "dimension": DIMENSION_LABELS.get(q.dimension, q.dimension),
                        "options": [{"value": o.value, "label": o.label} for o in q.options],
                    }
                    for q in section.questions
                ],
            })
        return sections

    @staticmethod
    def _profile_to_dict(profile: RiskProfile) -> Dict[str, Any]:
        return {
            "exists": True,
            "score": int(profile.risk_score),
            "label": profile.risk_label,
            "labelText": LABEL_NAMES.get(profile.risk_label, profile.risk_label),
            "description": profile.description,
            "dimensions": [
                {"name": DIMENSION_LABELS.get(key, key), "score": int(value)}
                for key, value in profile.dimension_scores.items()
            ],
            "allocation": [
                {"asset": asset, "weight": int(weight)} for asset, weight in profile.recommended_allocation.items()
            ],
            "notes": [n for n in profile.suitability_notes if _HIDDEN_NOTE_MARKER not in n.lower()],
            "answers": dict(profile.answers),
        }
