"""
Finansal dashboard HTML üreticisi — orkestratör.

Grafik fonksiyonları: charts.py
Finansal tablo: finansal_tablo.py
Offline Plotly: ensure_patched_plotly_js() ile yerel JS kullanır (CDN yok).
"""
from __future__ import annotations

from typing import Any

import plotly.graph_objects as go

from src.ui.pages.comparison.utils.plotly_html import ensure_patched_plotly_js
from src.ui.pages.financials.utils.charts import (
    _chart_bedelsiz,
    _chart_bilanco,
    _chart_degerleme,
    _chart_dupont,
    _chart_fcf_vs_netkar,
    _chart_heatmap,
    _chart_isletme_sermaye,
    _chart_kpi_table,
    _chart_nakit_akis,
    _chart_net_borc,
    _chart_piotroski,
    _chart_reel_buyume,
    _chart_satis_breakdown,
    _chart_satis_favok,
    _chart_sezonsellik,
    _chart_temettu,
    _chart_waterfall,
    _fig_to_div,
)
from src.ui.pages.financials.utils.finansal_tablo import build_finansal_tablo_pane
from src.ui.pages.financials.utils.value_table import build_value_table

# ---------------------------------------------------------------------------
# CSS + JS (tab navigasyonu)
# ---------------------------------------------------------------------------

_CSS = (
    "*, *::before, *::after{box-sizing:border-box;margin:0;padding:0}"
    "html,body{background:#0f172a;color:#f1f5f9;font-family:Inter,'Segoe UI',sans-serif;padding:12px;overflow:hidden}"
    ".nav-container{background:#1e293b;border:1px solid #334155;border-radius:8px 8px 0 0;padding:10px 12px;margin-bottom:0}"
    ".cat-nav{display:flex;flex-wrap:wrap;gap:6px;margin-bottom:8px;padding-bottom:8px;border-bottom:1px solid #334155}"
    ".cat-btn{background:#0f172a;color:#94a3b8;border:1px solid #334155;border-radius:6px;padding:6px 14px;"
    "cursor:pointer;font-size:.82rem;font-weight:600;transition:all .15s ease}"
    ".cat-btn:hover{background:#273549;color:#f1f5f9}"
    ".cat-btn.active{background:#00D4FF1f;color:#00D4FF;border-color:#00D4FF}"
    ".sub-nav{display:none;flex-wrap:wrap;gap:5px}"
    ".sub-nav.active{display:flex}"
    ".tab-btn{background:#0f172a;color:#64748b;border:1px solid #334155;border-radius:4px;padding:5px 12px;"
    "cursor:pointer;font-size:.78rem;white-space:nowrap;transition:all .12s ease}"
    ".tab-btn:hover{background:#1e293b;color:#e2e8f0}"
    ".tab-btn.active{background:#38bdf822;color:#38bdf8;border-color:#38bdf8;font-weight:600}"
    ".tab-pane{display:none;border:1px solid #334155;border-top:none;border-radius:0 0 8px 8px;background:#0f172a;padding:12px}"
    ".tab-pane.active{display:block}"
    ".tab-btn svg, .cat-btn svg{vertical-align:-2px;margin-right:4px}"
    ".insight-box{display:flex;gap:10px;background:#1e293b;border-left:3px solid #00D4FF;"
    "border-radius:0 6px 6px 0;padding:10px 14px;margin:12px 0 4px;font-size:.8rem}"
    ".ib-icon{font-size:1.1rem;flex-shrink:0;line-height:1.5}"
    ".ib-body{color:#94a3b8;line-height:1.6}"
    ".ib-body b{color:#f1f5f9;display:block;margin-bottom:2px}"
    ".ib-body p{margin:0}"
    ".val-tbl{width:100%;border-collapse:collapse;font-size:.78rem;"
    "margin:12px 0;background:#0f172a;border:1px solid #334155;border-radius:6px;overflow:hidden}"
    ".val-tbl thead th{background:#0a1628;color:#64748b;text-align:right;"
    "padding:7px 10px;font-weight:600;border-bottom:1px solid #334155}"
    ".val-tbl thead th:first-child{text-align:left}"
    ".val-tbl tbody td{padding:6px 10px;border-bottom:1px solid #1e293b;"
    "color:#e2e8f0;text-align:right;font-family:'JetBrains Mono','Courier New',monospace}"
    ".val-tbl tbody td:first-child{text-align:left;font-family:inherit;color:#cbd5e1}"
    ".val-tbl tbody tr:last-child td{border-bottom:none}"
    ".val-tbl tbody tr:hover td{background:#1a2535}"
)

