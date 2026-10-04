"""Piyasa takvimine bağlı modüller `date.today()` / `datetime.now()` yerine `market_clock` kullanmalı."""
from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Tamamen dönüştürülmüş modüller. Başka bilinçli yerel zaman kullananlar (market_data_sync_service kayıt damgaları,
# startup_jobs_controller tarama aralığı, system_controller işlem damgası) listede yoktur.
MARKET_CLOCK_MODULES = [
    "src/application/services/ai/advisor_tools.py",
    "src/application/services/analysis/financial_analysis_service.py",
    "src/application/services/analysis/stock_360_service.py",
    "src/application/services/analysis/technical/screener_service.py",
    "src/application/services/analysis/technical/technical_analysis_service.py",
    "src/application/services/market/price_data_health_service.py",
    "src/application/services/market/stock_lookup_service.py",
    "src/application/services/market_data/market_universe_migration_service.py",
    "src/application/services/portfolio/cash_movement_service.py",
    "src/application/services/portfolio/portfolio_update_coordinator.py",
    "src/domain/models/financial_goal.py",
    "src/ui_qml/controllers/price_data_controller.py",
]


@pytest.mark.parametrize("relative_path", MARKET_CLOCK_MODULES)
def test_market_sensitive_module_uses_market_clock(relative_path):
    text = (ROOT / relative_path).read_text(encoding="utf-8")

    offenders = [token for token in ("date.today()", "datetime.now()") if token in text]

    assert not offenders, f"{relative_path}: {offenders} yerine src.domain.market_clock kullanın"
