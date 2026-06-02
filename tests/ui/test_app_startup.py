import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        parts = [func.attr]
        value = func.value
        while isinstance(value, ast.Attribute):
            parts.append(value.attr)
            value = value.value
        if isinstance(value, ast.Name):
            parts.append(value.id)
        return ".".join(reversed(parts))
    return ""


def _function(tree: ast.Module, name: str) -> ast.FunctionDef:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    raise AssertionError(f"{name} function not found")


def test_app_sets_qt_webengine_attribute_before_qapplication():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    main_func = _function(tree, "main")

    calls = sorted(
        (node.lineno, _call_name(node))
        for node in ast.walk(main_func)
        if isinstance(node, ast.Call)
    )
    configure_line = next(
        line for line, name in calls if name == "configure_qt_application_attributes"
    )
    qapplication_line = next(line for line, name in calls if name == "QApplication")

    assert configure_line < qapplication_line


def test_qt_attribute_helper_enables_shared_opengl_contexts():
    tree = ast.parse((ROOT / "app.py").read_text(encoding="utf-8"))
    helper = _function(tree, "configure_qt_application_attributes")

    calls = [
        node
        for node in ast.walk(helper)
        if isinstance(node, ast.Call)
        and _call_name(node) == "QCoreApplication.setAttribute"
    ]

    assert calls, "Qt application attribute setup call is missing"
    assert any(
        isinstance(call.args[0], ast.Attribute)
        and call.args[0].attr == "AA_ShareOpenGLContexts"
        for call in calls
        if call.args
    )
