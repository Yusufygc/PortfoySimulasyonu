from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar, QGridLayout
from PyQt5.QtCore import Qt


# ── Metrik → Türkçe açıklama eşlemesi ────────────────────────────────────────

_METRIC_INFO = {
    "composite_score": {
        "label": "Bileşik Skor",
        "desc":  "Modelin genel başarısını tek sayıda özetler. Yön isabeti, hata ve risk metriklerinin ağırlıklı ortalamasıdır.",
        "unit":  "",
        "max":   100,
        "higher_is_better": True,
    },
    "directional_accuracy": {
        "label": "Yön İsabeti",
        "desc":  "Modelin fiyat yönünü (yukarı/aşağı) doğru tahmin etme oranı.",
        "unit":  "%",
        "max":   100,
        "higher_is_better": True,
    },
    "hit_rate": {
        "label": "İsabet Oranı",
        "desc":  "Tahminlerin gerçek fiyata ne kadar yakın olduğunun yüzdesi.",
        "unit":  "%",
        "max":   100,
        "higher_is_better": True,
    },
    "sharpe": {
        "label": "Sharpe Oranı",
        "desc":  "Birim risk başına getiri. 0'ın üstü iyi, 1'in üstü çok iyi kabul edilir.",
        "unit":  "",
        "max":   3.0,
        "higher_is_better": True,
    },
    "rmse": {
        "label": "RMSE",
        "desc":  "Kök Ortalama Kare Hata — tahminin gerçek fiyattan ortalama sapması. Düşük olması iyidir.",
        "unit":  "₺",
        "max":   10.0,
        "higher_is_better": False,
    },
    "mae": {
        "label": "MAE",
        "desc":  "Ortalama Mutlak Hata — tahmin ile gerçek arasındaki ortalama fark. Düşük olması iyidir.",
        "unit":  "₺",
        "max":   10.0,
        "higher_is_better": False,
    },
    "stability_score": {
        "label": "Kararlılık Skoru",
        "desc":  "Modelin farklı dönemlerdeki performans tutarlılığı. Yüksek olması iyidir.",
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

        title = QLabel("📊 MODEL PERFORMANSI")
        title.setProperty("cssClass", "cardLabel")
        layout.addWidget(title)

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
            lbl_name.setFixedWidth(120)

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
        self.lbl_hint = QLabel("ℹ Metrik adlarının üzerine gelerek açıklamasını görebilirsiniz")
        self.lbl_hint.setProperty("cssClass", "dateLabelMuted")
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
