from __future__ import annotations
import os
import tempfile
import logging
from datetime import date, timedelta
import pandas as pd
import numpy as np
from PyQt5.QtCore import QUrl, Qt, QThreadPool, QObject, QEvent, QCoreApplication, QSize, QTimer
from PyQt5.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QTextBrowser,
    QPushButton,
    QProgressBar,
    QMenu,
    QAction
)
from PyQt5.QtGui import QBrush, QColor
from PyQt5.QtWebEngineWidgets import QWebEngineView
import plotly.graph_objects as go

from src.ui.pages.base_page import BasePage
from src.ui.worker import Worker
from src.application.services.analysis.models import AnalysisFilterState
from src.application.services.analysis.comparison_service import ComparisonService
from src.ui.pages.comparison.chart_factory import ComparisonChartFactory
from src.ui.pages.comparison.widgets.ribbon_bar import ComparisonRibbonBar
from src.ui.pages.analysis.chart_builder import patch_plotly_html

# AI page core imports for LLM analysis
from src.ui.pages.ai_page.core.models import ChatMessage, MessageRole
from src.ui.pages.ai_page.core.gemini_service import GeminiWorker

logger = logging.getLogger(__name__)

class WheelRedirectFilter(QObject):
    def __init__(self, scroll_area, parent=None):
        super().__init__(parent)
        self.scroll_area = scroll_area
        
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Wheel:
            QCoreApplication.sendEvent(self.scroll_area, event)
            return True
        return super().eventFilter(obj, event)

