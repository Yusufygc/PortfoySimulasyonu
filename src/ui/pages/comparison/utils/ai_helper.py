# src/ui/pages/comparison/utils/ai_helper.py
"""AI yorum paneli widget kurulumu ve Gemini worker yönetimi."""

import logging
from PyQt5.QtCore import Qt, QCoreApplication, QSize
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QProgressBar, QPushButton,
    QSizePolicy, QTextBrowser, QVBoxLayout,
)
from PyQt5.QtWidgets import QMessageBox

from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole
from src.ui.pages.ai_page.core.gemini_service import GeminiWorker

logger = logging.getLogger(__name__)


class AICommentaryHelper:
    """AI yorum paneli widget'larını oluşturur ve Gemini Worker'ı yönetir."""

    def __init__(self, page) -> None:
        self.page = page
        self.ai_worker = None

    # ------------------------------------------------------------------
    # Panel kurulumu
    # ------------------------------------------------------------------

    def build_panel(self) -> QFrame:
        """
        AI yorum paneli QFrame'ini oluşturur ve page'e widget referanslarını bağlar.
        Döndürülen frame scroll layout'a eklenir.
        """
        page = self.page
        panel = QFrame()
        panel.setProperty("cssClass", "panelFramePadded")
        panel.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # Başlık
        title_row = QHBoxLayout()
        from src.ui.core.icon_manager import IconManager
        icon_lbl = QLabel()
        icon_lbl.setPixmap(
            IconManager.get_icon("bot", color="#38bdf8", size=QSize(28, 28)).pixmap(28, 28)
        )
        title_lbl = QLabel("Yapay Zeka Rapor ve Analiz Asistanı")
        title_lbl.setStyleSheet("color: #38bdf8; font-size: 18px; font-weight: bold;")
        title_row.addWidget(icon_lbl)
        title_row.addWidget(title_lbl)
        title_row.addStretch()
        layout.addLayout(title_row)

        # Açıklama
        desc = QLabel(
            "Karşılaştırma ekranında seçilen tüm varlıkların ve hesaplanan metriklerin "
            "(getiri, volatilite, drawdown) Gemini yapay zeka modeli ile kapsamlı bir "
            "şekilde yorumlanmasını sağlamak için aşağıdaki butona tıklayın."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 14px; line-height: 1.4;")
        layout.addWidget(desc)

        # Buton
        page.ai_btn = QPushButton("Yapay Zeka Yorumu Oluştur")
        page.ai_btn.setMinimumHeight(38)
        page.ai_btn.setMinimumWidth(200)
        page.ai_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        page.ai_btn.setFocusPolicy(Qt.NoFocus)
        page.ai_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7; color: white; font-weight: bold;
                border-radius: 6px; padding: 8px 16px; border: none;
            }
            QPushButton:hover { background-color: #0369a1; }
            QPushButton:disabled { background-color: #334155; color: #64748b; }
        """)
        page.ai_btn.clicked.connect(page._generate_ai_commentary)
        layout.addWidget(page.ai_btn)

        # Progress bar
        page.ai_progress = QProgressBar()
        page.ai_progress.setTextVisible(False)
        page.ai_progress.setRange(0, 0)
        page.ai_progress.setFixedHeight(4)
        page.ai_progress.setStyleSheet("""
            QProgressBar { border: none; background-color: #1e293b; border-radius: 2px; }
            QProgressBar::chunk { background-color: #38bdf8; border-radius: 2px; }
        """)
        page.ai_progress.setVisible(False)
        layout.addWidget(page.ai_progress)

        # Browser
        page.ai_browser = QTextBrowser()
        page.ai_browser.setFrameShape(QFrame.NoFrame)
        page.ai_browser.setReadOnly(True)
        page.ai_browser.setOpenExternalLinks(True)
        page.ai_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #1e293b; color: #f8fafc;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 18px; line-height: 1.6;
                border-radius: 8px; padding: 24px;
                border: 1px solid #38bdf8;
            }
        """)
        page.ai_browser.setMinimumHeight(400)
        page.ai_browser.setVisible(False)
        page.ai_browser.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(page.ai_browser)

        page.ai_panel = panel
        return panel

    # ------------------------------------------------------------------
    # Yorum üretimi
    # ------------------------------------------------------------------

    def generate_commentary(self) -> None:
        """Özet tablodan veri toplayarak Gemini'ye analiz promptu gönderir."""
        table_rows = []
        table = self.page.summary_table
        for row in range(table.rowCount()):
            name  = (table.item(row, 0) or type("", (), {"text": lambda: ""})()).text()
            start = (table.item(row, 1) or type("", (), {"text": lambda: ""})()).text()
            end   = (table.item(row, 2) or type("", (), {"text": lambda: ""})()).text()
            ret   = (table.item(row, 3) or type("", (), {"text": lambda: ""})()).text()
            if name:
                table_rows.append(
                    f"- **{name}**: Başlangıç: {start}, Dönem Sonu: {end}, Getiri: {ret}"
                )

        if not table_rows:
            QMessageBox.warning(
                self.page, "Uyarı",
                "Analiz edilecek veri bulunamadı. Lütfen varlıkları seçip grafikleri güncelleyin."
            )
            return

        start_date, end_date = self.page.ribbon_bar.date_range()
        mode = self.page.ribbon_bar.selected_mode()
        assets_info = "\n".join(table_rows)

        prompt = (
            f"Kullanıcı Karşılaştırma Laboratuvarı ekranında "
            f"{start_date.strftime('%d.%m.%Y')} ile {end_date.strftime('%d.%m.%Y')} "
            f"tarihleri arasında {mode} biçiminde aşağıdaki varlıkların performanslarını kıyaslıyor:\n\n"
            f"{assets_info}\n\n"
            "Ayrıca bu dönemde seçili varlıkların drawdown ve risk-getiri saçılım grafikleri de oluşturulmuştur.\n"
            "Bir finansal analist olarak, bu karşılaştırmayı detaylı ve profesyonelce yorumla:\n"
            "1. Dönemin en başarılı varlığı hangisidir ve neden öne çıkmıştır?\n"
            "2. Drawdown ve volatilite açısından en riskli ve en güvenli varlık hangisidir?\n"
            "3. Portföy çeşitlendirmesi için 2-3 pratik öneride bulun.\n\n"
            "Not: Yatırım tavsiyesi vermeden, veriye sadık kalarak, sade ve anlaşılır Türkçe ile kısa paragraflar halinde yaz."
        )

        system_msg = ChatMessage(
            role=MessageRole.SYSTEM,
            content="Sen profesyonel bir BIST ve küresel piyasalar portföy analiz asistanısın."
        )
        user_msg = ChatMessage(role=MessageRole.USER, content=prompt)

        scroll_bar = self.page.scroll_area.verticalScrollBar()
        scroll_pos = scroll_bar.value()

        self.page.ai_btn.setEnabled(False)
        self.page.ai_btn.setText("Yapay Zeka Analiz Ediyor...")
        self.page.ai_progress.setVisible(True)
        self.page.ai_browser.setMarkdown("*Analiz hazırlanıyor, lütfen bekleyin...*")
        self.page.ai_browser.setVisible(True)

        QCoreApplication.processEvents()
        scroll_bar.setValue(scroll_pos)

        self.ai_worker = GeminiWorker([system_msg, user_msg])
        self.ai_worker.response_ready.connect(self._on_ai_response_ready)
        self.ai_worker.error_occurred.connect(self._on_ai_error)
        self.ai_worker.start()

    def _on_ai_response_ready(self, response_text: str) -> None:
        scroll_bar = self.page.scroll_area.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        self.page.ai_btn.setEnabled(True)
        self.page.ai_btn.setText("Yapay Zeka Yorumu Oluştur")
        self.page.ai_progress.setVisible(False)
        try:
            self.page.ai_browser.setMarkdown(response_text)
        except Exception:
            self.page.ai_browser.setPlainText(response_text)
        self.page.ai_browser.setVisible(True)
        QCoreApplication.processEvents()
        scroll_bar.setValue(scroll_pos)

    def _on_ai_error(self, error_msg: str) -> None:
        scroll_bar = self.page.scroll_area.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        self.page.ai_btn.setEnabled(True)
        self.page.ai_btn.setText("Yapay Zeka Yorumu Oluştur")
        self.page.ai_progress.setVisible(False)
        error_html = (
            f"<div style='color: #ef4444; font-weight: bold;'>Yapay Zeka Hatasi:</div>"
            f"<div style='color: #f8fafc; margin-top: 8px;'>{error_msg}</div>"
        )
        self.page.ai_browser.setHtml(error_html)
        self.page.ai_browser.setVisible(True)
        QCoreApplication.processEvents()
        scroll_bar.setValue(scroll_pos)

    def cleanup(self) -> None:
        """Sayfa kapanırken çalışan worker'ı durdurur."""
        if self.ai_worker and self.ai_worker.isRunning():
            try:
                self.ai_worker.response_ready.disconnect()
                self.ai_worker.error_occurred.disconnect()
            except TypeError:
                pass
            self.ai_worker.terminate()
            self.ai_worker.wait()
