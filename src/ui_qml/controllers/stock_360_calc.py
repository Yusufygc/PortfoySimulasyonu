"""
Stock 360 Calculators — Bilanço, rasyo, nakit akışı, DuPont ve ortaklık analizi
için fintech hesaplama ve veri dönüştürme fonksiyonları.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from src.domain.models.shareholder import ShareholderSnapshot
from src.ui_qml.controllers.stock_360_formatters import (
    DONUT_COLORS,
    format_currency,
    format_price,
)

logger = logging.getLogger(__name__)


def _series_value(f: Dict[str, Any], key: str, period: str) -> Any:
    """`f[key]` bir dönem sözlüğüyse `period` değerini, değilse None döndürür."""
    series = f.get(key, {})
    return series.get(period) if isinstance(series, dict) else None


def _format_or_dash(value: Any, template: str) -> str:
    return template.format(value) if value is not None else "—"


def _format_positive(value: Any, template: str, otherwise: str) -> str:
    return template.format(value) if value is not None and value > 0 else otherwise


def parse_valuation_ratios(f: Dict[str, Any]) -> Dict[str, str]:
    """Değerleme ve rasyo göstergelerini sözlükten ayrıştırıp metinsel formatlara çevirir."""
    mv = f.get("_market_val", {}) or {}
    p0 = f.get("periods", [""])[0]

    fk = mv.get("fk")
    market_cap = mv.get("market_cap")
    pio = _series_value(f, "piotroski", p0)

    return {
        "pe_ratio": _format_positive(fk, "{:.1f}", "—" if fk is None else "Negatif"),
        "pb_ratio": _format_or_dash(mv.get("pddd"), "{:.2f}"),
        "ev_ebitda": _format_positive(mv.get("ev_favok"), "{:.1f}", "—"),
        "div_yield": _format_positive(mv.get("temettu_verimi"), "%{:.2f}", "%0.00"),
        "market_cap_str": format_currency(market_cap) if market_cap is not None else "—",
        "roe": _format_or_dash(_series_value(f, "roe", p0), "%{:.1f}"),
        "net_debt_ebitda": _format_or_dash(_series_value(f, "net_borc_favok_ttm", p0), "{:.2f}"),
        "piotroski_score": f"{pio}/9" if pio is not None else "—",
        "current_ratio": _format_or_dash(_series_value(f, "cari_oran", p0), "{:.2f}"),
    }


def compute_financial_bars(
    raw_data: Dict[str, Any],
    periods: List[str],
    active_tab: str,
) -> Tuple[List[Dict[str, Any]], str]:
    """Seçili sekmeye ('satis', 'brut_kar', 'favok', 'net_kar') göre çubuk grafik verisini ve özetini üretir."""
    if not raw_data:
        return [], ""

    metric_key = {
        "satis": "satis_ceyrek",
        "brut_kar": "brut_kar",
        "favok": "favok_ceyrek",
        "net_kar": "net_kar_ceyrek",
    }.get(active_tab, "satis_ceyrek")

    metric_name = {
        "satis": "Net Satışlar",
        "brut_kar": "Brüt Kâr",
        "favok": "FAVÖK",
        "net_kar": "Net Kâr",
    }.get(active_tab, "Net Satışlar")

    series = raw_data.get(metric_key, {})
    sub_periods = periods[:6]  # Son 6 çeyrek
    # Kronolojik sıra (eskiden yeniye doğru: soldan sağa)
    chronological_periods = list(reversed(sub_periods))

    bars = []
    max_val = 1.0
    for p in chronological_periods:
        v = series.get(p)
        if v is not None:
            max_val = max(max_val, abs(float(v)))

    for p in chronological_periods:
        v = series.get(p)
        val_float = float(v) if v is not None else 0.0
        bars.append({
            "period": p,
            "value": val_float,
            "ratio": min(1.0, abs(val_float) / max_val) if max_val > 0 else 0.0,
            "amount": format_currency(val_float) if v is not None else "—",
            "isPositive": val_float >= 0,
        })

    summary = ""
    if bars:
        last_bar = bars[-1]
        summary = f"{metric_name} ({last_bar['period']}): {last_bar['amount']}"

    return bars, summary


def _prior_year_period(period: str) -> str:
    """'2026/3' -> '2025/3'; biçim bozuksa ValueError yükseltir."""
    year, quarter = period.split("/")
    return f"{int(year) - 1}/{quarter}"


def _revenue_chart_items(satis_c, net_c, margin_c, chronological_periods) -> List[Dict[str, Any]]:
    max_rev = 1.0
    for p in chronological_periods:
        max_rev = max(max_rev, float(satis_c.get(p) or 0.0))

    chart_items = []
    for p in chronological_periods:
        rev_val = float(satis_c.get(p) or 0.0)
        net_val = float(net_c.get(p) or 0.0)
        mg_val = float(margin_c.get(p) or 0.0)
        chart_items.append({
            "period": p,
            "revenue": rev_val,
            "revenueStr": format_currency(rev_val),
            "revenue_str": format_currency(rev_val),
            "netIncome": net_val,
            "netIncomeStr": format_currency(net_val),
            "net_income_str": format_currency(net_val),
            "margin": mg_val,
            "marginStr": f"%{mg_val:.1f}",
            "margin_str": f"%{mg_val:.1f}",
            "isProfitable": net_val >= 0,
            "ratio": min(1.0, rev_val / max_rev) if max_rev > 0 else 0.0,
            "profitRatio": min(1.0, abs(net_val) / max_rev) if max_rev > 0 else 0.0,
        })
    return chart_items


def _revenue_yoy_growth(satis_c, period: str, last_rev: float) -> Optional[Tuple[str, bool]]:
    """Aynı çeyreğin bir önceki yıla göre ciro büyümesi (metin, pozitif mi); hesaplanamazsa None."""
    try:
        prev_rev = satis_c.get(_prior_year_period(period))
        if prev_rev and prev_rev > 0:
            yoy_growth = (last_rev - prev_rev) / prev_rev * 100.0
            is_pos = yoy_growth >= 0
            return f"{'+' if is_pos else ''}{yoy_growth:.1f}%", is_pos
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        logger.debug("Yıllık ciro büyümesi hesaplanamadı: %s", exc)
    return None


def compute_revenue_chart(
    metrics: Dict[str, Any],
    active_periods: List[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Gelir & kârlılık grafik serisini ve son çeyrek KPI rozetlerini hesaplar."""
    satis_c = _series_with_fallback(metrics, "satis_ceyrek", "satis")
    net_c = _series_with_fallback(metrics, "net_kar_ceyrek", "net_kar")
    margin_c = metrics.get("net_kar_marji", {})

    chart_items = _revenue_chart_items(satis_c, net_c, margin_c, list(reversed(active_periods)))

    kpis = {
        "latest_quarter_revenue": "—",
        "latest_quarter_net_income": "—",
        "latest_quarter_margin": "—",
        "revenue_yoy_growth": "—",
        "is_revenue_yoy_positive": True,
    }

    if active_periods:
        p0 = active_periods[0]
        last_rev = float(satis_c.get(p0) or 0.0)
        kpis["latest_quarter_revenue"] = format_currency(last_rev)
        kpis["latest_quarter_net_income"] = format_currency(float(net_c.get(p0) or 0.0))
        kpis["latest_quarter_margin"] = f"%{float(margin_c.get(p0) or 0.0):.2f}"

        yoy = _revenue_yoy_growth(satis_c, p0, last_rev)
        if yoy is not None:
            kpis["revenue_yoy_growth"], kpis["is_revenue_yoy_positive"] = yoy

    return chart_items, kpis


