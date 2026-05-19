from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar
from PyQt5.QtCore import Qt


class PredictionCard(QWidget):
    """Tahmin sonuçlarını gösteren kart — zengin API verileri destekler."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "aiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(6)

        title = QLabel("📈 TAHMİN")
        title.setProperty("cssClass", "cardLabel")
        layout.addWidget(title)

        # Hisse & Model bilgisi
        info_layout = QHBoxLayout()
        self.lbl_ticker = QLabel("Hisse: -")
        self.lbl_model = QLabel("")
        self.lbl_model.setProperty("cssClass", "dateLabelMuted")
        info_layout.addWidget(self.lbl_ticker)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_model)
        layout.addLayout(info_layout)

        # Fiyatlar
        price_layout = QHBoxLayout()
        self.lbl_price = QLabel("Tahmini Fiyat: -")
        self.lbl_price.setProperty("cssClass", "priceValueLargeCyan")
        self.lbl_last_close = QLabel("")
        self.lbl_last_close.setProperty("cssClass", "dateLabelMuted")
        price_layout.addWidget(self.lbl_price)
        price_layout.addStretch()
        price_layout.addWidget(self.lbl_last_close)
        layout.addLayout(price_layout)

        # Trend & Horizon
        trend_layout = QHBoxLayout()
        self.lbl_trend = QLabel("")
        self.lbl_trend.setAlignment(Qt.AlignCenter)
        self.lbl_trend.setProperty("cssClass", "trendBadge")
        self.lbl_horizon = QLabel("")
        self.lbl_horizon.setProperty("cssClass", "dateLabelMuted")
        self.lbl_return = QLabel("")
        self.lbl_return.setProperty("cssClass", "dateLabelMuted")
        trend_layout.addWidget(self.lbl_trend)
        trend_layout.addWidget(self.lbl_horizon)
        trend_layout.addStretch()
        trend_layout.addWidget(self.lbl_return)
        layout.addLayout(trend_layout)

        # Güven barı
        conf_layout = QHBoxLayout()
        conf_layout.addWidget(QLabel("Güven: "))
        self.progress_conf = QProgressBar()
        self.progress_conf.setRange(0, 100)
        self.progress_conf.setValue(0)
        self.progress_conf.setTextVisible(True)
        self.progress_conf.setProperty("cssClass", "aiProgressCyan")
        conf_layout.addWidget(self.progress_conf)
        self.lbl_conf_badge = QLabel("")
        self.lbl_conf_badge.setFixedWidth(60)
        self.lbl_conf_badge.setAlignment(Qt.AlignCenter)
        self.lbl_conf_badge.setProperty("cssClass", "confidenceBadge")
        conf_layout.addWidget(self.lbl_conf_badge)
        layout.addLayout(conf_layout)

    def update_data(
        self,
        ticker: str,
        predicted_price: float | None,
        confidence: float,
        confidence_label: str = "",
        model_name: str = "",
        last_close: float | None = None,
        trend_label: str | None = None,
        horizon_days: int | None = None,
        weekly_expected_return: float | None = None,
    ):
        self.lbl_ticker.setText(f"Hisse: {ticker}")

        if predicted_price is not None:
            self.lbl_price.setText(f"Tahmini Fiyat: ₺{predicted_price:.2f}")
        else:
            self.lbl_price.setText("Tahmini Fiyat: —")

        self.progress_conf.setValue(int(confidence * 100))

        # Güven badge
        badge_map = {"high": "YÜKSEK", "medium": "ORTA", "low": "DÜŞÜK"}
        badge_text = badge_map.get(confidence_label, "")
        self.lbl_conf_badge.setText(badge_text)
        self.lbl_conf_badge.setProperty("cssState", confidence_label or "low")
        self.lbl_conf_badge.style().unpolish(self.lbl_conf_badge)
        self.lbl_conf_badge.style().polish(self.lbl_conf_badge)

        # Model adı
        if model_name:
            self.lbl_model.setText(f"Model: {model_name}")

        # Son kapanış
        if last_close is not None:
            self.lbl_last_close.setText(f"Son Kapanış: ₺{last_close:.2f}")

        # Trend
        trend_map = {"up": "📈 Yükseliş", "down": "📉 Düşüş", "neutral": "➡ Yatay", "flat": "➡ Yatay"}
        if trend_label:
            tl_lower = trend_label.lower()
            self.lbl_trend.setText(trend_map.get(tl_lower, trend_label))
            self.lbl_trend.setProperty("cssState", tl_lower if tl_lower in ("up", "down") else "neutral")
            self.lbl_trend.style().unpolish(self.lbl_trend)
            self.lbl_trend.style().polish(self.lbl_trend)

        # Horizon
        if horizon_days is not None:
            self.lbl_horizon.setText(f"{horizon_days} günlük tahmin")

        # Beklenen getiri
        if weekly_expected_return is not None:
            pct = weekly_expected_return * 100
            sign = "+" if pct >= 0 else ""
            self.lbl_return.setText(f"Beklenen Getiri: {sign}{pct:.2f}%")

    def reset(self):
        self.lbl_ticker.setText("Hisse: -")
        self.lbl_price.setText("Tahmini Fiyat: -")
        self.lbl_model.setText("")
        self.lbl_last_close.setText("")
        self.lbl_trend.setText("")
        self.lbl_horizon.setText("")
        self.lbl_return.setText("")
        self.progress_conf.setValue(0)
        self.lbl_conf_badge.setText("")
