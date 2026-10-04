"""
finansal metrik hesaplayıcı — saf, ağsız.

Ham scraper verisinden (IFinancialStatementProvider.get_financial_data) türetilmiş
analiz metrikleri üretir.

Desteklenen metrikler:
  - Büyüme:      Satışlar, Brüt Kar, FAVÖK, Net Kar
  - Marjlar (%): Brüt Kar Marjı, FAVÖK Marjı, Net Kar Marjı
  - Borç:        Net Borç, Net Borç/FAVÖK
  - Likidite:    Cari Oran
  - Karlılık:    ROE, ROA, DuPont ayrıştırma (TTM)
  - Nakit:       FCF, FCF Marjı, Capex/Satış
  - İşletme:     DSO, DIO, DPO, Nakit Dönüşüm Döngüsü (CCC)
  - Değerleme:   TTM Satış, FAVÖK, Net Kar (valuation multiples için)
  - Sezonsellik: Diskret çeyrek satış/kar
  - Piotroski:   F-Score (0-9) + 9 alt kriter
  - Değişim:     QoQ % ve YoY % (her metrik için)

Not: isyatirim.com.tr verisi YTD kümülatif (2026/3 = Q1 YTD, 2025/12 = tüm yıl).
     De-kümülasyon: _discrete() ve _ttm() yardımcıları kullanır.
"""
from __future__ import annotations

import re
from typing import Any


# ---------------------------------------------------------------------------
# Kalem adı → bölüm ve anahtar eşleşme yardımcıları
# ---------------------------------------------------------------------------

def _get(
    sections: dict[str, dict],
    section: str,
    *candidates: str,
    period: str,
) -> float | None:
    """Bölümdeki aday kalem adlarından ilk değeri bulunanı döndür."""
    bucket = sections.get(section, {})
    for name in candidates:
        if name in bucket:
            val = bucket[name].get(period)
            if val is not None:
                return val
        for stored_key in bucket:
            if stored_key.startswith(name):
                val = bucket[stored_key].get(period)
                if val is not None:
                    return val
    return None


_PREFIX_RE = re.compile(r"^[\dIVXLC]+[.\d ]*\s*", re.IGNORECASE)


def _norm(s: str) -> str:
    return _PREFIX_RE.sub("", s).strip().lower()


def _find_b(bucket: dict, *names: str, period: str) -> float | None:
    """Bilanco kalemi: önek-sıyrılmış, büyük/küçük harf duyarsız eşleşme."""
    targets = {_norm(n) for n in names}
    for key, series in bucket.items():
        if _norm(key) in targets:
            val = series.get(period)
            if val is not None:
                return val
    return None


def _safe_div(a: float | None, b: float | None) -> float | None:
    if a is None or b is None or b == 0:
        return None
    return a / b


def _pct_change(current: float | None, previous: float | None) -> float | None:
    if current is None or previous is None or previous == 0:
        return None
    return ((current - previous) / abs(previous)) * 100.0


# ---------------------------------------------------------------------------
# De-kümülasyon yardımcıları
# ---------------------------------------------------------------------------

def _days_in_period(period: str) -> int:
    """Dönem sonuna kadar geçen yaklaşık gün sayısı (işletme sermayesi için)."""
    m = int(period.split("/")[1])
    return {3: 90, 6: 181, 9: 273, 12: 365}.get(m, 90)


def _prev_quarter_same_year(period: str, periods: list[str]) -> str | None:
    """Aynı yılın bir önceki çeyreği; Q1 veya mevcut değilse None."""
    y, m = int(period.split("/")[0]), int(period.split("/")[1])
    prev_m = {6: 3, 9: 6, 12: 9}.get(m)
    if prev_m is None:
        return None
    p = f"{y}/{prev_m}"
    return p if p in periods else None


def _prev_period(period: str, periods: list[str]) -> str | None:
    """Periods listesinde bir sonraki (daha eski) dönem."""
    try:
        idx = periods.index(period)
        return periods[idx + 1] if idx + 1 < len(periods) else None
    except ValueError:
        return None


