"""Finansal hesaplarda tek kaynaktan kullanılan varsayımlar.

Sharpe/Sortino/Alfa (analiz ve karşılaştırma ekranları) ile Markowitz optimizasyonu aynı risksiz faizi
kullanır; böylece aynı portföyün Sharpe oranı ekrandan ekrana değişmez. Optimizasyon ekranında kullanıcı
değeri yalnızca o çalıştırma için değiştirebilir.
"""
from __future__ import annotations

# Yıllık risksiz faiz (TL mevduat/politika faizi düzeyi için muhafazakâr varsayım, ondalık: 0.40 = %40)
DEFAULT_ANNUAL_RISK_FREE_RATE = 0.40

# Yıllık işlem günü sayısı (yıllıklaştırma)
TRADING_DAYS_PER_YEAR = 252
