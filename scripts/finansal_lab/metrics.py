"""
metrics.py — Türetilmiş Finansal Metrik Hesaplayıcı

Ham scraper verisinden analiz metrikleri üretir.

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

Kullanım:
    from metrics import compute_metrics
    m = compute_metrics(data)
    print(m["favok_marji"])     # {"2026/3": 6.89, ...}
    print(m["satis_ttm"])       # TTM satış
    print(m["piotroski"])       # {"2026/3": 7, ...}
    print(m["_delta"]["qoq"]["net_kar"])
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


# ---------------------------------------------------------------------------
# Önek-toleranslı bilanco bulucu (banka UFRS: "XVI. ÖZKAYNAKLAR" vb.)
# ---------------------------------------------------------------------------

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
# isyatirim verisi YTD kümülatif: 2026/3 = Q1 YTD, 2025/12 = tüm yıl
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
    Q1: YTD = diskret (subtraction yok).
    Diğerleri: YTD_şimdi − YTD_aynı_yıl_önceki_çeyrek.
    """
    cur = series.get(period)
    if cur is None:
        return None
    if int(period.split("/")[1]) == 3:
        return cur
    prev_p = _prev_quarter_same_year(period, periods)
    if prev_p is None:
        return cur  # önceki çeyrek yok → YTD'yi kullan
    prev = series.get(prev_p)
    if prev is None:
        return None
    return cur - prev


def _ttm(series: dict, period: str, periods: list[str]) -> float | None:
    """
    Son 4 diskret çeyreğin toplamı (Trailing Twelve Months).
    Herhangi bir çeyrek eksikse None döner.
    """
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
# Kalem adı sabitleri (isyatirim.com.tr'de görülen gerçek adlar)
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

# Yeni kalemler — değerleme, işletme sermayesi, DuPont, Piotroski
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

