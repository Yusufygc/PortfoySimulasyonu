"""Measure Python code quality thresholds for the project."""

from __future__ import annotations

import argparse
import ast
import io
import json
import re
import subprocess
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
BASELINE_DATE = "2026-06-13"
DEFAULT_OUTPUT_DIR = ROOT / "docs" / "wiki"
DEFAULT_HEALTH_REPORT = ROOT / "PortfoySimulasyonu_saglik_raporu.html"

EXCLUDED_DIRS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    "htmlcov",
    "venv",
    ".venv",
    "env",
    ".icon_cache",
    "downloads",
}

THRESHOLDS = {
    "class_effective_lines": 300,
    "class_methods": 20,
    "function_effective_lines": 50,
    "function_effective_params": 5,
    "function_complexity": 10,
    "ui_page_file_effective_lines": 400,
}


@dataclass(frozen=True)
class TokenMetrics:
    physical_lines: int
    blank_lines: int
    comment_lines: int
    inline_comment_lines: int
    code_lines: int
    code_line_numbers: frozenset[int]


@dataclass(frozen=True)
class FileMeasureContext:
    relative: str
    layer: str
    tokens: TokenMetrics
    docs: set[int]
    effective_lines: set[int]


def rel_path(path: Path, root: Path = ROOT) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def layer_for(path: Path, root: Path = ROOT) -> str:
    relative = rel_path(path, root)
    first = relative.split("/", 1)[0]
    if first in {"src", "tests", "scripts"}:
        return first
    return "root"


def iter_python_files(root: Path = ROOT) -> list[Path]:
    candidates: list[Path] = []
    for base in (root / "src", root / "tests", root / "scripts"):
        if base.exists():
            candidates.extend(
                path
                for path in base.rglob("*.py")
                if not set(path.relative_to(root).parts) & EXCLUDED_DIRS
            )
    app = root / "app.py"
    if app.exists():
        candidates.append(app)
    return sorted(candidates, key=lambda item: rel_path(item, root))


def token_metrics(source: str) -> TokenMetrics:
    lines = source.splitlines()
    blank_numbers = {index for index, line in enumerate(lines, start=1) if not line.strip()}
    code_numbers: set[int] = set()
    comment_numbers: set[int] = set()

    stream = io.BytesIO(source.encode("utf-8")).readline
    for token in tokenize.tokenize(stream):
        token_type = token.type
        if token_type == tokenize.COMMENT:
            comment_numbers.add(token.start[0])
            continue
        if token_type in {
            tokenize.ENCODING,
            tokenize.NL,
            tokenize.NEWLINE,
            tokenize.INDENT,
            tokenize.DEDENT,
            tokenize.ENDMARKER,
        }:
            continue
        start_line, end_line = token.start[0], token.end[0]
        for line_no in range(start_line, end_line + 1):
            if line_no not in blank_numbers:
                code_numbers.add(line_no)

    comment_only = comment_numbers - code_numbers
    inline_comments = comment_numbers & code_numbers
    return TokenMetrics(
        physical_lines=len(lines),
        blank_lines=len(blank_numbers),
        comment_lines=len(comment_only),
        inline_comment_lines=len(inline_comments),
        code_lines=len(code_numbers),
        code_line_numbers=frozenset(code_numbers),
    )


def _docstring_range(node: ast.AST) -> set[int]:
    body = getattr(node, "body", None)
    if not body:
        return set()
    first = body[0]
    if not (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    ):
        return set()
    start = getattr(first, "lineno", None)
    end = getattr(first, "end_lineno", start)
    if start is None or end is None:
        return set()
    return set(range(start, end + 1))


def docstring_lines(tree: ast.AST) -> set[int]:
    lines = set(_docstring_range(tree))
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            lines.update(_docstring_range(node))
    return lines


class ComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.score = 1

    def visit_If(self, node: ast.If) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        self.score += 1
        self.generic_visit(node)

    def visit_BoolOp(self, node: ast.BoolOp) -> None:
        self.score += max(0, len(node.values) - 1)
        self.generic_visit(node)

    def visit_comprehension(self, node: ast.comprehension) -> None:
        self.score += 1 + len(node.ifs)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        self.score += len(node.cases)
        self.generic_visit(node)


