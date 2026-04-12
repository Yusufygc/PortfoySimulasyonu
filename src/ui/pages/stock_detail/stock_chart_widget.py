# src/ui/pages/stock_detail/stock_chart_widget.py

import logging
from datetime import date, timedelta
import yfinance as yf

from PyQt5.QtWidgets import QFrame, QVBoxLayout

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates

logger = logging.getLogger(__name__)

class StockChartWidget(QFrame):
    """Hisse fiyat grafiğini çizen bağımsız bileşen."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #0f172a; border-radius: 8px;")
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.figure = Figure(figsize=(8, 5), facecolor='#0f172a')
        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas)

    def draw_chart(self, current_ticker: str, current_stock_id, current_price, portfolio_service):
        if not current_ticker:
            return
            
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#0f172a')
        
        try:
            end_date = date.today()
            start_date = end_date - timedelta(days=180) 
            
            yf_ticker = current_ticker if "." in current_ticker else f"{current_ticker}.IS"
            data = yf.download(yf_ticker, start=start_date, end=end_date + timedelta(days=1), progress=False, auto_adjust=False)
            
            if data is not None and not data.empty:
                close_col = 'Close' if 'Close' in data.columns else data.columns[0]
                
                if hasattr(data[close_col], 'values') and len(data[close_col].shape) > 1:
                    close_data = data[close_col].iloc[:, 0]
                else:
                    close_data = data[close_col]
                    
                ax.plot(data.index, close_data, color='#3b82f6', linewidth=2.5)
                ax.fill_between(data.index, close_data, alpha=0.1, color='#3b82f6')
                
                # Dinamik Y-Ekseni Ölçeklendirme
                ymin = close_data.min()
                ymax = close_data.max()
                padding = (ymax - ymin) * 0.1 if ymax > ymin else ymax * 0.1
                ax.set_ylim(max(0, ymin - padding), ymax + padding)

                # 1. Ort. Maliyet Çizgisi (Varsa)
                if current_stock_id and portfolio_service:
                    portfolio = portfolio_service.get_current_portfolio()
                    pos = portfolio.positions.get(current_stock_id)
                    if pos and pos.average_cost:
                        ax.axhline(y=float(pos.average_cost), color='#f59e0b', linestyle='--', linewidth=1.0, alpha=0.7, label='Ort. Maliyet')

                # 2. Son Fiyat Çizgisi
                if current_price:
                    ax.axhline(y=float(current_price), color='#10b981', linestyle='-', linewidth=1, alpha=0.9, label=f'Güncel: {current_price:.2f}')

                ax.set_title(f"{current_ticker} - Fiyat Geçmişi", color='#f1f5f9', fontsize=14, fontweight='bold', pad=20)
                
                ax.grid(True, which='major', color='#f1f5f9', linestyle='-', alpha=0.05)
                ax.grid(True, which='minor', color='#f1f5f9', linestyle=':', alpha=0.02)
                ax.minorticks_on()
                
                ax.tick_params(axis='both', colors='#94a3b8', labelsize=10)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d %b'))

                ax.legend(facecolor='#1e293b', edgecolor='#334155', labelcolor='#f1f5f9', loc='upper left') 
                
                for spine in ax.spines.values():
                    spine.set_visible(False)
            else:
                ax.text(0.5, 0.5, "Veri bulunamadı", color='#94a3b8', ha='center', va='center')
                
        except Exception as e:
            logger.error(f"Grafik hatası: {e}")
            ax.text(0.5, 0.5, "Grafik yüklenemedi", color='#94a3b8', ha='center', va='center')
            
        self.figure.tight_layout()
        self.canvas.draw()
