"""AiAdvisorService — araç kayıt defteri + dispatch testleri (bkz. plan §6.2, e1.1)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

from src.application.services.ai.ai_advisor_service import AiAdvisorService
from src.application.services.analysis.models import AnalysisOverviewDTO
from src.domain.models.ai_tool import ToolDeclaration


def _overview_dto() -> AnalysisOverviewDTO:
    return AnalysisOverviewDTO(
        total_value=Decimal("1000"), period_return_pct=5.0, benchmark_gap_pct=1.0, benchmark_label="BIST 100",
        largest_position_label="AKBNK", largest_position_weight_pct=50.0, best_contributor_label="AKBNK",
        best_contributor_pct=5.0, worst_contributor_label="-", worst_contributor_pct=None, max_drawdown_pct=-3.0,
        insights=[], warnings=[], portfolio_label="Ana Portföy",
    )


def _make_service() -> AiAdvisorService:
    portfolio_analytics_service = MagicMock()
    portfolio_analytics_service.get_first_trade_date_for_source.return_value = date(2024, 1, 1)
    portfolio_analytics_service.get_overview.return_value = _overview_dto()
    return AiAdvisorService(
        portfolio_analytics_service=portfolio_analytics_service,
        risk_optimization_bridge_service=MagicMock(),
        stock_360_service=MagicMock(),
    )


class TestToolSpecs:
    def test_exposes_four_tool_specs(self):
        service = _make_service()
        names = {spec.name for spec in service.tool_specs}
        assert names == {
            "get_portfolio_overview", "get_allocation_and_risk", "suggest_optimization", "get_stock_overview",
        }

    def test_tool_specs_returns_a_copy_not_internal_list(self):
        service = _make_service()
        specs = service.tool_specs
        specs.clear()
        assert len(service.tool_specs) == 4

    def test_tool_declarations_is_handler_free_domain_view(self):
        service = _make_service()
        declarations = service.tool_declarations
        assert len(declarations) == 4
        assert all(isinstance(d, ToolDeclaration) for d in declarations)
        by_name = {d.name: d for d in declarations}
        assert by_name["get_portfolio_overview"].description
        assert by_name["get_portfolio_overview"].parameters_schema["type"] == "object"


class TestCallTool:
    def test_known_tool_dispatches_to_handler(self):
        service = _make_service()
        result = service.call_tool("get_portfolio_overview")
        assert result["portfolio_label"] == "Ana Portföy"

    def test_arguments_forwarded_to_handler(self):
        service = _make_service()
        result = service.call_tool("get_stock_overview", {"ticker": ""})
        assert "error" in result  # boş ticker -> handler kendi hata mesajını üretir

    def test_none_arguments_defaults_to_empty_dict(self):
        service = _make_service()
        result = service.call_tool("get_portfolio_overview", None)
        assert "error" not in result

    def test_unknown_tool_name_returns_error_not_exception(self):
        service = _make_service()
        result = service.call_tool("uydurma_arac")
        assert "Bilinmeyen araç" in result["error"]
        assert "get_portfolio_overview" in result["error"]

    def test_handler_exception_is_captured_as_error_dict(self):
        service = _make_service()
        broken_spec = next(s for s in service.tool_specs if s.name == "get_portfolio_overview")
        service._tools_by_name["get_portfolio_overview"] = broken_spec.__class__(
            name="get_portfolio_overview", description="x", parameters_schema={"type": "object", "properties": {}},
            handler=lambda _args: (_ for _ in ()).throw(RuntimeError("beklenmeyen hata")),
        )

        result = service.call_tool("get_portfolio_overview")

        assert result == {"error": "beklenmeyen hata"}
