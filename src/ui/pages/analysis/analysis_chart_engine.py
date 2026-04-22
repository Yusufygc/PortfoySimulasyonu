# src/ui/pages/analysis/analysis_chart_engine.py

import logging
from typing import Dict, List, Tuple
import pandas as pd
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

logger = logging.getLogger(__name__)

class AnalysisChartEngine(QWidget):
    """
    Hisse performans grafikleri ve karşılaştırma çizim motoru.
    Domain objelerinden bağımsızdır (DataFrameler ile beslenir).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(10, 6), facecolor='#0f172a')
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self)
        self.toolbar.setProperty("cssClass", "chartToolbar")

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas)

        self.lbl_summary = QLabel("Hisse seçin ve grafik oluşturun")
        self.lbl_summary.setProperty("cssClass", "chartSummaryText")
        layout.addWidget(self.lbl_summary)

    def draw_empty_chart(self, message: str):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        ax.text(0.5, 0.5, message, ha='center', va='center', 
                fontsize=14, color='#94a3b8', transform=ax.transAxes)
        ax.set_xticks([])
        ax.set_yticks([])
        for spine in ax.spines.values():
            spine.set_visible(False)
        self.lbl_summary.setText(message)
        self.canvas.draw()

    def draw_price_chart(self, data_map: Dict[str, pd.DataFrame]):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        
        colors = plt.cm.tab10.colors
        valid_count = 0
        
        for i, (ticker, data) in enumerate(data_map.items()):
            if data is not None and not data.empty:
                close_col = 'Close' if 'Close' in data.columns else data.columns[0]
                if hasattr(data[close_col], 'values') and len(data[close_col].shape) > 1:
                    close_data = data[close_col].iloc[:, 0]
                else:
                    close_data = data[close_col]
                
                ax.plot(data.index, close_data, label=ticker, color=colors[i % len(colors)], linewidth=2)
                valid_count += 1
        
        if valid_count == 0:
            self.draw_empty_chart("Veri bulunamadı")
            return
            
        ax.set_title("Fiyat Grafiği", color='#f1f5f9', fontsize=14, fontweight='bold')
        ax.set_xlabel("Tarih", color='#94a3b8')
        ax.set_ylabel("Fiyat (TL)", color='#94a3b8')
        ax.tick_params(colors='#94a3b8')
        ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f1f5f9')
        ax.grid(True, alpha=0.3, color='#334155')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        for spine in ax.spines.values():
            spine.set_color('#334155')
            
        self.lbl_summary.setText(f"{valid_count} hisse gösteriliyor")
        self.canvas.draw()

    def draw_returns_chart(self, data_map: Dict[str, pd.DataFrame]):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        
        colors = plt.cm.tab10.colors
        valid_count = 0
        
        for i, (ticker, data) in enumerate(data_map.items()):
            if data is not None and not data.empty:
                close_col = 'Close' if 'Close' in data.columns else data.columns[0]
                if hasattr(data[close_col], 'values') and len(data[close_col].shape) > 1:
                    close_data = data[close_col].iloc[:, 0]
                else:
                    close_data = data[close_col]
                
                returns = close_data.pct_change() * 100
                cumulative_returns = (1 + returns / 100).cumprod() * 100 - 100
                
                ax.plot(data.index, cumulative_returns, label=ticker, color=colors[i % len(colors)], linewidth=2)
                valid_count += 1
        
        if valid_count == 0:
            self.draw_empty_chart("Veri bulunamadı")
            return
            
        ax.axhline(y=0, color='#ef4444', linestyle='--', alpha=0.5)
        ax.set_title("Kümülatif Getiri (%)", color='#f1f5f9', fontsize=14, fontweight='bold')
        ax.set_xlabel("Tarih", color='#94a3b8')
        ax.set_ylabel("Getiri (%)", color='#94a3b8')
        ax.tick_params(colors='#94a3b8')
        ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f1f5f9')
        ax.grid(True, alpha=0.3, color='#334155')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        for spine in ax.spines.values():
            spine.set_color('#334155')
            
        self.lbl_summary.setText(f"{valid_count} hisse getiri karşılaştırması")
        self.canvas.draw()

    def draw_comparison_chart(self, data_map: Dict[str, pd.DataFrame]):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        
        colors = plt.cm.tab10.colors
        valid_count = 0
        
        for i, (ticker, data) in enumerate(data_map.items()):
            if data is not None and not data.empty:
                close_col = 'Close' if 'Close' in data.columns else data.columns[0]
                if hasattr(data[close_col], 'values') and len(data[close_col].shape) > 1:
                    close_data = data[close_col].iloc[:, 0]
                else:
                    close_data = data[close_col]
                
                normalized = (close_data / close_data.iloc[0]) * 100
                
                ax.plot(data.index, normalized, label=ticker, color=colors[i % len(colors)], linewidth=2)
                valid_count += 1
                
        if valid_count == 0:
            self.draw_empty_chart("Veri bulunamadı")
            return
            
        ax.axhline(y=100, color='#94a3b8', linestyle='--', alpha=0.5)
        ax.set_title("Normalize Karşılaştırma (Başlangıç=100)", color='#f1f5f9', fontsize=14, fontweight='bold')
        ax.set_xlabel("Tarih", color='#94a3b8')
        ax.set_ylabel("Değer", color='#94a3b8')
        ax.tick_params(colors='#94a3b8')
        ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f1f5f9')
        ax.grid(True, alpha=0.3, color='#334155')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        for spine in ax.spines.values():
            spine.set_color('#334155')
            
        self.lbl_summary.setText(f"{valid_count} hisse normalize karşılaştırma")
        self.canvas.draw()

    def draw_portfolio_pie(self, title: str, breakdown: List[Tuple[str, float]]):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        
        if not breakdown:
            self.draw_empty_chart("Portföyde pozisyon yok veya değer hesaplanamadı")
            return
            
        labels = [item[0] for item in breakdown]
        values = [item[1] for item in breakdown]
        
        colors = plt.cm.Set3.colors[:len(labels)]
        
        wedges, texts, autotexts = ax.pie(
            values, labels=labels, autopct='%1.1f%%',
            colors=colors, textprops={'color': '#f1f5f9', 'fontsize': 11}
        )
        
        for autotext in autotexts:
            autotext.set_color('#0f172a')
            autotext.set_fontweight('bold')
        
        ax.set_title(title, color='#f1f5f9', fontsize=14, fontweight='bold')
        
        total = sum(values)
        self.lbl_summary.setText(f"Toplam {len(breakdown)} pozisyon, ₺{total:,.2f}")
        self.canvas.draw()

    def save_chart(self, file_path: str):
        self.figure.savefig(file_path, facecolor='#0f172a', edgecolor='none', bbox_inches='tight', dpi=150)