_JS = r"""
function showGroup(grpId, btn){
  document.querySelectorAll('.cat-btn').forEach(b=>b.classList.remove('active'));
  document.querySelectorAll('.sub-nav').forEach(s=>s.classList.remove('active'));
  btn.classList.add('active');
  const subNav = document.getElementById(grpId);
  if(subNav){
    subNav.classList.add('active');
    const firstTabBtn = subNav.querySelector('.tab-btn');
    if(firstTabBtn) firstTabBtn.click();
  }
}

function showTab(id, btn){
  document.querySelectorAll('.tab-pane').forEach(p=>p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
  const pane = document.getElementById(id);
  if(pane) pane.classList.add('active');
  btn.classList.add('active');
  setTimeout(()=>{
    if(pane){
      pane.querySelectorAll('.plotly-graph-div').forEach(el=>{
        if(window.Plotly) Plotly.Plots.resize(el);
      });
    }
  },30);
}
"""


# ---------------------------------------------------------------------------
# Inline SVG ikonlar — Tabler Icons MIT lisansı
# ---------------------------------------------------------------------------

_SVG_WRAP = (
    '<svg width="13" height="13" viewBox="0 0 24 24" fill="none" '
    'stroke="currentColor" stroke-width="1.6" '
    'stroke-linecap="round" stroke-linejoin="round">{}</svg> '
)

