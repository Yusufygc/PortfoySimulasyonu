"""API anahtarları için işletim sistemi sır deposu (Windows Kimlik Bilgisi Yöneticisi, `keyring` ile).

Anahtarlar düz metin `.env` dosyası yerine mümkünse işletim sistemi deposunda tutulur. `keyring` yoksa, depo
kullanılamıyorsa veya bir çağrı hata verirse işlemler sessizce başarısız sayılır (`False` / `None`) ve çağıran
`.env` yedeğine düşer; değer hiçbir zaman log'a yazılmaz.
"""
from __future__ import annotations

import logging
from typing import Protocol

logger = logging.getLogger(__name__)

SERVICE_NAME = "PortfoySimulasyonu"
SECRET_NAMES = ("GEMINI_API_KEY", "EVDS_API_KEY")


class SecretStore(Protocol):
    def get(self, name: str) -> str | None: ...

    def set(self, name: str, value: str) -> bool: ...

    def delete(self, name: str) -> bool: ...


class KeyringSecretStore:
    """`keyring` üzerinden sır deposu; her işlem hata durumunda güvenle başarısız olur."""

    def __init__(self, service_name: str = SERVICE_NAME) -> None:
        self._service = service_name

    def _keyring(self):
        try:
            import keyring

            return keyring
        except Exception as exc:  # keyring kurulu değil veya arka uç yüklenemedi
            logger.debug("keyring kullanılamıyor: %s", exc)
            return None

    def get(self, name: str) -> str | None:
        backend = self._keyring()
        if backend is None:
            return None
        try:
            return backend.get_password(self._service, name) or None
        except Exception as exc:
            logger.warning("Sır deposundan %s okunamadı: %s", name, type(exc).__name__)
            return None

    def set(self, name: str, value: str) -> bool:
        backend = self._keyring()
        if backend is None:
            return False
        try:
            backend.set_password(self._service, name, value)
            return True
        except Exception as exc:
            logger.warning("Sır deposuna %s yazılamadı: %s", name, type(exc).__name__)
            return False

    def delete(self, name: str) -> bool:
        backend = self._keyring()
        if backend is None:
            return False
        try:
            backend.delete_password(self._service, name)
            return True
        except Exception as exc:  # kayıt zaten yoksa da buraya düşer
            logger.debug("Sır deposundan %s silinemedi: %s", name, type(exc).__name__)
            return False


_store: SecretStore = KeyringSecretStore()


def get_secret_store() -> SecretStore:
    return _store


def set_secret_store(store: SecretStore) -> SecretStore:
    """Aktif depoyu değiştirir (testler gerçek Kimlik Bilgisi Yöneticisi'ne dokunmasın diye); önceki depoyu döner."""
    global _store
    previous, _store = _store, store
    return previous
