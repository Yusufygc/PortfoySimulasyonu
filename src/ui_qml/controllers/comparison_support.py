"""Karşılaştırma Laboratuvarı yardımcıları: seçim ayrıştırma, tarih aralığı, AI istemi, portföy hisse verisi.

Denetleyici durumundan bağımsız saf fonksiyonlardır; yalnızca verilen servis ve değerlerle çalışır.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from src.application.services.analysis.models import AnalysisFilterState

logger = logging.getLogger(__name__)

_PERIOD_DELTAS = {
    "1A": timedelta(days=30),
    "3A": timedelta(days=90),
    "6A": timedelta(days=180),
    "1Y": timedelta(days=365),
}

_MODE_LABELS = {"NORMALIZED": "Normalize (Baz 100)", "NORMAL": "Normal", "RATIO": "Rasyo"}
_CURRENCY_LABELS = {"TL": "TL", "USD": "USD", "REAL": "enflasyondan arındırılmış (reel)"}


def parse_date(text: str) -> Optional[date]:
    text = (text or "").strip()
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def resolve_start_date(label: str, end_dt: date) -> date:
    if label in _PERIOD_DELTAS:
        return end_dt - _PERIOD_DELTAS[label]
    if label == "YBB":
        return date(end_dt.year, 1, 1)
    return date(2022, 1, 1)


def resolve_range(period_label: str, custom_start: str, custom_end: str) -> Tuple[date, date]:
    end_dt = date.today()
    if period_label == "ÖZEL":
        start = parse_date(custom_start)
        end = parse_date(custom_end)
        if start is not None and end is not None and start < end:
            return start, end
    return resolve_start_date(period_label, end_dt), end_dt


def find_column(df: pd.DataFrame, code: str) -> Optional[str]:
    if code in df.columns:
        return code
    for c in df.columns:
        if code.lower() in c.lower() or c.lower() in code.lower():
            return c
    return df.columns[0] if len(df.columns) > 0 else None


def split_selection(
    selected_codes: Iterable[str],
    stock_ids_for_source: Callable[[str], Iterable[int]],
) -> Tuple[List[str], List[str], List[int]]:
    """Seçili kodları (portföy kaynağı, benchmark, hisse kimliği) üçlüsüne ayırır."""
    portfolio_sources: List[str] = []
    benchmarks: List[str] = []
    stock_ids: List[int] = []

    for code in selected_codes:
        if code.startswith("holdings:"):
            # Portföy + o portföyün hisseleri (tek tek kıyaslanır)
            source = code.split(":", 1)[1]
            _append_unique(portfolio_sources, source)
            for stock_id in _source_stock_ids(source, stock_ids_for_source):
                _append_unique(stock_ids, stock_id)
        elif _is_portfolio_source(code):
            _append_unique(portfolio_sources, code)
        elif code.isdigit():
            _append_unique(stock_ids, int(code))
        else:
            benchmarks.append(code)
    return portfolio_sources, benchmarks, stock_ids


def _append_unique(target: list, value) -> None:
    if value not in target:
        target.append(value)


def _is_portfolio_source(code: str) -> bool:
    return code == "dashboard" or code.startswith(("model:", "portfolio:"))


def _source_stock_ids(source: str, stock_ids_for_source: Callable[[str], Iterable[int]]) -> List[int]:
    try:
        return list(stock_ids_for_source(source))
    except Exception as exc:
        logger.warning("Portföy hisseleri okunamadı (%s): %s", source, exc)
        return []


def build_filter_state(
    selected_codes: Iterable[str],
    start_dt: date,
    end_dt: date,
    currency_mode: str,
    stock_ids_for_source: Callable[[str], Iterable[int]],
) -> AnalysisFilterState:
    portfolio_sources, benchmarks, stock_ids = split_selection(selected_codes, stock_ids_for_source)
    return AnalysisFilterState(
        start_date=start_dt,
        end_date=end_dt,
        selected_stock_ids=stock_ids,
        selected_benchmarks=benchmarks,
        portfolio_source=portfolio_sources[0] if portfolio_sources else "dashboard",
        comparison_portfolio_sources=portfolio_sources,
        currency_mode=currency_mode,
    )


def build_risk_return_metrics(aligned: pd.DataFrame, risk_return: Dict[str, Dict[str, float]]) -> List[Dict[str, Any]]:
    metrics = []
    for col in aligned.columns:
        rm = risk_return.get(col, {})
        metrics.append({
            "code": col,
            "label": col,
            "totalReturn": round(rm.get("total_return_pct", 0.0), 2),
            "volatility": round(rm.get("annual_volatility_pct", 0.0), 2),
        })
    return metrics


def build_commentary_prompt(
    last_range: Tuple[Optional[date], Optional[date]],
    metrics: List[Dict[str, Any]],
    comparison_mode: str,
    currency_mode: str,
) -> str:
    start, end = last_range
    rows = "\n".join(
        f"- **{m['label']}**: Toplam Getiri: %{m['totalReturn']}, Yıllık Volatilite: %{m['volatility']}"
        for m in metrics
    )
    period = (
        f"{start.strftime('%d.%m.%Y')} ile {end.strftime('%d.%m.%Y')} tarihleri arasında"
        if start and end else "seçili dönemde"
    )
    return (
        f"Kullanıcı Karşılaştırma Laboratuvarı ekranında {period} "
        f"{_MODE_LABELS.get(comparison_mode, comparison_mode)} biçiminde, "
        f"{_CURRENCY_LABELS.get(currency_mode, currency_mode)} cinsinden aşağıdaki varlıkların "
        f"performanslarını kıyaslıyor:\n\n{rows}\n\n"
        "Bir finansal analist olarak bu karşılaştırmayı profesyonelce yorumla:\n"
        "1. Dönemin en başarılı varlığı hangisidir ve neden öne çıkmıştır?\n"
        "2. Volatilite açısından en riskli ve en güvenli varlık hangisidir?\n"
        "3. Portföy çeşitlendirmesi için 2-3 pratik öneride bulun.\n\n"
        "Not: Yatırım tavsiyesi vermeden, yalnızca verileri yorumla."
    )


def fetch_portfolio_holdings(analysis_service, portfolio_code: str, period_label: str) -> List[Dict[str, Any]]:
    """Seçilen portföyün (ana portföy veya model portföyler) hisselerini, ağırlık ve getiri dağılımını çeker."""
    try:
        if not analysis_service:
            return []

        from src.application.services.analysis.risk_metrics import compute_position_snapshot

        end_dt = date.today()
        start_dt = resolve_start_date(period_label, end_dt)
        filter_state = AnalysisFilterState(
            start_date=start_dt,
            end_date=end_dt,
            selected_stock_ids=[],
            selected_benchmarks=[],
            portfolio_source=portfolio_code,
            comparison_portfolio_sources=[portfolio_code],
            currency_mode="TL",
        )
        bundle = analysis_service._build_analysis_bundle(filter_state)
        ticker_map = analysis_service._series_builder.get_ticker_map(list(bundle["portfolio"].positions.keys()))
        snapshot = compute_position_snapshot(bundle["portfolio"], ticker_map, bundle["position_values_end"])

        holdings = []
        for item in snapshot:
            w = round(float(item["weight"]), 2)
            lbl = str(item["label"])
            holdings.append({
                "code": lbl,
                "label": lbl,
                "ret": round(float(item["return_pct"]), 2),
                "weight": w,
                "value": max(w, 0.5),  # Treemap kutu alanı portföy ağırlığına göre
                "marketValue": round(float(item["current_value"]), 2),
                "costValue": round(float(item["cost_value"]), 2),
                "vol": 0.0,
            })
        return holdings
    except Exception as exc:
        logger.warning("Portföy hisseleri çekilirken hata (%s): %s", portfolio_code, exc)
        return []
