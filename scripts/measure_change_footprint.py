"""Değişiklik ayak izi: özellik commit'i başına değişen kaynak dosya sayısı ve kayıt merkezlerine dokunma oranı.

Yönetilebilirlik hedefi (docs/wiki/code_quality_guardrails.md): medyan kaynak dosya <= 5, commit başına kayıt
merkezi dokunuşu ortalama <= 1. Özellik commit'i: mesajı `ekle:` veya `güncelle:` ile başlayan commit.
Kaynak dosya: `src/` altındaki `.py` / `.qml` (test ve belge sayılmaz).

Kullanım:
    python scripts/measure_change_footprint.py               # son 200 commit
    python scripts/measure_change_footprint.py --limit 50
    python scripts/measure_change_footprint.py --range main..HEAD
"""
from __future__ import annotations

import argparse
import statistics
import subprocess
import sys
from dataclasses import dataclass
from typing import List, Sequence

FEATURE_PREFIXES = ("ekle:", "güncelle:")
SOURCE_SUFFIXES = (".py", ".qml")
# Her yeni özelliğin dokunmak zorunda kaldığı ortak kayıt dosyaları (eski ve yeni yollar).
HUBS = (
    "src/ui_qml/qml/theme/Strings.qml",
    "src/ui_qml/app.py",
    "src/ui_qml/messages.py",
    "src/ui_qml/controllers/registry.py",
    "src/application/container.py",
    "src/application/container_parts/services.py",
    "src/application/container_parts/repositories.py",
)
MARKER = "@@commit@@"


@dataclass(frozen=True)
class CommitFootprint:
    sha: str
    subject: str
    sources: int
    hubs: int


def _git_log(revision: Sequence[str]) -> str:
    command = ["git", "log", "--no-merges", "--name-only", f"--format={MARKER}%h %s", *revision]
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", check=True).stdout


def parse_log(text: str) -> List[CommitFootprint]:
    """`git log --name-only` çıktısından özellik commit'lerinin ayak izini çıkarır."""
    result: List[CommitFootprint] = []
    for block in text.split(MARKER)[1:]:
        header, *paths = [line.strip() for line in block.splitlines() if line.strip()]
        sha, _, subject = header.partition(" ")
        if not subject.lower().startswith(FEATURE_PREFIXES):
            continue
        sources = [p for p in paths if p.startswith("src/") and p.endswith(SOURCE_SUFFIXES)]
        result.append(CommitFootprint(sha, subject, len(sources), sum(p in HUBS for p in paths)))
    return result


def summarize(footprints: Sequence[CommitFootprint]) -> str:
    if not footprints:
        return "Özellik commit'i bulunamadı."
    sources = [f.sources for f in footprints]
    hub_touching = sum(f.hubs > 0 for f in footprints)
    lines = [
        f"Özellik commit'i: {len(footprints)}",
        f"Kaynak dosya medyanı: {statistics.median(sources):g} (hedef <= 5), en çok: {max(sources)}",
        f"Kayıt merkezine dokunan commit: {hub_touching} (%{100 * hub_touching / len(footprints):.0f})",
        f"Commit başına merkez dokunuşu: {sum(f.hubs for f in footprints) / len(footprints):.2f} (hedef <= 1)",
        "En geniş 5 commit:",
    ]
    widest = sorted(footprints, key=lambda f: f.sources, reverse=True)[:5]
    lines += [f"  {f.sha} {f.sources:>3} dosya, {f.hubs} merkez  {f.subject[:70]}" for f in widest]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--limit", type=int, default=200, help="incelenecek son commit sayısı")
    parser.add_argument("--range", dest="revision_range", help="git aralığı (ör. main..HEAD); verilirse --limit yok")
    args = parser.parse_args(argv)
    revision = [args.revision_range] if args.revision_range else [f"-{args.limit}"]
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")  # Windows konsolunda Türkçe karakter
    print(summarize(parse_log(_git_log(revision))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