def _discrete(series: dict, period: str, periods: list[str]) -> float | None:
    """
    YTD kümülatif seriyi diskret çeyreğe çevirir.
    Q1: YTD = diskret. Diğerleri: YTD_şimdi − YTD_aynı_yıl_önceki_çeyrek.
    """
    cur = series.get(period)
    if cur is None:
        return None
    if int(period.split("/")[1]) == 3:
        return cur
    prev_p = _prev_quarter_same_year(period, periods)
    if prev_p is None:
        return cur
    prev = series.get(prev_p)
    if prev is None:
        return None
    return cur - prev


def _ttm(series: dict, period: str, periods: list[str]) -> float | None:
    """Son 4 diskret çeyreğin toplamı (Trailing Twelve Months)."""
    parts: list[float] = []
    p: str | None = period
    while p is not None and len(parts) < 4:
        d = _discrete(series, p, periods)
        if d is None:
            return None
        parts.append(d)
        if len(parts) < 4:
            p = _prev_period(p, periods)
    return sum(parts) if len(parts) == 4 else None


# ---------------------------------------------------------------------------
# Kalem adı sabitleri
# ---------------------------------------------------------------------------

_SATIS            = ("Satış Gelirleri", "Net Satışlar")
_BRUT_KAR         = ("BRÜT KAR (ZARAR)", "Ticari Faaliyetlerden Brüt Kar (Zarar)")
_FAALKAR          = ("FAALİYET KARI (ZARARI)", "Faaliyet Karı (Zararı)")
_NET_KAR          = ("DÖNEM KARI (ZARARI)", "SÜRDÜRÜLEN FAALİYETLER DÖNEM KARI/ZARARI",
                     "Dönem Kar/Zararı")
_AMORTISMAN       = ("Amortisman Giderleri",)
_NAKIT            = ("Nakit ve Nakit Benzerleri",)
_FIN_BORC_KV      = ("Finansal Borçlar (1)", "Finansal Borçlar")
_FIN_BORC_UV      = ("Finansal Borçlar (2)",)
_DONEN            = ("Dönen Varlıklar",)
_KVY              = ("Kısa Vadeli Yükümlülükler",)
_OZKAYNAK         = ("Özkaynaklar",)
_ODENMIS_SERMAYE  = ("Ödenmiş Sermaye", "Ödenmiş/Çıkarılmış Sermaye")
_SERMAYE_DUZELTME = ("Sermaye Düzeltmesi Olumlu Farkları", "Sermaye Düzeltme Farkları",
                     "Sermaye Düzeltmesi Farkları")
_FCF              = ("Serbest Nakit Akım",)
_CAPEX            = ("Sabit Sermaye Yatırımları",)
_ISLETME_CF       = ("İşletme Faaliyetlerinden Kaynaklanan Net Nakit",)
_TOPLAM_VARLIK    = ("TOPLAM VARLIKLAR", "Toplam Varlıklar", "TOPLAM AKTİFLER", "Toplam Aktifler")
_TIC_ALACAK       = ("Ticari Alacaklar",)
_STOK             = ("Stoklar",)
_TIC_BORC         = ("Ticari Borçlar",)
_SATIS_MALY       = ("Satışların Maliyeti",)
_YURTICI_SAT      = ("Yurtiçi Satışlar",)
_YURTDISI_SAT     = ("Yurtdışı Satışlar",)
_TEMETTU_ODE      = ("Temettü Ödemeleri",)
_SERM_ARTIR       = ("Sermaye Artırımı",)
_HBK              = ("Hisse Başına Kazanç",)


# ---------------------------------------------------------------------------
# Tekil dönem metrikleri
# ---------------------------------------------------------------------------

def _bucket_value(bucket: dict, *candidates: str, period: str) -> float | None:
    return _get({"_": bucket}, "_", *candidates, period=period)


def _pct(value: float | None) -> float | None:
    return value * 100 if value is not None else None


def _sum_optional(first: float | None, second: float | None) -> float | None:
    """İkisi de yoksa None; biri varsa eksik olan 0 sayılarak toplanır."""
    if first is None and second is None:
        return None
    return (first or 0) + (second or 0)


def _turnover_days(balance: float | None, flow: float | None, days: int) -> float | None:
    """`bakiye / akış * gün`; akış yok veya sıfırsa None."""
    if balance is None or flow is None or flow == 0:
        return None
    return balance / flow * days


