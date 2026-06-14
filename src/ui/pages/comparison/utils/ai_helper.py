from src.ui.shared.locale_tr import L10N
# src/ui/pages/comparison/utils/ai_helper.py
"""AI yorum paneli widget kurulumu ve Gemini worker yönetimi."""

import logging
from src.qt_compat.qtcore import Qt, QCoreApplication, QSize, QThreadPool
from src.qt_compat.qtwidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QSizePolicy, QTextBrowser, QVBoxLayout,
)
from src.qt_compat.qtwidgets import QMessageBox

from src.domain.models.ai_analysis import ChatMessage, MessageRole
from src.ui.worker import Worker

logger = logging.getLogger(__name__)


def _collect_table_rows(table) -> list:
    rows = []
    for row in range(table.rowCount()):
        name  = (table.item(row, 0) or type("", (), {"text": lambda: ""})()).text()
        start = (table.item(row, 1) or type("", (), {"text": lambda: ""})()).text()
        end   = (table.item(row, 2) or type("", (), {"text": lambda: ""})()).text()
        ret   = (table.item(row, 3) or type("", (), {"text": lambda: ""})()).text()
        if name:
            rows.append(f"- **{name}**: Başlangıç: {start}, Dönem Sonu: {end}, Getiri: {ret}")
    return rows


def _build_commentary_prompt(table_rows: list, start_date, end_date, mode: str) -> str:
    assets_info = "\n".join(table_rows)
    return (
        f"Kullanıcı Karşılaştırma Laboratuvarı ekranında "
        f"{start_date.strftime('%d.%m.%Y')} ile {end_date.strftime('%d.%m.%Y')} "
        f"tarihleri arasında {mode} biçiminde aşağıdaki varlıkların performanslarını kıyaslıyor:\n\n"
        f"{assets_info}\n\n"
        "Ayrıca bu dönemde seçili varlıkların drawdown ve risk-getiri saçılım grafikleri de oluşturulmuştur.\n"
        "Bir finansal analist olarak, bu karşılaştırmayı detaylı ve profesyonelce yorumla:\n"
        "1. Dönemin en başarılı varlığı hangisidir ve neden öne çıkmıştır?\n"
        "2. Drawdown ve volatilite açısından en riskli ve en güvenli varlık hangisidir?\n"
        "3. Portföy çeşitlendirmesi için 2-3 pratik öneride bulun.\n\n"
        + L10N.NOT_YATIRIM_TAVSIYESI_VERMEDEN_VERIYE
    )


def _build_ai_panel_title_row() -> QHBoxLayout:
    from src.ui.core.icon_manager import IconManager
    title_row = QHBoxLayout()
    icon_lbl = QLabel()
    icon_lbl.setPixmap(
        IconManager.get_icon("bot", color="#38bdf8", size=QSize(28, 28)).pixmap(28, 28)
    )
    title_lbl = QLabel(L10N.YAPAY_ZEKA_RAPOR_VE_ANALIZ)
    title_lbl.setProperty("cssClass", "comparisonAiTitle")
    title_row.addWidget(icon_lbl)
    title_row.addWidget(title_lbl)
    title_row.addStretch()
    return title_row


def _build_ai_browser_widget(page, fit_cb) -> "QTextBrowser":
    browser = QTextBrowser()
    browser.setFrameShape(QFrame.NoFrame)
    browser.setReadOnly(True)
    browser.setOpenExternalLinks(True)
    browser.setProperty("cssClass", "comparisonAiBrowser")
    browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    browser.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
    browser.setMinimumHeight(0)
    browser.setVisible(False)
    browser.setFocusPolicy(Qt.NoFocus)
    browser.document().contentsChanged.connect(fit_cb)
    page.ai_browser = browser
    return browser


