"""Özellik modülleri ve kurulum sırası.

Yeni servis: ilgili özellik modülünün `PROVIDES` ve `build` kısmına eklenir; başka dosyaya dokunulmaz.
Yeni özellik: `features/<ad>.py` oluşturulur ve aşağıdaki `FEATURES` sırasına bir satır eklenir (bağımlı olduğu
özelliklerden sonra).
"""
from src.application.container_parts.features import (
    analysis,
    assets,
    corporate_actions,
    market,
    news,
    planning,
    portfolio,
    prices,
    reporting,
)
from src.application.container_parts.features._context import BuildContext, ServiceRegistry, build_features

FEATURES = (portfolio, prices, reporting, corporate_actions, market, planning, analysis, assets, news)


def service_names() -> tuple:
    """Container'ın açtığı tüm servis adları (statik; kurulum yapmadan)."""
    return tuple(name for feature in FEATURES for name in feature.PROVIDES)


__all__ = ["FEATURES", "BuildContext", "ServiceRegistry", "build_features", "service_names"]