def _income_items(sections: dict, period: str) -> dict[str, float | None]:
    g = sections.get("gelir", {})
    return {
        "satis":          _bucket_value(g, *_SATIS, period=period),
        "brut_kar":       _bucket_value(g, *_BRUT_KAR, period=period),
        "faal_kar":       _bucket_value(g, *_FAALKAR, period=period),
        "net_kar":        _bucket_value(g, *_NET_KAR, period=period),
        "satis_maliyeti": _bucket_value(g, *_SATIS_MALY, period=period),
        "hbk":            _bucket_value(g, *_HBK, period=period),
    }


def _balance_items(sections: dict, period: str) -> dict[str, float | None]:
    b = sections.get("bilanco", {})
    return {
        "nakit":           _bucket_value(b, *_NAKIT, period=period),
        "donen":           _bucket_value(b, *_DONEN, period=period),
        "kvy":             _bucket_value(b, *_KVY, period=period),
        "ozkaynak":        _find_b(b, *_OZKAYNAK, period=period),
        "odenmis_sermaye": _find_b(b, *_ODENMIS_SERMAYE, period=period),
        "serm_duzeltme":   _find_b(b, *_SERMAYE_DUZELTME, period=period),
        "toplam_varlik":   _find_b(b, *_TOPLAM_VARLIK, period=period),
        "ticari_alacak":   _bucket_value(b, *_TIC_ALACAK, period=period),
        "stok":            _bucket_value(b, *_STOK, period=period),
        "ticari_borc":     _bucket_value(b, *_TIC_BORC, period=period),
        "fin_kv":          _bucket_value(b, *_FIN_BORC_KV, period=period),
        "fin_uv":          _bucket_value(b, *_FIN_BORC_UV, period=period),
    }


def _note_and_cash_flow_items(sections: dict, period: str) -> dict[str, float | None]:
    d = sections.get("dipnot", {})
    na = sections.get("nakit_akim", {})
    return {
        "amorti":         _bucket_value(d, *_AMORTISMAN, period=period),
        "yurtici_satis":  _bucket_value(d, *_YURTICI_SAT, period=period),
        "yurtdisi_satis": _bucket_value(d, *_YURTDISI_SAT, period=period),
        "fcf":            _bucket_value(na, *_FCF, period=period),
        "capex":          _bucket_value(na, *_CAPEX, period=period),
        "isletme":        _bucket_value(na, *_ISLETME_CF, period=period),
        "temettu":        _bucket_value(na, *_TEMETTU_ODE, period=period),
        "serm_artir":     _bucket_value(na, *_SERM_ARTIR, period=period),
    }


def _working_capital_metrics(raw: dict[str, float | None], period: str) -> dict[str, float | None]:
    days = _days_in_period(period)
    cogs_abs = abs(raw["satis_maliyeti"]) if raw["satis_maliyeti"] is not None else None
    dso = _turnover_days(raw["ticari_alacak"], raw["satis"], days)
    dio = _turnover_days(raw["stok"], cogs_abs, days)
    dpo = _turnover_days(raw["ticari_borc"], cogs_abs, days)
    ccc = dso + dio - dpo if (dso is not None and dio is not None and dpo is not None) else None
    return {"dso": dso, "dio": dio, "dpo": dpo, "ccc": ccc}


_RAW_TO_OUTPUT: dict[str, str] = {
    "satis": "satis", "brut_kar": "brut_kar", "faal_kar": "faaliyet_kar", "net_kar": "net_kar",
    "nakit": "nakit", "donen": "donen_varlik", "kvy": "kisa_vadeli_yukuml", "ozkaynak": "ozkaynak",
    "odenmis_sermaye": "odenmis_sermaye", "serm_duzeltme": "sermaye_duzeltme", "fcf": "fcf",
    "capex": "capex", "isletme": "isletme_cf", "toplam_varlik": "toplam_varlik",
    "ticari_alacak": "ticari_alacak", "stok": "stok", "ticari_borc": "ticari_borc",
    "fin_uv": "fin_borc_uv", "satis_maliyeti": "satis_maliyeti", "yurtici_satis": "yurtici_satis",
    "yurtdisi_satis": "yurtdisi_satis", "temettu": "temettu_odeme", "serm_artir": "sermaye_artirimi",
    "hbk": "hbk",
}


def _favok(raw: dict[str, float | None]) -> float | None:
    faal_kar, amorti = raw["faal_kar"], raw["amorti"]
    return faal_kar + amorti if faal_kar is not None and amorti is not None else faal_kar


