from src.ui.shared.locale_tr import L10N
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QVBoxLayout,
    QWidget,
)
from src.ui.core.icon_manager import IconManager


class PeerCard(QWidget):
    """Kol-B (pooled global model) akran karşılaştırma kartı.

    Cross-sectional sıra (percentile/label), segment, kalibre trend eğilimi ve
    per-symbol sıra sürücüleri (Kol-B XAI). Peer yoksa kart gizlenir.
    """

    _PEER_LABEL_TR = {
        "outperform": "Akrandan iyi",
        "inline": "Akranla uyumlu",
        "underperform": "Akrandan zayıf",
        "unknown": "Belirsiz",
    }
    _CONF_TR = {"high": "Yüksek", "medium": "Orta", "low": "Düşük"}

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        self.setProperty("cssClass", "aiCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(8)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        lbl_icon = QLabel()
        lbl_icon.setPixmap(IconManager.get_icon("bar-chart-2", color="@COLOR_PRIMARY").pixmap(20, 20))
        title = QLabel(L10N.PEER_BASLIK)
        title.setProperty("cssClass", "cardLabel")
        self.lbl_as_of = QLabel("")
        self.lbl_as_of.setProperty("cssClass", "aiMetaText")
        header.addWidget(lbl_icon)
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.lbl_as_of)
        layout.addLayout(header)

        self.lbl_unavailable = QLabel(L10N.PEER_VERISI_YOK)
        self.lbl_unavailable.setAlignment(Qt.AlignCenter)
        self.lbl_unavailable.setProperty("cssClass", "aiHintText")
        self.lbl_unavailable.setVisible(False)
        layout.addWidget(self.lbl_unavailable)

        # Sıra + etiket
        rank_layout = QHBoxLayout()
        self.lbl_rank = QLabel("")
        self.lbl_rank.setProperty("cssClass", "aiPrimaryText")
        self.lbl_label = QLabel("")
        self.lbl_label.setAlignment(Qt.AlignCenter)
        self.lbl_label.setProperty("cssClass", "trendBadge")
        rank_layout.addWidget(self.lbl_rank)
        rank_layout.addStretch()
        rank_layout.addWidget(self.lbl_label)
        layout.addLayout(rank_layout)

        self.lbl_universe = QLabel("")
        self.lbl_universe.setProperty("cssClass", "aiMetaText")
        layout.addWidget(self.lbl_universe)

        self.lbl_segment = QLabel("")
        self.lbl_segment.setProperty("cssClass", "aiMetaText")
        self.lbl_segment.setWordWrap(True)
        layout.addWidget(self.lbl_segment)

        self.lbl_trend = QLabel("")
        self.lbl_trend.setProperty("cssClass", "aiStrongMetaText")
        self.lbl_trend.setWordWrap(True)
        layout.addWidget(self.lbl_trend)

        self.lbl_confidence = QLabel("")
        self.lbl_confidence.setProperty("cssClass", "aiMetaText")
        layout.addWidget(self.lbl_confidence)

        # Kol-B XAI sürücüleri
        self.lbl_xai_title = QLabel(L10N.PEER_XAI_BASLIK)
        self.lbl_xai_title.setProperty("cssClass", "xaiSectionTitle")
        self.lbl_xai_title.setVisible(False)
        layout.addWidget(self.lbl_xai_title)

        self.xai_layout = QVBoxLayout()
        self.xai_layout.setSpacing(4)
        layout.addLayout(self.xai_layout)

        self.lbl_caveat = QLabel("")
        self.lbl_caveat.setProperty("cssClass", "aiHintText")
        self.lbl_caveat.setWordWrap(True)
        self.lbl_caveat.setVisible(False)
        layout.addWidget(self.lbl_caveat)

    def update_data(self, peer) -> None:
        """PeerInfo ile kartı günceller. peer None/available=False ise kartı gizler."""
        self._clear_layout(self.xai_layout)
        if peer is None or not getattr(peer, "available", False):
            self.setVisible(False)
            return
        self.setVisible(True)

        self.lbl_as_of.setText(
            L10N.PEER_AS_OF_TMPL.format(date=peer.as_of_date) if peer.as_of_date else ""
        )

        if peer.peer_percentile is not None:
            self.lbl_rank.setText(L10N.PEER_SIRA_TMPL.format(percentile=f"{peer.peer_percentile:.0f}"))
        elif peer.peer_score is not None:
            self.lbl_rank.setText(L10N.PEER_SKOR_TMPL.format(score=f"{peer.peer_score:+.3f}"))
        else:
            self.lbl_rank.setText("")

        label_tr = self._PEER_LABEL_TR.get(str(peer.peer_label or ""), peer.peer_label or "")
        self.lbl_label.setText(label_tr)
        state = {"outperform": "up", "underperform": "down"}.get(str(peer.peer_label or ""), "neutral")
        self.lbl_label.setProperty("cssState", state)
        self.lbl_label.setVisible(bool(label_tr))
        self.lbl_label.style().unpolish(self.lbl_label)
        self.lbl_label.style().polish(self.lbl_label)

        if peer.universe_size:
            self.lbl_universe.setText(L10N.PEER_EVREN_TMPL.format(size=peer.universe_size))
            self.lbl_universe.setVisible(True)
        else:
            self.lbl_universe.setVisible(False)

        if peer.segment_liq or peer.segment_vol or peer.segment_sector:
            self.lbl_segment.setText(
                L10N.PEER_SEGMENT_TMPL.format(
                    liq=peer.segment_liq or "-",
                    vol=peer.segment_vol or "-",
                    sector=peer.segment_sector or "-",
                )
            )
            self.lbl_segment.setVisible(True)
        else:
            self.lbl_segment.setVisible(False)

        if peer.trend_label and peer.trend_prob_up is not None:
            ret = peer.trend_expected_return
            ret_txt = f"{ret * 100:+.2f}%" if ret is not None else "-"
            self.lbl_trend.setText(
                L10N.PEER_TREND_TMPL.format(
                    trend=peer.trend_label,
                    prob=f"{peer.trend_prob_up * 100:.0f}",
                    label="h-gün",
                    ret=ret_txt,
                )
            )
            self.lbl_trend.setVisible(True)
        else:
            self.lbl_trend.setVisible(False)

        if peer.confidence_label:
            conf_tr = self._CONF_TR.get(str(peer.confidence_label), peer.confidence_label)
            self.lbl_confidence.setText(L10N.PEER_GUVEN_TMPL.format(label=conf_tr))
            self.lbl_confidence.setVisible(True)
        else:
            self.lbl_confidence.setVisible(False)

        # Kol-B XAI sürücüleri (kompakt metin satırları)
        rows_added = False
        if peer.xai_available:
            for item in (peer.xai_top_positive or [])[:3]:
                self.xai_layout.addWidget(self._make_driver_row(item, "up"))
                rows_added = True
            for item in (peer.xai_top_negative or [])[:3]:
                self.xai_layout.addWidget(self._make_driver_row(item, "down"))
                rows_added = True
        self.lbl_xai_title.setVisible(rows_added)

        caveat = peer.xai_caveat if peer.xai_available else ""
        if caveat:
            self.lbl_caveat.setText(f"ℹ {caveat}")
            self.lbl_caveat.setVisible(True)
        else:
            self.lbl_caveat.setVisible(False)

    def reset(self) -> None:
        self._clear_layout(self.xai_layout)
        self.lbl_rank.setText("")
        self.lbl_label.setText("")
        self.lbl_universe.setText("")
        self.lbl_segment.setText("")
        self.lbl_trend.setText("")
        self.lbl_confidence.setText("")
        self.lbl_as_of.setText("")
        self.lbl_caveat.setVisible(False)
        self.lbl_xai_title.setVisible(False)
        self.lbl_unavailable.setVisible(False)
        self.setVisible(False)

    def _make_driver_row(self, item, direction: str) -> QWidget:
        name = self._item_value(item, "human_label") or self._item_value(item, "feature_name") or "-"
        reason = self._item_value(item, "reason") or ""
        icon = "🟢" if direction == "up" else "🔴"
        text = f"{icon} {name}"
        if reason:
            text += f" — {reason}"
        lbl = QLabel(text)
        lbl.setWordWrap(True)
        lbl.setProperty("cssClass", "xaiFactorReason")
        return lbl

    @staticmethod
    def _item_value(item, key: str):
        if isinstance(item, dict):
            return item.get(key)
        return getattr(item, key, None)

    def _clear_layout(self, layout) -> None:
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
