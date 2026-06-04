import pytest

pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QLabel, QWidget

from src.ui.widgets.shared.controls.icon_label import IconLabel
from src.ui.widgets.shared.feedback.toast import Toast, _ToastWidget, _strip_emoji


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
