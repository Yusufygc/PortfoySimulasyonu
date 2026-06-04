import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _src_rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def test_ui_has_no_custom_qthread_classes_or_imports():
    offenders = []

    for path in (ROOT / "src" / "ui").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module == "PyQt5.QtCore":
                if any(alias.name == "QThread" for alias in node.names):
                    offenders.append(f"{_src_rel(path)} imports QThread")
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "QThread":
                        offenders.append(f"{_src_rel(path)}::{node.name}")
                    if isinstance(base, ast.Attribute) and base.attr == "QThread":
                        offenders.append(f"{_src_rel(path)}::{node.name}")

    assert not offenders, f"Unexpected custom QThread usage in UI: {offenders}"


def test_ui_price_events_are_published_through_helper_only():
    allowed = {Path("src/ui/shared/price_event_publisher.py")}
    offenders = []

    for path in (ROOT / "src" / "ui").rglob("*.py"):
        rel_path = path.relative_to(ROOT)
        if rel_path in allowed:
            continue
        if "prices_updated.emit" in path.read_text(encoding="utf-8"):
            offenders.append(rel_path.as_posix())

    assert not offenders, f"UI must publish prices_updated through helper only: {offenders}"


def test_ui_large_class_threshold_has_only_documented_phase_5_exceptions():
    allowed = {
        ("src/ui/pages/risk_profile_page.py", "RiskProfilePage"),
        ("src/ui/pages/watchlist_page.py", "WatchlistPage"),
        ("src/ui/widgets/dashboard/dialogs/new_stock_trade_dialog.py", "NewStockTradeDialog"),
        ("src/ui/pages/optimization_page.py", "OptimizationPage"),
        ("src/ui/pages/stock_detail/stock_detail_page.py", "StockDetailPage"),
        ("src/ui/pages/comparison/utils/chart_renderer.py", "ChartRenderer"),
    }
    offenders = []

    for path in (ROOT / "src" / "ui").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            key = (_src_rel(path), node.name)
            end_lineno = getattr(node, "end_lineno", node.lineno)
            class_lines = end_lineno - node.lineno + 1
            methods = sum(
                isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef))
                for child in node.body
            )
            if key in allowed:
                continue
            if class_lines > 300 or methods > 20:
                offenders.append(
                    f"{key[0]}::{key[1]} lines={class_lines} methods={methods}"
                )

    assert not offenders, f"UI class threshold exceeded without whitelist: {offenders}"


def test_automated_tests_do_not_call_live_network_helpers_directly():
    allowed_manual = {
        Path("tests/infrastructure/market_data/test_benchmark_fetch_manual.py"),
    }
    live_network_patterns = (
        re.compile(r"\brequests\.(get|post|put|delete)\("),
        re.compile(r"\burllib\.request\.urlopen\("),
    )
    offenders = []

    for path in (ROOT / "tests").rglob("test_*.py"):
        rel_path = path.relative_to(ROOT)
        if rel_path in allowed_manual:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in live_network_patterns:
            if pattern.search(text):
                offenders.append(rel_path.as_posix())
                break

    assert not offenders, f"Automated tests must fake live network calls: {offenders}"
