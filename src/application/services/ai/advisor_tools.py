"""
Gemini Tool-Calling araçları — "Yatırım & Portföy Danışmanı" (bkz. plan §6.2,
e1.1). Mevcut `PortfolioAnalyticsService`/`RiskOptimizationBridgeService`/
`Stock360Service`'e delege eden, JSON-serileştirilebilir dict döndüren SALT
OKUNUR fonksiyonlar — hiçbiri işlem/emir/para hareketi yürütmez (bkz. plan
§6.2.3: bu mimari bir sınırdır, sadece bir prompt kuralı değil).

Bu modül Gemini SDK'sına (google-genai) hiç bağımlı değildir — saf Python,
JSON Schema'ya benzer `parameters_schema` dict'leri döner; SDK'ya özgü
`types.FunctionDeclaration`'a çevirme işi `gemini_advisor_chat_provider.py`'de
(e1.2) yapılacaktır. Bu ayrım, `series_mapper.py`/`QQuickPaintedItem` desenindeki
"saf hesap + framework'e özgü ince katman" ilkesiyle aynıdır.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional

from src.application.services.analysis.models import AnalysisFilterState
from src.domain.market_clock import market_today

_DEFAULT_LOOKBACK_DAYS = 365
_DEFAULT_BENCHMARK = "bist100"
_SCOPE_SOURCES = {"all": "unified", "bist": "dashboard"}   # varsayılan: tüm varlıklar (BIST + altın, kripto, ABD hissesi, nakit)

_VALID_RISK_LABELS = {"COK_MUHAFAZAKAR", "MUHAFAZAKAR", "DENGELI", "BUYUME_ODAKLI", "AGRESIF"}


def _to_float(value: Any) -> Optional[float]:
    return float(value) if value is not None else None


@dataclass(frozen=True)
class ToolSpec:
    """Bir aracın adı/açıklaması/parametre şeması/işleyicisi.

    `parameters_schema`, google-genai `types.FunctionDeclaration.parameters`'ın
    beklediği JSON Schema biçimiyle uyumludur (`{"type": "object", "properties": {...},
    "required": [...]}`) ama bu modül SDK'yı hiç import etmez — çeviri e1.2'de.
    `handler`, ayrıştırılmış argüman dict'ini alır, JSON-serileştirilebilir bir
    dict döner (hata durumunda da normal bir dict — `{"error": "..."}", exception
    fırlatmaz ki sohbet döngüsü çökmesin).
    """

    name: str
    description: str
    parameters_schema: Dict[str, Any]
    handler: Callable[[Dict[str, Any]], Dict[str, Any]]


_SCOPE_PROPERTY: Dict[str, Any] = {
    "type": "string",
    "enum": sorted(_SCOPE_SOURCES),
    "description": "Kapsam: 'all' (varsayılan) BIST hisseleri, altın/gümüş/platin, kripto, ABD hisseleri ve nakit dahil "
    "tüm varlıklar; 'bist' yalnızca BIST hisse portföyü.",
}


def _build_default_filter_state(portfolio_analytics_service, scope: Any = None) -> AnalysisFilterState:
    """Seçilen kapsama göre portföy kaynağı (varsayılan tüm varlıklar), BIST 100 benchmark, ilk işlem tarihinden bugüne."""
    source = _SCOPE_SOURCES.get(str(scope or "all").strip().lower(), _SCOPE_SOURCES["all"])
    today = market_today()
    start = portfolio_analytics_service.get_first_trade_date_for_source(source) or (
        today - timedelta(days=_DEFAULT_LOOKBACK_DAYS)
    )
    return AnalysisFilterState(
        start_date=start,
        end_date=today,
        portfolio_source=source,
        selected_benchmarks=[_DEFAULT_BENCHMARK],
    )


def _metrics_to_dict(metrics) -> Dict[str, Optional[float]]:
    return {
        "expected_return_pct": metrics.expected_return * 100.0,
        "volatility_pct": metrics.volatility * 100.0,
        "sharpe_ratio": metrics.sharpe_ratio,
    }


# ----------------------------------------------------------------------
# 1. get_portfolio_overview
# ----------------------------------------------------------------------

def _make_get_portfolio_overview_handler(portfolio_analytics_service) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
        filter_state = _build_default_filter_state(portfolio_analytics_service, arguments.get("scope"))
        overview = portfolio_analytics_service.get_overview(filter_state)
        return {
            "portfolio_label": overview.portfolio_label,
            "total_value_try": _to_float(overview.total_value),
            "period_return_pct": overview.period_return_pct,
            "benchmark_label": overview.benchmark_label,
            "benchmark_gap_pct": overview.benchmark_gap_pct,
            "largest_position_label": overview.largest_position_label,
            "largest_position_weight_pct": overview.largest_position_weight_pct,
            "best_contributor_label": overview.best_contributor_label,
            "best_contributor_pct": overview.best_contributor_pct,
            "worst_contributor_label": overview.worst_contributor_label,
            "worst_contributor_pct": overview.worst_contributor_pct,
            "max_drawdown_pct": overview.max_drawdown_pct,
            "warnings": list(overview.warnings),
        }

    return handler


_GET_PORTFOLIO_OVERVIEW_SCHEMA: Dict[str, Any] = {"type": "object", "properties": {"scope": _SCOPE_PROPERTY}}


# ----------------------------------------------------------------------
# 2. get_allocation_and_risk
# ----------------------------------------------------------------------

def _make_get_allocation_and_risk_handler(portfolio_analytics_service) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
        filter_state = _build_default_filter_state(portfolio_analytics_service, arguments.get("scope"))
        risk_view = portfolio_analytics_service.get_allocation_risk_view(filter_state)
        return {
            "items": [
                {
                    "label": item.label,
                    "weight_pct": item.weight_pct,
                    "current_value_try": item.current_value,
                }
                for item in risk_view.items
            ],
            "top_three_weight_pct": risk_view.top_three_weight_pct,
            "volatility_pct": risk_view.volatility_pct,
            "max_drawdown_pct": risk_view.max_drawdown_pct,
            "concentration_label": risk_view.concentration_label,
            "sharpe_ratio": risk_view.sharpe_ratio,
            "beta": risk_view.beta,
            "alpha": risk_view.alpha,
            "warnings": list(risk_view.warnings),
        }

    return handler


_GET_ALLOCATION_AND_RISK_SCHEMA: Dict[str, Any] = {"type": "object", "properties": {"scope": _SCOPE_PROPERTY}}


# ----------------------------------------------------------------------
# 2b. get_assets_overview
# ----------------------------------------------------------------------

def _holding_to_dict(holding) -> Dict[str, Any]:
    return {
        "symbol": holding.symbol,
        "name": holding.name,
        "class": holding.allocation_class.value,
        "quantity": _to_float(holding.quantity),
        "currency": holding.native_currency,
        "value_try": _to_float(holding.value_try),
        "cost_try": _to_float(holding.cost_try),
        "unrealized_pl_try": _to_float(holding.value_try - holding.cost_try),
        "weight_pct": _to_float(holding.weight_pct),
        "daily_change_pct": _to_float(holding.daily_change_pct),
        "is_priced": holding.is_priced,
    }


def _make_get_assets_overview_handler(unified_portfolio_service) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def handler(_arguments: Dict[str, Any]) -> Dict[str, Any]:
        try:
            summary = unified_portfolio_service.get_summary("TRY")
        except Exception as exc:
            return {"error": str(exc)}
        return {
            "total_value_try": _to_float(summary.total_value_try),
            "total_cost_try": _to_float(summary.total_cost_try),
            "daily_gain_try": _to_float(summary.daily_gain_try),
            "cash_try": _to_float(summary.cash_try),
            "cash_usd": _to_float(summary.usd_cash),
            "classes": [
                {"class": s.allocation_class.value, "value_try": _to_float(s.value_try),
                 "weight_pct": _to_float(s.weight_pct), "holdings": s.holdings_count}
                for s in summary.slices
            ],
            "holdings": [_holding_to_dict(h) for h in summary.holdings],
            "unpriced_symbols": list(summary.unpriced_symbols),
        }

    return handler


_GET_ASSETS_OVERVIEW_SCHEMA: Dict[str, Any] = {"type": "object", "properties": {}}


# ----------------------------------------------------------------------
# 3. suggest_optimization
# ----------------------------------------------------------------------

def _make_suggest_optimization_handler(risk_optimization_bridge_service) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
        risk_label = arguments.get("risk_label")
        if risk_label is not None and risk_label not in _VALID_RISK_LABELS:
            risk_label = None  # bilinmeyen etiket -> kayıtlı profile/varsayılana düş, uydurma değer kullanma

        try:
            outcome = risk_optimization_bridge_service.optimize_dashboard_portfolio_with_risk_profile(
                risk_label_override=risk_label,
            )
        except Exception as exc:
            return {"error": str(exc)}

        result = outcome.result
        return {
            "applied_risk_label": outcome.risk_label,
            "max_single_weight_pct": outcome.max_single_weight_pct,
            "used_default_profile": outcome.used_default_profile,
            "is_manual_override": outcome.is_manual_override,
            "current": _metrics_to_dict(result.current_metrics),
            "optimized": _metrics_to_dict(result.optimized_metrics),
            "min_volatility": _metrics_to_dict(result.min_volatility_metrics) if result.min_volatility_metrics else None,
            "suggestions": [
                {
                    "symbol": s.symbol,
                    "current_weight_pct": s.current_weight,
                    "optimal_weight_pct": s.optimal_weight,
                    "change_pct": s.change,
                    "action": s.action,
                }
                for s in result.suggestions
            ],
        }

    return handler


_SUGGEST_OPTIMIZATION_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "risk_label": {
            "type": "string",
            "description": (
                "Opsiyonel risk profili geçersiz kılma — kayıtlı anket profilini DEĞİŞTİRMEZ, "
                "sadece bu tek öneri için geçici bir önizleme üretir. Verilmezse kullanıcının "
                "kayıtlı risk profili (varsa) veya DENGELI varsayılanı kullanılır."
            ),
            "enum": sorted(_VALID_RISK_LABELS),
        },
    },
}


# ----------------------------------------------------------------------
# 4. get_stock_overview
# ----------------------------------------------------------------------

def _make_get_stock_overview_handler(stock_360_service) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
    def handler(arguments: Dict[str, Any]) -> Dict[str, Any]:
        ticker = str(arguments.get("ticker") or "").strip().upper()
        if not ticker:
            return {"error": "ticker parametresi zorunludur."}

        overview = stock_360_service.get_overview(ticker)
        if overview is None:
            return {"error": f"'{ticker}' için yerel veritabanında fiyat verisi bulunamadı."}

        payload: Dict[str, Any] = {
            "ticker": overview.ticker,
            "last_price": _to_float(overview.last_price),
            "last_price_date": overview.last_price_date.isoformat(),
            "daily_change_pct": overview.daily_change_pct,
            "volume": overview.volume,
            "week52_low": _to_float(overview.week52_low),
            "week52_high": _to_float(overview.week52_high),
        }

        technical = stock_360_service.get_technical_levels(ticker)
        if technical is not None:
            payload.update(
                {
                    "rsi14": technical.rsi14,
                    "macd_line": technical.macd_line,
                    "macd_signal": technical.macd_signal,
                    "sma50": technical.sma50,
                    "sma200": technical.sma200,
                    "ema20": technical.ema20,
                    "support": technical.support,
                    "resistance": technical.resistance,
                }
            )
        return payload

    return handler


_GET_STOCK_OVERVIEW_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "ticker": {
            "type": "string",
            "description": "Hisse kodu (örn. 'AKBNK' veya 'AKBNK.IS').",
        },
    },
    "required": ["ticker"],
}


# ----------------------------------------------------------------------
# Kayıt Defteri
# ----------------------------------------------------------------------

def build_tool_specs(
    portfolio_analytics_service,
    risk_optimization_bridge_service,
    stock_360_service,
    unified_portfolio_service=None,
) -> List[ToolSpec]:
    """Salt-okunur araç listesi (bkz. plan §6.2.3); varlık defteri servisi verilirse `get_assets_overview` da eklenir."""
    specs = [
        ToolSpec(
            name="get_portfolio_overview",
            description="Kullanıcının portföyünün genel özetini döner: toplam değer, dönem getirisi, "
            "benchmark (BIST 100) farkı, en büyük pozisyon, en iyi/kötü katkı sağlayan varlıklar. Varsayılan kapsam "
            "tüm varlıklardır (BIST hisseleri, altın/gümüş/platin, kripto, ABD hisseleri, nakit).",
            parameters_schema=_GET_PORTFOLIO_OVERVIEW_SCHEMA,
            handler=_make_get_portfolio_overview_handler(portfolio_analytics_service),
        ),
        ToolSpec(
            name="get_allocation_and_risk",
            description="Kullanıcının portföyündeki varlık dağılımını (ağırlık %) ve risk metriklerini "
            "(volatilite, maksimum drawdown, yoğunlaşma, Sharpe/Beta/Alfa) döner. Varsayılan kapsam tüm varlıklardır.",
            parameters_schema=_GET_ALLOCATION_AND_RISK_SCHEMA,
            handler=_make_get_allocation_and_risk_handler(portfolio_analytics_service),
        ),
        ToolSpec(
            name="suggest_optimization",
            description="Markowitz optimizasyonu çalıştırır: mevcut portföy, maksimum Sharpe ve minimum risk "
            "noktalarının getiri/risk metriklerini + hangi hisseden ne kadar alınıp satılacağına dair "
            "hisse bazlı önerileri (EKLE/AZALT/TUT) döner. SADECE ÖNERİ üretir, hiçbir işlem yapmaz.",
            parameters_schema=_SUGGEST_OPTIMIZATION_SCHEMA,
            handler=_make_suggest_optimization_handler(risk_optimization_bridge_service),
        ),
        ToolSpec(
            name="get_stock_overview",
            description="Tek bir hissenin son fiyatı, günlük değişimi, 52 haftalık aralığı ve teknik "
            "seviyelerini (RSI14, MACD, SMA50/200, EMA20, destek/direnç) döner.",
            parameters_schema=_GET_STOCK_OVERVIEW_SCHEMA,
            handler=_make_get_stock_overview_handler(stock_360_service),
        ),
    ]
    if unified_portfolio_service is not None:
        specs.insert(2, ToolSpec(
            name="get_assets_overview",
            description="Portföyün güncel TL değerini sınıf (BIST hissesi, ABD hissesi, kripto, kıymetli maden, nakit) ve "
            "pozisyon bazında döner: miktar, değer, maliyet, gerçekleşmemiş kâr/zarar, ağırlık, günlük değişim, TL ve USD nakit.",
            parameters_schema=_GET_ASSETS_OVERVIEW_SCHEMA,
            handler=_make_get_assets_overview_handler(unified_portfolio_service),
        ))
    return specs
