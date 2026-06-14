from typing import NamedTuple

from src.ui.shared.locale_tr import L10N
from src.qt_compat.qtwidgets import QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar
from src.qt_compat.qtcore import Qt
from src.ui.core.icon_manager import IconManager
from src.ui.formatters import display_ticker


class PredictionDisplayArgs(NamedTuple):
    ticker: str
    predicted_price: "float | None"
    confidence: float
    confidence_label: str = ""
    model_name: str = ""
    last_close: "float | None" = None
    trend_label: "str | None" = None
    horizon_days: "int | None" = None
    weekly_expected_return: "float | None" = None
    predicted_price_low: "float | None" = None
    predicted_price_high: "float | None" = None
    interval_method: "str | None" = None


class PredictionCard(QWidget):
    """Tahmin sonuçlarını gösteren kart — zengin API verileri destekler."""

    _INTERVAL_METHOD_TR = {
        "residual_b2": "Geçmiş Sapmalara Göre (%80 Olasılık)",
        "conformal": "Hata Analizine Göre (%90 Olasılık)",
        "quantile_model": "Olasılık Modeli",
    }

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "aiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)
        self._build_pred_header(layout)
        self._build_ticker_price_rows(layout)
        self._build_trend_confidence(layout)

    def _build_pred_header(self, layout) -> None:
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

    def _build_ticker_price_rows(self, layout) -> None:
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
        self.lbl_interval = QLabel("")
        self.lbl_interval.setProperty("cssClass", "aiMetaText")
        self.lbl_interval.setWordWrap(True)
        self.lbl_interval.setVisible(False)
        layout.addWidget(self.lbl_interval)

    def _build_trend_confidence(self, layout) -> None:
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

    def update_data(self, args: PredictionDisplayArgs) -> None:
        self._update_price_labels(args.ticker, args.predicted_price, args.last_close)
        self._update_interval_label(args.predicted_price_low, args.predicted_price_high, args.interval_method)
        self._update_trend_labels(args.trend_label, args.horizon_days, args.weekly_expected_return)
        self._update_confidence_display(args.confidence, args.confidence_label, args.model_name)

    def _update_price_labels(self, ticker: str, predicted_price: float | None, last_close: float | None) -> None:
        self.lbl_ticker.setText(L10N.HISSE_TMPL.format(ticker=display_ticker(ticker)))
        if predicted_price is not None:
            self.lbl_price.setText(L10N.TAHMINI_FIYAT_TMPL.format(price=f"{predicted_price:.2f}"))
        else:
            self.lbl_price.setText(L10N.TAHMINI_FIYAT_1)
        if last_close is not None:
            self.lbl_last_close.setText(L10N.SON_KAPANIS_FIYAT_TMPL.format(price=f"{last_close:.2f}"))

    def _update_interval_label(self, low: float | None, high: float | None, method: str | None) -> None:
        if low is not None and high is not None:
            method_text = self._INTERVAL_METHOD_TR.get(method or "", "")
            if method_text:
                self.lbl_interval.setText(
                    L10N.TAHMIN_ARALIGI_YONTEM_TMPL.format(
                        low=f"{low:.2f}", high=f"{high:.2f}", method=method_text,
                    )
                )
            else:
                self.lbl_interval.setText(
                    L10N.TAHMIN_ARALIGI_TMPL.format(low=f"{low:.2f}", high=f"{high:.2f}")
                )
            self.lbl_interval.setVisible(True)
        else:
            self.lbl_interval.clear()
            self.lbl_interval.setVisible(False)

    def _update_trend_labels(self, trend_label: str | None, horizon_days: int | None, weekly_expected_return: float | None) -> None:
        trend_map = {"up": L10N.TREND_YUKSELIS, "down": L10N.TREND_DUSUS, "neutral": L10N.TREND_YATAY, "flat": L10N.TREND_YATAY}
        if trend_label:
            tl_lower = trend_label.lower()
            self.lbl_trend.setText(trend_map.get(tl_lower, trend_label))
            self.lbl_trend.setProperty("cssState", tl_lower if tl_lower in ("up", "down") else "neutral")
            self.lbl_trend.style().unpolish(self.lbl_trend)
            self.lbl_trend.style().polish(self.lbl_trend)
        if horizon_days is not None:
            self.lbl_horizon.setText(L10N.GUNLUK_TAHMIN_TMPL.format(days=horizon_days))
        if weekly_expected_return is not None:
            pct = weekly_expected_return * 100
            sign = "+" if pct >= 0 else ""
            horizon_label = f"{horizon_days} Günlük" if horizon_days is not None else L10N.HORIZON_SONU
            self.lbl_return.setText(L10N.BILESIK_GETIRI_TMPL.format(label=horizon_label, value=f"{sign}{pct:.2f}%"))

    def _update_confidence_display(self, confidence: float, confidence_label: str, model_name: str) -> None:
        self.progress_conf.setValue(int(confidence * 100))
        badge_map = {"high": "YÜKSEK", "medium": "ORTA", "low": "DÜŞÜK"}
        self.lbl_conf_badge.setText(badge_map.get(confidence_label, ""))
        self.lbl_conf_badge.setProperty("cssState", confidence_label or "low")
        self.lbl_conf_badge.style().unpolish(self.lbl_conf_badge)
        self.lbl_conf_badge.style().polish(self.lbl_conf_badge)
        if model_name:
            self.lbl_model.setText(L10N.MODEL_TMPL.format(name=model_name))

    def reset(self):
        self.lbl_ticker.setText(L10N.HISSE)
        self.lbl_price.setText(L10N.TAHMINI_FIYAT)
        self.lbl_model.setText("")
        self.lbl_last_close.setText("")
        self.lbl_interval.clear()
        self.lbl_interval.setVisible(False)
        self.lbl_trend.setText("")
        self.lbl_horizon.setText("")
        self.lbl_return.setText("")
        self.progress_conf.setValue(0)
        self.lbl_conf_badge.setText("")
