"""Yerel akıllı analiz motoru: API anahtarı yokken veya ağ hatasında gerçek portföy verileriyle karar desteği.

Danışman servisinin `call_tool` araçlarını kullanır; sonuç Markdown metni ve kullanılan araç listesidir.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple

from src.ui_qml.controllers.advisor_query_intent import is_optimization_query
from src.ui_qml.presenters.formatting import tr_money, tr_number, tr_pct
from src.ui_qml.messages import msg

logger = logging.getLogger(__name__)

TOOL_LABELS = {
    "get_portfolio_overview": msg("advisor_local.portfoy_genel_ozeti"),
    "get_allocation_and_risk": msg("advisor_local.varlik_dagilimi_ve_risk"),
    "suggest_optimization": "Markowitz Optimizasyonu",
    "get_stock_overview": "Hisse Teknik & Fiyat Analizi",
}

_LOCAL_NOTE_OPTIMIZATION = (
    msg("advisor_local.not_yerel_analiz_motoru_calistirildi_gemini")
)
_LOCAL_NOTE_GENERAL = (
    msg("advisor_local.not_yerel_analiz_motoru_calistirildi_gemini_2")
)
_DISCLAIMER = msg("advisor_local.yatirim_tavsiyesi_degildir_ytd")


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
        msg("advisor_local.modern_portfoy_teorisi_yeniden_dengeleme_ana"),
        "",
        msg("advisor_local.mevcut_portfoyunuzun_toplam_buyuklugu_seviye", amount=tr_money(total_val)),
        "",
    ]
    if suggestions:
        lines.append(msg("advisor_local.hisse_mevcut_pay_hedef_pay_degisim"))
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
            msg("advisor_local.stratejik_degerlendirme_portfoyde_agirligi_y")
        )
    else:
        lines.append(msg("advisor_local.portfoyunuzde_henuz_yeterli_cesitlilikte_his"))

    lines.extend(["", _LOCAL_NOTE_OPTIMIZATION, "", _DISCLAIMER])
    return "\n".join(lines)


def _advisor_assessment(top3_weight: float, sharpe: float | None) -> List[str]:
    lines = [msg("advisor_local.danisman_degerlendirmesi")]
    if top3_weight > 60:
        lines.append(
            msg("advisor_local.yuksek_yogunlasma_riski_portfoyunuzun_60_ind")
        )
    else:
        lines.append(
            msg("advisor_local.dengeli_varlik_dagilimi_hisselerinizin_portf")
        )

    if sharpe is not None and sharpe > 1.0:
        lines.append(
            msg("advisor_local.guclu_risk_getiri_dengesi_sharpe_oraniniz")
        )
    else:
        lines.append(
            msg("advisor_local.getiri_potansiyeli_volatiliteye_oranla_getir")
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
        msg("advisor_local.portfoy_saglik_risk_durumu_raporu"),
        "",
        msg("advisor_local.portfoyunuzun_toplam_degeri_olup_piyasa_hare", amount=tr_money(total_val)),
        "",
        msg("advisor_local.donem_getirisi_bist_100_endeksine_gore", period=tr_pct(period_ret, with_sign=True), gap=tr_pct(benchmark_gap, with_sign=True)),
        msg("advisor_local.yillik_volatilite_risk", pct=tr_pct(volatility)),
        msg("advisor_local.sharpe_orani_birim_risk_basina_getiri", sharpe=tr_number(sharpe) if sharpe is not None else 'N/A'),
        msg("advisor_local.maksimum_geri_cekilme_drawdown", pct=tr_pct(max_dd)),
        msg("advisor_local.en_buyuk_pozisyon", ticker=largest_stock.replace('.IS', ''), weight=tr_pct(largest_weight)),
        msg("advisor_local.ilk_3_hisse_yogunlasmasi", pct=tr_pct(top3_weight)),
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