def _single_period(sections: dict, period: str) -> dict[str, float | None]:
    g  = sections.get("gelir",      {})
    b  = sections.get("bilanco",    {})
    d  = sections.get("dipnot",     {})
    na = sections.get("nakit_akim", {})

    def gv(bucket, *candidates):
        return _get({"_": bucket}, "_", *candidates, period=period)

    # --- Gelir tablosu ---
    satis          = gv(g, *_SATIS)
    brut_kar       = gv(g, *_BRUT_KAR)
    faal_kar       = gv(g, *_FAALKAR)
    net_kar        = gv(g, *_NET_KAR)
    satis_maliyeti = gv(g, *_SATIS_MALY)
    hbk            = gv(g, *_HBK)

    # --- Bilanço ---
    nakit           = gv(b, *_NAKIT)
    donen           = gv(b, *_DONEN)
    kvy             = gv(b, *_KVY)
    ozkaynak        = _find_b(b, *_OZKAYNAK,         period=period)
    odenmis_sermaye = _find_b(b, *_ODENMIS_SERMAYE,  period=period)
    serm_duzeltme   = _find_b(b, *_SERMAYE_DUZELTME, period=period)
    toplam_varlik   = _find_b(b, *_TOPLAM_VARLIK,    period=period)
    ticari_alacak   = gv(b, *_TIC_ALACAK)
    stok            = gv(b, *_STOK)
    ticari_borc     = gv(b, *_TIC_BORC)

    fin_kv = gv(b, *_FIN_BORC_KV)
    fin_uv = gv(b, *_FIN_BORC_UV)
    toplam_fin_borc = (
        (fin_kv or 0) + (fin_uv or 0)
        if (fin_kv is not None or fin_uv is not None) else None
    )
    net_borc = (
        toplam_fin_borc - nakit
        if toplam_fin_borc is not None and nakit is not None else None
    )

    # --- Dipnotlar ---
    amorti         = gv(d, *_AMORTISMAN)
    yurtici_satis  = gv(d, *_YURTICI_SAT)
    yurtdisi_satis = gv(d, *_YURTDISI_SAT)

    # --- Nakit akış ---
    fcf        = gv(na, *_FCF)
    capex      = gv(na, *_CAPEX)
    isletme    = gv(na, *_ISLETME_CF)
    temettu    = gv(na, *_TEMETTU_ODE)
    serm_artir = gv(na, *_SERM_ARTIR)

    # FAVÖK = Faaliyet Karı + Amortisman
    if faal_kar is not None and amorti is not None:
        favok: float | None = faal_kar + amorti
    else:
        favok = faal_kar  # dipnot yoksa proxy (veya None)

    # Enflasyon düzeltme tespiti (TMS 29 — 31.12.2023 itibaren zorunlu)
    yil = int(period.split("/")[0])
    enflasyon_duzeltildi: bool = (yil >= 2024) or (serm_duzeltme not in (None, 0))

    # Bedelsiz potansiyel = özkaynak / ödenmiş sermaye
    bedelsiz_x   = _safe_div(ozkaynak, odenmis_sermaye)
    bedelsiz_pct = (bedelsiz_x - 1) * 100 if bedelsiz_x is not None else None

    # --- Marjlar ---
    brut_marj  = _safe_div(brut_kar, satis)
    favok_marj = _safe_div(favok,    satis)
    nk_marj    = _safe_div(net_kar,  satis)
    fcf_marj   = _safe_div(fcf,      satis)
    capex_sat  = _safe_div(capex,    satis)

    # --- Karlılık ---
    roe_v = _safe_div(net_kar,  ozkaynak)
    roa_v = _safe_div(net_kar,  toplam_varlik)

    # --- DuPont bileşenleri (YTD; TTM versiyonu compute_metrics'te) ---
    varlik_devir_ytd = _safe_div(satis,         toplam_varlik)
    fin_kaldirac     = _safe_div(toplam_varlik,  ozkaynak)
    uv_borc_varlik   = _safe_div(fin_uv,        toplam_varlik)  # Piotroski F5

    # --- İşletme sermayesi (gün) ---
    days     = _days_in_period(period)
    cogs_abs = abs(satis_maliyeti) if satis_maliyeti is not None else None

    dso: float | None = (
        ticari_alacak / satis * days
        if (ticari_alacak is not None and satis is not None and satis != 0) else None
    )
    dio: float | None = (
        stok / cogs_abs * days
        if (stok is not None and cogs_abs is not None and cogs_abs != 0) else None
    )
    dpo: float | None = (
        ticari_borc / cogs_abs * days
        if (ticari_borc is not None and cogs_abs is not None and cogs_abs != 0) else None
    )
    ccc: float | None = (
        dso + dio - dpo
        if (dso is not None and dio is not None and dpo is not None) else None
    )

    # --- Yurtiçi/Yurtdışı ---
    toplam_satis_dipnot = (
        (yurtici_satis or 0) + (yurtdisi_satis or 0)
        if (yurtici_satis is not None or yurtdisi_satis is not None) else None
    )
    ihracat_orani: float | None = (
        yurtdisi_satis / toplam_satis_dipnot * 100
        if (yurtdisi_satis is not None
            and toplam_satis_dipnot is not None
            and toplam_satis_dipnot != 0) else None
    )

    # --- Temettü dağıtım oranı ---
    dagitim_orani: float | None = (
        abs(temettu) / net_kar * 100
        if (temettu is not None and net_kar is not None and net_kar != 0) else None
    )

    return {
        # Mutlak değerler (ham)
        "satis":               satis,
        "brut_kar":            brut_kar,
        "faaliyet_kar":        faal_kar,
        "favok":               favok,
        "net_kar":             net_kar,
        "nakit":               nakit,
        "net_borc":            net_borc,
        "donen_varlik":        donen,
        "kisa_vadeli_yukuml":  kvy,
        "ozkaynak":            ozkaynak,
        "odenmis_sermaye":     odenmis_sermaye,
        "sermaye_duzeltme":    serm_duzeltme,
        "enflasyon_duzeltildi": enflasyon_duzeltildi,
        "bedelsiz_potansiyel_x":   bedelsiz_x,
        "bedelsiz_potansiyel_pct": bedelsiz_pct,
        "fcf":                 fcf,
        "capex":               capex,
        "isletme_cf":          isletme,
        # Yeni ham kalemler
        "toplam_varlik":       toplam_varlik,
        "ticari_alacak":       ticari_alacak,
        "stok":                stok,
        "ticari_borc":         ticari_borc,
        "fin_borc_uv":         fin_uv,
        "satis_maliyeti":      satis_maliyeti,
        "yurtici_satis":       yurtici_satis,
        "yurtdisi_satis":      yurtdisi_satis,
        "temettu_odeme":       temettu,
        "sermaye_artirimi":    serm_artir,
        "hbk":                 hbk,
        # Oranlar (%)
        "brut_kar_marji":      (brut_marj  * 100) if brut_marj  is not None else None,
        "favok_marji":         (favok_marj * 100) if favok_marj is not None else None,
        "net_kar_marji":       (nk_marj    * 100) if nk_marj    is not None else None,
        "fcf_marji":           (fcf_marj   * 100) if fcf_marj   is not None else None,
        "capex_satis":         (capex_sat  * 100) if capex_sat  is not None else None,
        "roe":                 (roe_v * 100) if roe_v is not None else None,
        "roa":                 (roa_v * 100) if roa_v is not None else None,
        "ihracat_orani":       ihracat_orani,
        "dagitim_orani":       dagitim_orani,
        # Çarpanlar
        "net_borc_favok":      _safe_div(net_borc, favok),
        "cari_oran":           _safe_div(donen, kvy),
        # DuPont bileşenleri (YTD baz)
        "varlik_devir_ytd":    varlik_devir_ytd,
        "fin_kaldirac":        fin_kaldirac,
        "uv_borc_varlik":      uv_borc_varlik,
        # İşletme sermayesi (gün)
        "dso":                 dso,
        "dio":                 dio,
        "dpo":                 dpo,
        "ccc":                 ccc,
    }