def cyclomatic_complexity(node: ast.AST) -> int:
    visitor = ComplexityVisitor()
    visitor.visit(node)
    return visitor.score


def node_line_set(node: ast.AST) -> set[int]:
    start = getattr(node, "lineno", None)
    end = getattr(node, "end_lineno", start)
    if start is None or end is None:
        return set()
    return set(range(start, end + 1))


def function_param_counts(node: ast.FunctionDef | ast.AsyncFunctionDef, is_method: bool) -> dict[str, int]:
    args = node.args
    positional = list(args.posonlyargs) + list(args.args)
    raw = len(positional) + len(args.kwonlyargs)
    raw += 1 if args.vararg else 0
    raw += 1 if args.kwarg else 0
    effective = raw
    if is_method and positional and positional[0].arg in {"self", "cls"}:
        effective -= 1
    return {"raw_param_count": raw, "effective_param_count": effective}


def threshold_status(violations: list[str]) -> str:
    return "violation" if violations else "ok"


def class_violations(record: dict[str, object]) -> list[str]:
    violations: list[str] = []
    if int(record["effective_code_lines"]) > THRESHOLDS["class_effective_lines"]:
        violations.append("class_effective_lines")
    if int(record["method_count"]) > THRESHOLDS["class_methods"]:
        violations.append("class_methods")
    return violations


def function_violations(record: dict[str, object]) -> list[str]:
    violations: list[str] = []
    if int(record["effective_code_lines"]) > THRESHOLDS["function_effective_lines"]:
        violations.append("function_effective_lines")
    if int(record["effective_param_count"]) > THRESHOLDS["function_effective_params"]:
        violations.append("function_effective_params")
    if int(record["cyclomatic_complexity"]) > THRESHOLDS["function_complexity"]:
        violations.append("function_complexity")
    return violations


def file_violations(record: dict[str, object]) -> list[str]:
    path = str(record["path"])
    violations: list[str] = []
    if (
        path.startswith("src/ui/pages/")
        and path.endswith("_page.py")
        and int(record["effective_code_lines"]) > THRESHOLDS["ui_page_file_effective_lines"]
    ):
        violations.append("ui_page_file_effective_lines")
    return violations


def parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    parents: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parents[child] = parent
    return parents


