"""Özellik kurulum bağlamı ve servis kaydı.

Her özellik modülü (`features/<özellik>.py`) iki şey bildirir:
- `PROVIDES`: container'a açtığı servis adları (statik; ad koruma testleri kurulum yapmadan okur),
- `build(ctx) -> dict`: bu adları kuran fonksiyon. Önceki özelliklerin servisleri `ctx.services`, container'a
  açılmayan paylaşılan nesneler (ör. tek bölünme uygulayıcısı) `ctx.internal` üzerinden okunur.

Yeni servis eklemek yalnızca kendi özellik modülüne dokunur.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Iterator, Tuple


@dataclass
class BuildContext:
    repositories: Any
    market_clients: Any
    market_settings: Any = None
    services: Dict[str, Any] = field(default_factory=dict)
    internal: Dict[str, Any] = field(default_factory=dict)


class ServiceRegistry:
    """Kurulmuş servisler: öznitelik erişimi (`services.portfolio_service`) ve ad listesi; bilinmeyen ad hatadır."""

    def __init__(self, services: Dict[str, Any]) -> None:
        object.__setattr__(self, "_services", dict(services))

    def __getattr__(self, name: str) -> Any:
        try:
            return self._services[name]
        except KeyError:
            raise AttributeError(f"Kayıtlı servis yok: {name}") from None

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError("ServiceRegistry salt okunurdur")

    def __contains__(self, name: str) -> bool:
        return name in self._services

    def names(self) -> Tuple[str, ...]:
        return tuple(self._services)

    def items(self) -> Iterator[Tuple[str, Any]]:
        return iter(self._services.items())


def build_features(ctx: BuildContext, features: Iterable[Any]) -> ServiceRegistry:
    """Özellikleri sırayla kurar; her modülün döndürdüğü adların `PROVIDES` ile aynı olduğunu ve adların
    çakışmadığını doğrular."""
    for feature in features:
        built = feature.build(ctx)
        name = feature.__name__.rsplit(".", 1)[-1]
        if set(built) != set(feature.PROVIDES):
            raise RuntimeError(f"{name}: PROVIDES ile kurulan servisler farklı: {sorted(set(built) ^ set(feature.PROVIDES))}")
        clash = set(built) & set(ctx.services)
        if clash:
            raise RuntimeError(f"{name}: başka özellikte de tanımlı servis adları: {sorted(clash)}")
        ctx.services.update(built)
    return ServiceRegistry(ctx.services)
