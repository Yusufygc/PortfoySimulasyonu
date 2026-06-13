"""Onay diyalog yardımcısı.

PySide6 + global QSS kullanıldığında `QMessageBox.question(..., defaultButton=...)`
çağrısı `autoDefault` özelliğini yutar; sonuçta Enter tuşu hiçbir butonu
tetiklemez. Bu modül `QMessageBox`'ı elle kurar, varsayılan butonun
`setDefault(True)`, `setAutoDefault(True)` ve `setFocus()` çağrılarını
açıkça yapar; böylece Enter her zaman varsayılan seçeneği işler.
"""

from __future__ import annotations

from src.qt_compat.qtcore import Qt
from src.qt_compat.qtwidgets import QMessageBox, QWidget

from src.ui.shared.locale_tr import L10N


def ask_confirm(
    parent: QWidget | None,
    title: str,
    text: str,
    *,
    default_yes: bool = False,
    icon: QMessageBox.Icon = QMessageBox.Question,
) -> bool:
    """Evet/Hayır onay diyaloğu göster, Enter varsayılan butonu tetikler.

    Args:
        parent: Üst pencere.
        title: Pencere başlığı.
        text: Onay mesajı.
        default_yes: True ise Evet varsayılan (Enter = Evet). False (varsayılan)
            ise yıkıcı işlemler için Hayır varsayılan (Enter = İptal).
        icon: Diyalog ikonu (varsayılan Question).

    Returns:
        Kullanıcı Evet'i tıkladıysa True, aksi halde False.
    """
    box = QMessageBox(parent)
    box.setWindowTitle(title)
    box.setText(text)
    box.setIcon(icon)

    yes_btn = box.addButton(L10N.EVET, QMessageBox.YesRole)
    no_btn = box.addButton(L10N.HAYIR, QMessageBox.NoRole)

    default_btn = yes_btn if default_yes else no_btn
    default_btn.setDefault(True)
    default_btn.setAutoDefault(True)
    default_btn.setFocus(Qt.OtherFocusReason)

    # Diğer butonun autoDefault'u kapansın ki Enter yalnız varsayılana gitsin.
    other_btn = no_btn if default_yes else yes_btn
    other_btn.setDefault(False)
    other_btn.setAutoDefault(False)

    box.exec()
    return box.clickedButton() is yes_btn