def _first_period_with_data(metrics: Dict[str, Any], keys: Tuple[str, ...], periods: List[str]) -> str:
    """Verilen serilerden en az birinde değeri olan ilk dönem; yoksa en yeni dönem."""
    for p in periods:
        if any(metrics.get(key, {}).get(p) is not None for key in keys):
            return p
    return periods[0]


def _series_with_fallback(m: Dict[str, Any], primary: str, fallback: str) -> Dict[str, Any]:
    return m.get(primary, {}) or m.get(fallback, {})


def _statement_values(m: Dict[str, Any], period: str) -> Tuple[float, float, float, float]:
    """(satış, net kâr, toplam varlık, özkaynak) son çeyrek değerleri; eksikler 0."""
    satis_c = _series_with_fallback(m, "satis_ceyrek", "satis")
    net_c = _series_with_fallback(m, "net_kar_ceyrek", "net_kar")
    return (
        float(satis_c.get(period) or 0.0),
        float(net_c.get(period) or 0.0),
        float(m.get("toplam_varlik", {}).get(period) or 0.0),
        float(m.get("ozkaynak", {}).get(period) or 0.0),
    )


def _dupont_from_statements(m: Dict[str, Any], period: str, current: Tuple[Any, Any, Any, Any]) -> Tuple[Any, Any, Any, Any]:
    """TTM DuPont değerleri yoksa son çeyrek bilanço kalemlerinden türetir; (marj, devir, kaldıraç, ROE) döndürür."""
    nm, at, fl, roe = current
    s_val, n_val, tv_val, ozk_val = _statement_values(m, period)
    if s_val > 0:
        nm = (n_val / s_val) * 100.0
        if tv_val > 0:
            at = (s_val * 4.0) / tv_val  # Yıllıklandırılmış devir
    if ozk_val > 0 and tv_val > 0:
        fl = tv_val / ozk_val
    if nm is not None and at is not None and fl is not None:
        roe = nm * at * fl  # marj zaten yüzde: %marj x devir x kaldıraç = %ROE
    return nm, at, fl, roe


