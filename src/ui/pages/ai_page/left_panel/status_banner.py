from src.ui.shared.locale_tr import L10N
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt


class StatusBanner(QWidget):
    """
    API bağlantı durumu ve analiz durumunu gösteren banner widget'ı.

    Duruma göre renk ve ikon değişir:
    - API bağlı   → yeşil banner
    - Mock mod     → sarı banner
    - Hata / eski veri → kırmızı/turuncu banner
    """

    # ── analysis_status → (emoji, metin, css state) eşlemesi ─────────
    _STATUS_MAP = {
        "ok":               ("✅", L10N.ANALIZ_BASARILI_VERILER_GUNCEL, "success"),
        "stale_data":       ("⏳", L10N.DIKKAT_PIYASA_VERISI_ESKI_TAHMINLER, "warning"),
        "no_model":         ("❌", L10N.BU_HISSE_ICIN_KAYITLI_MODEL, "error"),
        "no_forecast":      ("📭", L10N.MODEL_MEVCUT_AMA_TAHMIN_URETILMEMIS, "warning"),
        "low_confidence":   ("⚠️", L10N.SONUC_MEVCUT_ANCAK_GUVEN_DUZEYI, "warning"),
        "xai_unavailable":  ("🔍", L10N.TAHMIN_MEVCUT_AMA_ACIKLANABILIRLIK_XAI, "warning"),
        "error":            ("💥", L10N.BEKLENMEYEN_BIR_HATA_OLUSTU, "error"),
    }

    def __init__(self) -> None:
        super().__init__()
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)

        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedWidth(24)
        self.lbl_icon.setAlignment(Qt.AlignCenter)

        self.lbl_text = QLabel()
        self.lbl_text.setWordWrap(True)
        self.lbl_text.setProperty("cssClass", "bannerText")

        layout.addWidget(self.lbl_icon)
        layout.addWidget(self.lbl_text, 1)

        # Varsayılan: gizli
        self.setVisible(False)
        self.setProperty("cssClass", "statusBanner")

    # ─── API Bağlantı Durumu ────────────────────────────────────────────

    def show_connecting(self) -> None:
        """Bağlantı denenirken nötr/bekleme banner'ı gösterir."""
        self._apply("⏳", L10N.YAPAY_ZEKA_MOTORUNA_BAGLANILIYOR_LUTFEN, "warning")

    def show_api_connected(self) -> None:
        """API başarıyla bağlandığında yeşil banner gösterir."""
        self._apply("✓", L10N.AI_CORE_MODELI_BAGLI, "success")

    def show_mock_mode(self) -> None:
        """MockAdapter etkinken sarı uyarı gösterir."""
        self._apply("⚠", L10N.MODEL_HENUZ_BAGLI_DEGIL_DEMO, "warning")

    # ─── Analiz Durumu ─────────────────────────────────────────────────

    def show_analysis_status(self, status: str, staleness_days: int = 0) -> None:
        """API'den dönen analysis_status'e göre banner'ı günceller."""
        icon, text, state = self._STATUS_MAP.get(
            status, ("❓", f"Bilinmeyen durum: {status}", "warning")
        )

        if status == "stale_data" and staleness_days > 0:
            text += f" ({staleness_days} işlem günü geride)"

        self._apply(icon, text, state)

    def show_error(self, message: str) -> None:
        """Genel hata mesajı gösterir."""
        self._apply("💥", message, "error")

    # ─── Internal ──────────────────────────────────────────────────────

    def _apply(self, icon: str, text: str, state: str) -> None:
        self.lbl_icon.setText(icon)
        self.lbl_text.setText(text)
        self.setProperty("cssState", state)
        self.style().unpolish(self)
        self.style().polish(self)
        self.setVisible(True)
