"""Denetleyici bağımlılıkları: denetleyici kullandığı servisleri `REQUIRES` ile bildirir, yalnızca onlara erişir.

`ServiceView(container, REQUIRES)`:
- bildirilen adı container'dan (yoksa `container.services`'ten) okur; servis yoksa veya container yoksa `None`
  (eski `getattr(container, ad, None)` davranışı),
- bildirilmeyen ada erişimde `AttributeError` verir: denetleyicinin bağımlılık listesi kodla birlikte doğru kalır,
- okuma her erişimde yapılır (testlerde sonradan atanan servisler görünür).

`tests/ui_qml/test_controller_dependencies.py` her `REQUIRES` adının gerçek container'da olduğunu ve `REQUIRES`
bildiren denetleyicinin container'a doğrudan erişmediğini doğrular.
"""
from __future__ import annotations

from typing import Any, Iterable


class ServiceView:
    __slots__ = ("_source", "_names")

    def __init__(self, container: Any, names: Iterable[str]) -> None:
        self._source = container
        self._names = frozenset(names)

    @property
    def available(self) -> bool:
        """Container verilmiş mi (servissiz/çevrimdışı mod değil)."""
        return self._source is not None

    @property
    def names(self) -> frozenset:
        return self._names

    def __getattr__(self, name: str) -> Any:
        if name not in self._names:
            raise AttributeError(f"'{name}' denetleyicinin REQUIRES listesinde yok")
        if self._source is None:
            return None
        value = getattr(self._source, name, None)
        if value is None:
            value = getattr(getattr(self._source, "services", None), name, None)
        return value