def _piotroski_band(score: int) -> Tuple[str, str]:
    if score >= 7:
        return "Yüksek Finansal Güç", "#089981"
    if score >= 4:
        return "Dengeli Finansal Yapı", "#2962ff"
    return "Baskılanmış Risk Bölgesi", "#f23645"


def compute_dupont_data(
    metrics: Dict[str, Any],
    active_periods: List[str],
) -> Dict[str, Any]:
    """DuPont kârlılık kırılımı (Net Kâr Marjı, Varlık Devri, Kaldıraç, ROE, Piotroski) verilerini hesaplar."""
    if not active_periods:
        return {}

    m = metrics
    dup_p = _first_period_with_data(m, ("dupont_net_kar_marji",), active_periods)

    dup_nm = m.get("dupont_net_kar_marji", {}).get(dup_p)
    dup_at = m.get("dupont_varlik_devir", {}).get(dup_p)
    dup_fl = m.get("dupont_fin_kaldirac", {}).get(dup_p)
    dup_roe = m.get("dupont_roe", {}).get(dup_p)
    pio = m.get("piotroski", {}).get(dup_p)

    # Fallback: TTM hesaplanamamışsa son çeyrek bilanço kalemlerinden türet
    if dup_nm is None:
        dup_nm, dup_at, dup_fl, dup_roe = _dupont_from_statements(m, dup_p, (dup_nm, dup_at, dup_fl, dup_roe))

    pio_score = int(pio) if pio is not None else 7
    pio_status, pio_color = _piotroski_band(pio_score)

    return {
        "netMargin": _format_or_dash(dup_nm, "%{:.2f}"),
        "assetTurnover": _format_or_dash(dup_at, "{:.2f}x"),
        "financialLeverage": _format_or_dash(dup_fl, "{:.2f}x"),
        "roe": _format_or_dash(dup_roe, "%{:.2f}"),
        "piotroski": f"{pio_score}/9",
        "piotroskiStatus": pio_status,
        "piotroskiColor": pio_color,
    }


