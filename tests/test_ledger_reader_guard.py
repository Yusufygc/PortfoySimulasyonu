"""Defterler-arası okuma koruması: birden çok defteri (ana, model, varlık) tarayan kod `ILedgerReader` kullanır.

Model portföy işlemlerini tek tek portföy dolaşarak okumak yalnızca o portföyün kendi servislerinde meşrudur.
Yeni bir servis üç defteri ayrı ayrı sorgularsa defterler-arası özellik (bölünme, komisyon, nakit türü) bir defteri
yine unutur (2026-11-07: model portföy aylarca bölünme düzeltmesi almadı).
"""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
PER_LEDGER_READS = {"get_trades_by_portfolio_id", "get_all_stock_ids_in_portfolio"}
ALLOWED = {  # tek model portföyün kendi servisleri
    "src/application/services/planning/model_portfolio_trade_service.py",
    "src/application/services/simulation/model_portfolio_history_simulation_service.py",
}
REPOSITORY_LAYER = "src/infrastructure/db/sqlalchemy/repositories/"


def test_cross_ledger_scans_use_the_ledger_reader():
    offenders = {}
    for path in SRC.rglob("*.py"):
        rel = path.relative_to(SRC.parent).as_posix()
        if "__pycache__" in path.parts or rel in ALLOWED or rel.startswith(REPOSITORY_LAYER):
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in PER_LEDGER_READS:
                offenders.setdefault(rel, []).append(f"{node.func.attr}:{node.lineno}")
    assert not offenders, f"Defter deposunu doğrudan tarayan kod (ILedgerReader.snapshot kullanın): {offenders}"
