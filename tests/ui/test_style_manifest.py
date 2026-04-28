import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
THEME_MANAGER = ROOT / "src" / "ui" / "theme_manager.py"
STYLES_DIR = ROOT / "src" / "ui" / "styles"


def _style_manifest() -> tuple[str, ...]:
    tree = ast.parse(THEME_MANAGER.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == "STYLE_MANIFEST"
        ):
            return ast.literal_eval(node.value)
    raise AssertionError("STYLE_MANIFEST not found")


def test_style_manifest_files_exist_and_are_utf8_without_bom():
    for entry in _style_manifest():
        path = STYLES_DIR / entry.format(theme_name="dark_theme")
        assert path.exists(), f"Missing QSS manifest file: {path}"

        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"QSS file has UTF-8 BOM: {path}"


def test_qss_manifest_files_have_balanced_blocks():
    for entry in _style_manifest():
        path = STYLES_DIR / entry.format(theme_name="dark_theme")
        balance = 0
        min_balance = 0
        for char in path.read_text(encoding="utf-8").replace("\ufeff", ""):
            if char == "{":
                balance += 1
            elif char == "}":
                balance -= 1
                min_balance = min(min_balance, balance)

        assert balance == 0 and min_balance == 0, f"Unbalanced QSS block braces: {path}"