def compute_cash_flow_data(
    metrics: Dict[str, Any],
    active_periods: List[str],
) -> Dict[str, Any]:
    """Nakit akışı ve borçluluk göstergelerini hesaplar."""
    if not active_periods:
        return {}

    m = metrics
    cf_p = _first_period_with_data(m, ("isletme_cf", "net_borc"), active_periods)

    ocf = m.get("isletme_cf", {}).get(cf_p)
    cpx = m.get("capex", {}).get(cf_p)
    fcf_val = m.get("fcf", {}).get(cf_p)
    nb = m.get("net_borc", {}).get(cf_p)
    nb_fav = m.get("net_borc_favok_ttm", {}).get(cf_p)

    is_safe = (nb_fav is None or nb_fav < 2.5)
    return {
        "operatingCf": format_currency(ocf),
        "capex": format_currency(cpx),
        "fcf": format_currency(fcf_val),
        "netDebt": format_currency(nb),
        "netDebtEbitda": _format_or_dash(nb_fav, "{:.2f}x"),
        "isDebtSafe": is_safe,
        "debtStatus": "Sürdürülebilir & Sağlıklı" if is_safe else "Yüksek Borçluluk",
    }


_STATEMENT_HEADER_KEYWORDS = (
    "DÖNEN VARLIKLAR", "DURAN VARLIKLAR", "KISA VADELİ YÜKÜMLÜLÜKLER",
    "UZUN VADELİ YÜKÜMLÜLÜKLER", "ÖZKAYNAKLAR", "TOPLAM VARLIKLAR",
    "TOPLAM KAYNAKLAR", "SÜRDÜRÜLEN FAALİYETLER", "DÖNEM KARI",
    "İŞLETME FAALİYETLERİNDEN", "YATIRIM FAALİYETLERİNDEN", "FİNANSMAN FAALİYETLERİNDEN",
)


def _statement_yoy(name: str, p_dict: Dict[str, Any], periods: List[str]) -> Tuple[str, bool]:
    """En yeni dönemin bir önceki yılın aynı çeyreğine göre değişimi (metin, pozitif mi)."""
    if not periods:
        return "—", True
    p0 = periods[0]
    v0 = p_dict.get(p0)
    try:
        v_prev = p_dict.get(_prior_year_period(p0))
        if v0 is not None and v_prev is not None and abs(v_prev) > 0:
            pct = (v0 - v_prev) / abs(v_prev) * 100.0
            is_pos_yoy = pct >= 0
            return f"{'+' if is_pos_yoy else ''}{pct:.1f}%", is_pos_yoy
    except Exception as exc:
        logger.debug("YoY hesaplanamadı (%s): %s", name, exc)
    return "—", True


def compute_financial_table_rows(
    metrics: Dict[str, Any],
    statement_type: str,
    query: str,
    periods: List[str],
) -> List[Dict[str, Any]]:
    """Bilanço, gelir ve nakit akım tablosu satırlarını filtreler ve biçimlendirir."""
    if not metrics:
        return []

    section_data = metrics.get("_raw_sections", {}).get(statement_type, {})
    if not periods:
        periods = metrics.get("periods", [])[:8]

    q = query.strip().lower()
    rows = []
    for name, p_dict in section_data.items():
        if q and q not in name.lower():
            continue
        yoy_str, is_pos_yoy = _statement_yoy(name, p_dict, periods)
        rows.append({
            "name": name,
            "isHeader": any(kw in name.upper() for kw in _STATEMENT_HEADER_KEYWORDS),
            "values": [format_currency(p_dict.get(p)) for p in periods],
            "yoyChange": yoy_str,
            "isPositiveYoY": is_pos_yoy,
        })
    return rows