def _net_debt(raw: dict[str, float | None]) -> float | None:
    total_fin_debt = _sum_optional(raw["fin_kv"], raw["fin_uv"])
    if total_fin_debt is None or raw["nakit"] is None:
        return None
    return total_fin_debt - raw["nakit"]


def _export_ratio(raw: dict[str, float | None]) -> float | None:
    foreign = raw["yurtdisi_satis"]
    total = _sum_optional(raw["yurtici_satis"], foreign)
    if foreign is None or total is None or total == 0:
        return None
    return foreign / total * 100


def _payout_ratio(raw: dict[str, float | None]) -> float | None:
    dividend, net_profit = raw["temettu"], raw["net_kar"]
    if dividend is None or net_profit is None or net_profit == 0:
        return None
    return abs(dividend) / net_profit * 100


def _is_inflation_adjusted(raw: dict[str, float | None], period: str) -> bool:
    return int(period.split("/")[0]) >= 2024 or raw["serm_duzeltme"] not in (None, 0)


def _derived_metrics(raw: dict[str, float | None], period: str) -> dict[str, float | None]:
    favok = _favok(raw)
    net_borc = _net_debt(raw)
    bedelsiz_x = _safe_div(raw["ozkaynak"], raw["odenmis_sermaye"])
    return {
        "favok": favok,
        "net_borc": net_borc,
        "enflasyon_duzeltildi": _is_inflation_adjusted(raw, period),
        "bedelsiz_potansiyel_x": bedelsiz_x,
        "bedelsiz_potansiyel_pct": (bedelsiz_x - 1) * 100 if bedelsiz_x is not None else None,
        "ihracat_orani": _export_ratio(raw),
        "dagitim_orani": _payout_ratio(raw),
        "net_borc_favok": _safe_div(net_borc, favok),
    }


def _ratio_metrics(raw: dict[str, float | None], favok: float | None) -> dict[str, float | None]:
    satis, net_kar = raw["satis"], raw["net_kar"]
    ozkaynak, toplam_varlik = raw["ozkaynak"], raw["toplam_varlik"]
    return {
        "brut_kar_marji":   _pct(_safe_div(raw["brut_kar"], satis)),
        "favok_marji":      _pct(_safe_div(favok, satis)),
        "net_kar_marji":    _pct(_safe_div(net_kar, satis)),
        "fcf_marji":        _pct(_safe_div(raw["fcf"], satis)),
        "capex_satis":      _pct(_safe_div(raw["capex"], satis)),
        "roe":              _pct(_safe_div(net_kar, ozkaynak)),
        "roa":              _pct(_safe_div(net_kar, toplam_varlik)),
        "cari_oran":        _safe_div(raw["donen"], raw["kvy"]),
        "varlik_devir_ytd": _safe_div(satis, toplam_varlik),
        "fin_kaldirac":     _safe_div(toplam_varlik, ozkaynak),
        "uv_borc_varlik":   _safe_div(raw["fin_uv"], toplam_varlik),
    }


def _single_period(sections: dict, period: str) -> dict[str, float | None]:
    raw = {
        **_income_items(sections, period),
        **_balance_items(sections, period),
        **_note_and_cash_flow_items(sections, period),
    }
    derived = _derived_metrics(raw, period)
    result = {output: raw[source] for source, output in _RAW_TO_OUTPUT.items()}
    result.update(derived)
    result.update(_ratio_metrics(raw, derived["favok"]))
    result.update(_working_capital_metrics(raw, period))
    return result


# ---------------------------------------------------------------------------
# QoQ / YoY delta
# ---------------------------------------------------------------------------

def _quarter_index(period: str) -> tuple[int, int]:
    parts = period.split("/")
    return int(parts[0]), int(parts[1])


def _find_qoq_period(period: str, all_periods: list[str]) -> str | None:
    try:
        idx = all_periods.index(period)
        return all_periods[idx + 1] if idx + 1 < len(all_periods) else None
    except ValueError:
        return None


def _find_yoy_period(period: str, all_periods: list[str]) -> str | None:
    y, m = _quarter_index(period)
    for p in all_periods:
        py, pm = _quarter_index(p)
        if py == y - 1 and pm == m:
            return p
    return None