class ChartPlaceholder(QFrame):
    def __init__(self, text="Grafik hazırlanıyor...", parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "panelFrame")
        self.setStyleSheet("""
            QFrame[cssClass="panelFrame"] {
                background-color: #0f172a;
                border: 1px dashed #1e293b;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        self.label = QLabel(text)
        self.label.setStyleSheet("color: #64748b; font-size: 15px; font-weight: 500;")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.setMinimumHeight(600)


class ChartInfoCard(QFrame):
    def __init__(self, title: str, nedir: str, yorum: str, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "panelFramePadded")
        self.setStyleSheet("""
            QFrame[cssClass="panelFramePadded"] {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        
        from src.ui.core.icon_manager import IconManager
        icon_path = IconManager.get_icon_path("info", color="#00ffff")
        
        html_content = f"""
        <div style="font-family: 'Segoe UI', sans-serif; line-height: 1.5; padding: 5px;">
            <b style="color: #00ffff; font-size: 19px; text-shadow: 0 0 10px rgba(0, 255, 255, 0.4);">
                <img src="file:///{icon_path}" width="22" height="22" style="vertical-align: middle; margin-right: 8px;" />
                {title}
            </b>
            <p style="margin: 12px 0 0 0; color: #ffffff; font-size: 17px;">
                <b style="color: #fbbf24;">Nedir:</b> {nedir}
            </p>
            <p style="margin: 8px 0 0 0; color: #ffffff; font-size: 17px;">
                <b style="color: #fbbf24;">Nasıl Yorumlanır:</b> {yorum}
            </p>
        </div>
        """
        self.label = QLabel(html_content)
        self.label.setWordWrap(True)
        self.label.setTextFormat(Qt.RichText)
        layout.addWidget(self.label)


class ChartPanel(QFrame):
    def __init__(self, title: str, content_widget: QWidget, icon_name: str | None = None, parent=None):
        super().__init__(parent)
        self.setProperty("cssClass", "panelFrame")
        self.setStyleSheet("""
            QFrame[cssClass="panelFrame"] {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Header
        header_layout = QHBoxLayout()
        
        from src.ui.core.icon_manager import IconManager
        if icon_name:
            self.icon_label = QLabel()
            pixmap = IconManager.get_icon(icon_name, color="#38bdf8", size=QSize(24, 24)).pixmap(24, 24)
            self.icon_label.setPixmap(pixmap)
            header_layout.addWidget(self.icon_label)
            
        self.title_label = QLabel(title)
        self.title_label.setStyleSheet("color: #e2e8f0; font-size: 16px; font-weight: bold;")
        header_layout.addWidget(self.title_label)
        header_layout.addStretch()
        
        # Action Button for portfolio compare
        self.inspect_btn = QPushButton()
        self.inspect_btn.setMinimumHeight(32)
        inspect_icon = IconManager.get_icon("layers", color="#38bdf8", size=QSize(16, 16))
        self.inspect_btn.setIcon(inspect_icon)
        self.inspect_btn.setText("Portföy İçeriğini Kıyasla")
        self.inspect_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px 12px;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #334155;
                color: #0ea5e9;
            }
            QPushButton::menu-indicator {
                image: none;
            }
        """)
        header_layout.addWidget(self.inspect_btn)
        layout.addLayout(header_layout)
        layout.addWidget(content_widget)
        
        self.inspect_btn.setVisible(False) # Invisible by default
        
    def update_portfolio_options(self, portfolio_options: list[tuple[str, str]], current_override: str | None, on_portfolio_selected) -> None:
        if not portfolio_options:
            self.inspect_btn.setVisible(False)
            return
            
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 25px 6px 25px;
                border-radius: 4px;
                color: #f8fafc;
            }
            QMenu::item:selected {
                background-color: #334155;
                color: #38bdf8;
            }
            QMenu::item:checked {
                font-weight: bold;
                color: #00ffff;
            }
        """)
        
        self.actions = []
        
        # 1. Add "Küresel Seçime Dön" action
        from src.ui.core.icon_manager import IconManager
        global_action = QAction(IconManager.get_icon("refresh-cw", color="#ef4444", size=QSize(16, 16)), "Küresel Seçime Dön", self)
        global_action.setCheckable(True)
        global_action.setChecked(current_override is None)
        global_action.triggered.connect(lambda checked: on_portfolio_selected(None))
        menu.addAction(global_action)
        self.actions.append(global_action)
        
        menu.addSeparator()
        
        # 2. Add portfolio options
        for label, code in portfolio_options:
            action = QAction(label, self)
            action.setCheckable(True)
            action.setChecked(current_override == code)
            action.triggered.connect(lambda checked, c=code: on_portfolio_selected(c))
            menu.addAction(action)
            self.actions.append(action)
            
        self.inspect_btn.setMenu(menu)
        self.inspect_btn.setVisible(True)



class ComparisonPage(BasePage):
    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container
        self.page_title = "Karşılaştırma Laboratuvarı"
        self.analysis_service = container.analysis_service
        self.threadpool = QThreadPool.globalInstance()
        self._request_seq = 0
        self._temp_files = []
        self.chart_overrides = {}
        self.last_global_df = None
        self._init_ui()
        self._load_initial_options()

    def _init_ui(self) -> None:
        layout = self.main_layout
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Üst Başlık ve Açıklama
        header_layout = QHBoxLayout()
        title_col = QVBoxLayout()
        title_col.setSpacing(4)
        
        lbl_title = QLabel("Karşılaştırma Laboratuvarı")
        lbl_title.setProperty("cssClass", "pageTitle")
        title_col.addWidget(lbl_title)
        
        lbl_desc = QLabel("Varlıkları, benchmarkları ve portföyleri rasyo, drawdown ve risk-getiri bazında kıyaslayın.")
        lbl_desc.setProperty("cssClass", "pageDescription")
        title_col.addWidget(lbl_desc)
        
        header_layout.addLayout(title_col)
        layout.addLayout(header_layout)
        
        # 1. Ribbon Bar
        self.ribbon_bar = ComparisonRibbonBar()
        self.ribbon_bar.filter_changed.connect(self._request_refresh)
        layout.addWidget(self.ribbon_bar)
        
        # 2. Dinamik Uyarı Paneli (Tarih doğrulama hataları vb. için)
        self.warning_panel = QFrame()
        self.warning_panel.setProperty("cssClass", "panelFramePadded")
        self.warning_panel.setStyleSheet("""
            QFrame {
                background-color: #2d1616;
                border: 1px solid #7f1d1d;
                border-radius: 8px;
            }
        """)
        warning_layout = QVBoxLayout(self.warning_panel)
        warning_layout.setContentsMargins(15, 10, 15, 10)
        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color: #fca5a5; font-size: 13px; font-weight: 500;")
        warning_layout.addWidget(self.warning_label)
        self.warning_panel.setVisible(False)
        layout.addWidget(self.warning_panel)
        
        # 3. Scroll Area (Tüm Grafiklerin Dikey Listesi)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(0, 10, 0, 0)
        scroll_layout.setSpacing(20) # Grafikler arası boşluk
        
        # 1. Ana Performans Kıyaslama Grafiği ve Açıklama Kartı
        self.main_info_card = ChartInfoCard(
            "Ana Performans Kıyaslama Grafiği",
            "Seçilen varlıkların, benchmarkların veya portföylerin kümülatif getiri gelişimini ya da birbirlerine oranlarını (rasyosunu) zaman serisi olarak gösterir.",
            "Grafik 'Kümülatif' veya 'Normalize' modda ise çizgilerin yukarı yönlü eğimi getiriyi, dikey dalgalanmalar ise oynaklığı (riski) temsil eder. "
            "'Rasyo Modu' seçildiğinde ise Pay / Payda varlıklarının göreli gücü izlenir. Oranın yükselmesi paydaki varlığın paydadakine göre daha iyi performans gösterdiğini ifade eder."
        )
        scroll_layout.addWidget(self.main_info_card)
        
        self.main_chart_container = QWidget()
        self.main_chart_layout = QVBoxLayout(self.main_chart_container)
        self.main_chart_layout.setContentsMargins(0, 0, 0, 0)
        self.main_chart_placeholder = ChartPlaceholder("Performans grafiği yükleniyor...")
        self.main_chart_layout.addWidget(self.main_chart_placeholder)
        self._main_chart_view = None
        self.main_chart_panel = ChartPanel("Kümülatif Getiri ve Performans Kıyaslaması", self.main_chart_container, "line-chart")
        scroll_layout.addWidget(self.main_chart_panel)
        
        # 2. Dönem Sonu Getiri Özeti Tablosu ve Açıklama Kartı
        self.summary_info_card = ChartInfoCard(
            "Dönem Sonu Getiri Özeti Tablosu",
            "Seçilen tarih aralığında varlıkların başlangıç değerlerini, dönem sonu değerlerini ve toplam net getiri yüzdelerini tablo halinde listeler.",
            "Varlıkların net kazanç/kayıp performanslarını sayısal ve karşılaştırmalı olarak incelemek için kullanılır. "
            "Yeşil renkli satırlar pozitif getiri, kırmızı renkli satırlar ise negatif getiri anlamına gelir. Hücre verileri ortalanmış olarak daha okunaklıdır."
        )
        scroll_layout.addWidget(self.summary_info_card)
        
        self.summary_table = QTableWidget()
        self.summary_table.setColumnCount(4)
        self.summary_table.setHorizontalHeaderLabels([
            "Varlık Adı", "Başlangıç Değeri", "Dönem Sonu Değeri", "Toplam Getiri %"
        ])
        self.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.summary_table.verticalHeader().setVisible(False)
        self.summary_table.verticalHeader().setDefaultSectionSize(36)
        self.summary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.summary_table.setSelectionMode(QTableWidget.NoSelection)
        self.summary_table.setFocusPolicy(Qt.NoFocus)
        self.summary_table.setAlternatingRowColors(True)
        self.summary_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.summary_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.summary_table.setProperty("cssClass", "summaryTable")
        
        self.summary_table_panel = ChartPanel("Dönem Sonu Getiri Özeti Tablosu", self.summary_table, "clipboard-list")
        scroll_layout.addWidget(self.summary_table_panel)
        
        # 3. Maksimum Drawdown Analizi Grafiği ve Açıklama Kartı
        self.drawdown_info_card = ChartInfoCard(
            "Maksimum Drawdown (Değer Kaybı) Grafiği",
            "Varlıkların tarihsel olarak zirve noktalarından (tepe değerlerinden) yaşadıkları en büyük yüzde düşüşleri (kayıpları) dikey eksende gösterir.",
            "Varlıkların stres altında (krizlerde, piyasa düşüşlerinde) ne kadar kaybettirdiğini ölçer. Sıfıra (%0) ne kadar yakınsa o kadar dirençlidir. "
            "Aşağıya sarkan derin çukurlar ise yüksek değer kaybı riskini ve toparlanma süresinin uzunluğunu gösterir."
        )
        scroll_layout.addWidget(self.drawdown_info_card)
        
        self.drawdown_chart_container = QWidget()
        self.drawdown_chart_layout = QVBoxLayout(self.drawdown_chart_container)
        self.drawdown_chart_layout.setContentsMargins(0, 0, 0, 0)
        self.drawdown_chart_placeholder = ChartPlaceholder("Drawdown grafiği yükleniyor...")
        self.drawdown_chart_layout.addWidget(self.drawdown_chart_placeholder)
        self._drawdown_chart_view = None
        self.drawdown_chart_panel = ChartPanel("Maksimum Değer Kaybı (Drawdown) Analizi", self.drawdown_chart_container, "trending-down")
        scroll_layout.addWidget(self.drawdown_chart_panel)
        
        # 4. Dönemsel Getiri Karşılaştırması Grafiği ve Açıklama Kartı
        self.periodic_info_card = ChartInfoCard(
            "Dönemsel Getiri Karşılaştırması Grafiği",
            "Seçilen varlıkların aylık (veya periyodik) bazda elde ettikleri net yüzde getirileri sütun grafik olarak kıyaslar.",
            "Varlıkların aydan aya gösterdiği istikrarı veya oynaklığı gösterir. Farklı varlıkların hangi aylarda zıt yönlü hareket ettiğini (korelasyon durumunu) "
            "görerek portföy çeşitlendirme fırsatları yakalanabilir."
        )
        scroll_layout.addWidget(self.periodic_info_card)
        
        self.periodic_chart_container = QWidget()
        self.periodic_chart_layout = QVBoxLayout(self.periodic_chart_container)
        self.periodic_chart_layout.setContentsMargins(0, 0, 0, 0)
        self.periodic_chart_placeholder = ChartPlaceholder("Dönemsel getiri grafiği yükleniyor...")
        self.periodic_chart_layout.addWidget(self.periodic_chart_placeholder)
        self._periodic_chart_view = None
        self.periodic_chart_panel = ChartPanel("Dönemsel Getiri Karşılaştırması", self.periodic_chart_container, "bar-chart-2")
        scroll_layout.addWidget(self.periodic_chart_panel)
        
        # 5. Risk-Getiri Dağılımı Grafiği ve Açıklama Kartı
        self.scatter_info_card = ChartInfoCard(
            "Risk-Getiri Dağılımı (Saçılım) Grafiği",
            "Varlıkların yıllıklandırılmış oynaklığını (riski temsil eden volatilite) yatay eksende, toplam dönem getirisini ise dikey eksende kıyaslar.",
            "En verimli varlıklar grafik alanının sol-üst köşesinde (Düşük Risk, Yüksek Getiri) yer alanlardır. "
            "Sağ-alt köşe ise verimsiz varlıkları temsil eder. Çeşitli varlıkların verimlilik derecelerini kıyaslamayı sağlar."
        )
        scroll_layout.addWidget(self.scatter_info_card)
        
        self.scatter_chart_container = QWidget()
        self.scatter_chart_layout = QVBoxLayout(self.scatter_chart_container)
        self.scatter_chart_layout.setContentsMargins(0, 0, 0, 0)
        self.scatter_chart_placeholder = ChartPlaceholder("Risk-getiri grafiği yükleniyor...")
        self.scatter_chart_layout.addWidget(self.scatter_chart_placeholder)
        self._scatter_chart_view = None
        self.scatter_chart_panel = ChartPanel("Risk-Getiri Dağılımı (Saçılım)", self.scatter_chart_container, "target")
        scroll_layout.addWidget(self.scatter_chart_panel)
        
        # 6. Treemap (Getiri Katkı Haritası) Grafiği ve Açıklama Kartı
        self.treemap_info_card = ChartInfoCard(
            "Treemap (Getiri Katkı Haritası) Grafiği",
            "Varlıkların getiri büyüklüklerini (kutunun alanı) ve getiri yönlerini (kutunun rengi) tek bir ısı haritası üzerinde gösterir.",
            "Kutunun büyüklüğü varlığın kıyaslamadaki / portföydeki getiri/değer ağırlığını, rengi ise yönünü temsil eder. "
            "Koyu yeşil renkler en yüksek getiriyi, koyu kırmızı renkler ise en yüksek kaybı işaret eder. Toplam performansa etki eden lokomotif varlıkları hızlıca tespit etmeye yarar."
        )
        scroll_layout.addWidget(self.treemap_info_card)
        
        self.treemap_chart_container = QWidget()
        self.treemap_chart_layout = QVBoxLayout(self.treemap_chart_container)
        self.treemap_chart_layout.setContentsMargins(0, 0, 0, 0)
        self.treemap_chart_placeholder = ChartPlaceholder("Getiri katkı haritası yükleniyor...")
        self.treemap_chart_layout.addWidget(self.treemap_chart_placeholder)
        self._treemap_chart_view = None
        self.treemap_chart_panel = ChartPanel("Getiri Katkı Haritası (Treemap)", self.treemap_chart_container, "layers")
        scroll_layout.addWidget(self.treemap_chart_panel)
        
        # 7. Yapay Zeka Rapor ve Analiz Asistanı Kartı
        self.ai_panel = QFrame()
        self.ai_panel.setProperty("cssClass", "panelFramePadded")
        self.ai_panel.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
        """)
        ai_layout = QVBoxLayout(self.ai_panel)
        ai_layout.setContentsMargins(25, 25, 25, 25)
        ai_layout.setSpacing(15)
        
        ai_title_layout = QHBoxLayout()
        from src.ui.core.icon_manager import IconManager
        ai_icon_lbl = QLabel()
        ai_icon_pixmap = IconManager.get_icon("bot", color="#38bdf8", size=QSize(28, 28)).pixmap(28, 28)
        ai_icon_lbl.setPixmap(ai_icon_pixmap)
        ai_title_lbl = QLabel("Yapay Zeka Rapor ve Analiz Asistanı")
        ai_title_lbl.setStyleSheet("color: #38bdf8; font-size: 18px; font-weight: bold;")
        ai_title_layout.addWidget(ai_icon_lbl)
        ai_title_layout.addWidget(ai_title_lbl)
        ai_title_layout.addStretch()
        ai_layout.addLayout(ai_title_layout)
        
        ai_desc = QLabel(
            "Karşılaştırma ekranında seçilen tüm varlıkların ve hesaplanan metriklerin (getiri, volatilite, drawdown) "
            "Gemini yapay zeka modeli ile kapsamlı bir şekilde yorumlanmasını sağlamak için aşağıdaki butona tıklayın."
        )
        ai_desc.setWordWrap(True)
        ai_desc.setStyleSheet("color: #94a3b8; font-size: 14px; line-height: 1.4;")
        ai_layout.addWidget(ai_desc)
        
        self.ai_btn = QPushButton("Yapay Zeka Yorumu Oluştur")
        self.ai_btn.setMinimumHeight(38)
        self.ai_btn.setMinimumWidth(200)
        self.ai_btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.ai_btn.setFocusPolicy(Qt.NoFocus)
        self.ai_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
            QPushButton:disabled {
                background-color: #334155;
                color: #64748b;
            }
        """)
        self.ai_btn.clicked.connect(self._generate_ai_commentary)
        ai_layout.addWidget(self.ai_btn)
        
        self.ai_progress = QProgressBar()
        self.ai_progress.setTextVisible(False)
        self.ai_progress.setRange(0, 0) # Indeterminate spinner
        self.ai_progress.setFixedHeight(4)
        self.ai_progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #1e293b;
                border-radius: 2px;
            }
            QProgressBar::chunk {
                background-color: #38bdf8;
                border-radius: 2px;
            }
        """)
        self.ai_progress.setVisible(False)
        ai_layout.addWidget(self.ai_progress)
        
        self.ai_browser = QTextBrowser()
        self.ai_browser.setFrameShape(QFrame.NoFrame)
        self.ai_browser.setReadOnly(True)
        self.ai_browser.setOpenExternalLinks(True)
        self.ai_browser.setStyleSheet("""
            QTextBrowser {
                background-color: #1e293b;
                color: #f8fafc;
                font-family: 'Segoe UI', -apple-system, sans-serif;
                font-size: 18px;
                line-height: 1.6;
                border-radius: 8px;
                padding: 24px;
                border: 1px solid #38bdf8;
            }
        """)
        self.ai_browser.setMinimumHeight(400)
        self.ai_browser.setVisible(False)
        self.ai_browser.setFocusPolicy(Qt.NoFocus)
        ai_layout.addWidget(self.ai_browser)
        
        scroll_layout.addWidget(self.ai_panel)
        
        self.scroll_area.setWidget(scroll_content)
        layout.addWidget(self.scroll_area, 1)
        
        # Wheel event redirect filter setup
        self.wheel_redirect_filter = WheelRedirectFilter(self.scroll_area)
        
        # Kademeli yükleme (staggered loading)
        QTimer.singleShot(150, lambda: self._lazy_init_view_safe("main"))
        QTimer.singleShot(300, lambda: self._lazy_init_view_safe("drawdown"))
        QTimer.singleShot(450, lambda: self._lazy_init_view_safe("periodic"))
        QTimer.singleShot(600, lambda: self._lazy_init_view_safe("scatter"))
        QTimer.singleShot(750, lambda: self._lazy_init_view_safe("treemap"))


    def _install_filters_on_children(self, view: QWebEngineView) -> None:
        if not hasattr(self, "wheel_redirect_filter"):
            return
        view.installEventFilter(self.wheel_redirect_filter)
        proxy = view.focusProxy()
        if proxy:
            proxy.installEventFilter(self.wheel_redirect_filter)
        for child in view.findChildren(QWidget):
            child.installEventFilter(self.wheel_redirect_filter)

    def _lazy_init_view_safe(self, name: str) -> None:
        import sip
        try:
            if sip.isdeleted(self):
                return
        except Exception:
            return
        self._get_or_create_view(name)

    def _get_or_create_view(self, name: str) -> QWebEngineView:
        attr_name = f"_{name}_chart_view"
        view = getattr(self, attr_name, None)
        if view is None:
            view = QWebEngineView()
            view.setMinimumHeight(600)
            
            # Yönlendirme filtresini ekle
            if hasattr(self, "wheel_redirect_filter"):
                view.loadFinished.connect(lambda ok, v=view: self._install_filters_on_children(v))
                self._install_filters_on_children(view)
                
            # Konteyner layout'unu bul ve placeholder'ı kaldır
            layout_attr = f"{name}_chart_layout"
            layout = getattr(self, layout_attr, None)
            if layout:
                placeholder_attr = f"{name}_chart_placeholder"
                placeholder = getattr(self, placeholder_attr, None)
                if placeholder:
                    layout.removeWidget(placeholder)
                    placeholder.deleteLater()
                    setattr(self, placeholder_attr, None)
                layout.addWidget(view)
                
            setattr(self, attr_name, view)
        return view

    @property
    def main_chart_view(self) -> QWebEngineView:
        return self._get_or_create_view("main")

    @property
    def drawdown_chart_view(self) -> QWebEngineView:
        return self._get_or_create_view("drawdown")

    @property
    def periodic_chart_view(self) -> QWebEngineView:
        return self._get_or_create_view("periodic")

    @property
    def scatter_chart_view(self) -> QWebEngineView:
        return self._get_or_create_view("scatter")

    @property
    def treemap_chart_view(self) -> QWebEngineView:
        return self._get_or_create_view("treemap")


    def on_page_enter(self) -> None:
        old_assets = getattr(self, "_base_assets_cache", [])
        self._load_initial_options()
        new_assets = getattr(self, "_base_assets_cache", [])
        
        current_assets = self.ribbon_bar.selected_assets()
        current_dates = self.ribbon_bar.date_range()
        
        if (old_assets != new_assets or
            not hasattr(self, "_last_loaded_assets") or
            self._last_loaded_assets != current_assets or 
            self._last_loaded_dates != current_dates):
            self._request_refresh()

    def _get_current_base_assets(self) -> list[tuple[str, str]]:
        assets = []
        if not hasattr(self, "_asset_labels"):
            self._asset_labels = {}
            
        # Portfolios
        portfolios = self.analysis_service.get_portfolio_options()
        for p in portfolios:
            assets.append((p.label, p.code))
            assets.append((f"{p.label} + Hisseleri", f"holdings:{p.code}"))
            self._asset_labels[p.code] = p.label
            self._asset_labels[f"holdings:{p.code}"] = f"{p.label} + Hisseleri"
            
        # Benchmarks
        benchmarks = self.analysis_service.get_benchmark_definitions()
        for b in benchmarks:
            assets.append((b.label, b.code))
            self._asset_labels[b.code] = b.label
            
        # Add any already resolved stock codes to prevent losing them on set_assets
        for code, label in self._asset_labels.items():
            if code.isdigit() and not any(item[1] == code for item in assets):
                assets.append((label, code))
                
        self._base_assets_cache = assets
        return assets

    def _load_initial_options(self) -> None:
        self._asset_labels = {}
        assets = self._get_current_base_assets()
        self.ribbon_bar.set_assets(assets)
        self._refresh_panel_options()

    def _refresh_panel_options(self) -> None:
        portfolio_choices = []
        portfolios = self.analysis_service.get_portfolio_options()
        for p in portfolios:
            portfolio_choices.append((p.label, p.code))
            
        # Update each panel with current override state and action callback
        self.main_chart_panel.update_portfolio_options(portfolio_choices, self.chart_overrides.get("main_chart"), lambda code, ck="main_chart": self.handle_chart_portfolio_selected(ck, code))
        self.summary_table_panel.update_portfolio_options(portfolio_choices, self.chart_overrides.get("summary_table"), lambda code, ck="summary_table": self.handle_chart_portfolio_selected(ck, code))
        self.drawdown_chart_panel.update_portfolio_options(portfolio_choices, self.chart_overrides.get("drawdown_chart"), lambda code, ck="drawdown_chart": self.handle_chart_portfolio_selected(ck, code))
        self.periodic_chart_panel.update_portfolio_options(portfolio_choices, self.chart_overrides.get("periodic_chart"), lambda code, ck="periodic_chart": self.handle_chart_portfolio_selected(ck, code))
        self.scatter_chart_panel.update_portfolio_options(portfolio_choices, self.chart_overrides.get("scatter_chart"), lambda code, ck="scatter_chart": self.handle_chart_portfolio_selected(ck, code))
        self.treemap_chart_panel.update_portfolio_options(portfolio_choices, self.chart_overrides.get("treemap_chart"), lambda code, ck="treemap_chart": self.handle_chart_portfolio_selected(ck, code))

    def handle_chart_portfolio_selected(self, chart_key: str, portfolio_code: str | None) -> None:
        self.chart_overrides[chart_key] = portfolio_code
        self._refresh_panel_options()
        
        if portfolio_code is None:
            # Restore to global
            if self.last_global_df is not None:
                mode = self.ribbon_bar.selected_mode()
                if chart_key == "main_chart":
                    self._render_main_chart(self.last_global_df)
                else:
                    df_metrics = self.last_global_df
                    if mode == "Rasyo Modu":
                        num_code, den_code = self.ribbon_bar.ratio_assets()
                        num_col = self._find_column_by_code(self.last_global_df, num_code)
                        den_col = self._find_column_by_code(self.last_global_df, den_code)
                        if num_col and den_col:
                            ratio_series = ComparisonService.calculate_asset_ratio(self.last_global_df[num_col], self.last_global_df[den_col])
                            ratio_name = f"{num_col} / {den_col}"
                            df_metrics = pd.DataFrame({ratio_name: ratio_series})
                    self._render_single_chart(chart_key, df_metrics)
        else:
            # Request custom data for this chart
            self._request_override_refresh(chart_key, portfolio_code)

    def _request_override_refresh(self, chart_key: str, portfolio_code: str) -> None:
        start_date, end_date = self.ribbon_bar.date_range()
        try:
            stock_map = self.analysis_service.get_stock_map_for_source(portfolio_code)
            stock_ids = list(stock_map.keys())
            
            # Save mapping of stock IDs to tickers in self._asset_labels
            for sid, ticker in stock_map.items():
                self._asset_labels[str(sid)] = ticker
                
            filter_state = AnalysisFilterState(
                start_date=start_date,
                end_date=end_date,
                selected_stock_ids=stock_ids,
                selected_benchmarks=[],
                portfolio_source=portfolio_code,
                comparison_portfolio_sources=[portfolio_code],
                currency_mode="TL"
            )
            
            self._request_seq += 1
            request_id = self._request_seq
            
            worker = Worker(self.analysis_service.get_comparison_view, filter_state)
            worker.signals.result.connect(lambda result, rid=request_id, ck=chart_key, pc=portfolio_code: self._on_override_data_ready(rid, ck, pc, result))
            worker.signals.error.connect(lambda err: logger.error("Error fetching override data: %s", err))
            self.threadpool.start(worker)
            
        except Exception as e:
            logger.error("Error in override refresh for %s: %s", chart_key, e, exc_info=True)

    def _on_override_data_ready(self, request_id: int, chart_key: str, portfolio_code: str, dto) -> None:
        if self.chart_overrides.get(chart_key) != portfolio_code:
            return
            
        series_dict = {}
        # Primary portfolio
        if dto.portfolio_series:
            p_series = pd.Series({pd.Timestamp(d): float(v) for d, v in dto.portfolio_series.items()})
            p_series.name = dto.current_portfolio_label
            series_dict[dto.current_portfolio_label] = p_series
            self.code_to_label[portfolio_code] = dto.current_portfolio_label
            self.code_to_label[f"portfolio:{portfolio_code}"] = dto.current_portfolio_label
            
        # Comparison portfolios
        for cp in dto.comparison_portfolios:
            if cp.points:
                s = pd.Series({pd.Timestamp(d): float(v) for d, v in cp.points.items()})
                s.name = cp.label
                series_dict[cp.label] = s
                self.code_to_label[cp.code] = cp.label
                self.code_to_label[f"portfolio:{cp.code}"] = cp.label
                
        # Stocks
        for stock_id, points in dto.stock_series.items():
            if points:
                s = pd.Series({pd.Timestamp(d): float(v) for d, v in points.items()})
                s.name = self._asset_labels.get(str(stock_id), str(stock_id))
                series_dict[s.name] = s
                
        if not series_dict:
            return
            
        aligned_df = ComparisonService.align_financial_series(series_dict)
        
        mode = self.ribbon_bar.selected_mode()
        if chart_key == "main_chart":
            self._render_main_chart(aligned_df)
        else:
            df_metrics = aligned_df
            if mode == "Rasyo Modu":
                num_code, den_code = self.ribbon_bar.ratio_assets()
                num_col = self._find_column_by_code(aligned_df, num_code)
                den_col = self._find_column_by_code(aligned_df, den_code)
                if num_col and den_col:
                    ratio_series = ComparisonService.calculate_asset_ratio(aligned_df[num_col], aligned_df[den_col])
                    ratio_name = f"{num_col} / {den_col}"
                    df_metrics = pd.DataFrame({ratio_name: ratio_series})
            self._render_single_chart(chart_key, df_metrics)

    def _check_date_warnings(self) -> list[str]:
        warnings = []
        start_date, end_date = self.ribbon_bar.date_range()
        
        if start_date > end_date:
            warnings.append("Başlangıç tarihi bitiş tarihinden sonra olamaz.")
            return warnings
            
        if end_date > date.today():
            warnings.append("Bitiş tarihi bugünden ileri bir tarih olamaz.")
            
        selected_codes = self.ribbon_bar.selected_assets()
        for code in selected_codes:
            if code == "dashboard" or code.startswith("portfolio:") or code.startswith("model:"):
                try:
                    first_trade_dt = self.analysis_service.get_first_trade_date_for_source(code)
                    if first_trade_dt and start_date < first_trade_dt:
                        label = getattr(self, "_asset_labels", {}).get(code, code)
                        start_str = start_date.strftime("%d.%m.%Y")
                        first_str = first_trade_dt.strftime("%d.%m.%Y")
                        warnings.append(
                            f"Seçilen başlangıç tarihi ({start_str}), <b>{label}</b> varlığının ilk işlem tarihinden ({first_str}) öncedir. "
                            f"Bu dönemde portföy değeri 0 veya sabit nakit olarak görüneceğinden kıyaslama yanıltıcı olabilir."
                        )
                except Exception as e:
                    logger.debug("Failed to get first trade date for source %s: %s", code, e)
                    
        duration = end_date - start_date
        if duration.days < 7:
            warnings.append("Seçilen tarih aralığı çok kısa (7 günden az). Yıllıklandırılmış volatilite ve drawdown hesaplamaları kararsız olabilir.")
            
        return warnings

    def _request_refresh(self) -> None:
        start_date, end_date = self.ribbon_bar.date_range()
        selected_codes = self.ribbon_bar.selected_assets()
        
        if not selected_codes:
            self._render_empty_state("Lütfen kıyaslanacak varlıkları seçin.")
            return
            
        # Intercept holdings sanal selections
        has_holdings_trigger = False
        new_selected_codes = list(selected_codes)
        for code in selected_codes:
            if code.startswith("holdings:"):
                has_holdings_trigger = True
                portfolio_code = code.split(":", 1)[1]
                try:
                    stock_map = self.analysis_service.get_stock_map_for_source(portfolio_code)
                    if stock_map:
                        if portfolio_code not in new_selected_codes:
                            new_selected_codes.append(portfolio_code)
                        for sid, ticker in stock_map.items():
                            sid_str = str(sid)
                            self._asset_labels[sid_str] = ticker
                            if sid_str not in new_selected_codes:
                                new_selected_codes.append(sid_str)
                except Exception as e:
                    logger.error("Error loading holdings option in refresh: %s", e)
                    
        if has_holdings_trigger:
            # Rebuild assets list to make sure we include any resolved stocks
            updated_assets = self._get_current_base_assets()
            self.ribbon_bar.blockSignals(True)
            try:
                self.ribbon_bar.set_assets(updated_assets)
                # Update checkable selections
                self.ribbon_bar.set_selected_assets(new_selected_codes)
            finally:
                self.ribbon_bar.blockSignals(False)
            
            selected_codes = new_selected_codes
            
        # Clear overrides on global filter change
        self.chart_overrides.clear()
        self._refresh_panel_options()
        
        # Run proactive warnings
        warnings = self._check_date_warnings()
        if warnings:
            warning_text = "<b>⚠️ Dikkat:</b><br>" + "<br>".join([f"• {w}" for w in warnings])
            self.warning_label.setText(warning_text)
            self.warning_panel.setVisible(True)
        else:
            self.warning_panel.setVisible(False)
            
        self._request_seq += 1
        request_id = self._request_seq
        
        portfolio_sources = []
        benchmarks = []
        stock_ids = []
        
        for code in selected_codes:
            if code == "dashboard" or code.startswith("portfolio:") or code.startswith("model:"):
                portfolio_sources.append(code)
            elif code in ["bist100", "gold", "silver", "usd", "euro", "deposit", "cpi"]:
                benchmarks.append(code)
            else:
                try:
                    stock_ids.append(int(code))
                except ValueError:
                    pass
                    
        self._selected_stock_ids = stock_ids
        primary_source = portfolio_sources[0] if portfolio_sources else "dashboard"
        
        filter_state = AnalysisFilterState(
            start_date=start_date,
            end_date=end_date,
            selected_stock_ids=stock_ids,
            selected_benchmarks=benchmarks,
            portfolio_source=primary_source,
            comparison_portfolio_sources=portfolio_sources,
            currency_mode="TL"
        )
        
        worker = Worker(self.analysis_service.get_comparison_view, filter_state)
        worker.signals.result.connect(lambda result, rid=request_id: self._on_data_ready(rid, result))
        worker.signals.error.connect(lambda err, rid=request_id: self._on_data_error(rid, err))
        self.threadpool.start(worker)

    def _on_data_ready(self, request_id: int, dto) -> None:
        if request_id != self._request_seq:
            return
            
        series_dict = {}
        self.code_to_label = {}
        
        # Primary portfolio
        if dto.portfolio_series:
            p_series = pd.Series({pd.Timestamp(d): float(v) for d, v in dto.portfolio_series.items()})
            p_series.name = dto.current_portfolio_label
            series_dict[dto.current_portfolio_label] = p_series
            self.code_to_label["dashboard"] = dto.current_portfolio_label
            
        # Comparison portfolios
        for cp in dto.comparison_portfolios:
            if cp.points:
                s = pd.Series({pd.Timestamp(d): float(v) for d, v in cp.points.items()})
                s.name = cp.label
                series_dict[cp.label] = s
                self.code_to_label[cp.code] = cp.label
                self.code_to_label[f"portfolio:{cp.code}"] = cp.label
                
        # Benchmarks
        for b in dto.benchmark_series:
            if b.points:
                s = pd.Series({pd.Timestamp(d): float(v) for d, v in b.points.items()})
                s.name = b.label
                series_dict[b.label] = s
                self.code_to_label[b.code] = b.label
                
        # Stocks (only add if the user explicitly selected them)
        selected_sids = getattr(self, "_selected_stock_ids", [])
        if selected_sids:
            for stock_id, points in dto.stock_series.items():
                if points:
                    s = pd.Series({pd.Timestamp(d): float(v) for d, v in points.items()})
                    s.name = str(stock_id)
                    series_dict[s.name] = s
                    self.code_to_label[str(stock_id)] = s.name
                
        if not series_dict:
            self._render_empty_state("Seçilen filtreler için veri bulunamadı.")
            return
            
        # Align series
        aligned_df = ComparisonService.align_financial_series(series_dict)
        
        # Cache global dataset
        self.last_global_df = aligned_df
        
        # Render charts
        self._render_charts(aligned_df)
        
        # Cache the successfully loaded filters state
        self._last_loaded_assets = self.ribbon_bar.selected_assets()
        self._last_loaded_dates = self.ribbon_bar.date_range()

    def _on_data_error(self, request_id: int, err_tuple) -> None:
        if request_id != self._request_seq:
            return
        self._render_empty_state(f"Veri yükleme hatası: {err_tuple[1]}")

    def _render_charts(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
            
        mode = self.ribbon_bar.selected_mode()
        df_analysis = df
        
        if mode == "Normalize (Baz 100)":
            df_norm = df.copy()
            for col in df_norm.columns:
                base_val = df_norm[col].iloc[0]
                if base_val != 0:
                    df_norm[col] = (df_norm[col] / base_val) * 100.0
            df_analysis = df_norm
        elif mode == "Rasyo Modu":
            num_code, den_code = self.ribbon_bar.ratio_assets()
            num_col = self._find_column_by_code(df, num_code)
            den_col = self._find_column_by_code(df, den_code)
            if num_col and den_col:
                ratio_series = ComparisonService.calculate_asset_ratio(df[num_col], df[den_col])
                ratio_name = f"{num_col} / {den_col}"
                df_analysis = pd.DataFrame({ratio_name: ratio_series})
        else:
            df_ret = df.copy()
            for col in df_ret.columns:
                base_val = df_ret[col].iloc[0]
                df_ret[col] = ((df_ret[col] - base_val) / base_val) * 100.0 if base_val != 0 else 0.0
            df_analysis = df_ret
            
        df_metrics = df_analysis if mode == "Rasyo Modu" else df
        
        # Render each chart, respecting overrides if set
        if not self.chart_overrides.get("main_chart"):
            self._render_main_chart(df)
            
        if not self.chart_overrides.get("summary_table"):
            self._render_summary_table(df_metrics)
            
        if not self.chart_overrides.get("drawdown_chart"):
            self._render_drawdown_chart(df_metrics)
            
        if not self.chart_overrides.get("periodic_chart"):
            self._render_periodic_chart(df_metrics)
            
        if not self.chart_overrides.get("scatter_chart"):
            self._render_scatter_chart(df_metrics)
            
        if not self.chart_overrides.get("treemap_chart"):
            self._render_treemap_chart(df_metrics)

    def _render_main_chart(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        mode = self.ribbon_bar.selected_mode()
        fig_main = go.Figure()
        colors_palette = ["#3b82f6", "#10b981", "#f59e0b", "#8b5cf6", "#ef4444", "#06b6d4"]
        
        if mode == "Normalize (Baz 100)":
            df_norm = df.copy()
            for col in df_norm.columns:
                base_val = df_norm[col].iloc[0]
                if base_val != 0:
                    df_norm[col] = (df_norm[col] / base_val) * 100.0
            for i, col in enumerate(df_norm.columns):
                color = colors_palette[i % len(colors_palette)]
                fig_main.add_trace(go.Scatter(x=df_norm.index, y=df_norm[col], name=col, line=dict(width=2, color=color)))
            ComparisonChartFactory._apply_theme_layout(fig_main, "Normalize Performans Kıyaslaması (Baz 100)")
        elif mode == "Rasyo Modu":
            num_code, den_code = self.ribbon_bar.ratio_assets()
            num_col = self._find_column_by_code(df, num_code)
            den_col = self._find_column_by_code(df, den_code)
            
            if num_col and den_col:
                ratio_series = ComparisonService.calculate_asset_ratio(df[num_col], df[den_col])
                ratio_name = f"{num_col} / {den_col}"
                fig_main.add_trace(go.Scatter(x=ratio_series.index, y=ratio_series.values, name=ratio_name, line=dict(width=2, color="#00D4FF")))
                ComparisonChartFactory._apply_theme_layout(fig_main, f"Rasyo Gösterimi: {ratio_name}")
            else:
                for i, col in enumerate(df.columns):
                    color = colors_palette[i % len(colors_palette)]
                    fig_main.add_trace(go.Scatter(x=df.index, y=df[col], name=col, line=dict(width=2, color=color)))
                ComparisonChartFactory._apply_theme_layout(fig_main, "Performans Kıyaslaması")
        else:
            df_ret = df.copy()
            for col in df_ret.columns:
                base_val = df_ret[col].iloc[0]
                df_ret[col] = ((df_ret[col] - base_val) / base_val) * 100.0 if base_val != 0 else 0.0
            for i, col in enumerate(df_ret.columns):
                color = colors_palette[i % len(colors_palette)]
                fig_main.add_trace(go.Scatter(x=df_ret.index, y=df_ret[col], name=col, line=dict(width=2, color=color)))
            ComparisonChartFactory._apply_theme_layout(fig_main, "Kümülatif Performans Getirisi (%)")
            
        self._load_plotly_to_view(self.main_chart_view, fig_main)

    def _render_summary_table(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        self.summary_table.setRowCount(0)
        self.summary_table.setRowCount(len(df.columns))
        
        for row, col in enumerate(df.columns):
            series = df[col].dropna()
            if not series.empty:
                start_val = float(series.iloc[0])
                end_val = float(series.iloc[-1])
                tot_ret = ((end_val - start_val) / start_val) * 100.0 if start_val != 0.0 else 0.0
                
                item_name = QTableWidgetItem(col)
                item_start = QTableWidgetItem(f"{start_val:,.2f}")
                item_end = QTableWidgetItem(f"{end_val:,.2f}")
                
                sign = "+" if tot_ret > 0 else ""
                item_ret = QTableWidgetItem(f"{sign}{tot_ret:.2f}%")
                
                item_name.setTextAlignment(Qt.AlignCenter)
                item_start.setTextAlignment(Qt.AlignCenter)
                item_end.setTextAlignment(Qt.AlignCenter)
                item_ret.setTextAlignment(Qt.AlignCenter)
                
                if tot_ret > 0:
                    item_ret.setForeground(QBrush(QColor("#10b981")))
                elif tot_ret < 0:
                    item_ret.setForeground(QBrush(QColor("#ef4444")))
                else:
                    item_ret.setForeground(QBrush(QColor("#94a3b8")))
                    
                self.summary_table.setItem(row, 0, item_name)
                self.summary_table.setItem(row, 1, item_start)
                self.summary_table.setItem(row, 2, item_end)
                self.summary_table.setItem(row, 3, item_ret)
                
        self._update_table_height()

    def _render_drawdown_chart(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        df_dd = ComparisonService.calculate_drawdowns(df)
        fig_dd = ComparisonChartFactory.build_drawdown_chart(df_dd)
        self._load_plotly_to_view(self.drawdown_chart_view, fig_dd)

    def _render_periodic_chart(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        df_periodic = ComparisonService.calculate_periodic_returns(df, freq="ME")
        fig_periodic = ComparisonChartFactory.build_period_bar_chart(df_periodic)
        self._load_plotly_to_view(self.periodic_chart_view, fig_periodic)

    def _render_scatter_chart(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        metrics = ComparisonService.calculate_risk_return_metrics(df)
        scatter_data = []
        for name, m in metrics.items():
            scatter_data.append({
                "Volatilite %": m["annual_volatility_pct"],
                "Getiri %": m["total_return_pct"],
                "Varlık": name
            })
        df_scatter = pd.DataFrame(scatter_data).set_index("Varlık")
        fig_scatter = ComparisonChartFactory.build_risk_return_scatter(df_scatter)
        self._load_plotly_to_view(self.scatter_chart_view, fig_scatter)

    def _render_treemap_chart(self, df: pd.DataFrame) -> None:
        if df.empty:
            return
        metrics = ComparisonService.calculate_risk_return_metrics(df)
        weights = [max(abs(m["total_return_pct"]), 1.0) for m in metrics.values()]
        df_weights = pd.DataFrame({
            "Varlık Ağırlığı %": weights,
            "Getiri %": [tot_ret["total_return_pct"] for tot_ret in metrics.values()]
        }, index=df.columns)
        fig_tree = ComparisonChartFactory.build_treemap(df_weights)
        self._load_plotly_to_view(self.treemap_chart_view, fig_tree)

    def _render_single_chart(self, chart_key: str, df: pd.DataFrame) -> None:
        if df.empty:
            return
            
        if chart_key == "main_chart":
            self._render_main_chart(df)
        elif chart_key == "summary_table":
            self._render_summary_table(df)
        elif chart_key == "drawdown_chart":
            self._render_drawdown_chart(df)
        elif chart_key == "periodic_chart":
            self._render_periodic_chart(df)
        elif chart_key == "scatter_chart":
            self._render_scatter_chart(df)
        elif chart_key == "treemap_chart":
            self._render_treemap_chart(df)

    def _update_table_height(self) -> None:
        row_count = self.summary_table.rowCount()
        header_height = self.summary_table.horizontalHeader().height()
        if header_height <= 0:
            header_height = 38
            
        total_row_height = 0
        for i in range(row_count):
            h = self.summary_table.rowHeight(i)
            if h <= 0:
                h = 36
            total_row_height += h
            
        if total_row_height == 0 and row_count > 0:
            total_row_height = row_count * 36
            
        total_height = header_height + total_row_height + 4
        self.summary_table.setMinimumHeight(total_height)
        self.summary_table.setMaximumHeight(total_height)
        self.summary_table.updateGeometry()


    def _find_column_by_code(self, df: pd.DataFrame, code: str) -> str | None:
        if not hasattr(self, "code_to_label"):
            self.code_to_label = {}
            
        label = self.code_to_label.get(code)
        if label and label in df.columns:
            return label
            
        for col in df.columns:
            if col.lower() == code.lower():
                return col
            if code.isdigit() and col == code:
                return col
            if code.lower().replace(" ", "").replace("_", "") in col.lower().replace(" ", "").replace("_", ""):
                return col
        return df.columns[0] if not df.empty else None

    def _load_plotly_to_view(self, view: QWebEngineView, fig: go.Figure) -> None:
        if not hasattr(self, "shared_plotly_path") or not os.path.exists(self.shared_plotly_path):
            self.shared_plotly_path = os.path.join(tempfile.gettempdir(), "plotly-shared.min.js")
            if not os.path.exists(self.shared_plotly_path):
                try:
                    import plotly
                    with open(self.shared_plotly_path, "w", encoding="utf-8") as f:
                        f.write(plotly.offline.get_plotlyjs())
                except Exception as e:
                    logger.error("Failed to write shared plotly.js: %s", e)

        html = fig.to_html(include_plotlyjs=False)
        html = patch_plotly_html(html)
        
        shared_js_url = QUrl.fromLocalFile(self.shared_plotly_path).toString()
        script_tag = f'<script type="text/javascript" src="{shared_js_url}"></script>'
        if "<head>" in html:
            html = html.replace("<head>", f"<head>\n{script_tag}", 1)
        else:
            html = f"{script_tag}\n{html}"
            
        f = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
        f.write(html)
        f.close()
        
        if not hasattr(self, "_view_temp_files"):
            self._view_temp_files = {}
            
        old_path = self._view_temp_files.get(view)
        if old_path and os.path.exists(old_path):
            try:
                os.remove(old_path)
            except OSError:
                pass
                
        self._view_temp_files[view] = f.name
        view.load(QUrl.fromLocalFile(f.name))

    def _render_empty_state(self, message: str) -> None:
        empty_html = f"""
        <html>
        <body style="background-color:#0f172a; color:#94a3b8; font-family:Segoe UI, sans-serif; text-align:center; padding-top:150px;">
            <h3>{message}</h3>
        </body>
        </html>
        """
        self.main_chart_view.setHtml(empty_html)
        self.summary_table.setRowCount(0)
        self.drawdown_chart_view.setHtml(empty_html)
        self.periodic_chart_view.setHtml(empty_html)
        self.scatter_chart_view.setHtml(empty_html)
        self.treemap_chart_view.setHtml(empty_html)

    def _generate_ai_commentary(self) -> None:
        table_rows = []
        for row in range(self.summary_table.rowCount()):
            name = self.summary_table.item(row, 0).text() if self.summary_table.item(row, 0) else ""
            start = self.summary_table.item(row, 1).text() if self.summary_table.item(row, 1) else ""
            end = self.summary_table.item(row, 2).text() if self.summary_table.item(row, 2) else ""
            ret = self.summary_table.item(row, 3).text() if self.summary_table.item(row, 3) else ""
            table_rows.append(f"- **{name}**: Başlangıç Değeri: {start}, Dönem Sonu Değeri: {end}, Toplam Getiri: {ret}")
            
        if not table_rows:
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Uyarı", "Analiz edilecek veri bulunamadı. Lütfen varlıkları seçip grafikleri güncelleyin.")
            return
            
        start_date, end_date = self.ribbon_bar.date_range()
        start_str = start_date.strftime("%d.%m.%Y")
        end_str = end_date.strftime("%d.%m.%Y")
        
        assets_info = "\n".join(table_rows)
        mode = self.ribbon_bar.selected_mode()
        
        prompt = f"""Kullanıcı Karşılaştırma Laboratuvarı ekranında {start_str} ile {end_str} tarihleri arasında {mode} biçiminde aşağıdaki varlıkların performanslarını kıyaslıyor:

{assets_info}

Ayrıca bu dönemde seçili varlıkların drawdown (değer kaybı) ve risk-getiri saçılım grafikleri de oluşturulmuştur.
Bir finansal analist ve risk yönetimi uzmanı olarak, bu karşılaştırmayı detaylı ve profesyonelce yorumla.
Lütfen aşağıdaki noktaları açıkla:
1. Dönemin en başarılı varlığı hangisidir ve neden öne çıkmıştır?
2. Varlıkların oynaklık (volatilite) ve drawdown durumları karşılaştırıldığında en riskli ve en güvenli duran hangisidir?
3. Rasyo Modu veya Normalize durumların (seçime göre) bu karşılaştırmaya katkısı nedir?
4. Portföy çeşitlendirmesi ve risk yönetimi açısından kullanıcıya 2-3 pratik öneride bulun.

Not: Yatırım tavsiyesi vermeden, veriye sadık kalarak, sade ve anlaşılır Türkçe ile kısa paragraflar halinde yaz."""

        system_msg = ChatMessage(role=MessageRole.SYSTEM, content="Sen profesyonel bir BIST ve küresel piyasalar portföy analiz asistanısın.")
        user_msg = ChatMessage(role=MessageRole.USER, content=prompt)
        
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        
        self.ai_btn.setEnabled(False)
        self.ai_btn.setText("Yapay Zeka Analiz Ediyor...")
        self.ai_progress.setVisible(True)
        
        # Display the premium inline placeholder loading message
        self.ai_browser.setMarkdown("*Analiz hazırlanıyor, lütfen bekleyin...*")
        self.ai_browser.setVisible(True)
        
        # Process layout event and preserve scroll position
        QCoreApplication.processEvents()
        scroll_bar.setValue(scroll_pos)
        
        self.ai_worker = GeminiWorker([system_msg, user_msg])
        self.ai_worker.response_ready.connect(self._on_ai_response_ready)
        self.ai_worker.error_occurred.connect(self._on_ai_error)
        self.ai_worker.start()

    def _on_ai_response_ready(self, response_text: str) -> None:
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        
        self.ai_btn.setEnabled(True)
        self.ai_btn.setText("Yapay Zeka Yorumu Oluştur")
        self.ai_progress.setVisible(False)
        
        try:
            self.ai_browser.setMarkdown(response_text)
        except Exception:
            self.ai_browser.setPlainText(response_text)
            
        self.ai_browser.setVisible(True)
        
        # Process layout changes and restore scroll position
        QCoreApplication.processEvents()
        scroll_bar.setValue(scroll_pos)
            
    def _on_ai_error(self, error_msg: str) -> None:
        scroll_bar = self.scroll_area.verticalScrollBar()
        scroll_pos = scroll_bar.value()
        
        self.ai_btn.setEnabled(True)
        self.ai_btn.setText("Yapay Zeka Yorumu Oluştur")
        self.ai_progress.setVisible(False)
        
        error_html = f"<div style='color: #ef4444; font-weight: bold;'>⚠️ Yapay Zeka Hatası:</div><div style='color: #f8fafc; margin-top: 8px;'>{error_msg}</div>"
        self.ai_browser.setHtml(error_html)
        self.ai_browser.setVisible(True)
        
        # Process layout changes and restore scroll position
        QCoreApplication.processEvents()
        scroll_bar.setValue(scroll_pos)

    def on_page_leave(self) -> None:
        # Clean up view-specific temp files
        if hasattr(self, "_view_temp_files"):
            for path in list(self._view_temp_files.values()):
                if os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass
            self._view_temp_files.clear()
            
        # Clean up general temp files
        for path in list(self._temp_files):
            if os.path.exists(path):
                try:
                    os.remove(path)
                except OSError:
                    pass
        self._temp_files.clear()
        
        # Safely terminate Gemini worker if running to prevent crashes
        if hasattr(self, "ai_worker") and self.ai_worker.isRunning():
            try:
                self.ai_worker.response_ready.disconnect()
                self.ai_worker.error_occurred.disconnect()
            except TypeError:
                pass
            self.ai_worker.terminate()
            self.ai_worker.wait()

    def closeEvent(self, event) -> None:
        self.on_page_leave()
        super().closeEvent(event)