_IP: dict[str, str] = {
    "ftablo": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<rect x="3" y="5" width="18" height="14" rx="2"/>'
        '<path d="M3 10h18"/><path d="M10 3v18"/>'
    ),
    "kpi": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M3 12m0 1a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v6a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z"/>'
        '<path d="M9 8m0 1a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v10a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z"/>'
        '<path d="M15 4m0 1a1 1 0 0 1 1 -1h2a1 1 0 0 1 1 1v14a1 1 0 0 1 -1 1h-2a1 1 0 0 1 -1 -1z"/>'
    ),
    "satis": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M3 17l6 -6l4 4l8 -8"/><path d="M14 7l7 0l0 7"/>'
    ),
    "bilanco": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M3 21l18 0"/><path d="M3 10l18 0"/>'
        '<path d="M5 6l7 -3l7 3"/>'
        '<path d="M4 10l0 11"/><path d="M20 10l0 11"/>'
        '<path d="M8 14l0 3"/><path d="M12 14l0 3"/><path d="M16 14l0 3"/>'
    ),
    "netborc": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M3 5m0 3a3 3 0 0 1 3 -3h12a3 3 0 0 1 3 3v8a3 3 0 0 1 -3 3h-12a3 3 0 0 1 -3 -3z"/>'
        '<path d="M3 10l18 0"/><path d="M7 15l.01 0"/><path d="M11 15l2 0"/>'
    ),
    "waterfall": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M4 18v-4"/><path d="M8 18v-8"/>'
        '<path d="M12 18v-12"/><path d="M16 18v-7"/><path d="M20 18v-3"/>'
        '<path d="M4 10l4 -4l4 4l4 -5l4 4"/>'
    ),
    "fcf": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M3 21v-4a4 4 0 1 1 4 4h-4"/>'
        '<path d="M21 3v4a4 4 0 1 1 -4 -4h4"/>'
        '<path d="M3 11h12"/><path d="M9 3v12"/>'
    ),
    "nakit": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M3 3m0 2a2 2 0 0 1 2 -2h14a2 2 0 0 1 2 2v10a2 2 0 0 1 -2 2h-14a2 2 0 0 1 -2 -2z"/>'
        '<path d="M12 8m0 1a1 1 0 0 1 1 -1h0a1 1 0 0 1 1 1v4a1 1 0 0 1 -1 1h0a1 1 0 0 1 -1 -1z"/>'
        '<path d="M12 6l0 .01"/>'
    ),
    "heatmap": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<circle cx="5" cy="5" r="1"/><circle cx="12" cy="5" r="1"/>'
        '<circle cx="19" cy="5" r="1"/><circle cx="5" cy="12" r="1"/>'
        '<circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>'
        '<circle cx="5" cy="19" r="1"/><circle cx="12" cy="19" r="1"/>'
        '<circle cx="19" cy="19" r="1"/>'
    ),
    "dupont": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M12 3l8 4.5v9l-8 4.5l-8 -4.5v-9z"/>'
        '<path d="M12 12l8 -4.5"/><path d="M12 12v9"/>'
        '<path d="M12 12l-8 -4.5"/>'
    ),
    "isletme": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<circle cx="12" cy="12" r="3"/>'
        '<path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06 .06a2 2 0 0 1 -2.83 2.83l-.06 -.06'
        'a1.65 1.65 0 0 0 -1.82 -.33a1.65 1.65 0 0 0 -1 1.51v.17a2 2 0 0 1 -4 0v-.09'
        'a1.65 1.65 0 0 0 -1 -1.51a1.65 1.65 0 0 0 -1.82 .33l-.06 .06a2 2 0 0 1 -2.83 -2.83'
        'l.06 -.06a1.65 1.65 0 0 0 .33 -1.82a1.65 1.65 0 0 0 -1.51 -1h-.17a2 2 0 0 1 0 -4h.09'
        'a1.65 1.65 0 0 0 1.51 -1a1.65 1.65 0 0 0 -.33 -1.82l-.06 -.06a2 2 0 0 1 2.83 -2.83'
        'l.06 .06a1.65 1.65 0 0 0 1.82 .33h.08a1.65 1.65 0 0 0 1 -1.51v-.17a2 2 0 0 1 4 0v.09'
        'a1.65 1.65 0 0 0 1 1.51h.08a1.65 1.65 0 0 0 1.82 -.33l.06 -.06a2 2 0 0 1 2.83 2.83'
        'l-.06 .06a1.65 1.65 0 0 0 -.33 1.82v.08a1.65 1.65 0 0 0 1.51 1h.17a2 2 0 0 1 0 4h-.09'
        'a1.65 1.65 0 0 0 -1.51 1z"/>'
    ),
    "fscore": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M12 2l3.09 6.26l6.91 1l-5 4.87l1.18 6.87l-6.18 -3.25'
        'l-6.18 3.25l1.18 -6.87l-5 -4.87l6.91 -1l3.09 -6.26z"/>'
    ),
    "sezon": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<rect x="4" y="5" width="16" height="16" rx="2"/>'
        '<path d="M16 3v4"/><path d="M8 3v4"/>'
        '<path d="M4 11h16"/><path d="M11 15h1"/><path d="M12 15v3"/>'
    ),
    "temettu": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M12 12m-3 0a3 3 0 1 0 6 0a3 3 0 1 0 -6 0"/>'
        '<path d="M12 12m-8 0a8 8 0 1 0 16 0a8 8 0 1 0 -16 0"/>'
        '<path d="M12 4v1"/><path d="M12 19v1"/>'
        '<path d="M4 12h1"/><path d="M19 12h1"/>'
    ),
    "reel": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M3 17l4 -4l4 4l4 -10l4 4"/>'
    ),
    "deger": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<path d="M6 4m0 2a2 2 0 0 1 2 -2h8a2 2 0 0 1 2 2v12a2 2 0 0 1 -2 2h-8a2 2 0 0 1 -2 -2z"/>'
        '<path d="M12 9v6"/><path d="M9 12h6"/>'
    ),
    "bedelsiz": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<circle cx="12" cy="12" r="1"/>'
        '<circle cx="12" cy="12" r="5"/>'
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M12 3l0 3"/><path d="M12 18l0 3"/>'
        '<path d="M3 12l3 0"/><path d="M18 12l3 0"/>'
    ),
    "satisbd": (
        '<path stroke="none" d="M0 0h24v24H0z" fill="none"/>'
        '<circle cx="12" cy="12" r="9"/>'
        '<path d="M3.6 9h16.8"/><path d="M3.6 15h16.8"/>'
        '<path d="M11.5 3a17 17 0 0 0 0 18"/>'
        '<path d="M12.5 3a17 17 0 0 1 0 18"/>'
    ),
}


