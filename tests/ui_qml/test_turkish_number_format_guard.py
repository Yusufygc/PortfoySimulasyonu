"""Kullanıcıya görünen sayılar Türkçe biçimlenir: ABD binlik biçimi (`:,`) yalnızca açık ayraç çevirmesiyle kullanılabilir."""
from __future__ import annotations

import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "ui_qml"
US_THOUSANDS = re.compile(r":,[.}d]")
SWAPPED = ('.replace(",", "X")', '.replace(",", ".")')          # sonradan Türkçeye çevrilen biçimler
EXEMPT_FILES = {"formatting.py"}


def test_no_us_style_thousands_separator_in_ui_python_code():
    offenders = []
    for path in sorted(SRC.rglob("*.py")):
        if path.name in EXEMPT_FILES or "__pycache__" in path.parts:
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if US_THOUSANDS.search(line) and not line.lstrip().startswith("#") and not any(token in line for token in SWAPPED):
                offenders.append(f"{path.relative_to(SRC)}:{number}: {line.strip()[:90]}")
    assert not offenders, "ABD binlik biçimi yerine tr_number/tr_pct kullanın:\n" + "\n".join(offenders)
