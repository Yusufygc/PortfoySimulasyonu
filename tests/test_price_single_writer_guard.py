"""Tek fiyat kaynağı koruması: SQLite `daily_prices`'a fiyat değeri yazan tek uygulama kodu PriceProjectionService'tir.

Fiyatın sahibi DuckDB'dir; başka bir servis SQLite'a doğrudan yazarsa iki depo yeniden ayrışır (2026-11-07 denetimi:
6.914 satır farklı, SDTTR bölünmesi yalnızca bir depoda). Silme (`delete_prices_in_range`) bakım içindir ve DuckDB
silmesiyle birlikte yapılır; bu test onu kapsamaz.
"""
from __future__ import annotations

import ast
from pathlib import Path

SRC = Path(__file__).resolve().parents[1] / "src"
WRITERS = {"upsert_daily_prices_bulk", "upsert_daily_price", "delete_prices_for_dates"}
ALLOWED = {"src/application/services/market_data/price_projection_service.py"}
REPOSITORY_LAYER = "src/infrastructure/db/sqlalchemy/repositories/"


def _callers() -> dict[str, list[str]]:
    found: dict[str, list[str]] = {}
    for path in SRC.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        rel = path.relative_to(SRC.parent).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in WRITERS:
                found.setdefault(rel, []).append(f"{node.func.attr}:{node.lineno}")
    return found


def test_only_the_projection_writes_sqlite_prices():
    offenders = {p: c for p, c in _callers().items() if p not in ALLOWED and not p.startswith(REPOSITORY_LAYER)}
    assert not offenders, f"SQLite fiyatına doğrudan yazan kod (PriceProjectionService kullanın): {offenders}"


def test_guard_sees_the_projection_writer():
    assert "src/application/services/market_data/price_projection_service.py" in _callers()