# ---------------------------------------------------------------------------
# QoQ / YoY değişim
# ---------------------------------------------------------------------------

def _quarter_index(period: str) -> tuple[int, int]:
    parts = period.split("/")
    return int(parts[0]), int(parts[1])


def _find_qoq_period(period: str, all_periods: list[str]) -> str | None:
    try:
        idx = all_periods.index(period)
        if idx + 1 < len(all_periods):
            return all_periods[idx + 1]
    except ValueError:
        pass
    return None


def _find_yoy_period(period: str, all_periods: list[str]) -> str | None:
    y, m = _quarter_index(period)
    target_year = y - 1
    for p in all_periods:
        py, pm = _quarter_index(p)
        if py == target_year and pm == m:
            return p
    return None


# ---------------------------------------------------------------------------
# Piotroski F-Score (9 ikili kriter, YoY karşılaştırmalı)
# ---------------------------------------------------------------------------

def _piotroski(all_single: dict, periods: list[str]) -> dict[str, dict]:
    """
    Piotroski F-Score (0–9). Her dönem için hesaplanır.
    YoY karşılaştırma: aynı dönemin bir yıl öncesiyle.
    Bankalar için bazı kriterler None (COGS/işletme sermayesi yok).
    """

    def g(key: str, p: str) -> float | None:
        return all_single.get(key, {}).get(p)

    result: dict[str, dict] = {}

    for period in periods:
        yoy_p = _find_yoy_period(period, periods)

        def cur(key: str) -> float | None:
            return g(key, period)

        def prv(key: str) -> float | None:
            return g(key, yoy_p) if yoy_p else None

        def s_up(key: str) -> int | None:
            c, p_ = cur(key), prv(key)
            if c is None or p_ is None:
                return None
            return 1 if c > p_ else 0

        def s_dn(key: str) -> int | None:
            c, p_ = cur(key), prv(key)
            if c is None or p_ is None:
                return None
            return 1 if c < p_ else 0

        def s_pos(key: str) -> int | None:
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
# Delta hesabı
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
    Scraper çıktısından tüm metrikleri hesaplar.

    Dönüş sözlüğündeki önemli anahtarlar:
      periods, ticker, currency
      satis, favok, net_kar, net_borc, ...        ← YTD ham
      satis_ttm, net_kar_ttm, favok_ttm           ← TTM (Trailing 12 Month)
      satis_ceyrek, net_kar_ceyrek, favok_ceyrek  ← diskret çeyrek
      dso, dio, dpo, ccc                          ← işletme sermayesi (gün)
      dupont_net_kar_marji, dupont_varlik_devir, dupont_fin_kaldirac, dupont_roe
      piotroski                                   ← F-Score (0-9)
      piotroski_f1 .. piotroski_f9                ← alt kriterler
      _delta.qoq / _delta.yoy                    ← % değişim
      _raw_sections                               ← ham bilanco/gelir/dipnot/nakit
      _piotroski_detail                           ← tam kriter kırılımı
    """
    sections = data["sections"]
    periods  = data["periods"]

    # Her dönem için tekil metrikleri hesapla
    all_single: dict[str, dict[str, float | None]] = {}
    for period in periods:
        single = _single_period(sections, period)
        for metric, value in single.items():
            if metric not in all_single:
                all_single[metric] = {}
            all_single[metric][period] = value

    # --- De-kümülasyon: diskret çeyrek & TTM ---
    for src_key, dst_key in [
        ("satis",   "satis_ceyrek"),
        ("net_kar", "net_kar_ceyrek"),
        ("favok",   "favok_ceyrek"),
    ]:
        src = all_single.get(src_key, {})
        all_single[dst_key] = {p: _discrete(src, p, periods) for p in periods}

    for src_key, dst_key in [
        ("satis",   "satis_ttm"),
        ("net_kar", "net_kar_ttm"),
        ("favok",   "favok_ttm"),
    ]:
        src = all_single.get(src_key, {})
        all_single[dst_key] = {p: _ttm(src, p, periods) for p in periods}

    # --- DuPont (TTM gelir + anlık bilanço) ---
    sttm  = all_single.get("satis_ttm",   {})
    nkttm = all_single.get("net_kar_ttm", {})
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

        nkm = _safe_div(n_ttm, s_ttm)
        vd  = _safe_div(s_ttm, tv)
        fk  = _safe_div(tv,    ozk)

        dup_nkm[p] = (nkm * 100) if nkm is not None else None
        dup_vd[p]  = vd
        dup_fk[p]  = fk
        dup_roe[p] = (nkm * vd * fk * 100) if None not in (nkm, vd, fk) else None

    all_single["dupont_net_kar_marji"] = dup_nkm
    all_single["dupont_varlik_devir"]  = dup_vd
    all_single["dupont_fin_kaldirac"]  = dup_fk
    all_single["dupont_roe"]           = dup_roe

    # Net Borç/FAVÖK (TTM bazlı)
    all_single["net_borc_favok_ttm"] = {
        p: _safe_div(all_single.get("net_borc", {}).get(p),
                     all_single.get("favok_ttm", {}).get(p))
        for p in periods
    }

    # --- Piotroski F-Score ---
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

    # --- Delta hesabı ---
    qoq = _compute_deltas(all_single, periods, "qoq")
    yoy = _compute_deltas(all_single, periods, "yoy")

    return {
        "ticker":              data.get("ticker", ""),
        "periods":             periods,
        "currency":            data.get("currency", "TRY"),
        "_raw_sections":       sections,
        "_piotroski_detail":   piotroski_raw,
        **all_single,
        "_delta": {"qoq": qoq, "yoy": yoy},
    }


def print_summary(m: dict) -> None:
    """Terminale metrik özeti yazdır."""
    periods = m["periods"]
    p0, p1, p2, p3 = (periods + [None, None, None, None])[:4]

    print(f"\n{'='*72}")
    print(f"  {m['ticker']} — Finansal Metrik Özeti ({m['currency']})")
    print(f"{'='*72}")
    header = f"{'Metrik':<28} {p0 or '':>12} {p1 or '':>12} {p2 or '':>12} {p3 or '':>12}"
    print(header)
    print("-" * 72)

    def fmt_abs(v: float | None, scale: float = 1e9) -> str:
        if v is None:
            return "       —"
        return f"{v / scale:>12.2f}"

    def fmt_pct(v: float | None) -> str:
        if v is None:
            return "       —"
        return f"{v:>11.1f}%"

    def fmt_ratio(v: float | None) -> str:
        if v is None:
            return "       —"
        return f"{v:>11.2f}x"

    def fmt_days(v: float | None) -> str:
        if v is None:
            return "       —"
        return f"{v:>10.0f}g"

    rows = [
        ("Satışlar (mn)",     "satis",          1e6, "abs"),
        ("FAVÖK (mn)",        "favok",          1e6, "abs"),
        ("Net Kar (mn)",      "net_kar",        1e6, "abs"),
        ("Net Borç (mn)",     "net_borc",       1e6, "abs"),
        ("FCF (mn)",          "fcf",            1e6, "abs"),
        ("Toplam Varlık (mn)","toplam_varlik",  1e6, "abs"),
        ("Brüt Marj %",       "brut_kar_marji", 1,   "pct"),
        ("FAVÖK Marjı %",     "favok_marji",    1,   "pct"),
        ("Net Kar Marj %",    "net_kar_marji",  1,   "pct"),
        ("ROE %",             "roe",            1,   "pct"),
        ("ROA %",             "roa",            1,   "pct"),
        ("Net Borç/FAVÖK",    "net_borc_favok", 1,   "ratio"),
        ("Cari Oran",         "cari_oran",      1,   "ratio"),
        ("DSO (gün)",         "dso",            1,   "days"),
        ("DIO (gün)",         "dio",            1,   "days"),
        ("DPO (gün)",         "dpo",            1,   "days"),
        ("CCC (gün)",         "ccc",            1,   "days"),
        ("DuPont ROE %",      "dupont_roe",     1,   "pct"),
        ("İhracat Oranı %",   "ihracat_orani",  1,   "pct"),
        ("Piotroski F-Score", "piotroski",      1,   "ratio"),
    ]

    for label, key, scale, kind in rows:
        vals = [m.get(key, {}).get(p) for p in [p0, p1, p2, p3]]
        if kind == "abs":
            cells = "".join(fmt_abs(v, scale) for v in vals)
        elif kind == "ratio":
            cells = "".join(fmt_ratio(v) for v in vals)
        elif kind == "days":
            cells = "".join(fmt_days(v) for v in vals)
        else:
            cells = "".join(fmt_pct(v) for v in vals)
        print(f"  {label:<26} {cells}")

    if p0 and p1:
        print(f"\n  QoQ Degisim ({p1} -> {p0}):")
        for label, key, _, _ in rows[:5]:
            delta = m["_delta"]["qoq"].get(key, {}).get(p0)
            arrow = ("↑" if delta > 0 else "↓") if delta is not None else " "
            dstr  = f"{delta:+.1f}%" if delta is not None else "—"
            print(f"    {label:<26} {arrow} {dstr}")

    if p0:
        bx = m.get("bedelsiz_potansiyel_x",  {}).get(p0)
        bp = m.get("bedelsiz_potansiyel_pct", {}).get(p0)
        ef = m.get("enflasyon_duzeltildi",    {}).get(p0)
        if bx is not None:
            ef_label = "[✓ enflasyon düzeltmeli]" if ef else "[⚠ nominal — düzeltme yok]"
            print(f"\n  Bedelsiz Potansiyel ({p0}): {bx:.2f}x  (~%{bp:.0f})  {ef_label}")

    print(f"{'='*72}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import io, sys, json
    from pathlib import Path
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "buffer"):
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print("Kullanım: python metrics.py <finansal_json_dosyasi>")
        sys.exit(1)

    path = Path(sys.argv[1])
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    m = compute_metrics(data)
    print_summary(m)
