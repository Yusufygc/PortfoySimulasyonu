import pytest

pytest.importorskip("PySide6")

from src.qt_compat.qtwidgets import QLabel, QToolButton, QWidget

from src.ui.theme_manager import ThemeManager
from src.ui.widgets.shared.controls.icon_label import IconLabel
from src.ui.widgets.shared.feedback.toast import Toast, _ToastCloseButton, _ToastWidget, _strip_emoji


TOAST_CASES = (
    ("success", Toast.success, "shield-check"),
    ("error", Toast.error, "alert-triangle"),
    ("warning", Toast.warning, "alert-triangle"),
    ("info", Toast.info, "info"),
)

CHECK = "\u2705"
INFO = "\u2139\ufe0f"
WARNING = "\u26a0\ufe0f"
PARTY = "\U0001f389"
ROCKET = "\U0001f680"
TURKISH_TEXT = "\u0130\u015flem tamamland\u0131"
LIRA = "\u20ba"
BULLET = "\u2022"


def _parent(qapp) -> QWidget:
    parent = QWidget()
    parent.resize(900, 600)
    parent.show()
    qapp.processEvents()
    return parent


def _latest_toast(parent: QWidget):
    return _ToastWidget._registry[(id(parent), "top")][-1]


def _cleanup(widget, parent: QWidget, qapp) -> None:
    widget._cleanup()
    parent.close()
    qapp.processEvents()


def test_strip_emoji_preserves_turkish_text_currency_and_punctuation():
    message = f"{CHECK} {TURKISH_TEXT} {PARTY} {LIRA} 1.000,50 {BULLET} portfoy guncellendi."

    assert _strip_emoji(message) == f"{TURKISH_TEXT} {LIRA} 1.000,50 {BULLET} portfoy guncellendi."
    assert _strip_emoji(f"{INFO} Bilgi mesaji") == "Bilgi mesaji"
    assert _strip_emoji(f"{WARNING} Dikkat: kontrol edin.") == "Dikkat: kontrol edin."


@pytest.mark.parametrize(("kind", "show_toast", "icon_name"), TOAST_CASES)
def test_toast_uses_svg_status_icon_without_emoji_text(kind, show_toast, icon_name, qapp):
    parent = _parent(qapp)

    show_toast(parent, f"{kind} bildirimi {CHECK} {INFO} {ROCKET}", duration_ms=60000)
    toast = _latest_toast(parent)

    icon_labels = toast.findChildren(IconLabel)
    label_texts = [
        label.text()
        for label in toast.findChildren(QLabel)
        if not isinstance(label, IconLabel)
    ]
    rendered_text = " ".join(label_texts)

    assert icon_labels
    assert icon_labels[0]._icon_name == icon_name
    assert CHECK not in rendered_text
    assert "\u2139" not in rendered_text
    assert ROCKET not in rendered_text
    assert f"{kind} bildirimi" in rendered_text

    _cleanup(toast, parent, qapp)


@pytest.mark.parametrize(("theme_id", "show_toast"), (("dark", Toast.warning), ("light", Toast.error)))
def test_toast_close_button_uses_visible_svg_icon(theme_id, show_toast, qapp):
    ThemeManager.apply_theme(qapp, "dark")
    ThemeManager.switch_theme(theme_id)
    parent = _parent(qapp)

    show_toast(parent, "Kapatma ikonu kontrolu", duration_ms=60000)
    toast = _latest_toast(parent)
    close_button = toast.findChild(_ToastCloseButton)

    assert close_button is not None
    assert close_button.isVisible() is True
    assert close_button.size().width() == 26
    assert close_button.size().height() == 26
    assert close_button.icon().isNull() is False
    assert close_button.iconSize().width() == 16
    assert close_button.text() == ""

    _cleanup(toast, parent, qapp)


def test_toast_close_icon_refreshes_on_theme_change(qapp):
    ThemeManager.apply_theme(qapp, "dark")
    ThemeManager.switch_theme("dark")
    parent = _parent(qapp)

    Toast.info(parent, "Tema degisimi", duration_ms=60000)
    toast = _latest_toast(parent)
    close_button = toast.findChild(_ToastCloseButton)
    dark_pixmap_key = close_button.icon().pixmap(16, 16).cacheKey()

    ThemeManager.switch_theme("light")
    qapp.processEvents()
    light_pixmap_key = close_button.icon().pixmap(16, 16).cacheKey()

    assert close_button.icon().isNull() is False
    assert dark_pixmap_key != light_pixmap_key

    _cleanup(toast, parent, qapp)


def test_toast_close_button_click_removes_toast_from_registry(qapp):
    parent = _parent(qapp)

    Toast.info(parent, "Kapat", duration_ms=60000)
    toast = _latest_toast(parent)
    close_button = toast.findChild(QToolButton)

    close_button.click()
    toast._anim_out.setCurrentTime(300)
    qapp.processEvents()

    assert (id(parent), "top") not in _ToastWidget._registry
    parent.close()
    qapp.processEvents()


def test_toast_cleanup_after_parent_close_does_not_raise(qapp):
    parent = _parent(qapp)

    Toast.info(parent, "Parent kapanirken temizle", duration_ms=60000)
    toast = _latest_toast(parent)
    parent.close()
    qapp.processEvents()

    toast._cleanup()
    qapp.processEvents()

    assert (id(parent), "top") not in _ToastWidget._registry


def test_toast_reposition_ignores_deleted_anchor_runtime_error(qapp, monkeypatch):
    parent = _parent(qapp)

    Toast.info(parent, "Anchor hatasi", duration_ms=60000)
    toast = _latest_toast(parent)
    monkeypatch.setattr(
        _ToastWidget,
        "_anchor_for",
        staticmethod(lambda _parent: (_ for _ in ()).throw(RuntimeError("deleted"))),
    )

    _ToastWidget._reposition_for_parent(parent)

    toast._cleanup()
    parent.close()
    qapp.processEvents()
