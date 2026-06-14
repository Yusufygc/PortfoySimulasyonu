from typing import NamedTuple

from src.ui.shared.locale_tr import L10N
from src.qt_compat.qtcore import Qt
from src.qt_compat.qtwidgets import (
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


class XaiDisplayArgs(NamedTuple):
    available: bool = True
    method: str = ""
    caveat: str = ""


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
        self._build_xai_header(layout)
        self.lbl_unavailable = QLabel(L10N.XAI_VERISI_MEVCUT_DEGIL)
        self.lbl_unavailable.setAlignment(Qt.AlignCenter)
        self.lbl_unavailable.setProperty("cssClass", "aiHintText")
        self.lbl_unavailable.setVisible(False)
        layout.addWidget(self.lbl_unavailable)
        self.lbl_pos_title = self._make_factors_title("trending-up", "@COLOR_SUCCESS", L10N.FIYATI_YUKARI_CEKEN_FAKTORLER)
        layout.addWidget(self.lbl_pos_title)
        self.positive_layout = QVBoxLayout()
        self.positive_layout.setSpacing(8)
        layout.addLayout(self.positive_layout)
        _div1 = QWidget()
        _div1.setFixedHeight(1)
        _div1.setProperty("cssClass", "horizontalDivider")
        layout.addWidget(_div1)
        self.lbl_neg_title = self._make_factors_title("trending-down", "@COLOR_DANGER", L10N.FIYATA_ASAGI_BASKI_YAPAN_FAKTORLER)
        layout.addWidget(self.lbl_neg_title)
        self.negative_layout = QVBoxLayout()
        self.negative_layout.setSpacing(8)
        layout.addLayout(self.negative_layout)
        self.features_layout = QVBoxLayout()
        self.features_layout.setSpacing(8)
        layout.addLayout(self.features_layout)
        _div2 = QWidget()
        _div2.setFixedHeight(1)
        _div2.setProperty("cssClass", "horizontalDivider")
        layout.addWidget(_div2)
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

    def _build_xai_header(self, layout) -> None:
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconManager.get_icon("search", color="@COLOR_PRIMARY").pixmap(20, 20))
        title = QLabel(L10N.MODEL_ACIKLAMASI_XAI)
        title.setProperty("cssClass", "cardLabel")
        self.lbl_method = QLabel("")
        self.lbl_method.setProperty("cssClass", "aiMetaText")
        self.lbl_method.setWordWrap(True)
        header_layout.addWidget(lbl_icon)
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_method)
        layout.addLayout(header_layout)

    def _make_factors_title(self, icon_name: str, color: str, text: str) -> QWidget:
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        icon = QLabel()
        icon.setPixmap(IconManager.get_icon(icon_name, color=color).pixmap(18, 18))
        lbl = QLabel(text)
        lbl.setProperty("cssClass", "xaiSectionTitle")
        row.addWidget(icon)
        row.addWidget(lbl)
        row.addStretch()
        return container

    def _populate_reasons(self, reasons: list, layout, kind: str) -> None:
        for item in reasons:
            layout.addWidget(self._make_factor_row(item, kind))

    def _populate_xai_views(self, positive_reasons, negative_reasons, features: dict) -> None:
        self.lbl_unavailable.setVisible(False)
        self.lbl_pos_title.setVisible(True)
        self.lbl_neg_title.setVisible(True)
        if positive_reasons:
            self._populate_reasons(positive_reasons, self.positive_layout, "positive")
        if negative_reasons:
            self._populate_reasons(negative_reasons, self.negative_layout, "negative")
        if not positive_reasons and not negative_reasons and features:
            self.lbl_pos_title.setVisible(False)
            self.lbl_neg_title.setVisible(False)
            for name, value in features.items():
                self.features_layout.addWidget(self._make_factor_row(
                    {"human_label": name, "feature_name": name, "importance": value, "direction": "neutral"},
                    "neutral",
                ))

    def update_data(
        self,
        features: dict[str, float],
        text: str,
        xai: XaiDisplayArgs = XaiDisplayArgs(),
        positive_reasons: list | None = None,
        negative_reasons: list | None = None,
    ):
        friendly_method = self._friendly_method(xai.method)
        self.lbl_method.setText(L10N.YONTEM_TMPL.format(method=friendly_method) if friendly_method else "")
        self._clear_layout(self.positive_layout)
        self._clear_layout(self.negative_layout)
        self._clear_layout(self.features_layout)

        if not xai.available:
            self.lbl_unavailable.setVisible(True)
            self.lbl_pos_title.setVisible(False)
            self.lbl_neg_title.setVisible(False)
            self.txt_explanation.setText(self._clean_text(text) or L10N.BU_MODEL_ICIN_XAI_ACIKLANABILIRLIK)
            self._set_caveat(self._clean_text(xai.caveat))
            return

        self._populate_xai_views(positive_reasons, negative_reasons, features)
        self.txt_explanation.setText(self._clean_text(text))
        self._set_caveat(self._clean_text(xai.caveat))

    def reset(self):
        self._clear_layout(self.positive_layout)
        self._clear_layout(self.negative_layout)
        self._clear_layout(self.features_layout)
        self.txt_explanation.clear()
        self.lbl_method.setText("")
        self.lbl_caveat.setVisible(False)
        self.lbl_unavailable.setVisible(False)

    def _build_factor_header_row(self, name, feature_name, direction, group, bar_val) -> QHBoxLayout:
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
        return header

    def _make_factor_row(self, item, direction: str) -> QWidget:
        name = self._item_value(item, "human_label") or self._item_value(item, "feature_name") or "-"
        feature_name = self._item_value(item, "feature_name") or name
        reason = self._item_value(item, "reason") or ""
        group = self._group_label(self._item_value(item, "feature_group"))
        method = self._method_label(self._item_value(item, "method"))
        contribution = self._item_value(item, "contribution")
        approximate = self._item_value(item, "approximate")
        importance = self._safe_float(self._item_value(item, "importance"))
        bar_val = min(abs(importance) * 100 if abs(importance) <= 1.0 else abs(importance), 100)
        wrapper = QFrame()
        wrapper.setProperty("cssClass", "xaiFactorRow")
        outer = QVBoxLayout(wrapper)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(4)
        outer.addLayout(self._build_factor_header_row(name, feature_name, direction, group, bar_val))
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
        if reason:
            friendly_reason = reason.replace("volatilite", "dalgalanma").replace("esigi", "sınırı").replace("eşiği", "sınırı")
            return friendly_reason
        return ""

    @staticmethod
    def _group_label(group: str | None) -> str:
        labels = {
            "technical": "Grafik ve Fiyat Eğilimleri",
            "macro": "Genel Ekonomik Göstergeler (Dolar, Faiz vb.)",
            "market_relative": "Borsa Endeksi ile İlişki",
            "volume": "İşlem Hacmi (Yatırımcı İlgisi)",
            "volatility": "Dalgalanma Riski",
            "regime": "Piyasa Dönemi ve Rejimi",
            "lag": "Geçmiş Fiyat Seviyeleri",
            "signal": "Yapay Zeka Karar Kuralı",
            L10N.SINYAL_KARARI: "Yapay Zeka Karar Kuralı",
            "model_summary": "Yapay Zeka Genel Eğilimi",
            "other": "Diğer Faktörler",
        }
        if not group:
            return ""
        return labels.get(str(group), str(group))

    @staticmethod
    def _method_label(method: str | None) -> str:
        labels = {
            "rule_based": "Kural Tabanlı Analiz",
            "signal_rules": "Tahmin Kuralları",
            "sequence": "Zaman Serisi Analizi",
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

    @staticmethod
    def _friendly_method(method: str | None) -> str:
        if not method:
            return ""
        m_lower = method.lower().replace("\n", " ").strip()
        if "shap" in m_lower or "treeexplainer" in m_lower:
            return "Yapay Zeka Karar Analizi"
        if "feature importance" in m_lower:
            return "Gösterge Ağırlık Analizi"
        if "demo" in m_lower:
            return "Demo Analiz"
        return method

    @staticmethod
    def _clean_text(text: str) -> str:
        if not text:
            return ""
        import re
        # 1. Remove bracketed technical keys like [model_summary] or [Sinyal karari]
        text = re.sub(r'\s*\[[^\]]+\]', '', text)

        # 2. Fix Turkish character replacements from raw data and simplify terms
        replacements = {
            "walk-forward": "tarihsel test",
            "volatilite": "dalgalanma",
            "Volatilite": "Dalgalanma",
            "esigi": "sınırı",
            "eşiği": "sınırı",
            "esiginin": "sınırının",
            "eşiğinin": "sınırının",
            "cikis": "çıkış",
            "çıkış": "çıkış",
            "cikildi": "çıkıldı",
            "al sinyali": "alım kararı",
            "sat sinyali": "satım kararı",
            "giris": "giriş",
            "nakitte bekleme": "nakit koruma",
            "tahmini fiyat": "beklenen fiyat",
            "Tahmini fiyat": "Beklenen fiyat",
            "XAI, modelin tahmininde öne çıkan değişkenleri gösterir; nedensellik kanıtı değildir.":
                "Bu liste, yapay zekanın tahmin yaparken en çok önem verdiği nedenleri gösterir; kesin bir sebep-sonuç ilişkisi anlamına gelmez."
        }
        for k, v in replacements.items():
            text = text.replace(k, v)

        # 3. Format float numbers dynamically (e.g. 26.8850 -> 26.89)
        def format_match(match):
            val_str = match.group(0)
            try:
                val = float(val_str)
                if abs(val) < 0.1 and val != 0.0:
                    return f"%{val*100:+.2f}"
                return f"{val:.2f}"
            except ValueError:
                return val_str

        text = re.sub(r'-?\d+\.\d{3,}', format_match, text)

        # Double periods cleanup
        text = text.replace("..", ".").replace(" .", ".")
        return text