def _ic(tab_id: str) -> str:
    return _SVG_WRAP.format(_IP.get(tab_id, ""))


# ---------------------------------------------------------------------------
# Teknik bilgi kutucukları (sekme → HTML snippet)
# ---------------------------------------------------------------------------

_INSIGHTS: dict[str, str] = {
    "kpi": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>KPI Özeti Nasıl Okunur?</b>"
        "<p>Her satır bir temel finansal göstergeyi dönem bazında listeler. "
        "▲ yeşil ok = önceki döneme göre artış, ▼ kırmızı = düşüş. "
        "Satışlar ve FAVÖK büyürken net kar marjı sıkışıyorsa maliyet baskısı sinyali olabilir.</p>"
        "</div></div>"
    ),
    "satis": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Satışlar & Marjlar Nasıl Okunur?</b>"
        "<p>Mavi çubuklar satış gelirini (sol eksen), turuncu çizgi FAVÖK marjını, "
        "noktalı yeşil çizgi brüt marjı gösterir (sağ eksen). "
        "Çubuklar büyürken marjlar daralıyorsa büyüme kârsız olabilir.</p>"
        "</div></div>"
    ),
    "bilanco": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Bilanço Nasıl Okunur?</b>"
        "<p>Dönen varlık / kısa vadeli yükümlülük oranının (cari oran) 1,5x üzerinde "
        "olması likidite sağlığı göstergesidir. Özkaynaklar büyürken borçlar "
        "sabit kalıyorsa finansal kaldıraç kontrol altında demektir.</p>"
        "</div></div>"
    ),
    "netborc": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Net Borç Nasıl Okunur?</b>"
        "<p>Net Borç/FAVÖK &lt; 2x genellikle yönetilebilir kaldıraç, "
        "&gt; 4x dikkat eşiği olarak kabul edilir. "
        "Net nakit pozisyonu (negatif net borç) güçlü bilançonun işaretidir.</p>"
        "</div></div>"
    ),
    "waterfall": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Gelir Köprüsü Nasıl Okunur?</b>"
        "<p>Satışlardan başlayarak her kâr kaleminin bir öncekine katkısını gösterir. "
        "Brüt kar → Faaliyet karı farkı operasyonel giderler, "
        "Faaliyet karı → Net kar farkı ise faiz ve vergi yükünü yansıtır.</p>"
        "</div></div>"
    ),
    "fcf": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>FCF vs Net Kar Nasıl Okunur?</b>"
        "<p>Serbest nakit akımının (FCF) net kara yakın veya üzerinde olması "
        "yüksek kazanç kalitesini gösterir. Büyük negatif fark şirketin kâr "
        "açıkladığı hâlde nakit üretemediğine işaret edebilir.</p>"
        "</div></div>"
    ),
    "nakit": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Nakit Akış Nasıl Okunur?</b>"
        "<p>İşletme faaliyetlerinden nakit (mavi) > capex (kırmızı mutlak) "
        "organik büyüme kapasitesini, pozitif FCF (yeşil) ise sermaye verimliliğini "
        "gösterir. Negatif işletme CF sürekli ise temel işin nakit üretemediğini işaret eder.</p>"
        "</div></div>"
    ),
    "heatmap": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>YoY Isı Haritası Nasıl Okunur?</b>"
        "<p>Her hücre o metriğin yıllık % değişimini gösterir. "
        "Koyu yeşil = güçlü büyüme, koyu kırmızı = daralma. "
        "±50% sınırlarında renk doyar; sütunlar geneli kırmızıysa o dönemde "
        "baskı yaşandığına işaret eder.</p>"
        "</div></div>"
    ),
    "dupont": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>DuPont Analizi Nasıl Okunur?</b>"
        "<p>ROE = Net Kar Marjı × Varlık Devir Hızı × Finansal Kaldıraç. "
        "Hangi bileşenin ROE'yi sürüklediğini görmek için üç faktörün trendini karşılaştırın. "
        "Kaldıraçtan beslenen ROE artışı riskli; marj ve devir hızından gelen sürdürülebilirdir.</p>"
        "</div></div>"
    ),
    "isletme": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>İşletme Sermayesi Döngüsü Nasıl Okunur?</b>"
        "<p>CCC (Nakit Dönüşüm Döngüsü) = DSO + DIO − DPO. "
        "CCC ne kadar kısa olursa şirket nakdini o kadar hızlı döndürür; "
        "negatif CCC (örn. büyük perakendeciler) iş modelinin güçlü nakit dinamiğine işaret eder.</p>"
        "</div></div>"
    ),
    "fscore": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Piotroski F-Skoru Nasıl Okunur?</b>"
        "<p>9 ikili kriter üzerinden toplam skor (0-9). "
        "≥ 7 güçlü finansal sağlık, ≤ 3 zayıf sinyali. "
        "Kârlılık, finansman yapısı ve operasyonel verimlilik alt kriterlerini "
        "incelemek için 🔍 Piotroski detay satırlarına bakın.</p>"
        "</div></div>"
    ),
    "sezon": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Sezonsellik Nasıl Okunur?</b>"
        "<p>Her yılın çeyreklik (Q1-Q4) satışları gruplandırılarak karşılaştırılır. "
        "Belirli çeyreklerde tutarlı yüksek satış sezonsal güç anlamına gelir. "
        "Yıldan yıla aynı çeyrekte büyüme görülmesi organik talebi doğrular.</p>"
        "</div></div>"
    ),
    "temettu": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Temettü Analizi Nasıl Okunur?</b>"
        "<p>Dağıtım oranı (payout ratio) &lt; %60 sürdürülebilir temettü sinyali, "
        "&gt; %80 kâr kalitesi veya büyüme yatırımı için baskı anlamına gelebilir. "
        "Temettünün FCF'den finanse edilip edilmediğini nakit akış sekmesiyle karşılaştırın.</p>"
        "</div></div>"
    ),
    "reel": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Reel Büyüme Nasıl Okunur?</b>"
        "<p>Nominal büyüme oranından TÜFE enflasyonu çıkarılarak satın alma gücü cinsinden "
        "büyüme hesaplanır (Fisher denklemi yaklaşımı). "
        "Reel büyüme pozitifse şirket enflasyonun üzerinde gerçek değer üretiyor demektir.</p>"
        "</div></div>"
    ),
    "deger": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Değerleme Nasıl Okunur?</b>"
        "<p>F/K ve EV/FAVÖK aynı sektördeki rakiplerle karşılaştırılarak yorumlanmalıdır. "
        "Düşük çarpan tek başına ucuzluk değil, büyüme beklentisi veya risk priminin "
        "fiyatlandırması da olabilir. PD/DD &lt; 1 maddi değerin altında işlem anlamına gelir.</p>"
        "</div></div>"
    ),
    "bedelsiz": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Bedelsiz Potansiyel Nasıl Okunur?</b>"
        "<p>Enflasyon muhasebesi (TMS 29) uygulanan bilançoda özkaynaklar reel bazda "
        "güncellenir; bu durum bedelsiz artırım potansiyelini doğrudan etkiler. "
        "Yeşil ✓ etiketi TMS 29 uygulandığını, turuncu ⚠ nominal değerlerin kullanıldığını gösterir.</p>"
        "</div></div>"
    ),
    "satisbd": (
        "<div class='insight-box'><span class='ib-icon'>📌</span>"
        "<div class='ib-body'><b>Satış Kırılımı Nasıl Okunur?</b>"
        "<p>Yurt içi / yurt dışı satış dağılımı ihracat oranını ve coğrafi çeşitlendirmeyi "
        "gösterir. Yüksek ihracat oranı döviz geliri sağlar; "
        "kur güçlenirse yurt dışı gelirlerin TRY karşılığı artar.</p>"
        "</div></div>"
    ),
}