# ---------------------------------------------------------------------------
# Piotroski F-Score
# ---------------------------------------------------------------------------

def _piotroski(all_single: dict, periods: list[str]) -> dict[str, dict]:
    """Piotroski F-Score (0–9). YoY karşılaştırma ile."""

    def g(key: str, p: str) -> float | None:
        return all_single.get(key, {}).get(p)

    result: dict[str, dict] = {}
    for period in periods:
        yoy_p = _find_yoy_period(period, periods)

        def cur(key: str) -> float | None:   # noqa: E731
            return g(key, period)

        def prv(key: str) -> float | None:   # noqa: E731
            return g(key, yoy_p) if yoy_p else None

        def s_up(key: str) -> int | None:    # noqa: E731
            c, p_ = cur(key), prv(key)
            return None if (c is None or p_ is None) else (1 if c > p_ else 0)

        def s_dn(key: str) -> int | None:    # noqa: E731
            c, p_ = cur(key), prv(key)
            return None if (c is None or p_ is None) else (1 if c < p_ else 0)

        def s_pos(key: str) -> int | None:   # noqa: E731
            v = cur(key)
            return None if v is None else (1 if v > 0 else 0)

        f1 = s_pos("net_kar")
        f2 = s_pos("isletme_cf")
        f3 = s_up("roa")
        ic, nk = cur("isletme_cf"), cur("net_kar")
        f4 = (1 if (ic is not None and nk is not None and ic > nk)
              else 0 if (ic is not None and nk is not None) else None)
        f5 = s_dn("uv_borc_varlik")
        f6 = s_up("cari_oran")
        ods_c, ods_p = cur("odenmis_sermaye"), prv("odenmis_sermaye")
        f7 = (1 if (ods_c is not None and ods_p is not None and ods_c <= ods_p)
              else 0 if (ods_c is not None and ods_p is not None) else None)
        f8 = s_up("brut_kar_marji")
        f9 = s_up("varlik_devir_ytd")

        criteria = [f1, f2, f3, f4, f5, f6, f7, f8, f9]
        known    = [c for c in criteria if c is not None]
        score    = sum(known) if known else None

        result[period] = {
            "score":                 score,
            "f1_net_kar_pozitif":    f1,
            "f2_isletme_cf_pozitif": f2,
            "f3_roa_artan":          f3,
            "f4_cf_kar_ustu":        f4,
            "f5_uv_borc_azalan":     f5,
            "f6_cari_oran_artan":    f6,
            "f7_hisse_artmadi":      f7,
            "f8_brut_marj_artan":    f8,
            "f9_varlik_devir_artan": f9,
        }
    return result


# ---------------------------------------------------------------------------
# Delta
# ---------------------------------------------------------------------------

_DELTA_SKIP = {
    "enflasyon_duzeltildi",
    "piotroski", "piotroski_f1", "piotroski_f2", "piotroski_f3",
    "piotroski_f4", "piotroski_f5", "piotroski_f6", "piotroski_f7",
    "piotroski_f8", "piotroski_f9",
}


def _compute_deltas(
    metric_series: dict[str, dict[str, float | None]],
    periods: list[str],
    kind: str,
) -> dict[str, dict[str, float | None]]:
    deltas: dict[str, dict[str, float | None]] = {}
    for metric, series in metric_series.items():
        if metric in _DELTA_SKIP:
            continue
        deltas[metric] = {}
        for period in periods:
            current = series.get(period)
            prev_p = (
                _find_qoq_period(period, periods) if kind == "qoq"
                else _find_yoy_period(period, periods)
            )
            prev = series.get(prev_p) if prev_p else None
            deltas[metric][period] = _pct_change(current, prev)
    return deltas


# ---------------------------------------------------------------------------
# Ana API
# ---------------------------------------------------------------------------

