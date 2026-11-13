"""Kullanıcı ayarları (QSettings) için tek fabrika.

`QSettings("PortfoySimulasyonu", "PortfoySimulasyonu")` her zaman yerel biçimi (Windows kayıt defteri) kullanır;
`QSettings.setDefaultFormat` yalnızca argümansız kurucuyu etkiler. Bu yüzden testler ve QA oturumları gerçek kullanıcının
sohbet geçmişine, tema tercihine ve açılış işi damgalarına yazıyordu (2026-11-08). Uygulama kodu ayarı yalnızca
`user_settings()` ile açar; testler ve araçlar `use_ini_file(yol)` ile bir INI dosyasına yönlendirir
(`tests/conftest.py` her oturumda yapar).
"""
from __future__ import annotations

import os
from typing import Optional

from PySide6.QtCore import QSettings

ORGANIZATION = "PortfoySimulasyonu"
APPLICATION = "PortfoySimulasyonu"
INI_ENV = "PORTFOY_SETTINGS_INI"

_ini_path: Optional[str] = None


def use_ini_file(path: Optional[str]) -> Optional[str]:
    """Ayarları `path` INI dosyasına yönlendirir (`None`: yerel biçime dön). Önceki yolu döner."""
    global _ini_path
    previous, _ini_path = _ini_path, path
    return previous


def user_settings() -> QSettings:
    """Uygulamanın kullanıcı ayarları; yönlendirme (`use_ini_file` veya `PORTFOY_SETTINGS_INI`) varsa INI dosyası."""
    path = _ini_path or os.environ.get(INI_ENV)
    if path:
        return QSettings(path, QSettings.Format.IniFormat)
    return QSettings(ORGANIZATION, APPLICATION)
