"""
FeeSettingsController — Ayarlar > Ücretler (QML).

BIST komisyonu, BIST dışı varlık komisyonu ve BSMV oranları (yüzde, varsayılan 0). Yalnızca `FeeSettingsService`
üzerinden okur/yazar; ücret işlem anında hesaplanır ve işlemle saklanır, bu yüzden değişiklik eski işlemleri etkilemez.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from PySide6.QtCore import Property, QObject, Signal, Slot

from src.domain.models.fees import VALID_FEE_MODES, FeeRates
from src.ui_qml.controllers.number_input import parse_decimal_text
from src.ui_qml.messages import msg

_MODE_ATTRS = {"bist": "_bist_mode", "asset": "_asset_mode", "bsmv": "_bsmv_mode"}


def rate_text(value: Decimal) -> str:
    """0.2 -> '0,2'; 5.00 -> '5'; 0 -> '0' (Türkçe ondalık virgülü)."""
    text = format(value.normalize(), "f")
    return text.replace(".", ",")


class FeeSettingsController(QObject):
    ratesChanged = Signal()
    modesChanged = Signal()
    notify = Signal(bool, str, arguments=["success", "message"])

    def __init__(self, container=None, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._service = getattr(container, "fee_settings_service", None) if container else None
        self._rates = self._service.get_rates() if self._service else FeeRates()
        self._bist_mode = self._rates.bist_mode
        self._asset_mode = self._rates.asset_mode
        self._bsmv_mode = self._rates.bsmv_mode

    bistCommission = Property(str, lambda self: rate_text(self._rates.bist_commission_pct), notify=ratesChanged)
    assetCommission = Property(str, lambda self: rate_text(self._rates.asset_commission_pct), notify=ratesChanged)
    bsmv = Property(str, lambda self: rate_text(self._rates.bsmv_pct), notify=ratesChanged)
    bistMode = Property(str, lambda self: self._bist_mode, notify=modesChanged)
    assetMode = Property(str, lambda self: self._asset_mode, notify=modesChanged)
    bsmvMode = Property(str, lambda self: self._bsmv_mode, notify=modesChanged)

    @Slot()
    def reload(self) -> None:
        if self._service:
            self._rates = self._service.get_rates()
            self._bist_mode = self._rates.bist_mode
            self._asset_mode = self._rates.asset_mode
            self._bsmv_mode = self._rates.bsmv_mode
            self.ratesChanged.emit()
            self.modesChanged.emit()

    @Slot(str, str)
    def setMode(self, field: str, mode: str) -> None:
        attr = _MODE_ATTRS.get(field)
        normalized = (mode or "").strip().upper()
        if attr is None or normalized not in VALID_FEE_MODES:
            return
        if getattr(self, attr) != normalized:
            setattr(self, attr, normalized)
            self.modesChanged.emit()

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
            rates = FeeRates(
                values[0],
                values[1],
                values[2],
                self._bist_mode,
                self._asset_mode,
                self._bsmv_mode,
            )
        except ValueError as exc:
            self.notify.emit(False, str(exc))
            return
        self._service.set_rates(rates)
        self._rates = rates
        self.ratesChanged.emit()
        self.modesChanged.emit()
        self.notify.emit(True, msg("fees.saved"))