def compute_metrics(data: dict) -> dict[str, Any]:
    """
    IFinancialStatementProvider.get_financial_data() çıktısından metrikleri hesaplar.

    Returns:
        Dict with keys: periods, ticker, currency, satis, favok, net_kar, ...,
        satis_ttm, net_kar_ttm, favok_ttm, dso/dio/dpo/ccc,
        dupont_*, piotroski, piotroski_f1..f9, _delta.{qoq,yoy},
        _raw_sections, _piotroski_detail.
    """
    sections = data["sections"]
    periods  = data["periods"]

    all_single: dict[str, dict[str, float | None]] = {}
    for period in periods:
        single = _single_period(sections, period)
        for metric, value in single.items():
            if metric not in all_single:
                all_single[metric] = {}
            all_single[metric][period] = value

    # Diskret çeyrek
    for src_key, dst_key in [
        ("satis",   "satis_ceyrek"),
        ("net_kar", "net_kar_ceyrek"),
        ("favok",   "favok_ceyrek"),
    ]:
        src = all_single.get(src_key, {})
        all_single[dst_key] = {p: _discrete(src, p, periods) for p in periods}

    # TTM
    for src_key, dst_key in [
        ("satis",   "satis_ttm"),
        ("net_kar", "net_kar_ttm"),
        ("favok",   "favok_ttm"),
    ]:
        src = all_single.get(src_key, {})
        all_single[dst_key] = {p: _ttm(src, p, periods) for p in periods}

    # DuPont (TTM baz)
    sttm  = all_single.get("satis_ttm",    {})
    nkttm = all_single.get("net_kar_ttm",  {})
    tv_s  = all_single.get("toplam_varlik", {})
    ozk_s = all_single.get("ozkaynak",      {})

    dup_nkm: dict[str, float | None] = {}
    dup_vd:  dict[str, float | None] = {}
    dup_fk:  dict[str, float | None] = {}
    dup_roe: dict[str, float | None] = {}
    for p in periods:
        s_ttm = sttm.get(p)
        n_ttm = nkttm.get(p)
        tv    = tv_s.get(p)
        ozk   = ozk_s.get(p)
        nkm   = _safe_div(n_ttm, s_ttm)
        vd    = _safe_div(s_ttm, tv)
        fk    = _safe_div(tv,    ozk)
        dup_nkm[p] = (nkm * 100) if nkm is not None else None
        dup_vd[p]  = vd
        dup_fk[p]  = fk
        dup_roe[p] = (nkm * vd * fk * 100) if None not in (nkm, vd, fk) else None

    all_single["dupont_net_kar_marji"] = dup_nkm
    all_single["dupont_varlik_devir"]  = dup_vd
    all_single["dupont_fin_kaldirac"]  = dup_fk
    all_single["dupont_roe"]           = dup_roe

    all_single["net_borc_favok_ttm"] = {
        p: _safe_div(
            all_single.get("net_borc", {}).get(p),
            all_single.get("favok_ttm", {}).get(p),
        )
        for p in periods
    }

    # Piotroski
    piotroski_raw = _piotroski(all_single, periods)
    all_single["piotroski"]    = {p: piotroski_raw[p]["score"] for p in periods}
    all_single["piotroski_f1"] = {p: piotroski_raw[p]["f1_net_kar_pozitif"]    for p in periods}
    all_single["piotroski_f2"] = {p: piotroski_raw[p]["f2_isletme_cf_pozitif"] for p in periods}
    all_single["piotroski_f3"] = {p: piotroski_raw[p]["f3_roa_artan"]          for p in periods}
    all_single["piotroski_f4"] = {p: piotroski_raw[p]["f4_cf_kar_ustu"]        for p in periods}
    all_single["piotroski_f5"] = {p: piotroski_raw[p]["f5_uv_borc_azalan"]     for p in periods}
    all_single["piotroski_f6"] = {p: piotroski_raw[p]["f6_cari_oran_artan"]    for p in periods}
    all_single["piotroski_f7"] = {p: piotroski_raw[p]["f7_hisse_artmadi"]      for p in periods}
    all_single["piotroski_f8"] = {p: piotroski_raw[p]["f8_brut_marj_artan"]    for p in periods}
    all_single["piotroski_f9"] = {p: piotroski_raw[p]["f9_varlik_devir_artan"] for p in periods}

    qoq = _compute_deltas(all_single, periods, "qoq")
    yoy = _compute_deltas(all_single, periods, "yoy")

    return {
        "ticker":            data.get("ticker", ""),
        "periods":           periods,
        "currency":          data.get("currency", "TRY"),
        "_raw_sections":     sections,
        "_piotroski_detail": piotroski_raw,
        **all_single,
        "_delta": {"qoq": qoq, "yoy": yoy},
    }
