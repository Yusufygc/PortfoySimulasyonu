"""Yerel akıllı analiz motoru: API anahtarı yokken veya ağ hatasında gerçek portföy verileriyle karar desteği.

Danışman servisinin `call_tool` araçlarını kullanır; sonuç Markdown metni ve kullanılan araç listesidir.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from src.ui_qml.controllers.advisor_query_intent import is_optimization_query
from src.ui_qml.presenters.formatting import tr_money, tr_pct

logger = logging.getLogger(__name__)

TOOL_LABELS = {
    "get_portfolio_overview": "Portföy Genel Özeti",
    "get_allocation_and_risk": "Varlık Dağılımı ve Risk",
    "suggest_optimization": "Markowitz Optimizasyonu",
    "get_stock_overview": "Hisse Teknik & Fiyat Analizi",
}

_LOCAL_NOTE_OPTIMIZATION = (
    "*Not: Yerel analiz motoru çalıştırıldı. Gemini API anahtarı ekleyerek çoklu turlu etkileşimli danışmanlığı aktif edebilirsiniz.*"
)
_LOCAL_NOTE_GENERAL = (
    "*Not: Yerel analiz motoru çalıştırıldı. Gemini API anahtarı tanımlandığında model ile doğrudan serbest sohbet edebilirsiniz.*"
)
_DISCLAIMER = "**Yatırım Tavsiyesi Değildir (YTD).**"


def _call_tool(advisor: Any, name: str, args: Dict[str, Any], used_tools: List[Dict[str, str]]) -> Dict[str, Any]:
    """Aracı çağırır; başarılıysa `used_tools`'a ekler, hata olursa boş sonuç döner."""
    if not advisor:
        return {}
    try:
        data = advisor.call_tool(name, args)
        used_tools.append({"name": name, "label": TOOL_LABELS[name]})
        return data
    except Exception:
        logger.warning("Yerel analiz aracı başarısız: %s", name, exc_info=True)
        return {}


def _optimization_report(total_val: float, opt_data: Dict[str, Any]) -> str:
    suggestions = opt_data.get("suggestions", [])
    lines = [
        "### Modern Portföy Teorisi — Yeniden Dengeleme Analizi",
        "",
        f"Mevcut portföyünüzün toplam büyüklüğü **{tr_money(total_val)}** seviyesindedir. "
        f"Dengeli risk profili simülasyonuna göre portföyünüzün getiri/risk oranını maksimize etmek için aşağıdaki düzenlemeler önerilmektedir:",
        "",
    ]
    if suggestions:
        lines.append("| Hisse | Mevcut Pay | Hedef Pay | Değişim | Aksiyon |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for s in suggestions[:6]:
            sym = s.get("symbol", "").replace(".IS", "")
            cur_w = tr_pct(s.get("current_weight_pct"))
            opt_w = tr_pct(s.get("optimal_weight_pct"))
            chg = tr_pct(s.get("change_pct"), with_sign=True)
            act = s.get("action", "TUT")
            lines.append(f"| **{sym}** | {cur_w} | {opt_w} | {chg} | **{act}** |")
        lines.append("")
        lines.append(
            "**Stratejik Değerlendirme:** Portföyde ağırlığı yüksek olan hisselerden kâr realizasyonu "
            "yapılarak ağırlığı düşük kalan hisselere pay aktarılması genel portföy volatilitesini düşürecektir."
        )
    else:
        lines.append("Portföyünüzde henüz yeterli çeşitlilikte hisse senedi bulunmadığından optimizasyon matrisi oluşturulamadı.")

    lines.extend(["", _LOCAL_NOTE_OPTIMIZATION, "", _DISCLAIMER])
    return "\n".join(lines)


def _advisor_assessment(top3_weight: float, sharpe: float | None) -> List[str]:
    lines = ["#### Danışman Değerlendirmesi:"]
    if top3_weight > 60:
        lines.append(
            "- **Yüksek Yoğunlaşma Riski:** Portföyünüzün %60'ından fazlası ilk 3 hissede toplanmış durumda. "
            "Sektörel şoklara karşı dayanıklılığı artırmak için portföyü farklı sektörlere yaymanız önerilir."
        )
    else:
        lines.append(
            "- **Dengeli Varlık Dağılımı:** Hisselerinizin portföye dağılımı makul seviyelerde. Tek bir hisseye aşırı bağımlılık riski düşük."
        )

    if sharpe is not None and sharpe > 1.0:
        lines.append(
            "- **Güçlü Risk-Getiri Dengesi:** Sharpe oranınız 1.0 seviyesinin üzerinde, bu da aldığınız riskin getiri ile iyi dengelendiğini gösteriyor."
        )
    else:
        lines.append(
            "- **Getiri Potansiyeli:** Volatiliteye oranla getiri marjını yükseltmek için 'Optimizasyon' sekmesindeki rebalance modelini inceleyebilirsiniz."
        )
    return lines


def _general_report(overview_data: Dict[str, Any], risk_data: Dict[str, Any]) -> str:
    total_val = overview_data.get("total_value_try") or 0.0
    period_ret = overview_data.get("period_return_pct")
    benchmark_gap = overview_data.get("benchmark_gap_pct")
    largest_stock = overview_data.get("largest_position_label") or "Yok"
    largest_weight = overview_data.get("largest_position_weight_pct") or 0.0
    sharpe = risk_data.get("sharpe_ratio")
    volatility = risk_data.get("volatility_pct")
    max_dd = risk_data.get("max_drawdown_pct")
    top3_weight = risk_data.get("top_three_weight_pct") or 0.0

    lines = [
        "### Portföy Sağlık & Risk Durumu Raporu",
        "",
        f"Portföyünüzün toplam değeri **{tr_money(total_val)}** olup piyasa hareketlerine karşı genel görünümü şöyledir:",
        "",
        f"- **Dönem Getirisi:** {tr_pct(period_ret, with_sign=True)} "
        f"(BIST 100 Endeksine Göre: {tr_pct(benchmark_gap, with_sign=True)})",
        f"- **Yıllık Volatilite (Risk):** {tr_pct(volatility)}",
        f"- **Sharpe Oranı:** {f'{sharpe:.2f}' if sharpe is not None else 'N/A'} (Birim risk başına getiri kalitesi)",
        f"- **Maksimum Geri Çekilme (Drawdown):** {tr_pct(max_dd)}",
        f"- **En Büyük Pozisyon:** **{largest_stock.replace('.IS', '')}** ({tr_pct(largest_weight)})",
        f"- **İlk 3 Hisse Yoğunlaşması:** {tr_pct(top3_weight)}",
        "",
    ]
    lines.extend(_advisor_assessment(top3_weight, sharpe))
    lines.extend(["", _LOCAL_NOTE_GENERAL, "", _DISCLAIMER])
    return "\n".join(lines)


def generate_local_portfolio_analysis(advisor: Any, query: str) -> Tuple[str, List[Dict[str, str]]]:
    """Reel portföy verileriyle zengin karar desteği üretir: `(Markdown metin, kullanılan araçlar)`."""
    used_tools: List[Dict[str, str]] = []
    overview_data = _call_tool(advisor, "get_portfolio_overview", {}, used_tools)
    risk_data = _call_tool(advisor, "get_allocation_and_risk", {}, used_tools)

    # Soru Optimizasyon / Rebalance ile ilgiliyse
    if is_optimization_query(query):
        opt_data = _call_tool(advisor, "suggest_optimization", {"risk_label": "DENGELI"}, used_tools)
        return _optimization_report(overview_data.get("total_value_try") or 0.0, opt_data), used_tools

    return _general_report(overview_data, risk_data), used_tools
