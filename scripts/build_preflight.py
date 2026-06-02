from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    message: str


def _require_file(root: Path, relative_path: str) -> CheckResult:
    path = root / relative_path
    return CheckResult(
        relative_path,
        path.exists(),
        "found" if path.exists() else f"missing: {relative_path}",
    )


def _pinned_requirements(root: Path, relative_path: str) -> CheckResult:
    path = root / relative_path
    if not path.exists():
        return CheckResult(relative_path, False, f"missing: {relative_path}")

    unpinned = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "==" not in stripped:
            unpinned.append(stripped)

    return CheckResult(
        f"{relative_path} pins",
        not unpinned,
        "all dependencies pinned" if not unpinned else f"unpinned dependencies: {', '.join(unpinned)}",
    )


def _nuitka_requirement(root: Path) -> CheckResult:
    path = root / "requirements-build.txt"
    if not path.exists():
        return CheckResult("nuitka requirement", False, "requirements-build.txt missing")

    has_nuitka = any(
        line.strip().lower().startswith("nuitka==")
        for line in path.read_text(encoding="utf-8").splitlines()
    )
    return CheckResult(
        "nuitka requirement",
        has_nuitka,
        "nuitka is pinned" if has_nuitka else "nuitka must be pinned in requirements-build.txt",
    )


def _python_version() -> CheckResult:
    ok = sys.version_info >= (3, 11)
    version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return CheckResult(
        "python version",
        ok,
        f"Python {version}" if ok else f"Python {version}; expected >= 3.11",
    )


def _module_importable(python_executable: str, module_name: str) -> bool:
    completed = subprocess.run(
        [python_executable, "-c", f"import {module_name}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return completed.returncode == 0


def _nuitka_import(python_executable: str) -> CheckResult:
    ok = _module_importable(python_executable, "nuitka")
    return CheckResult(
        "nuitka import",
        ok,
        "nuitka importable" if ok else "nuitka is not installed in the active Python environment",
    )


def _pytest_ini_markers(root: Path) -> CheckResult:
    path = root / "pytest.ini"
    if not path.exists():
        return CheckResult("pytest markers", False, "pytest.ini missing")
    text = path.read_text(encoding="utf-8")
    missing = [marker for marker in ("manual", "network", "ui", "integration") if marker not in text]
    return CheckResult(
        "pytest markers",
        not missing,
        "required markers present" if not missing else f"missing markers: {', '.join(missing)}",
    )


def _dist_env_guard(root: Path) -> CheckResult:
    env_path = root / "dist" / ".env"
    return CheckResult(
        "dist env guard",
        not env_path.exists(),
        "dist/.env absent" if not env_path.exists() else "dist/.env must not be shipped",
    )


def run_checks(
    root: Path = ROOT,
    python_executable: str = sys.executable,
    include_runtime_imports: bool = True,
) -> list[CheckResult]:
    checks = [
        _python_version(),
        _require_file(root, ".env.example"),
        _require_file(root, "icons/portfoy-simulasyonu.ico"),
        _require_file(root, "build_nuitka.bat"),
        _pinned_requirements(root, "requirements.txt"),
        _pinned_requirements(root, "requirements-build.txt"),
        _nuitka_requirement(root),
        _pytest_ini_markers(root),
        _dist_env_guard(root),
    ]
    if include_runtime_imports:
        checks.append(_nuitka_import(python_executable))
    return checks


def main() -> int:
    checks = run_checks()
    for check in checks:
        status = "OK" if check.ok else "FAIL"
        print(f"[{status}] {check.name}: {check.message}")

    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
