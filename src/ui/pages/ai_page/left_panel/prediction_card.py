from src.ui.shared.locale_tr import L10N
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar
from PyQt5.QtCore import Qt
from src.ui.core.icon_manager import IconManager
from src.ui.formatters import display_ticker


class PredictionCard(QWidget):
    """Tahmin sonuçlarını gösteren kart — zengin API verileri destekler."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "aiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconManager.get_icon("trending-up", color="@COLOR_PRIMARY").pixmap(20, 20))
        title = QLabel(L10N.TAHMIN)
        title.setProperty("cssClass", "cardLabel")
        header_layout.addWidget(lbl_icon)
        header_layout.addWidget(title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Hisse & Model bilgisi
        info_layout = QHBoxLayout()
        self.lbl_ticker = QLabel(L10N.HISSE)
        self.lbl_ticker.setProperty("cssClass", "aiPrimaryText")
        self.lbl_model = QLabel("")
        self.lbl_model.setProperty("cssClass", "aiMetaText")
        self.lbl_model.setWordWrap(True)
        info_layout.addWidget(self.lbl_ticker)
        info_layout.addStretch()
        info_layout.addWidget(self.lbl_model)
        layout.addLayout(info_layout)

        # Fiyatlar
        price_layout = QHBoxLayout()
        self.lbl_price = QLabel(L10N.TAHMINI_FIYAT)
        self.lbl_price.setProperty("cssClass", "priceValueLargeCyan")
        self.lbl_last_close = QLabel("")
        self.lbl_last_close.setProperty("cssClass", "aiMetaText")
        self.lbl_last_close.setWordWrap(True)
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
        self.lbl_horizon.setProperty("cssClass", "aiMetaText")
        self.lbl_return = QLabel("")
        self.lbl_return.setProperty("cssClass", "aiStrongMetaText")
        self.lbl_return.setWordWrap(True)
        trend_layout.addWidget(self.lbl_trend)
        trend_layout.addWidget(self.lbl_horizon)
        trend_layout.addStretch()
        trend_layout.addWidget(self.lbl_return)
        layout.addLayout(trend_layout)

        # Güven barı
        conf_layout = QHBoxLayout()
        lbl_conf = QLabel(L10N.GUVEN)
        lbl_conf.setProperty("cssClass", "aiStrongMetaText")
        conf_layout.addWidget(lbl_conf)
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
        self.lbl_ticker.setText(f"Hisse: {display_ticker(ticker)}")

        if predicted_price is not None:
            self.lbl_price.setText(f"Tahmini Fiyat: ₺{predicted_price:.2f}")
        else:
            self.lbl_price.setText(L10N.TAHMINI_FIYAT_1)

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

        # Horizon sonundaki bileşik beklenen getiri
        if weekly_expected_return is not None:
            pct = weekly_expected_return * 100
            sign = "+" if pct >= 0 else ""
            horizon_label = f"{horizon_days} Günlük" if horizon_days is not None else L10N.HORIZON_SONU
            self.lbl_return.setText(f"{horizon_label} Bileşik Getiri: {sign}{pct:.2f}%")

    def reset(self):
        self.lbl_ticker.setText(L10N.HISSE)
        self.lbl_price.setText(L10N.TAHMINI_FIYAT)
        self.lbl_model.setText("")
        self.lbl_last_close.setText("")
        self.lbl_trend.setText("")
        self.lbl_horizon.setText("")
        self.lbl_return.setText("")
        self.progress_conf.setValue(0)
        self.lbl_conf_badge.setText("")
