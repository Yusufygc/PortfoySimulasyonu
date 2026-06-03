from __future__ import annotations

from PyQt5.QtWidgets import QComboBox

FALLBACK_SCOPE_OPTIONS = [("all_active", "Tüm aktif portföyler"), ("dashboard", "Ana Portföy")]


def populate_scope_combo(combo: QComboBox, price_data_health_service) -> None:
    combo.clear()
    for value, label in portfolio_scope_options(price_data_health_service):
        combo.addItem(label, value)


def portfolio_scope_options(price_data_health_service) -> list[tuple[str, str]]:
    if price_data_health_service is None:
        return list(FALLBACK_SCOPE_OPTIONS)
    options_func = getattr(price_data_health_service, "portfolio_scope_options", None)
    if options_func is None:
        return list(FALLBACK_SCOPE_OPTIONS)
    return [(option.value, option.label) for option in options_func()]
