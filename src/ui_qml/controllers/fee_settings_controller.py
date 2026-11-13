"""
FeeSettingsController — Ayarlar > Ücretler (QML).

BIST komisyonu, BIST dışı varlık komisyonu ve BSMV oranları (yüzde, varsayılan 0). Yalnızca `FeeSettingsService`
üzerinden okur/yazar; ücret işlem anında hesaplanır ve işlemle saklanır, bu yüzden değişiklik eski işlemleri etkilemez.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.domain.models.fees import FeeRates
from src.ui_qml.controllers.number_input import parse_decimal_text
from src.ui_qml.messages import msg


def rate_text(value: Decimal) -> str:
    """0.2 -> '0,2'; 5.00 -> '5'; 0 -> '0' (Türkçe ondalık virgülü)."""
    text = format(value.normalize(), "f")
    return text.replace(".", ",")


class FeeSettingsController(QObject):
    ratesChanged = Signal()
    notify = Signal(bool, str, arguments=["success", "message"])

    def __init__(self, container=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = getattr(container, "fee_settings_service", None) if container else None
        self._rates = self._service.get_rates() if self._service else FeeRates()

    bistCommission = Property(str, lambda self: rate_text(self._rates.bist_commission_pct), notify=ratesChanged)
    assetCommission = Property(str, lambda self: rate_text(self._rates.asset_commission_pct), notify=ratesChanged)
    bsmv = Property(str, lambda self: rate_text(self._rates.bsmv_pct), notify=ratesChanged)

    @Slot()
    def reload(self) -> None:
        if self._service:
            self._rates = self._service.get_rates()
            self.ratesChanged.emit()

    @Slot(str, str, str)
    def save(self, bist_text: str, asset_text: str, bsmv_text: str) -> None:
        if self._service is None:
            self.notify.emit(False, msg("fees.service_missing"))
            return
        values = [parse_decimal_text(text) if (text or "").strip() else Decimal("0") for text in (bist_text, asset_text, bsmv_text)]
        if any(value is None for value in values):
            self.notify.emit(False, msg("fees.invalid_number"))
            return
        try:
            rates = FeeRates(*values)
        except ValueError as exc:
            self.notify.emit(False, str(exc))
            return
        self._service.set_rates(rates)
        self._rates = rates
        self.ratesChanged.emit()
        self.notify.emit(True, msg("fees.saved"))
