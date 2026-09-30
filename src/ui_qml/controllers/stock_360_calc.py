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


def parse_valuation_ratios(f: Dict[str, Any]) -> Dict[str, str]:
    """Değerleme ve rasyo göstergelerini sözlükten ayrıştırıp metinsel formatlara çevirir."""
    mv = f.get("_market_val", {}) or {}
    p0 = f.get("periods", [""])[0]

    fk = mv.get("fk")
    pddd = mv.get("pddd")
    ev_favok = mv.get("ev_favok")
    temettu = mv.get("temettu_verimi")
    mc = mv.get("market_cap")

    pe_ratio = f"{fk:.1f}" if fk is not None and fk > 0 else ("—" if fk is None else "Negatif")
    pb_ratio = f"{pddd:.2f}" if pddd is not None else "—"
    ev_ebitda = f"{ev_favok:.1f}" if ev_favok is not None and ev_favok > 0 else "—"
    div_yield = f"%{temettu:.2f}" if temettu is not None and temettu > 0 else "%0.00"
    market_cap_str = format_currency(mc) if mc is not None else "—"

    # ROE
    roe_series = f.get("roe", {})
    roe_val = roe_series.get(p0) if isinstance(roe_series, dict) else None
    roe_str = f"%{roe_val:.1f}" if roe_val is not None else "—"

    # Net Borç / FAVÖK
    nb_favok_series = f.get("net_borc_favok_ttm", {})
    nb_favok = nb_favok_series.get(p0) if isinstance(nb_favok_series, dict) else None
    net_debt_ebitda_str = f"{nb_favok:.2f}" if nb_favok is not None else "—"

    # Piotroski F-Score
    piotroski_series = f.get("piotroski", {})
    pio = piotroski_series.get(p0) if isinstance(piotroski_series, dict) else None
    piotroski_score_str = f"{pio}/9" if pio is not None else "—"

    # Cari Oran
    cari_series = f.get("cari_oran", {})
    cari = cari_series.get(p0) if isinstance(cari_series, dict) else None
    current_ratio_str = f"{cari:.2f}" if cari is not None else "—"

    return {
        "pe_ratio": pe_ratio,
        "pb_ratio": pb_ratio,
        "ev_ebitda": ev_ebitda,
        "div_yield": div_yield,
        "market_cap_str": market_cap_str,
        "roe": roe_str,
        "net_debt_ebitda": net_debt_ebitda_str,
        "piotroski_score": piotroski_score_str,
        "current_ratio": current_ratio_str,
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


def compute_revenue_chart(
    metrics: Dict[str, Any],
    active_periods: List[str],
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Gelir & kârlılık grafik serisini ve son çeyrek KPI rozetlerini hesaplar."""
    chronological_periods = list(reversed(active_periods))
    satis_c = metrics.get("satis_ceyrek", {}) or metrics.get("satis", {})
    net_c = metrics.get("net_kar_ceyrek", {}) or metrics.get("net_kar", {})
    margin_c = metrics.get("net_kar_marji", {})

    chart_items = []
    max_rev = 1.0
    for p in chronological_periods:
        rev_val = float(satis_c.get(p) or 0.0)
        max_rev = max(max_rev, rev_val)

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
        last_net = float(net_c.get(p0) or 0.0)
        last_mg = float(margin_c.get(p0) or 0.0)
        kpis["latest_quarter_revenue"] = format_currency(last_rev)
        kpis["latest_quarter_net_income"] = format_currency(last_net)
        kpis["latest_quarter_margin"] = f"%{last_mg:.2f}"

        try:
            y0, q0 = p0.split("/")
            prev_p = f"{int(y0) - 1}/{q0}"
            prev_rev = satis_c.get(prev_p)
            if prev_rev and prev_rev > 0:
                yoy_growth = (last_rev - prev_rev) / prev_rev * 100.0
                is_pos = yoy_growth >= 0
                kpis["revenue_yoy_growth"] = f"{'+' if is_pos else ''}{yoy_growth:.1f}%"
                kpis["is_revenue_yoy_positive"] = is_pos
        except Exception:
            pass

    return chart_items, kpis


def compute_dupont_data(
    metrics: Dict[str, Any],
    active_periods: List[str],
) -> Dict[str, Any]:
    """DuPont kârlılık kırılımı (Net Kâr Marjı, Varlık Devri, Kaldıraç, ROE, Piotroski) verilerini hesaplar."""
    if not active_periods:
        return {}

    m = metrics
    satis_c = m.get("satis_ceyrek", {}) or m.get("satis", {})
    net_c = m.get("net_kar_ceyrek", {}) or m.get("net_kar", {})

    dup_p = None
    for p in active_periods:
        if m.get("dupont_net_kar_marji", {}).get(p) is not None:
            dup_p = p
            break
    if not dup_p:
        dup_p = active_periods[0]

    dup_nm = m.get("dupont_net_kar_marji", {}).get(dup_p)
    dup_at = m.get("dupont_varlik_devir", {}).get(dup_p)
    dup_fl = m.get("dupont_fin_kaldirac", {}).get(dup_p)
    dup_roe = m.get("dupont_roe", {}).get(dup_p)
    pio = m.get("piotroski", {}).get(dup_p)

    # Fallback: TTM hesaplanamamışsa son çeyrek bilanço kalemlerinden türet
    if dup_nm is None:
        s_val = float(satis_c.get(dup_p) or 0.0)
        n_val = float(net_c.get(dup_p) or 0.0)
        tv_val = float(m.get("toplam_varlik", {}).get(dup_p) or 0.0)
        ozk_val = float(m.get("ozkaynak", {}).get(dup_p) or 0.0)
        if s_val > 0:
            dup_nm = (n_val / s_val) * 100.0
        if tv_val > 0 and s_val > 0:
            dup_at = (s_val * 4.0) / tv_val  # Yıllıklandırılmış devir
        if ozk_val > 0 and tv_val > 0:
            dup_fl = tv_val / ozk_val
        if dup_nm is not None and dup_at is not None and dup_fl is not None:
            dup_roe = (dup_nm * dup_at * dup_fl) / 100.0

    pio_score = int(pio) if pio is not None else 7
    if pio_score >= 7:
        pio_status = "Yüksek Finansal Güç"
        pio_color = "#089981"
    elif pio_score >= 4:
        pio_status = "Dengeli Finansal Yapı"
        pio_color = "#2962ff"
    else:
        pio_status = "Baskılanmış Risk Bölgesi"
        pio_color = "#f23645"

    return {
        "netMargin": f"%{dup_nm:.2f}" if dup_nm is not None else "—",
        "assetTurnover": f"{dup_at:.2f}x" if dup_at is not None else "—",
        "financialLeverage": f"{dup_fl:.2f}x" if dup_fl is not None else "—",
        "roe": f"%{dup_roe:.2f}" if dup_roe is not None else "—",
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
    cf_p = None
    for p in active_periods:
        if m.get("isletme_cf", {}).get(p) is not None or m.get("net_borc", {}).get(p) is not None:
            cf_p = p
            break
    if not cf_p:
        cf_p = active_periods[0]

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
        "netDebtEbitda": f"{nb_fav:.2f}x" if nb_fav is not None else "—",
        "isDebtSafe": is_safe,
        "debtStatus": "Sürdürülebilir & Sağlıklı" if is_safe else "Yüksek Borçluluk",
    }


def compute_financial_table_rows(
    metrics: Dict[str, Any],
    statement_type: str,
    query: str,
    periods: List[str],
) -> List[Dict[str, Any]]:
    """Bilanço, gelir ve nakit akım tablosu satırlarını filtreler ve biçimlendirir."""
    if not metrics:
        return []

    raw_sec = metrics.get("_raw_sections", {})
    section_data = raw_sec.get(statement_type, {})
    if not periods:
        periods = metrics.get("periods", [])[:8]

    header_keywords = [
        "DÖNEN VARLIKLAR", "DURAN VARLIKLAR", "KISA VADELİ YÜKÜMLÜLÜKLER",
        "UZUN VADELİ YÜKÜMLÜLÜKLER", "ÖZKAYNAKLAR", "TOPLAM VARLIKLAR",
        "TOPLAM KAYNAKLAR", "SÜRDÜRÜLEN FAALİYETLER", "DÖNEM KARI",
        "İŞLETME FAALİYETLERİNDEN", "YATIRIM FAALİYETLERİNDEN", "FİNANSMAN FAALİYETLERİNDEN"
    ]

    q = query.strip().lower()
    rows = []

    for name, p_dict in section_data.items():
        if q and q not in name.lower():
            continue

        is_hdr = any(kw in name.upper() for kw in header_keywords)
        vals = [format_currency(p_dict.get(p)) for p in periods]

        # YoY hesaplama
        yoy_str = "—"
        is_pos_yoy = True
        if periods and len(periods) >= 1:
            p0 = periods[0]
            v0 = p_dict.get(p0)
            try:
                y0, q0 = p0.split("/")
                prev_p = f"{int(y0) - 1}/{q0}"
                v_prev = p_dict.get(prev_p)
                if v0 is not None and v_prev is not None and abs(v_prev) > 0:
                    pct = (v0 - v_prev) / abs(v_prev) * 100.0
                    is_pos_yoy = pct >= 0
                    yoy_str = f"{'+' if is_pos_yoy else ''}{pct:.1f}%"
            except Exception as exc:
                logger.debug("YoY hesaplanamadı (%s): %s", name, exc)

        rows.append({
            "name": name,
            "isHeader": is_hdr,
            "values": vals,
            "yoyChange": yoy_str,
            "isPositiveYoY": is_pos_yoy,
        })

    return rows


def compute_shareholder_timeline(snapshots: List[Any]) -> List[Dict[str, Any]]:
    """KAP snapshot dizisinden ortaklık değişim geçmişini (timeline) üretir."""
    if not snapshots or len(snapshots) < 2:
        return []

    events = []
    for i in range(len(snapshots) - 1):
        curr = snapshots[i]
        prev = snapshots[i + 1]
        curr_date = curr.creation_date.strftime("%d.%m.%Y") if curr.creation_date else "—"
        prev_map = {r.shareholder_name.strip(): float(r.ratio_in_capital or 0) for r in prev.rows if not r.is_total}

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
        if len(events) >= 15:
            break

    return events


def parse_shareholder_data(snap: ShareholderSnapshot) -> Dict[str, Any]:
    """KAP pay sahipliği snapshot nesnesini Donut dilimleri ve listesine dönüştürür."""
    date_str = snap.creation_date.strftime("%d.%m.%Y") if getattr(snap, "creation_date", None) else "—"

    shareholders = []
    slices = []
    total_nominal = Decimal("0")
    free_float_ratio = Decimal("0")

    # Önce toplam satırını ve normal satırları ayıkla
    rows = [r for r in snap.rows if not r.is_total and (r.ratio_in_capital or 0) > 0]
    # Orana göre sırala (en büyük ortaklar üstte)
    sorted_rows = sorted(rows, key=lambda r: r.ratio_in_capital or 0, reverse=True)

    for i, r in enumerate(sorted_rows):
        name = r.shareholder_name.strip()
        ratio = float(r.ratio_in_capital or 0)
        share_tl = float(r.share_in_capital or 0)
        voting = float(r.voting_right_ratio or 0)

        total_nominal += (r.share_in_capital or Decimal("0"))

        is_free_float = "DİĞER" in name.upper() or "HALKA" in name.upper()
        if is_free_float:
            color = DONUT_COLORS[-1]  # Nötr gri
            free_float_ratio = Decimal(str(ratio))
        else:
            color = DONUT_COLORS[i % (len(DONUT_COLORS) - 1)]

        item = {
            "name": name,
            "ratio": ratio,
            "ratioStr": f"%{ratio:.2f}",
            "share": format_currency(share_tl),
            "votingRatio": f"%{voting:.2f}",
            "color": color,
            "isFreeFloat": is_free_float,
        }
        shareholders.append(item)
        slices.append({
            "label": name,
            "pct": ratio / 100.0,
            "color": color,
            "amount": format_currency(share_tl),
        })

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
