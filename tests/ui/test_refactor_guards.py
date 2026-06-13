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
            if isinstance(node, ast.ImportFrom) and node.module in {"src.qt_compat.qtcore", "PySide6.QtCore"}:
                if any(alias.name == "QThread" for alias in node.names):
                    offenders.append(f"{_src_rel(path)} imports QThread")
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    if isinstance(base, ast.Name) and base.id == "QThread":
                        offenders.append(f"{_src_rel(path)}::{node.name}")
                    if isinstance(base, ast.Attribute) and base.attr == "QThread":
                        offenders.append(f"{_src_rel(path)}::{node.name}")

    assert not offenders, f"Unexpected custom QThread usage in UI: {offenders}"


def test_ui_imports_qt_through_compat_layer_only():
    forbidden_roots = {
        "Py" + "Qt5",
        "Py" + "Qt6",
        "Py" + "Side6",
        "Py" + "QtWebEngine",
        "s" + "ip",
    }
    offenders = []

    for path in (ROOT / "src" / "ui").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in forbidden_roots:
                        offenders.append(f"{_src_rel(path)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in forbidden_roots:
                    offenders.append(f"{_src_rel(path)} imports from {node.module}")

    assert not offenders, f"UI must import Qt through src.qt_compat only: {offenders}"


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
        ("src/ui/pages/ai_page/right_panel/chatbot_panel.py", "ChatbotPanel"),
        # P2 (2026-06-06): crosshair + ₺ axis + TR ay format birlikte; ileride
        # CrosshairOverlay/PyqtgraphChart base sınıfına bölme planlandı.
        ("src/ui/pages/stock_detail/stock_chart_widget.py", "StockChartWidget"),
        ("src/ui/shared/locale_tr.py", "L10N"),
        ("src/ui/pages/ai_page/left_panel/xai_card.py", "XAICard"),
        # P2 (2026-06-13): sağlık raporu temelli geniş refactor öncesi baseline.
        # Bu sınıflar ilgili fazlarda panel/helper ayrımıyla küçültülecek.
        ("src/ui/pages/planning_page.py", "PlanningPage"),
        ("src/ui/pages/comparison/utils/comparison_data_manager.py", "ComparisonDataManager"),
        ("src/ui/pages/settings/price_data_panel.py", "PriceDataPanel"),
        ("src/ui/widgets/shared/controls/currency_spin_box.py", "CurrencySpinBox"),
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


def test_ui_does_not_import_backend_clients_or_sdks():
    """UI katmanı dış servis/SDK'leri doğrudan import etmez.

    HTTP istemci (requests), Gemini SDK (google.genai) ve piyasa verisi
    (yfinance) yalnızca infrastructure katmanında bulunur; UI bunları DI ile
    enjekte edilen servis/sağlayıcılar üzerinden kullanır.
    """
    forbidden_roots = {"requests", "yfinance", "google"}
    offenders = []

    for path in (ROOT / "src" / "ui").rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in forbidden_roots:
                        offenders.append(f"{_src_rel(path)} imports {alias.name}")
            elif isinstance(node, ast.ImportFrom) and node.module:
                root = node.module.split(".")[0]
                if root in forbidden_roots:
                    offenders.append(f"{_src_rel(path)} imports from {node.module}")

    assert not offenders, f"UI must not import backend clients/SDKs directly: {offenders}"


def test_ai_page_core_backend_module_is_removed():
    """ai_page/core/ backend sızıntısı kalıcı olarak kaldırıldı; geri gelmemeli."""
    legacy_dir = ROOT / "src" / "ui" / "pages" / "ai_page" / "core"
    assert not legacy_dir.exists(), (
        "src/ui/pages/ai_page/core kaldırıldı; backend kodu domain/application/"
        "infrastructure katmanlarında olmalı."
    )


def test_ui_user_facing_text_uses_l10n_not_hardcoded_literals():
    """Kullanıcıya dönük metinler koda gömülmez; L10N üzerinden gelir.

    AST ile kullanıcıya dönük setter/constructor çağrılarındaki düz string
    literal argümanları taranır; Türkçe harf içeren literal bulunmamalı.
    f-string (JoinedStr) ve L10N.* erişimleri doğal olarak hariçtir.
    """
    turkish_chars = set("çğıöşüÇĞİÖŞÜ")
    ui_text_callables = {
        "QLabel", "QPushButton", "AnimatedButton", "QRadioButton", "QCheckBox",
        "QGroupBox", "QToolButton", "setText", "setPlaceholderText",
        "setWindowTitle", "setToolTip", "setTitle", "addTab", "setTabText",
        "setStatusTip", "setWhatsThis",
    }
    # Kaçınılmaz/bilinçli istisnalar (dosya yolu, gerekçe ile)
    allowed = set()

    def call_name(func) -> str:
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            return func.attr
        return ""

    offenders = []
    for path in (ROOT / "src" / "ui").rglob("*.py"):
        rel = _src_rel(path)
        if rel in allowed:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if call_name(node.func) not in ui_text_callables:
                continue
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                    if any(ch in turkish_chars for ch in arg.value):
                        offenders.append(f"{rel}:{node.lineno}: {arg.value!r}")

    assert not offenders, (
        "Kullanıcıya dönük metinler L10N'e taşınmalı (hardcoded literal):\n"
        + "\n".join(offenders)
    )


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
