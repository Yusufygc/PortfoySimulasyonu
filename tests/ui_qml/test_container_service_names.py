"""Denetleyiciler konteynerden servisi dize adıyla ister (`getattr(container, "ad", None)`).

Yanlış yazılmış ad açılışta değil, ilk kullanıcı tıklamasında "servis kullanılamıyor" iletisine dönüşür. Bu test
kaynakta geçen her servis adının `AppContainer`'ın gerçekten sunduğu bir alan olduğunu doğrular.
"""
from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path

from src.application.container_parts import AiSet, MarketClientSet, RepositorySet, ServiceSet

ROOT = Path(__file__).resolve().parents[2]
_CONTAINER_NAMES = {"container", "_container", "self._container", "self.container"}
# AppContainer'ın doğrudan öznitelikleri (container.py)
_CONTAINER_ATTRS = {
    "settings", "db_config", "event_bus", "conn_provider", "repositories", "market_clients", "services",
    "database_maintenance_service", "ai",
}


def _exposed_names() -> set[str]:
    names = set(_CONTAINER_ATTRS)
    for bundle in (RepositorySet, MarketClientSet, ServiceSet, AiSet):
        names.update(field.name for field in fields(bundle))
    return names


def _container_request(node: ast.AST) -> str | None:
    """`getattr(container, "ad", ...)` / `hasattr(container, "ad")` çağrısındaki servis adı; başka çağrıda None."""
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("getattr", "hasattr")):
        return None
    if len(node.args) < 2 or ast.unparse(node.args[0]) not in _CONTAINER_NAMES:
        return None
    name = node.args[1]
    return name.value if isinstance(name, ast.Constant) and isinstance(name.value, str) else None


def _requested_names() -> dict[str, list[str]]:
    requested: dict[str, list[str]] = {}
    for path in (ROOT / "src").rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            name = _container_request(node)
            if name is not None:
                requested.setdefault(name, []).append(f"{path.relative_to(ROOT).as_posix()}:{node.lineno}")
    return requested


def test_every_service_name_requested_from_the_container_exists():
    exposed = _exposed_names()
    missing = {name: places[:3] for name, places in _requested_names().items() if name not in exposed}

    assert not missing, f"Konteynerde bulunmayan servis adları (yazım hatası?): {missing}"


def test_scan_finds_the_known_dashboard_service_requests():
    requested = _requested_names()

    assert "trade_entry_service" in requested and "portfolio_service" in requested
