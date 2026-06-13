from src.ui.shared.locale_tr import L10N
from src.qt_compat.qtwidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar, QGridLayout
from src.qt_compat.qtcore import Qt
from src.ui.core.icon_manager import IconManager


# ── Metrik → Türkçe açıklama eşlemesi ────────────────────────────────────────

_METRIC_INFO = {
    "composite_score": {
        "label": L10N.METRIC_COMPOSITE_SCORE_LABEL,
        "desc":  L10N.METRIC_COMPOSITE_SCORE_DESC,
        "unit":  "",
        "max":   100,
        "higher_is_better": True,
    },
    "directional_accuracy": {
        "label": L10N.METRIC_DIRECTIONAL_ACCURACY_LABEL,
        "desc":  L10N.METRIC_DIRECTIONAL_ACCURACY_DESC,
        "unit":  "%",
        "max":   100,
        "higher_is_better": True,
    },
    "hit_rate": {
        "label": L10N.METRIC_HIT_RATE_LABEL,
        "desc":  L10N.METRIC_HIT_RATE_DESC,
        "unit":  "%",
        "max":   100,
        "higher_is_better": True,
    },
    "sharpe": {
        "label": L10N.METRIC_SHARPE_LABEL,
        "desc":  L10N.METRIC_SHARPE_DESC,
        "unit":  "",
        "max":   3.0,
        "higher_is_better": True,
    },
    "rmse": {
        "label": L10N.METRIC_RMSE_LABEL,
        "desc":  L10N.METRIC_RMSE_DESC,
        "unit":  "₺",
        "max":   10.0,
        "higher_is_better": False,
    },
    "mae": {
        "label": L10N.METRIC_MAE_LABEL,
        "desc":  L10N.METRIC_MAE_DESC,
        "unit":  "₺",
        "max":   10.0,
        "higher_is_better": False,
    },
    "stability_score": {
        "label": L10N.METRIC_STABILITY_SCORE_LABEL,
        "desc":  L10N.METRIC_STABILITY_SCORE_DESC,
        "unit":  "",
        "max":   100,
        "higher_is_better": True,
    },
}


class PerformanceCard(QWidget):
    """Model performans metriklerini Türkçe açıklamalarla gösteren kart."""

    def __init__(self) -> None:
        super().__init__()
        self._bars: dict[str, tuple[QLabel, QProgressBar, QLabel]] = {}
        self._init_ui()

    def _init_ui(self) -> None:
        self.setProperty("cssClass", "aiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconManager.get_icon("bar-chart-2", color="@COLOR_PRIMARY").pixmap(20, 20))
        title = QLabel(L10N.MODEL_PERFORMANSI)
        title.setProperty("cssClass", "cardLabel")
        header_layout.addWidget(lbl_icon)
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        self.grid = QGridLayout()
        self.grid.setSpacing(6)
        layout.addLayout(self.grid)

        # Metrikleri sırala — önemli olanlar üstte
        metric_order = [
            "composite_score",
            "directional_accuracy",
            "hit_rate",
            "sharpe",
            "rmse",
            "mae",
            "stability_score",
        ]

        for row, key in enumerate(metric_order):
            info = _METRIC_INFO[key]

            # Metrik adı etiketi (kalın)
            lbl_name = QLabel(info["label"])
            lbl_name.setProperty("cssClass", "metricLabel")
            lbl_name.setToolTip(info["desc"])
            lbl_name.setMinimumWidth(130)

            # Progress bar
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setValue(0)
            bar.setTextVisible(False)
            bar.setFixedHeight(14)

            css_class = "aiProgressGreen" if info["higher_is_better"] else "aiProgressOrange"
            bar.setProperty("cssClass", css_class)

            # Değer etiketi
            lbl_value = QLabel("-")
            lbl_value.setFixedWidth(60)
            lbl_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            lbl_value.setProperty("cssClass", "metricValue")

            self.grid.addWidget(lbl_name, row, 0)
            self.grid.addWidget(bar, row, 1)
            self.grid.addWidget(lbl_value, row, 2)

            self._bars[key] = (lbl_name, bar, lbl_value)

        # Açıklama alt etiketi
        self.lbl_hint = QLabel(L10N.METRIK_ADLARININ_UZERINE_GELEREK_ACIKLAMASINI)
        self.lbl_hint.setProperty("cssClass", "aiHintText")
        self.lbl_hint.setWordWrap(True)
        layout.addWidget(self.lbl_hint)

    def update_data(
        self,
        composite_score: float | None = None,
        directional_accuracy: float | None = None,
        hit_rate: float | None = None,
        sharpe: float | None = None,
        rmse: float | None = None,
        mae: float | None = None,
        stability_score: float | None = None,
        last_close: float | None = None,
    ) -> None:
        """Performans metriklerini kartlara yazar."""
        values = {
            "composite_score": composite_score,
            "directional_accuracy": directional_accuracy,
            "hit_rate": hit_rate,
            "sharpe": sharpe,
            "rmse": rmse,
            "mae": mae,
            "stability_score": stability_score,
        }

        for key, val in values.items():
            if key not in self._bars:
                continue
            _, bar, lbl_value = self._bars[key]
            info = _METRIC_INFO[key]

            if val is None:
                bar.setValue(0)
                lbl_value.setText("-")
                continue

            # Değer metnini oluştur
            unit = info["unit"]
            if unit == "%":
                lbl_value.setText(f"%{val:.1f}")
            elif unit == "₺":
                lbl_value.setText(f"₺{val:.2f}")
            else:
                lbl_value.setText(f"{val:.2f}")

            # Bar yüzdesi hesapla
            max_val = info["max"]
            if info["higher_is_better"]:
                pct = min(max(val / max_val * 100, 0), 100)
            else:
                # Düşük iyi (RMSE, MAE) -> Hisse fiyatına oranla hesapla
                if last_close and last_close > 0:
                    # % Hata payı (Örn: ₺15 hata / ₺300 fiyat = %5 hata)
                    error_pct = (val / last_close) * 100
                    # %10 hata ve üstü 0 bar verir, %0 hata 100 bar verir
                    pct = max(100 - (error_pct * 10), 0)
                else:
                    # Fallback (sabit limite göre)
                    pct = max(100 - (val / max_val * 100), 0)

            bar.setValue(int(pct))

    def reset(self) -> None:
        for _, (_, bar, lbl_value) in self._bars.items():
            bar.setValue(0)
            lbl_value.setText("-")
