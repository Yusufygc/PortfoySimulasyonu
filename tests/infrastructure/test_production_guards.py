import re
from pathlib import Path

from scripts import build_preflight


ROOT = Path(__file__).resolve().parents[2]
SCANNED_SUFFIXES = {
    ".bat",
    ".example",
    ".ini",
    ".md",
    ".ps1",
    ".py",
    ".txt",
    ".yaml",
    ".yml",
}
IGNORED_PARTS = {
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "logs",
    "venv",
    ".venv",
}
PLACEHOLDER_VALUES = {
    "",
    "change-me",
    "password",
    "gemini-key",
    "evds-key",
    "your_password",
    "your_gemini_key",
}


def _iter_scanned_files():
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        rel_parts = set(path.relative_to(ROOT).parts)
        if rel_parts & IGNORED_PARTS:
            continue
        if path.name == ".env":
            continue
        if path.suffix.lower() in SCANNED_SUFFIXES or path.name == ".env.example":
            yield path


def test_repository_does_not_contain_real_secret_literals():
    high_entropy_patterns = (
        re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
        re.compile(r"sk-[A-Za-z0-9]{20,}"),
        re.compile(r"BEGIN (RSA |OPENSSH |EC |DSA )?PRIVATE KEY"),
    )
    assignment_pattern = re.compile(
        r"^(DB_PASSWORD|GEMINI_API_KEY|EVDS_API_KEY|AI_CORE_API_KEY)[ \t]*=[ \t]*([^\s#]*)",
        re.MULTILINE,
    )
    offenders = []

    for path in _iter_scanned_files():
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel_path = path.relative_to(ROOT).as_posix()
        for pattern in high_entropy_patterns:
            if pattern.search(text):
                offenders.append(rel_path)
                break
        for match in assignment_pattern.finditer(text):
            value = match.group(2).strip().strip('"').strip("'")
            if value not in PLACEHOLDER_VALUES:
                offenders.append(f"{rel_path}:{match.group(1)}")

    assert not offenders, f"Potential real secrets found: {sorted(set(offenders))}"


def test_build_preflight_static_checks_pass_without_runtime_imports():
    failures = [
        check
        for check in build_preflight.run_checks(ROOT, include_runtime_imports=False)
        if not check.ok
    ]

    assert not failures, [f"{failure.name}: {failure.message}" for failure in failures]
