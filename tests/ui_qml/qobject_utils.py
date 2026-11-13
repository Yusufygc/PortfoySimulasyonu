"""QML nesne ağacında sınıf adına göre arama; QML'in aradaki nesneleri silmesine dayanıklıdır.

CI Python 3.12'de `findChildren(QObject)` döndükten sonra QML (JS çöp toplayıcı) bir nesneyi silebiliyor ve `metaObject()`
"Internal C++ object already deleted" ile düşüyordu (`isValid` kontrolü kontrol ile çağrı arasındaki yarışı kapatmaz)."""
from __future__ import annotations

from typing import List

from PySide6.QtCore import QObject


def children_of_class(item: QObject, fragment: str) -> List[QObject]:
    found = []
    for child in item.findChildren(QObject):
        try:
            if fragment in child.metaObject().className():
                found.append(child)
        except RuntimeError:  # arama sırasında silindi
            continue
    return found