def _snapshot_changes(curr: Any, prev: Any) -> List[Dict[str, Any]]:
    """İki ardışık KAP snapshot'ı arasında en az %0.05 değişen ortakları listeler."""
    curr_date = curr.creation_date.strftime("%d.%m.%Y") if curr.creation_date else "—"
    prev_map = {r.shareholder_name.strip(): float(r.ratio_in_capital or 0) for r in prev.rows if not r.is_total}

    events = []
    for r in curr.rows:
        if r.is_total:
            continue
        name = r.shareholder_name.strip()
        new_ratio = float(r.ratio_in_capital or 0)
        old_ratio = prev_map.get(name, 0.0)
        diff = new_ratio - old_ratio
        if abs(diff) >= 0.05:  # En az %0.05 değişim
            events.append({
                "date": curr_date,
                "name": name,
                "newRatio": f"%{new_ratio:.2f}",
                "oldRatio": f"%{old_ratio:.2f}",
                "diff": diff,
                "diffStr": f"{diff:+.2f}%",
                "isIncrease": diff > 0,
                "votingRatio": f"%{float(r.voting_right_ratio or 0):.2f}",
            })
    return events


def compute_shareholder_timeline(snapshots: List[Any]) -> List[Dict[str, Any]]:
    """KAP snapshot dizisinden ortaklık değişim geçmişini (timeline) üretir."""
    if not snapshots or len(snapshots) < 2:
        return []

    events: List[Dict[str, Any]] = []
    for i in range(len(snapshots) - 1):
        events.extend(_snapshot_changes(snapshots[i], snapshots[i + 1]))
        if len(events) >= 15:
            break
    return events


def _donut_entry(index: int, row: Any) -> Tuple[Dict[str, Any], Dict[str, Any], bool]:
    """Bir ortaklık satırından liste öğesi, donut dilimi ve halka açık mı bilgisini üretir."""
    name = row.shareholder_name.strip()
    ratio = float(row.ratio_in_capital or 0)
    share_tl = float(row.share_in_capital or 0)
    voting = float(row.voting_right_ratio or 0)

    is_free_float = "DİĞER" in name.upper() or "HALKA" in name.upper()
    if is_free_float:
        color = DONUT_COLORS[-1]  # Nötr gri
    else:
        color = DONUT_COLORS[index % (len(DONUT_COLORS) - 1)]

    item = {
        "name": name,
        "ratio": ratio,
        "ratioStr": f"%{ratio:.2f}",
        "share": format_currency(share_tl),
        "votingRatio": f"%{voting:.2f}",
        "color": color,
        "isFreeFloat": is_free_float,
    }
    donut_slice = {
        "label": name,
        "pct": ratio / 100.0,
        "color": color,
        "amount": format_currency(share_tl),
    }
    return item, donut_slice, is_free_float


def _ranked_rows(snap: ShareholderSnapshot) -> List[Any]:
    """Toplam satırını ve sıfır paylıları ayıklar; orana göre sıralar (en büyük ortaklar üstte)."""
    rows = [r for r in snap.rows if not r.is_total and (r.ratio_in_capital or 0) > 0]
    return sorted(rows, key=lambda r: r.ratio_in_capital or 0, reverse=True)


def parse_shareholder_data(snap: ShareholderSnapshot) -> Dict[str, Any]:
    """KAP pay sahipliği snapshot nesnesini Donut dilimleri ve listesine dönüştürür."""
    date_str = snap.creation_date.strftime("%d.%m.%Y") if getattr(snap, "creation_date", None) else "—"

    shareholders = []
    slices = []
    total_nominal = Decimal("0")
    free_float_ratio = Decimal("0")

    for i, r in enumerate(_ranked_rows(snap)):
        item, donut_slice, is_free_float = _donut_entry(i, r)
        total_nominal += (r.share_in_capital or Decimal("0"))
        if is_free_float:
            free_float_ratio = Decimal(str(item["ratio"]))
        shareholders.append(item)
        slices.append(donut_slice)

    free_float_ratio_str = f"%{float(free_float_ratio):.2f}" if free_float_ratio > 0 else "—"
    paid_capital_str = format_currency(total_nominal) if total_nominal > 0 else "—"

    return {
        "date_str": date_str,
        "shareholders_list": shareholders,
        "shareholder_slices": slices,
        "free_float_ratio_str": free_float_ratio_str,
        "free_float_pct": float(free_float_ratio) / 100.0,
        "paid_capital_str": paid_capital_str,
    }