def build_class_records(
    class_nodes: list[ast.ClassDef],
    context: FileMeasureContext,
) -> list[dict[str, object]]:
    records = []
    for node in class_nodes:
        block_lines = node_line_set(node)
        methods = [
            child
            for child in node.body
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        record: dict[str, object] = {
            "path": context.relative,
            "layer": context.layer,
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "code_lines": len(context.tokens.code_line_numbers & block_lines),
            "effective_code_lines": len(context.effective_lines & block_lines),
            "docstring_lines": len(context.docs & block_lines),
            "method_count": len(methods),
            "function_count": len(methods),
        }
        violations = class_violations(record)
        record["violations"] = violations
        record["threshold_status"] = threshold_status(violations)
        records.append(record)
    return sorted(records, key=lambda item: (item["path"], item["lineno"], item["name"]))


def build_function_records(
    function_nodes: list[ast.FunctionDef | ast.AsyncFunctionDef],
    parents: dict[ast.AST, ast.AST],
    context: FileMeasureContext,
) -> list[dict[str, object]]:
    records = []
    for node in function_nodes:
        block_lines = node_line_set(node)
        is_method = isinstance(parents.get(node), ast.ClassDef)
        record = {
            "path": context.relative,
            "layer": context.layer,
            "name": node.name,
            "lineno": node.lineno,
            "end_lineno": getattr(node, "end_lineno", node.lineno),
            "code_lines": len(context.tokens.code_line_numbers & block_lines),
            "effective_code_lines": len(context.effective_lines & block_lines),
            "docstring_lines": len(context.docs & block_lines),
            "is_method": is_method,
            "cyclomatic_complexity": cyclomatic_complexity(node),
            **function_param_counts(node, is_method),
        }
        violations = function_violations(record)
        record["violations"] = violations
        record["threshold_status"] = threshold_status(violations)
        records.append(record)
    return sorted(records, key=lambda item: (item["path"], item["lineno"], item["name"]))


def build_file_record(
    context: FileMeasureContext,
    class_records: list[dict[str, object]],
    function_records: list[dict[str, object]],
) -> dict[str, object]:
    record: dict[str, object] = {
        "path": context.relative,
        "layer": context.layer,
        "physical_lines": context.tokens.physical_lines,
        "code_lines": context.tokens.code_lines,
        "effective_code_lines": len(context.effective_lines),
        "comment_lines": context.tokens.comment_lines,
        "inline_comment_lines": context.tokens.inline_comment_lines,
        "blank_lines": context.tokens.blank_lines,
        "docstring_lines": len(context.docs),
        "class_count": len(class_records),
        "method_count": sum(1 for item in function_records if item["is_method"]),
        "function_count": sum(1 for item in function_records if not item["is_method"]),
        "max_function_lines": max(
            (int(item["effective_code_lines"]) for item in function_records),
            default=0,
        ),
    }
    violations = file_violations(record)
    record["violations"] = violations
    record["threshold_status"] = threshold_status(violations)
    return record


def measure_file(path: Path, root: Path = ROOT) -> dict[str, object]:
    source = path.read_text(encoding="utf-8")
    tokens = token_metrics(source)
    tree = ast.parse(source, filename=str(path))
    docs = docstring_lines(tree)
    effective_lines = tokens.code_line_numbers - docs
    relative = rel_path(path, root)
    layer = layer_for(path, root)
    context = FileMeasureContext(relative, layer, tokens, docs, effective_lines)

    class_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
    function_nodes = [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    class_records = build_class_records(class_nodes, context)
    function_records = build_function_records(function_nodes, parent_map(tree), context)
    file_record = build_file_record(context, class_records, function_records)

    return {
        "file": file_record,
        "classes": class_records,
        "functions": function_records,
    }


def git_commit(root: Path = ROOT) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown"
    return result.stdout.strip() or "unknown"


def normalized_health_matches(text: str) -> list[str]:
    matches = re.findall(r"[\w./\\-]+\.py", text)
    return sorted({
        match.replace("\\", "/").lstrip("./")
        for match in matches
        if not match.startswith(("site-packages", "Lib/"))
    })


def measured_paths_by_name(root: Path) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for measured_path in iter_python_files(root):
        grouped.setdefault(measured_path.name, []).append(rel_path(measured_path, root))
    return grouped


def repo_candidates_from_health_item(
    item: str,
    by_name: dict[str, list[str]],
) -> set[str]:
    candidates = set()
    if item.startswith(("src/", "tests/", "scripts/")) or item == "app.py":
        candidates.add(item)
    for prefix in ("src/", "tests/", "scripts/"):
        marker = f"/{prefix}"
        if marker in item:
            candidates.add(prefix + item.split(marker, 1)[1])
    if item.endswith("/app.py"):
        candidates.add("app.py")
    if "/" not in item:
        candidates.update(by_name.get(item, []))
    return candidates


def health_report_paths(path: Path = DEFAULT_HEALTH_REPORT, root: Path = ROOT) -> list[str]:
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    measured_by_name = measured_paths_by_name(root)
    repo_paths = set()
    for item in normalized_health_matches(text):
        repo_paths.update(repo_candidates_from_health_item(item, measured_by_name))
    return sorted(path for path in repo_paths if (root / path).exists())


def flatten_measured_records(measured: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    return {
        "files": [item["file"] for item in measured],
        "classes": [record for item in measured for record in item["classes"]],
        "functions": [record for item in measured for record in item["functions"]],
    }


def violating_records(records: dict[str, list[dict[str, object]]]) -> dict[str, list[dict[str, object]]]:
    return {
        key: [record for record in value if record["threshold_status"] != "ok"]
        for key, value in records.items()
    }


def layer_summary(files: list[dict[str, object]]) -> dict[str, dict[str, int]]:
    summary = {}
    for layer in ("src", "tests", "scripts", "root"):
        layer_files = [record for record in files if record["layer"] == layer]
        summary[layer] = {
            "file_count": len(layer_files),
            "effective_code_lines": sum(int(record["effective_code_lines"]) for record in layer_files),
            "violation_count": sum(1 for record in layer_files if record["threshold_status"] != "ok"),
        }
    return summary


def health_crosswalk(
    files: list[dict[str, object]],
    root: Path,
    health_report: Path,
) -> dict[str, object]:
    health_paths = health_report_paths(health_report, root)
    measured_paths = {str(record["path"]) for record in files}
    overlap = sorted(measured_paths & set(health_paths))
    return {
        "referenced_paths": health_paths,
        "matched_measured_paths": overlap,
        "unmatched_health_paths": sorted(set(health_paths) - measured_paths),
    }


def report_summary(
    records: dict[str, list[dict[str, object]]],
    violations: dict[str, list[dict[str, object]]],
    crosswalk: dict[str, object],
) -> dict[str, object]:
    files = records["files"]
    return {
        "file_count": len(files),
        "class_count": len(records["classes"]),
        "function_count": len(records["functions"]),
        "effective_code_lines": sum(int(record["effective_code_lines"]) for record in files),
        "violating_files": len(violations["files"]),
        "violating_classes": len(violations["classes"]),
        "violating_functions": len(violations["functions"]),
        "by_layer": layer_summary(files),
        "health_report_referenced_files": len(crosswalk["referenced_paths"]),
        "health_report_overlap": len(crosswalk["matched_measured_paths"]),
    }


def build_report(root: Path = ROOT, health_report: Path = DEFAULT_HEALTH_REPORT) -> dict[str, object]:
    measured = [measure_file(path, root) for path in iter_python_files(root)]
    records = flatten_measured_records(measured)
    violations = violating_records(records)
    crosswalk = health_crosswalk(records["files"], root, health_report)

    return {
        "metadata": {
            "baseline_date": BASELINE_DATE,
            "generated_at": BASELINE_DATE,
            "git_commit": git_commit(root),
            "root": str(root),
            "health_report_path": rel_path(health_report, root) if health_report.exists() else None,
        },
        "thresholds": THRESHOLDS,
        "exclusions": sorted(EXCLUDED_DIRS),
        "summary": report_summary(records, violations, crosswalk),
        "health_report_crosswalk": crosswalk,
        "files": records["files"],
        "classes": records["classes"],
        "functions": records["functions"],
        "violations": violations,
    }


def top_records(records: Iterable[dict[str, object]], key: str, limit: int = 15) -> list[dict[str, object]]:
    return sorted(records, key=lambda item: (-int(item[key]), str(item.get("path", "")), str(item.get("name", ""))))[:limit]


def markdown_header(report: dict[str, object]) -> list[str]:
    metadata = report["metadata"]
    summary = report["summary"]
    return [
        "# Code Quality Baseline - 2026-06-13",
        "",
        "> Ana sayfa: [index.md](index.md) | Guardrail: [code_quality_guardrails.md](code_quality_guardrails.md)",
        "",
        "Bu rapor `scripts/measure_code_quality.py` ile uretilen tekrarlanabilir baseline'dir.",
        "`PortfoySimulasyonu_saglik_raporu.html` referans girdi olarak kullanilir; refactor karari bu metriklerle dogrulanir.",
        "",
        "## Ozet",
        "",
        f"- Git commit: `{metadata['git_commit']}`",
        f"- Dosya: {summary['file_count']}",
        f"- Sinif: {summary['class_count']}",
        f"- Fonksiyon/metot: {summary['function_count']}",
        f"- Effective code lines: {summary['effective_code_lines']}",
        f"- Ihlalli sinif: {summary['violating_classes']}",
        f"- Ihlalli fonksiyon/metot: {summary['violating_functions']}",
        f"- Saglik raporu eslesen dosya: {summary['health_report_overlap']}/{summary['health_report_referenced_files']}",
        "",
    ]


def markdown_layer_summary(report: dict[str, object]) -> list[str]:
    lines = [
        "## Katman Ozeti",
        "",
        "| Katman | Dosya | Effective satir | Dosya ihlali |",
        "|---|---:|---:|---:|",
    ]
    for layer, item in report["summary"]["by_layer"].items():
        lines.append(
            f"| {layer} | {item['file_count']} | {item['effective_code_lines']} | {item['violation_count']} |"
        )
    lines.append("")
    return lines


def markdown_largest_files(report: dict[str, object]) -> list[str]:
    lines = [
        "## En Buyuk Dosyalar",
        "",
        "| Dosya | Katman | Effective satir | Sinif | Metot | Fonksiyon | Durum |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for record in top_records(report["files"], "effective_code_lines"):
        lines.append(
            "| {path} | {layer} | {effective_code_lines} | {class_count} | {method_count} | "
            "{function_count} | {threshold_status} |".format(**record)
        )
    lines.append("")
    return lines


def markdown_class_violations(report: dict[str, object]) -> list[str]:
    lines = [
        "## Sinif Ihlalleri",
        "",
        "| Dosya | Sinif | Effective satir | Metot | Ihlal |",
        "|---|---|---:|---:|---|",
    ]
    for record in top_records(report["violations"]["classes"], "effective_code_lines", limit=30):
        lines.append(
            "| {path} | {name} | {effective_code_lines} | {method_count} | {violations} |".format(
                **{**record, "violations": ", ".join(record["violations"])}
            )
        )
    lines.append("")
    return lines


def markdown_function_violations(report: dict[str, object]) -> list[str]:
    lines = [
        "## Fonksiyon/Metot Ihlalleri",
        "",
        "| Dosya | Fonksiyon | Effective satir | Parametre | Complexity | Ihlal |",
        "|---|---|---:|---:|---:|---|",
    ]
    for record in top_records(report["violations"]["functions"], "effective_code_lines", limit=30):
        lines.append(
            "| {path} | {name} | {effective_code_lines} | {effective_param_count} | "
            "{cyclomatic_complexity} | {violations} |".format(
                **{**record, "violations": ", ".join(record["violations"])}
            )
        )
    lines.append("")
    return lines


def markdown_crosswalk_and_priority(report: dict[str, object]) -> list[str]:
    summary = report["summary"]
    return [
        "## Saglik Raporu Crosswalk",
        "",
        "Saglik HTML'i tek kaynak degildir. Bu bolum yalniz HTML'de adi gecen dosyalarin yeni metriklerle eslesip eslesmedigini gosterir.",
        "",
        "| Metrik | Deger |",
        "|---|---:|",
        f"| HTML'de bulunan repo dosyasi | {summary['health_report_referenced_files']} |",
        f"| Olcumde eslesen dosya | {summary['health_report_overlap']} |",
        "",
        "## Refactor Onceligi",
        "",
        "1. Application servis facade'lari: fiyat sagligi, model portfoy trade, kurumsal aksiyon, risk profili ve optimizasyon.",
        "2. UI page/widget ayrimi: buyuk `_init_ui`, tablo doldurma, chart cizimi ve worker orchestration bloklari.",
        "3. Infrastructure ve dependency temizligi: yalniz dogrulanmis kullanilmayan paketler kaldirilir.",
        "",
    ]


def render_markdown(report: dict[str, object]) -> str:
    lines = []
    for section in (
        markdown_header,
        markdown_layer_summary,
        markdown_largest_files,
        markdown_class_violations,
        markdown_function_violations,
        markdown_crosswalk_and_priority,
    ):
        lines.extend(section(report))
    return "\n".join(lines)


def write_outputs(report: dict[str, object], output_dir: Path = DEFAULT_OUTPUT_DIR) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"code_quality_baseline_{BASELINE_DATE}.json"
    md_path = output_dir / f"code_quality_baseline_{BASELINE_DATE}.md"
    json_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(render_markdown(report), encoding="utf-8")
    return md_path, json_path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--health-report", type=Path, default=DEFAULT_HEALTH_REPORT)
    parser.add_argument("--fail-on-threshold", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = build_report(args.root.resolve(), args.health_report.resolve())
    md_path, json_path = write_outputs(report, args.output_dir.resolve())
    print(f"Wrote {md_path}")
    print(f"Wrote {json_path}")
    if args.fail_on_threshold and (
        report["violations"]["files"]
        or report["violations"]["classes"]
        or report["violations"]["functions"]
    ):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
