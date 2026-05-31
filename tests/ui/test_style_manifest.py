import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
THEME_MANAGER = ROOT / "src" / "ui" / "theme_manager.py"
STYLES_DIR = ROOT / "src" / "ui" / "styles"


def _style_manifest(theme_name="dark_theme") -> list[str]:
    from src.ui.theme_manager import ThemeManager
    return ThemeManager._get_style_manifest(theme_name)


def test_style_manifest_files_exist_and_are_utf8_without_bom():
    for entry in _style_manifest("dark_theme"):
        path = STYLES_DIR / entry
        assert path.exists(), f"Missing QSS manifest file: {path}"

        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"QSS file has UTF-8 BOM: {path}"


def test_qss_manifest_files_have_balanced_blocks():
    for entry in _style_manifest("dark_theme"):
        path = STYLES_DIR / entry
        balance = 0
        min_balance = 0
        for char in path.read_text(encoding="utf-8").replace("\ufeff", ""):
            if char == "{":
                balance += 1
            elif char == "}":
                balance -= 1
                min_balance = min(min_balance, balance)

        assert balance == 0 and min_balance == 0, f"Unbalanced QSS block braces: {path}"


def test_theme_qss_resolves_all_known_tokens():
    from src.ui.styles.tokens import DARK_THEME, LIGHT_THEME
    from src.ui.theme_manager import ThemeManager

    assert set(DARK_THEME) == set(LIGHT_THEME)

    for theme_name, tokens in (("dark_theme", DARK_THEME), ("light_theme", LIGHT_THEME)):
        qss = "\n".join(
            (STYLES_DIR / entry).read_text(encoding="utf-8")
            for entry in _style_manifest(theme_name)
        )
        qss = re.sub(
            r"@([A-Z0-9_]+)",
            lambda match: (
                "icons/generated.svg"
                if match.group(1).startswith("ICON_")
                else tokens.get(match.group(1), match.group(0))
            ),
            qss,
        )
        qss_without_comments = re.sub(r"/\*.*?\*/", "", qss, flags=re.DOTALL)
        unresolved = sorted(set(re.findall(r"@([A-Z0-9_]+)", qss_without_comments)))
        assert not unresolved, f"Unresolved QSS tokens in {theme_name}: {unresolved}"

    assert ThemeManager.validate_theme_tokens("dark") == []
    assert ThemeManager.validate_theme_tokens("light") == []


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", value), f"Expected 6-digit hex color, got {value!r}"
    return tuple(int(value[index : index + 2], 16) / 255 for index in (1, 3, 5))


def _linearize(channel: float) -> float:
    return channel / 12.92 if channel <= 0.03928 else ((channel + 0.055) / 1.055) ** 2.4


def _relative_luminance(value: str) -> float:
    red, green, blue = (_linearize(channel) for channel in _hex_to_rgb(value))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def _contrast_ratio(foreground: str, background: str) -> float:
    lighter, darker = sorted(
        (_relative_luminance(foreground), _relative_luminance(background)),
        reverse=True,
    )
    return (lighter + 0.05) / (darker + 0.05)


def test_component_token_contrast_pairs_are_readable():
    from src.ui.styles.tokens import DARK_THEME, LIGHT_THEME

    pairs = (
        ("BUTTON_PRIMARY_TEXT", "BUTTON_PRIMARY_BG"),
        ("BUTTON_SECONDARY_TEXT", "BUTTON_SECONDARY_BG"),
        ("TABLE_TEXT", "TABLE_BG"),
        ("TABLE_HEADER_TEXT", "TABLE_HEADER_BG"),
        ("FORM_TEXT", "FORM_BG"),
        ("FORM_LABEL_TEXT", "FORM_BG"),
        ("COLOR_TEXT_SECONDARY", "COLOR_CARD_SURFACE"),
        ("COLOR_TEXT_BRIGHT", "COLOR_CARD_SURFACE"),
    )

    for theme_name, tokens in (("dark", DARK_THEME), ("light", LIGHT_THEME)):
        for fg_token, bg_token in pairs:
            ratio = _contrast_ratio(tokens[fg_token], tokens[bg_token])
            assert ratio >= 4.5, f"{theme_name} {fg_token}/{bg_token} contrast too low: {ratio:.2f}"
