# src/ui/pages/comparison/widgets/ui_builder.py
"""
Karşılaştırma sayfasının grafik panel widget'larını oluşturan factory sınıfı.

ComparisonPage'in _build_*_panel metodlarını burada toplar;
böylece ComparisonPage sınıfı yalnızca orkestrasyon ve yaşam döngüsü
sorumluluğunu üstlenir.
"""
from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFrame,
    QHeaderView,
    QLabel,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from src.ui.pages.comparison.widgets.chart_panels import (
    ChartInfoCard,
    ChartPanel,
    ChartPlaceholder,
)


class ComparisonUIBuilder:
    """
    Karşılaştırma sayfasındaki 6 grafik panelini ve uyarı panelini
    oluşturan factory nesnesi.

    page nesnesi üzerinde gerekli attribute'ları (summary_table,
    *_chart_container, *_chart_layout vb.) doğrudan atar.
    """

    def __init__(self, page) -> None:
        self.page = page

    # ------------------------------------------------------------------
    # Uyarı paneli
    # ------------------------------------------------------------------

    def build_warning_panel(self, layout: QVBoxLayout) -> None:
        """Tarih doğrulama uyarı panelini oluşturur ve layout'a ekler."""
        page = self.page
        page.warning_panel = QFrame()
        page.warning_panel.setProperty("cssClass", "comparisonWarningPanel")
        warning_layout = QVBoxLayout(page.warning_panel)
        warning_layout.setContentsMargins(15, 10, 15, 10)
        page.warning_label = QLabel()
        page.warning_label.setWordWrap(True)
        page.warning_label.setProperty("cssClass", "comparisonWarningLabel")
        warning_layout.addWidget(page.warning_label)
        page.warning_panel.setVisible(False)
        layout.addWidget(page.warning_panel)

    # ------------------------------------------------------------------
    # Grafik panelleri
    # ------------------------------------------------------------------

    def _make_chart_slot(
        self, name: str, placeholder_text: str, layout: QVBoxLayout
    ) -> None:
        """Paylaşılan kalıpla bir grafik konteyner + placeholder oluşturur."""
        page = self.page
        container = QWidget()
        chart_layout = QVBoxLayout(container)
        chart_layout.setContentsMargins(0, 0, 0, 0)
        placeholder = ChartPlaceholder(placeholder_text)
        chart_layout.addWidget(placeholder)
        setattr(page, f"{name}_chart_container", container)
        setattr(page, f"{name}_chart_layout", chart_layout)
        setattr(page, f"{name}_chart_placeholder", placeholder)
        setattr(page, f"_{name}_chart_view", None)

    def build_main_chart_panel(self, layout: QVBoxLayout) -> None:
        page = self.page
        page.main_info_card = ChartInfoCard(
            "Ana Performans Kıyaslama Grafiği",
            "Seçilen varlıkların, benchmarkların veya portföylerin kümülatif getiri "
            "gelişimini ya da birbirlerine oranlarını (rasyosunu) zaman serisi olarak gösterir.",
            "'Kümülatif' veya 'Normalize' modda çizgilerin yukarı eğimi getiriyi, "
            "dalgalanmalar ise oynaklığı temsil eder. 'Rasyo Modu'nda Pay/Payda göreli gücü izlenir.",
        )
        layout.addWidget(page.main_info_card)
        self._make_chart_slot("main", "Performans grafiği yükleniyor...", layout)
        page.main_chart_panel = ChartPanel(
            "Kümülatif Getiri ve Performans Kıyaslaması",
            page.main_chart_container, "line-chart",
        )
        layout.addWidget(page.main_chart_panel)

    def build_summary_table_panel(self, layout: QVBoxLayout) -> None:
        page = self.page
        page.summary_info_card = ChartInfoCard(
            "Dönem Sonu Getiri Özeti Tablosu",
            "Seçilen tarih aralığında varlıkların başlangıç değerlerini, dönem sonu "
            "değerlerini ve toplam net getiri yüzdelerini tablo halinde listeler.",
            "Yeşil satırlar pozitif getiri, kırmızı satırlar negatif getiri anlamına gelir.",
        )
        layout.addWidget(page.summary_info_card)
        page.summary_table = QTableWidget()
        page.summary_table.setColumnCount(4)
        page.summary_table.setHorizontalHeaderLabels(
            ["Varlık Adı", "Başlangıç Değeri", "Dönem Sonu Değeri", "Toplam Getiri %"]
        )
        page.summary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        page.summary_table.verticalHeader().setVisible(False)
        page.summary_table.verticalHeader().setDefaultSectionSize(36)
        page.summary_table.setEditTriggers(QTableWidget.NoEditTriggers)
        page.summary_table.setSelectionMode(QTableWidget.NoSelection)
        page.summary_table.setFocusPolicy(Qt.NoFocus)
        page.summary_table.setAlternatingRowColors(True)
        page.summary_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page.summary_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        page.summary_table.setProperty("cssClass", "summaryTable")
        page.summary_table_panel = ChartPanel(
            "Dönem Sonu Getiri Özeti Tablosu", page.summary_table, "clipboard-list"
        )
        layout.addWidget(page.summary_table_panel)

    def build_drawdown_chart_panel(self, layout: QVBoxLayout) -> None:
        page = self.page
        page.drawdown_info_card = ChartInfoCard(
            "Maksimum Drawdown (Değer Kaybı) Grafiği",
            "Varlıkların tarihsel olarak zirve noktalarından yaşadıkları en büyük "
            "yüzde düşüşleri dikey eksende gösterir.",
            "Aşağıya sarkan derin çukurlar yüksek kayıp riskini ve uzun toparlanma süresini gösterir.",
        )
        layout.addWidget(page.drawdown_info_card)
        self._make_chart_slot("drawdown", "Drawdown grafiği yükleniyor...", layout)
        page.drawdown_chart_panel = ChartPanel(
            "Maksimum Değer Kaybı (Drawdown) Analizi",
            page.drawdown_chart_container, "trending-down",
        )
        layout.addWidget(page.drawdown_chart_panel)

    def build_periodic_chart_panel(self, layout: QVBoxLayout) -> None:
        page = self.page
        page.periodic_info_card = ChartInfoCard(
            "Dönemsel Getiri Karşılaştırması Grafiği",
            "Seçilen varlıkların aylık bazda elde ettikleri net yüzde getirilerini sütun "
            "grafik olarak kıyaslar.",
            "Hangi aylarda zıt yönlü hareket ettiğini görerek çeşitlendirme fırsatları yakalanabilir.",
        )
        layout.addWidget(page.periodic_info_card)
        self._make_chart_slot("periodic", "Dönemsel getiri grafiği yükleniyor...", layout)
        page.periodic_chart_panel = ChartPanel(
            "Dönemsel Getiri Karşılaştırması",
            page.periodic_chart_container, "bar-chart-2",
        )
        layout.addWidget(page.periodic_chart_panel)

    def build_scatter_chart_panel(self, layout: QVBoxLayout) -> None:
        page = self.page
        page.scatter_info_card = ChartInfoCard(
            "Risk-Getiri Dağılımı (Saçılım) Grafiği",
            "Varlıkların yıllıklandırılmış oynaklığını yatay eksende, toplam dönem "
            "getirisini ise dikey eksende kıyaslar.",
            "Sol-üst: Düşük Risk, Yüksek Getiri (verimli). Sağ-alt: Yüksek Risk, Düşük Getiri.",
        )
        layout.addWidget(page.scatter_info_card)
        self._make_chart_slot("scatter", "Risk-getiri grafiği yükleniyor...", layout)
        page.scatter_chart_panel = ChartPanel(
            "Risk-Getiri Dağılımı (Saçılım)",
            page.scatter_chart_container, "target",
        )
        layout.addWidget(page.scatter_chart_panel)

    def build_treemap_chart_panel(self, layout: QVBoxLayout) -> None:
        page = self.page
        page.treemap_info_card = ChartInfoCard(
            "Treemap (Getiri Katkı Haritası) Grafiği",
            "Varlıkların getiri büyüklüklerini (kutunun alanı) ve yönlerini (renk) "
            "tek bir ısı haritasında gösterir.",
            "Koyu yeşil: en yüksek getiri. Koyu kırmızı: en yüksek kayıp.",
        )
        layout.addWidget(page.treemap_info_card)
        self._make_chart_slot("treemap", "Getiri katkı haritası yükleniyor...", layout)
        page.treemap_chart_panel = ChartPanel(
            "Getiri Katkı Haritası (Treemap)",
            page.treemap_chart_container, "layers",
        )
        layout.addWidget(page.treemap_chart_panel)

    # ------------------------------------------------------------------
    # Toplu kurulum
    # ------------------------------------------------------------------

    def build_all_chart_panels(self, layout: QVBoxLayout) -> None:
        """Tüm grafik panellerini sırayla oluşturur."""
        self.build_main_chart_panel(layout)
        self.build_summary_table_panel(layout)
        self.build_drawdown_chart_panel(layout)
        self.build_periodic_chart_panel(layout)
        self.build_scatter_chart_panel(layout)
        self.build_treemap_chart_panel(layout)
