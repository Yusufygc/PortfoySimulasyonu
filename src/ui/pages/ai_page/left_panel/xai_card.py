from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QLabel,
    QFrame,
    QHBoxLayout,
    QProgressBar,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from src.ui.core.icon_manager import IconManager


class XAICard(QWidget):
    """Model açıklanabilirliği kartı."""

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "aiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconManager.get_icon("search", color="@COLOR_PRIMARY").pixmap(20, 20))
        title = QLabel("MODEL AÇIKLAMASI (XAI)")
        title.setProperty("cssClass", "cardLabel")
        self.lbl_method = QLabel("")
        self.lbl_method.setProperty("cssClass", "aiMetaText")
        self.lbl_method.setWordWrap(True)
        header_layout.addWidget(lbl_icon)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_method)
        layout.addLayout(header_layout)

        self.lbl_unavailable = QLabel("XAI verisi mevcut değil")
        self.lbl_unavailable.setAlignment(Qt.AlignCenter)
        self.lbl_unavailable.setProperty("cssClass", "aiHintText")
        self.lbl_unavailable.setVisible(False)
        layout.addWidget(self.lbl_unavailable)

        self.lbl_pos_title = QWidget()
        pos_layout = QHBoxLayout(self.lbl_pos_title)
        pos_layout.setContentsMargins(0, 0, 0, 0)
        pos_icon = QLabel()
        pos_icon.setPixmap(IconManager.get_icon("trending-up", color="@COLOR_SUCCESS").pixmap(18, 18))
        pos_text = QLabel("Fiyatı Yukarı Çeken Faktörler")
        pos_text.setProperty("cssClass", "xaiSectionTitle")
        pos_layout.addWidget(pos_icon)
        pos_layout.addWidget(pos_text)
        pos_layout.addStretch()
        layout.addWidget(self.lbl_pos_title)

        self.positive_layout = QVBoxLayout()
        self.positive_layout.setSpacing(8)
        layout.addLayout(self.positive_layout)

        line = QWidget()
        line.setFixedHeight(1)
        line.setProperty("cssClass", "horizontalDivider")
        layout.addWidget(line)

        self.lbl_neg_title = QWidget()
        neg_layout = QHBoxLayout(self.lbl_neg_title)
        neg_layout.setContentsMargins(0, 0, 0, 0)
        neg_icon = QLabel()
        neg_icon.setPixmap(IconManager.get_icon("trending-down", color="@COLOR_DANGER").pixmap(18, 18))
        neg_text = QLabel("Fiyata Aşağı Baskı Yapan Faktörler")
        neg_text.setProperty("cssClass", "xaiSectionTitle")
        neg_layout.addWidget(neg_icon)
        neg_layout.addWidget(neg_text)
        neg_layout.addStretch()
        layout.addWidget(self.lbl_neg_title)

        self.negative_layout = QVBoxLayout()
        self.negative_layout.setSpacing(8)
        layout.addLayout(self.negative_layout)

        self.features_layout = QVBoxLayout()
        self.features_layout.setSpacing(8)
        layout.addLayout(self.features_layout)

        line2 = QWidget()
        line2.setFixedHeight(1)
        line2.setProperty("cssClass", "horizontalDivider")
        layout.addWidget(line2)

        self.txt_explanation = QTextEdit()
        self.txt_explanation.setReadOnly(True)
        self.txt_explanation.setProperty("cssClass", "aiTextEdit")
        self.txt_explanation.setFixedHeight(112)
        layout.addWidget(self.txt_explanation)

        self.lbl_caveat = QLabel("")
        self.lbl_caveat.setProperty("cssClass", "aiHintText")
        self.lbl_caveat.setWordWrap(True)
        self.lbl_caveat.setVisible(False)
        layout.addWidget(self.lbl_caveat)

    def update_data(
        self,
        features: dict[str, float],
        text: str,
        xai_available: bool = True,
        xai_method: str = "",
        positive_reasons: list | None = None,
        negative_reasons: list | None = None,
        xai_caveat: str = "",
    ):
        """Kartı API verileriyle günceller."""
        self.lbl_method.setText(f"Yöntem: {xai_method}" if xai_method else "")
        self._clear_layout(self.positive_layout)
        self._clear_layout(self.negative_layout)
        self._clear_layout(self.features_layout)

        if not xai_available:
            self.lbl_unavailable.setVisible(True)
            self.lbl_pos_title.setVisible(False)
            self.lbl_neg_title.setVisible(False)
            self.txt_explanation.setText(text or "Bu model için XAI açıklanabilirlik verisi üretilmemiş.")
            self._set_caveat(xai_caveat)
            return

        self.lbl_unavailable.setVisible(False)
        self.lbl_pos_title.setVisible(True)
        self.lbl_neg_title.setVisible(True)

        if positive_reasons:
            for item in positive_reasons:
                self.positive_layout.addWidget(self._make_factor_row(item, "positive"))

        if negative_reasons:
            for item in negative_reasons:
                self.negative_layout.addWidget(self._make_factor_row(item, "negative"))

        if not positive_reasons and not negative_reasons and features:
            self.lbl_pos_title.setVisible(False)
            self.lbl_neg_title.setVisible(False)
            for name, value in features.items():
                self.features_layout.addWidget(self._make_factor_row(
                    {
                        "human_label": name,
                        "feature_name": name,
                        "importance": value,
                        "direction": "neutral",
                    },
                    "neutral",
                ))

        self.txt_explanation.setText(text)
        self._set_caveat(xai_caveat)

    def reset(self):
        self._clear_layout(self.positive_layout)
        self._clear_layout(self.negative_layout)
        self._clear_layout(self.features_layout)
        self.txt_explanation.clear()
        self.lbl_method.setText("")
        self.lbl_caveat.setVisible(False)
        self.lbl_unavailable.setVisible(False)

    def _make_factor_row(self, item, direction: str) -> QWidget:
        """Tek bir XAI faktör satırı oluşturur."""
        name = self._item_value(item, "human_label") or self._item_value(item, "feature_name") or "-"
        feature_name = self._item_value(item, "feature_name") or name
        reason = self._item_value(item, "reason") or ""
        group = self._group_label(self._item_value(item, "feature_group"))
        method = self._method_label(self._item_value(item, "method"))
        contribution = self._item_value(item, "contribution")
        approximate = self._item_value(item, "approximate")
        importance = self._safe_float(self._item_value(item, "importance"))
        bar_val = abs(importance) * 100 if abs(importance) <= 1.0 else abs(importance)
        bar_val = min(bar_val, 100)

        wrapper = QFrame()
        wrapper.setProperty("cssClass", "xaiFactorRow")
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(6)

        icon_map = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}
        lbl_icon = QLabel(icon_map.get(direction, "⚪"))
        lbl_icon.setFixedWidth(22)

        lbl_name = QLabel(name)
        lbl_name.setWordWrap(True)
        lbl_name.setToolTip(feature_name if feature_name == name else f"{name}\n{feature_name}")
        lbl_name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        lbl_name.setProperty("cssClass", "xaiFactorLabel")

        lbl_group = QLabel(group)
        lbl_group.setProperty("cssClass", "xaiFactorGroup")
        lbl_group.setVisible(bool(group))

        lbl_value = QLabel(f"{bar_val:.0f}%")
        lbl_value.setFixedWidth(48)
        lbl_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl_value.setProperty("cssClass", "metricValue")

        header.addWidget(lbl_icon)
        header.addWidget(lbl_name, 1)
        header.addWidget(lbl_group)
        header.addWidget(lbl_value)
        outer.addLayout(header)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(int(bar_val))
        bar.setTextVisible(False)
        bar.setFixedHeight(12)
        css_map = {"positive": "aiProgressGreen", "negative": "aiProgressRed", "neutral": "aiProgressBlue"}
        bar.setProperty("cssClass", css_map.get(direction, "aiProgressBlue"))
        outer.addWidget(bar)

        details = self._details_text(reason, method, contribution, approximate)
        if details:
            lbl_reason = QLabel(details)
            lbl_reason.setWordWrap(True)
            lbl_reason.setProperty("cssClass", "xaiFactorReason")
            outer.addWidget(lbl_reason)

        return wrapper

    def _set_caveat(self, xai_caveat: str) -> None:
        if xai_caveat:
            self.lbl_caveat.setText(f"ℹ {xai_caveat}")
            self.lbl_caveat.setVisible(True)
        else:
            self.lbl_caveat.setVisible(False)

    @staticmethod
    def _details_text(reason: str, method: str, contribution, approximate) -> str:
        parts = []
        if reason:
            parts.append(reason)
        method_parts = []
        if method:
            method_parts.append(f"yöntem: {method}")
        try:
            if contribution is not None:
                method_parts.append(f"katkı: {float(contribution):+.4f}")
        except (TypeError, ValueError):
            pass
        if approximate is True:
            method_parts.append("yaklaşık")
        if method_parts:
            parts.append(" · ".join(method_parts))
        return "\n".join(parts)

    @staticmethod
    def _group_label(group: str | None) -> str:
        labels = {
            "technical": "Teknik",
            "macro": "Makro",
            "market_relative": "Endeks",
            "volume": "Hacim",
            "volatility": "Volatilite",
            "regime": "Rejim",
            "lag": "Gecikmeli",
            "signal": "Model faktörü",
            "Sinyal karari": "Model faktörü",
            "model_summary": "Model Özeti",
            "other": "Diğer",
        }
        if not group:
            return ""
        return labels.get(str(group), str(group))

    @staticmethod
    def _method_label(method: str | None) -> str:
        labels = {
            "rule_based": "kural bazlı özet",
            "signal_rules": "model faktör kuralları",
            "sequence": "sekans katkısı",
        }
        if not method:
            return ""
        return labels.get(str(method), str(method))

    @staticmethod
    def _item_value(item, key: str):
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    @staticmethod
    def _safe_float(value) -> float:
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            return 0.0

    def _clear_layout(self, layout) -> None:
        """Layout içindeki tüm widget'ları temizler."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
