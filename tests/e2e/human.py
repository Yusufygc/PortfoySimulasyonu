"""Gerçek kullanıcı gibi davranan sürücü: Main.qml penceresinde fare tıklaması ve klavye olayı gönderir.

Denetleyici slotlarını doğrudan çağırmaz; ekranda görünen metni bulur, merkezine tıklar, alanlara klavye ile yazar.
Böylece QML bağlama hataları, örtülü düğmeler, görünmeyen öğeler ve yanlış tıklama alanları da yakalanır.

Ekran okuma `human_screen.py`, fare/klavye `human_input.py` içindedir; bu sınıf zaman, bekleme ve gezinmeyi ekler.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QCoreApplication

from tests.e2e.human_input import InputMixin
from tests.e2e.human_screen import ScreenReaderMixin


class Human(ScreenReaderMixin, InputMixin):
    """Pencere üzerinde görünür öğeleri metne göre bulup tıklayan, yazan ve ekran görüntüsü alan test kullanıcısı."""

    def __init__(self, engine, controllers, container, shots_dir: Optional[Path] = None) -> None:
        self.engine = engine
        self.c = controllers
        self.container = container
        self.window = engine.rootObjects()[0]
        self.shots_dir = shots_dir

    # --- zaman ---------------------------------------------------------------------------------------------------
    def pump(self, rounds: int = 6, delay: float = 0.0) -> None:
        for _ in range(rounds):
            QCoreApplication.processEvents()
            if delay:
                time.sleep(delay)

    def wait_until(self, condition: Callable[[], bool], timeout: float = 8.0) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.pump(2, 0.01)
            if condition():
                return True
        return bool(condition())

    def settle(self, timeout: float = 6.0) -> None:
        """Arka plan işleri bitene kadar bekler (Portföyüm varlık işlemleri ve fiyat yenilemesi)."""
        assets = self.c.get("assetsController")
        self.wait_until(lambda: not getattr(assets, "busy", False), timeout)
        self.pump(8)


    def wait_sees(self, needle: str, timeout: float = 8.0, exact: bool = False) -> bool:
        return self.wait_until(lambda: self.sees(needle, exact), timeout)

    def wait_gone(self, needle: str, timeout: float = 8.0, exact: bool = False) -> bool:
        return self.wait_until(lambda: not self.sees(needle, exact), timeout)


    # --- görüntü -------------------------------------------------------------------------------------------------
    def screenshot(self, name: str) -> Optional[Path]:
        if self.shots_dir is None:
            return None
        self.shots_dir.mkdir(parents=True, exist_ok=True)
        path = self.shots_dir / f"{name}.png"
        self.pump(6)
        self.window.grabWindow().save(str(path))
        return path

    # --- kısa yollar ---------------------------------------------------------------------------------------------
    def open_page(self, title: str) -> None:
        """Kenar çubuğundan sayfa açar (yalnızca sol sütundaki etiket)."""
        sidebar_items = [i for i in self.items_with_text(title, exact=True)
                         if self.center_of(i).x() < self.window.width() * 0.25]
        assert sidebar_items, f"Kenar çubuğunda '{title}' yok. Görünen: {self.visible_texts()[:30]}"
        self.click_item(sidebar_items[0])
        self.pump(20, 0.005)

    @property
    def active_page(self) -> int:
        return int(self.c["shellController"].activePage)

