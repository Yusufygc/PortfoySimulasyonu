"""Bağımlılık kilidi: `constraints.txt` geçişli paketleri sabitler ve `requirements.txt` ile çelişmez."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PIN = re.compile(r"^([A-Za-z0-9_.-]+)==(\S+)$")


def _pins(name: str) -> dict[str, str]:
    pins = {}
    for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
        match = _PIN.match(line.strip())
        if match:
            pins[match.group(1).lower().replace("_", "-")] = match.group(2)
    return pins


def test_every_direct_requirement_is_pinned_to_the_same_version_in_constraints():
    direct, locked = _pins("requirements.txt"), _pins("constraints.txt")

    assert direct, "requirements.txt pinli paket içermiyor"
    mismatched = {name: (version, locked.get(name)) for name, version in direct.items() if locked.get(name) != version}
    assert not mismatched, f"constraints.txt ile uyuşmayan doğrudan paketler (requirements, constraints): {mismatched}"


def test_constraints_pin_transitive_packages_too():
    direct, locked = _pins("requirements.txt"), _pins("constraints.txt")

    assert len(locked) > len(direct) + 20, "constraints.txt geçişli bağımlılıkları da içermelidir"


def test_constraints_contains_only_exact_pins():
    lines = [l.strip() for l in (ROOT / "constraints.txt").read_text(encoding="utf-8").splitlines()]
    loose = [l for l in lines if l and not l.startswith("#") and not _PIN.match(l)]

    assert not loose, f"Sabitlenmemiş satırlar: {loose}"