# ---------------------------------------------------------------------------
# Yardımcı değer tabloları — sekme → (metric_key, label, fmt, scale)
# ---------------------------------------------------------------------------

_TABLE_ROWS: dict[str, list[tuple[str, str, str, float]]] = {
    "satis": [
        ("satis",          "Satışlar (mn TRY)", ",.0f", 1e6),
        ("favok",          "FAVÖK (mn TRY)",    ",.0f", 1e6),
        ("favok_marji",    "FAVÖK Marjı %",     ".2f",  1),
        ("brut_kar_marji", "Brüt Marj %",       ".2f",  1),
    ],
    "netborc": [
        ("net_borc",       "Net Borç (mn TRY)", ",.0f", 1e6),
        ("net_borc_favok", "Net Borç/FAVÖK",    ".2f",  1),
    ],
    "fcf": [
        ("fcf",     "FCF (mn TRY)",     ",.0f", 1e6),
        ("net_kar", "Net Kar (mn TRY)", ",.0f", 1e6),
    ],
    "nakit": [
        ("isletme_cf", "İşletme CF (mn TRY)", ",.0f", 1e6),
        ("fcf",        "FCF (mn TRY)",        ",.0f", 1e6),
        ("capex",      "Capex (mn TRY)",      ",.0f", 1e6),
    ],
    "dupont": [
        ("dupont_net_kar_marji", "Net Kar Marjı %",   ".2f", 1),
        ("dupont_varlik_devir",  "Varlık Devir Hızı", ".2f", 1),
        ("dupont_fin_kaldirac",  "Finansal Kaldıraç", ".2f", 1),
        ("dupont_roe",           "ROE %",             ".2f", 1),
    ],
    "isletme": [
        ("dso", "DSO — Alacak Tahsil Süresi (gün)", ".0f", 1),
        ("dio", "DIO — Stok Tutma Süresi (gün)",     ".0f", 1),
        ("dpo", "DPO — Borç Ödeme Süresi (gün)",     ".0f", 1),
        ("ccc", "CCC — Nakit Dönüşüm Döngüsü (gün)", ".0f", 1),
    ],
    "temettu": [
        ("temettu_odeme", "Temettü Ödemesi (mn TRY)", ",.0f", 1e6),
        ("dagitim_orani", "Dağıtım Oranı %",          ".2f",  1),
    ],
    "bedelsiz": [
        ("bedelsiz_potansiyel_x",   "Bedelsiz Potansiyel (x)",  ".2f",  1),
        ("bedelsiz_potansiyel_pct", "Bedelsiz Potansiyel %",    ".2f",  1),
        ("ozkaynak",                "Özkaynak (mn TRY)",        ",.0f", 1e6),
        ("odenmis_sermaye",         "Ödenmiş Sermaye (mn TRY)", ",.0f", 1e6),
    ],
    "satisbd": [
        ("yurtici_satis",  "Yurtiçi Satış (mn TRY)",  ",.0f", 1e6),
        ("yurtdisi_satis", "Yurtdışı Satış (mn TRY)", ",.0f", 1e6),
        ("ihracat_orani",  "İhracat Oranı %",         ".2f",  1),
    ],
}


