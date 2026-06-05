# src/ui/pages/comparison/widgets/ui_builder.py
"""
Karşılaştırma sayfasının grafik panel widget'larını oluşturan factory sınıfı.

ComparisonPage'in _build_*_panel metodlarını burada toplar;
böylece ComparisonPage sınıfı yalnızca orkestrasyon ve yaşam döngüsü
sorumluluğunu üstlenir.
"""
from __future__ import annotations
from src.ui.shared.locale_tr import L10N

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
            L10N.ANA_PERFORMANS_KIYASLAMA_GRAFIGI,
            L10N.ANA_PERFORMANS_NORMAL_NEDIR,
            L10N.ANA_PERFORMANS_NORMAL_YORUM,
        )
        layout.addWidget(page.main_info_card)
        self._make_chart_slot("main", L10N.PERFORMANS_GRAFIGI_YUKLENIYOR, layout)
        page.main_chart_panel = ChartPanel(
            L10N.KUMULATIF_GETIRI_VE_PERFORMANS_KIYASLAMASI,
            page.main_chart_container, "line-chart",
        )
        layout.addWidget(page.main_chart_panel)

    def build_summary_table_panel(self, layout: QVBoxLayout) -> None:
        page = self.page
        page.summary_info_card = ChartInfoCard(
            L10N.DONEM_SONU_GETIRI_OZETI_TABLOSU,
            L10N.SECILEN_TARIH_ARALIGINDA_VARLIKLARIN_BASLANGIC +
            L10N.DEGERLERINI_VE_TOPLAM_NET_GETIRI,
            L10N.YESIL_SATIRLAR_POZITIF_GETIRI_KIRMIZI,
        )
        layout.addWidget(page.summary_info_card)
        page.summary_table = QTableWidget()
        page.summary_table.setColumnCount(4)
        page.summary_table.setHorizontalHeaderLabels(
            [L10N.VARLIK_ADI, L10N.BASLANGIC_DEGERI, L10N.DONEM_SONU_DEGERI, L10N.TOPLAM_GETIRI]
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
            L10N.DONEM_SONU_GETIRI_OZETI_TABLOSU, page.summary_table, "clipboard-list"
        )
        layout.addWidget(page.summary_table_panel)

    def build_drawdown_chart_panel(self, layout: QVBoxLayout) -> None:
        page = self.page
        page.drawdown_info_card = ChartInfoCard(
            L10N.MAKSIMUM_DRAWDOWN_DEGER_KAYBI_GRAFIGI,
            L10N.VARLIKLARIN_TARIHSEL_OLARAK_ZIRVE_NOKTALARINDAN +
            L10N.YUZDE_DUSUSLERI_DIKEY_EKSENDE_GOSTERIR,
            L10N.ASAGIYA_SARKAN_DERIN_CUKURLAR_YUKSEK,
        )
        layout.addWidget(page.drawdown_info_card)
        self._make_chart_slot("drawdown", L10N.DRAWDOWN_GRAFIGI_YUKLENIYOR, layout)
        page.drawdown_chart_panel = ChartPanel(
            L10N.MAKSIMUM_DEGER_KAYBI_DRAWDOWN_ANALIZI,
            page.drawdown_chart_container, "trending-down",
        )
        layout.addWidget(page.drawdown_chart_panel)

    def build_periodic_chart_panel(self, layout: QVBoxLayout) -> None:
        page = self.page
        page.periodic_info_card = ChartInfoCard(
            L10N.DONEMSEL_GETIRI_KARSILASTIRMASI_GRAFIGI,
            L10N.SECILEN_VARLIKLARIN_AYLIK_BAZDA_ELDE +
            L10N.GRAFIK_OLARAK_KIYASLAR,
            L10N.HANGI_AYLARDA_ZIT_YONLU_HAREKET,
        )
        layout.addWidget(page.periodic_info_card)
        self._make_chart_slot("periodic", L10N.DONEMSEL_GETIRI_GRAFIGI_YUKLENIYOR, layout)
        page.periodic_chart_panel = ChartPanel(
            L10N.DONEMSEL_GETIRI_KARSILASTIRMASI_1,
            page.periodic_chart_container, "bar-chart-2",
        )
        layout.addWidget(page.periodic_chart_panel)

    def build_scatter_chart_panel(self, layout: QVBoxLayout) -> None:
        page = self.page
        page.scatter_info_card = ChartInfoCard(
            L10N.RISKGETIRI_DAGILIMI_SACILIM_GRAFIGI,
            L10N.VARLIKLARIN_YILLIKLANDIRILMIS_OYNAKLIGINI_YATAY_EKSENDE +
            L10N.GETIRISINI_ISE_DIKEY_EKSENDE_KIYASLAR,
            L10N.SOLUST_DUSUK_RISK_YUKSEK_GETIRI,
        )
        layout.addWidget(page.scatter_info_card)
        self._make_chart_slot("scatter", L10N.RISKGETIRI_GRAFIGI_YUKLENIYOR, layout)
        page.scatter_chart_panel = ChartPanel(
            L10N.RISKGETIRI_DAGILIMI_SACILIM,
            page.scatter_chart_container, "target",
        )
        layout.addWidget(page.scatter_chart_panel)

    def build_treemap_chart_panel(self, layout: QVBoxLayout) -> None:
        page = self.page
        page.treemap_info_card = ChartInfoCard(
            L10N.TREEMAP_GETIRI_KATKI_HARITASI_GRAFIGI,
            L10N.VARLIKLARIN_GETIRI_BUYUKLUKLERINI_KUTUNUN_ALANI +
            L10N.TEK_BIR_ISI_HARITASINDA_GOSTERIR,
            L10N.KOYU_YESIL_EN_YUKSEK_GETIRI,
        )
        layout.addWidget(page.treemap_info_card)
        self._make_chart_slot("treemap", L10N.GETIRI_KATKI_HARITASI_YUKLENIYOR, layout)
        page.treemap_chart_panel = ChartPanel(
            L10N.GETIRI_KATKI_HARITASI_TREEMAP,
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
