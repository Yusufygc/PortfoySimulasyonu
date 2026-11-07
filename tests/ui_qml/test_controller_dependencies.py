"""Denetleyici bağımlılıkları: `REQUIRES` bildiren denetleyici container'a doğrudan erişmez; doğrudan erişen
(henüz geçmemiş) denetleyici sayısı yalnızca azalabilir. Ad doğruluğu: test_container_service_names.py."""
from __future__ import annotations

import ast
from pathlib import Path

from src.ui_qml.controllers.deps import ServiceView

CONTROLLERS = Path(__file__).resolve().parents[2] / "src" / "ui_qml" / "controllers"
# REQUIRES'a geçmemiş, container'ı doğrudan kullanan denetleyici modülü sayısı (tavan; yalnızca düşürülür)
DIRECT_ACCESS_CEILING = 19
# REQUIRES bildiren sınıfın yardımcı mixin modülleri (aynı self._deps'i kullanır)
MIXINS_OF = {"stock_detail_controller": ("stock_detail_loader", "stock_detail_actions")}


def _uses_container(tree: ast.AST) -> list[int]:
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == "_container":
            lines.append(node.lineno)
    return lines


def _declares_requires(tree: ast.AST) -> bool:
    return any(
        isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "REQUIRES" for t in node.targets)
        for node in ast.walk(tree)
    )


def _modules():
    for path in sorted(CONTROLLERS.glob("*.py")):
        yield path.stem, ast.parse(path.read_text(encoding="utf-8"))


def test_controllers_with_requires_do_not_touch_the_container():
    trees = dict(_modules())
    offenders = {}
    for name, tree in trees.items():
        if not _declares_requires(tree):
            continue
        for module in (name, *MIXINS_OF.get(name, ())):
            lines = _uses_container(trees[module])
            if lines:
                offenders[module] = lines
    assert not offenders, f"REQUIRES bildiren denetleyicide doğrudan container erişimi: {offenders}"


def test_direct_container_access_only_shrinks():
    mixins = {m for group in MIXINS_OF.values() for m in group}
    direct = sorted(name for name, tree in _modules()
                    if name not in mixins and _uses_container(tree) and not _declares_requires(tree))
    assert len(direct) <= DIRECT_ACCESS_CEILING, (
        f"Container'a doğrudan erişen denetleyici arttı ({len(direct)} > {DIRECT_ACCESS_CEILING}); "
        f"yeni denetleyici REQUIRES + ServiceView kullanmalı: {direct}"
    )


def test_service_view_semantics():
    from types import SimpleNamespace

    import pytest

    container = SimpleNamespace(a_service=1, services=SimpleNamespace(b_service=2))
    view = ServiceView(container, ("a_service", "b_service", "c_service"))
    assert (view.a_service, view.b_service, view.c_service, view.available) == (1, 2, None, True)
    with pytest.raises(AttributeError):
        view.undeclared_service
    offline = ServiceView(None, ("a_service",))
    assert offline.a_service is None and offline.available is False
    container.c_service = 3  # sonradan atanan servis görünür
    assert view.c_service == 3
