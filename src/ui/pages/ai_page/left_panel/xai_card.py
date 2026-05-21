from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QHBoxLayout, QProgressBar, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt


class XAICard(QWidget):
    """
    Model açıklanabilirliği (Explainable AI) kartı.
    Pozitif ve negatif faktörleri ayrı gruplar halinde gösterir.
    """

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "aiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)

        # Başlık satırı
        header_layout = QHBoxLayout()
        title = QLabel("🔍 MODEL AÇIKLAMASI (XAI)")
        title.setProperty("cssClass", "cardLabel")
        self.lbl_method = QLabel("")
        self.lbl_method.setProperty("cssClass", "dateLabelMuted")
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.lbl_method)
        layout.addLayout(header_layout)

        # XAI mevcut değil mesajı
        self.lbl_unavailable = QLabel("XAI verisi mevcut değil")
        self.lbl_unavailable.setAlignment(Qt.AlignCenter)
        self.lbl_unavailable.setProperty("cssClass", "dateLabelMuted")
        self.lbl_unavailable.setVisible(False)
        layout.addWidget(self.lbl_unavailable)

        # ── Yukarı çeken faktörler ──────────────────────────────────────
        self.lbl_pos_title = QLabel("📈 Fiyatı Yukarı Çeken Faktörler")
        self.lbl_pos_title.setProperty("cssClass", "xaiSectionTitle")
        layout.addWidget(self.lbl_pos_title)

        self.positive_layout = QVBoxLayout()
        self.positive_layout.setSpacing(3)
        layout.addLayout(self.positive_layout)

        # ── Ayraç ──────────────────────────────────────────────────────
        line = QWidget()
        line.setFixedHeight(1)
        line.setProperty("cssClass", "horizontalDivider")
        layout.addWidget(line)

        # ── Aşağı iten faktörler ────────────────────────────────────────
        self.lbl_neg_title = QLabel("📉 Fiyata Aşağı Baskı Yapan Faktörler")
        self.lbl_neg_title.setProperty("cssClass", "xaiSectionTitle")
        layout.addWidget(self.lbl_neg_title)

        self.negative_layout = QVBoxLayout()
        self.negative_layout.setSpacing(3)
        layout.addLayout(self.negative_layout)

        # ── Eski uyumluluk: genel özellik barları ──────────────────────
        self.features_layout = QVBoxLayout()
        self.features_layout.setSpacing(3)
        layout.addLayout(self.features_layout)

        # ── Ayraç ──────────────────────────────────────────────────────
        line2 = QWidget()
        line2.setFixedHeight(1)
        line2.setProperty("cssClass", "horizontalDivider")
        layout.addWidget(line2)

        # ── Metin açıklama ─────────────────────────────────────────────
        self.txt_explanation = QTextEdit()
        self.txt_explanation.setReadOnly(True)
        self.txt_explanation.setProperty("cssClass", "aiTextEdit")
        self.txt_explanation.setFixedHeight(80)
        layout.addWidget(self.txt_explanation)

        # ── Caveat / uyarı ─────────────────────────────────────────────
        self.lbl_caveat = QLabel("")
        self.lbl_caveat.setProperty("cssClass", "dateLabelMuted")
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
        """
        Kartı API verileriyle günceller.

        Args:
            features: {feature_label: importance} dict (eski uyumluluk)
            text: Metin açıklama
            xai_available: XAI verisi var mı?
            xai_method: Kullanılan XAI yöntemi (örn: SHAP TreeExplainer)
            positive_reasons: [{feature_name, human_label, importance, direction}]
            negative_reasons: [{feature_name, human_label, importance, direction}]
            xai_caveat: Uyarı metni
        """
        # XAI yöntemi
        if xai_method:
            self.lbl_method.setText(f"Yöntem: {xai_method}")

        # XAI mevcut değilse
        if not xai_available:
            self.lbl_unavailable.setVisible(True)
            self.lbl_pos_title.setVisible(False)
            self.lbl_neg_title.setVisible(False)
            self.txt_explanation.setText(text or "Bu model için XAI açıklanabilirlik verisi üretilmemiş.")
            if xai_caveat:
                self.lbl_caveat.setText(f"ℹ {xai_caveat}")
                self.lbl_caveat.setVisible(True)
            return

        self.lbl_unavailable.setVisible(False)
        self.lbl_pos_title.setVisible(True)
        self.lbl_neg_title.setVisible(True)

        # ── Pozitif faktörler ────────────────────────────────────────────
        self._clear_layout(self.positive_layout)
        if positive_reasons:
            for item in positive_reasons:
                # XaiFactorItem veya dict olabilir
                name = getattr(item, "human_label", None) or item.get("human_label", "")
                importance = getattr(item, "importance", None)
                if importance is None:
                    importance = item.get("importance", 0)
                widget = self._make_factor_row(name, importance, "positive")
                self.positive_layout.addWidget(widget)

        # ── Negatif faktörler ────────────────────────────────────────────
        self._clear_layout(self.negative_layout)
        if negative_reasons:
            for item in negative_reasons:
                name = getattr(item, "human_label", None) or item.get("human_label", "")
                importance = getattr(item, "importance", None)
                if importance is None:
                    importance = item.get("importance", 0)
                widget = self._make_factor_row(name, importance, "negative")
                self.negative_layout.addWidget(widget)

        # ── Eski uyumluluk: genel features dict ─────────────────────────
        self._clear_layout(self.features_layout)
        if not positive_reasons and not negative_reasons and features:
            # Eski format: düz features dict kullan
            self.lbl_pos_title.setVisible(False)
            self.lbl_neg_title.setVisible(False)
            for name, value in features.items():
                widget = self._make_factor_row(name, value, "neutral")
                self.features_layout.addWidget(widget)

        self.txt_explanation.setText(text)

        if xai_caveat:
            self.lbl_caveat.setText(f"ℹ {xai_caveat}")
            self.lbl_caveat.setVisible(True)
        else:
            self.lbl_caveat.setVisible(False)

    def reset(self):
        self._clear_layout(self.positive_layout)
        self._clear_layout(self.negative_layout)
        self._clear_layout(self.features_layout)
        self.txt_explanation.clear()
        self.lbl_method.setText("")
        self.lbl_caveat.setVisible(False)
        self.lbl_unavailable.setVisible(False)

    # ── Yardımcılar ────────────────────────────────────────────────────

    def _make_factor_row(self, name: str, importance: float, direction: str) -> QWidget:
        """Tek bir XAI faktör satırı oluşturur."""
        row = QHBoxLayout()

        # Yön ikonu
        icon_map = {"positive": "🟢", "negative": "🔴", "neutral": "⚪"}
        lbl_icon = QLabel(icon_map.get(direction, "⚪"))
        lbl_icon.setFixedWidth(20)

        lbl = QLabel(name)
        lbl.setFixedWidth(140)
        lbl.setProperty("cssClass", "dateLabelMuted")

        bar = QProgressBar()
        bar.setRange(0, 100)
        # importance 0-1 arası olabilir (SHAP) veya 0-100 arası
        bar_val = importance * 100 if importance <= 1.0 else importance
        bar.setValue(int(min(bar_val, 100)))
        bar.setTextVisible(True)
        bar.setFixedHeight(14)

        css_map = {"positive": "aiProgressGreen", "negative": "aiProgressRed", "neutral": "aiProgressBlue"}
        bar.setProperty("cssClass", css_map.get(direction, "aiProgressBlue"))

        row.addWidget(lbl_icon)
        row.addWidget(lbl)
        row.addWidget(bar)

        wrapper = QWidget()
        wrapper.setLayout(row)
        wrapper.setProperty("cssClass", "borderlessFrame")
        row.setContentsMargins(0, 0, 0, 0)
        return wrapper

    def _clear_layout(self, layout) -> None:
        """Layout içindeki tüm widget'ları temizler."""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