def _value_table_for(tid: str, m: dict, n: int) -> str:
    rows = _TABLE_ROWS.get(tid)
    if not rows:
        return ""
    return build_value_table(m, n, rows)


def _content(x: go.Figure | str) -> str:
    return x if isinstance(x, str) else _fig_to_div(x)


def build_dashboard(m: dict[str, Any], n_periods: int = 8) -> str:
    """
    Tek HTML dosyası olarak finansal dashboard üret (18 sekme, 4 ana grup).
    Plotly JS yerel dosyadan yüklenir (CDN bağımlılığı yok).
    """
    ticker = m.get("ticker", "")

    groups = [
        ("grp-1", "📋 Finansal Tablolar & Özet", [
            ("ftablo",    f"{_ic('ftablo')}Finansal Tablo",     build_finansal_tablo_pane(m, n_periods)),
            ("kpi",       f"{_ic('kpi')}KPI Özeti",            _chart_kpi_table(m, n_periods)),
            ("bilanco",   f"{_ic('bilanco')}Bilanço",          _chart_bilanco(m, n_periods)),
            ("waterfall", f"{_ic('waterfall')}Gelir Köprüsü",  _chart_waterfall(m, n_periods)),
        ]),
        ("grp-2", "📈 Performans & Büyüme", [
            ("satis",     f"{_ic('satis')}Satışlar & Marjlar", _chart_satis_favok(m, n_periods)),
            ("satisbd",   f"{_ic('satisbd')}Satış Kırılımı",   _chart_satis_breakdown(m, n_periods)),
            ("sezon",     f"{_ic('sezon')}Sezonsellik",        _chart_sezonsellik(m, n_periods)),
            ("reel",      f"{_ic('reel')}Reel Büyüme",         _chart_reel_buyume(m, n_periods)),
            ("heatmap",   f"{_ic('heatmap')}YoY Isı Haritası", _chart_heatmap(m, n_periods)),
        ]),
        ("grp-3", "📊 Kârlılık & Değerleme", [
            ("deger",     f"{_ic('deger')}Değerleme",          _chart_degerleme(m, n_periods)),
            ("dupont",    f"{_ic('dupont')}DuPont",            _chart_dupont(m, n_periods)),
            ("fcf",       f"{_ic('fcf')}FCF vs Net Kar",       _chart_fcf_vs_netkar(m, n_periods)),
            ("temettu",   f"{_ic('temettu')}Temettü",          _chart_temettu(m, n_periods)),
        ]),
        ("grp-4", "🛡️ Borç, Likidite & Kalite", [
            ("netborc",   f"{_ic('netborc')}Net Borç",         _chart_net_borc(m, n_periods)),
            ("nakit",     f"{_ic('nakit')}Nakit Akış",         _chart_nakit_akis(m, n_periods)),
            ("isletme",   f"{_ic('isletme')}İşletme Sermayesi",_chart_isletme_sermaye(m, n_periods)),
            ("fscore",    f"{_ic('fscore')}Piotroski",         _chart_piotroski(m, n_periods)),
            ("bedelsiz",  f"{_ic('bedelsiz')}Bedelsiz Pot.",   _chart_bedelsiz(m, n_periods)),
        ]),
    ]

    cat_buttons = []
    sub_navs = []
    panes = []

    is_first_tab = True
    for g_idx, (gid, gtitle, gtabs) in enumerate(groups):
        cat_active = " active" if g_idx == 0 else ""
        cat_buttons.append(
            f"<button class='cat-btn{cat_active}' onclick=\"showGroup('{gid}',this)\">{gtitle}</button>"
        )

        sub_btns = []
        for t_idx, (tid, lbl, content) in enumerate(gtabs):
            tab_active = " active" if is_first_tab else ""
            sub_btns.append(
                f"<button class='tab-btn{tab_active}' onclick=\"showTab('{tid}',this)\">{lbl}</button>"
            )
            panes.append(
                f"<div id='{tid}' class='tab-pane{tab_active}'>"
                + _content(content)
                + _value_table_for(tid, m, n_periods)
                + _INSIGHTS.get(tid, "")
                + "</div>"
            )
            is_first_tab = False

        sub_nav_active = " active" if g_idx == 0 else ""
        sub_navs.append(
            f"<div id='{gid}' class='sub-nav{sub_nav_active}'>{''.join(sub_btns)}</div>"
        )

    nav_html = (
        "<div class='nav-container'>"
        f"<div class='cat-nav'>{''.join(cat_buttons)}</div>"
        + "".join(sub_navs)
        + "</div>"
    )

    js_path     = ensure_patched_plotly_js()
    js_file_url = js_path.replace("\\", "/")
    if not js_file_url.startswith("file://"):
        js_file_url = "file:///" + js_file_url

    return (
        "<!DOCTYPE html>\n<html lang='tr'>\n<head>\n"
        "<meta charset='utf-8'>\n"
        f"<title>{ticker} — Finansal Dashboard</title>\n"
        f"<script src='{js_file_url}'></script>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n<body>\n"
        f"{nav_html}\n"
        + "".join(panes)
        + f"\n<script>\n{_JS}\n</script>\n"
        "</body>\n</html>"
    )