class AICommentaryHelper:
    """AI yorum paneli widget'larını oluşturur ve Gemini Worker'ı yönetir."""

    def __init__(self, page, chat_service) -> None:
        self.page = page
        self._chat_service = chat_service
        self.ai_worker = None
        self._threadpool = QThreadPool.globalInstance()
        self._request_seq = 0

    # ------------------------------------------------------------------
    # Panel kurulumu
    # ------------------------------------------------------------------

    def build_panel(self) -> QFrame:
        page = self.page
        panel = QFrame()
        panel.setProperty("cssClass", "comparisonAiPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)
        layout.addLayout(_build_ai_panel_title_row())
        desc = QLabel(
            L10N.KARSILASTIRMA_EKRANINDA_SECILEN_TUM_VARLIKLARIN +
            L10N.GETIRI_VOLATILITE_DRAWDOWN_GEMINI_YAPAY +
            L10N.SEKILDE_YORUMLANMASINI_SAGLAMAK_ICIN_ASAGIDAKI
        )
        desc.setWordWrap(True)
        desc.setProperty("cssClass", "comparisonAiDescription")
        layout.addWidget(desc)
        page.ai_btn = QPushButton(L10N.YAPAY_ZEKA_YORUMU_OLUSTUR)
        page.ai_btn.setMinimumHeight(38)
        page.ai_btn.setMinimumWidth(200)
        page.ai_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        page.ai_btn.setFocusPolicy(Qt.NoFocus)
        page.ai_btn.setProperty("cssClass", "comparisonAiButton")
        page.ai_btn.clicked.connect(page._generate_ai_commentary)
        layout.addWidget(page.ai_btn)
        page.ai_progress = QProgressBar()
        page.ai_progress.setTextVisible(False)
        page.ai_progress.setRange(0, 0)
        page.ai_progress.setFixedHeight(4)
        page.ai_progress.setProperty("cssClass", "comparisonAiProgress")
        page.ai_progress.setVisible(False)
        layout.addWidget(page.ai_progress)
        layout.addWidget(_build_ai_browser_widget(page, self._fit_ai_browser_to_content))
        page.ai_panel = panel
        return panel

    # ------------------------------------------------------------------
    # Yorum üretimi
    # ------------------------------------------------------------------

    def generate_commentary(self) -> None:
        table_rows = _collect_table_rows(self.page.summary_table)
        if not table_rows:
            QMessageBox.warning(self.page, "Uyarı", L10N.ANALIZ_EDILECEK_VERI_BULUNAMADI_LUTFEN)
            return
        start_date, end_date = self.page.ribbon_bar.date_range()
        mode = self.page.ribbon_bar.selected_mode()
        prompt = _build_commentary_prompt(table_rows, start_date, end_date, mode)
        system_msg = ChatMessage(role=MessageRole.SYSTEM, content=L10N.SEN_PROFESYONEL_BIR_BIST_VE)
        user_msg = ChatMessage(role=MessageRole.USER, content=prompt)
        scroll_bar = self.page.scroll_area.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        self.page.ai_btn.setEnabled(False)
        self.page.ai_btn.setText(L10N.YAPAY_ZEKA_ANALIZ_EDIYOR)
        self.page.ai_progress.setVisible(True)
        self.page.ai_browser.setMarkdown(L10N.ANALIZ_HAZIRLANIYOR_LUTFEN_BEKLEYIN)
        self.page.ai_browser.setVisible(True)
        self._fit_ai_browser_to_content()
        QCoreApplication.processEvents()
        scroll_bar.setValue(scroll_pos)
        self._request_seq += 1
        request_id = self._request_seq
        self.ai_worker = Worker(self._chat_service.generate, [system_msg, user_msg])
        self.ai_worker.signals.result.connect(
            lambda response, rid=request_id: self._on_ai_response_ready(rid, response)
        )
        self.ai_worker.signals.error.connect(
            lambda err, rid=request_id: self._on_ai_error(rid, err)
        )
        self._threadpool.start(self.ai_worker)

    def _on_ai_response_ready(self, request_id: int, response_text: str) -> None:
        if request_id != self._request_seq:
            return
        scroll_bar = self.page.scroll_area.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        self.page.ai_btn.setEnabled(True)
        self.page.ai_btn.setText(L10N.YAPAY_ZEKA_YORUMU_OLUSTUR)
        self.page.ai_progress.setVisible(False)
        try:
            self.page.ai_browser.setMarkdown(response_text)
        except Exception:
            self.page.ai_browser.setPlainText(response_text)
        self.page.ai_browser.setVisible(True)
        self._fit_ai_browser_to_content()
        QCoreApplication.processEvents()
        scroll_bar.setValue(scroll_pos)

    def _on_ai_error(self, request_id: int, err_tuple) -> None:
        if request_id != self._request_seq:
            return
        scroll_bar = self.page.scroll_area.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        self.page.ai_btn.setEnabled(True)
        self.page.ai_btn.setText(L10N.YAPAY_ZEKA_YORUMU_OLUSTUR)
        self.page.ai_progress.setVisible(False)
        error_html = (
            f"<div style='color: #ef4444; font-weight: bold;'>Yapay Zeka Hatasi:</div>"
            f"<div style='color: #f8fafc; margin-top: 8px;'>{err_tuple[1]}</div>"
        )
        self.page.ai_browser.setHtml(error_html)
        self.page.ai_browser.setVisible(True)
        self._fit_ai_browser_to_content()
        QCoreApplication.processEvents()
        scroll_bar.setValue(scroll_pos)

    def _fit_ai_browser_to_content(self) -> None:
        """QTextBrowser içeriğini kendi içinde scroll üretmeden sayfa akışına yayar."""
        browser = getattr(self.page, "ai_browser", None)
        if browser is None:
            return
        viewport_width = max(320, browser.viewport().width())
        browser.document().setTextWidth(viewport_width)
        content_height = int(browser.document().size().height())
        browser.setMinimumHeight(max(120, content_height + 56))
        browser.updateGeometry()

    def cleanup(self) -> None:
        """Sayfa kapanırken bekleyen worker sonucunu geçersiz kılar."""
        self._request_seq += 1
        self.ai_worker = None
