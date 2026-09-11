"""
d0 POC çalıştırıcı — QQuickPaintedItem tabanlı `LineChartItem`'ı gerçek portföy
verisiyle QML üzerinde gösterir (bkz. plan §9.4/§7.4 karar + POC).

Otomatik test SÜİTİNİN parçası değildir (gerçek pencere açar) — manuel görsel
doğrulama içindir:

    python -m src.ui_qml.main_poc
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path
from typing import List

from src.qt_compat.qtcore import QUrl
from src.qt_compat.qtgui import QGuiApplication
from src.qt_compat.qtqml import qmlRegisterType
from src.qt_compat.qtquick import QQuickView

from src.ui_qml.charts.line_chart_item import LineChartItem

_QML_FILE = Path(__file__).parent / "qml" / "poc" / "LineChartPoc.qml"
_FALLBACK_DEMO_SERIES = [100.0, 102.0, 98.0, 105.0, 110.0, 108.0, 115.0, 120.0, 118.0, 125.0]


def _load_real_cumulative_return_series() -> List[float]:
    """Gerçek dashboard portföyünün değer serisini döner.

    Portföy/servis erişilemezse (boş DB, ilk kurulum, veri yok) sentetik bir demo
    serisine düşer — POC'un tek başına da (başka bir makinede/DB'de) çalışabilmesi için.
    """
    try:
        from src.application.container import AppContainer
        from src.application.services.analysis.models import AnalysisFilterState

        container = AppContainer()
        state = AnalysisFilterState(
            start_date=date.today() - timedelta(days=365),
            end_date=date.today(),
            portfolio_source="dashboard",
        )
        comparison = container.portfolio_analytics_service.get_comparison_view(state)
        series = comparison.portfolio_series
        if not series:
            raise ValueError("Portföy serisi boş.")
        return [float(v) for _, v in sorted(series.items())]
    except Exception as exc:
        print(f"[d0 POC] Gerçek portföy verisi alınamadı ({exc}), demo seriye düşülüyor.")
        return _FALLBACK_DEMO_SERIES


def main() -> int:
    # `LineChartPoc.qml`'in kökü bir Window değil düz `Rectangle` (yeniden kullanılabilir
    # bileşen olarak kalsın diye) — bu yüzden `QQmlApplicationEngine` tek başına hiçbir
    # şey göstermez (kök bir Item ise engine otomatik pencere açmaz). `QQuickView`
    # kökü kendi penceresinin içeriği olarak render eder (bkz. d0 duman testindeki
    # `grabWindow()` doğrulaması ile aynı mekanizma).
    qmlRegisterType(LineChartItem, "PortfoyCharts", 1, 0, "LineChartItem")

    app = QGuiApplication(sys.argv)
    view = QQuickView()
    view.rootContext().setContextProperty("chartValues", _load_real_cumulative_return_series())
    view.setSource(QUrl.fromLocalFile(str(_QML_FILE.resolve())))

    if view.status() == QQuickView.Error:
        print("QML yüklenemedi:", _QML_FILE)
        return 1

    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.resize(640, 360)
    view.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
