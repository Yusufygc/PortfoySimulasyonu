import src.application.services.analysis as analysis_module


def test_analysis_public_import_surface_is_preserved():
    assert analysis_module.AnalysisService is not None
    assert analysis_module.AnalysisFilterState is not None
    assert analysis_module.BenchmarkDefinition is not None
    assert analysis_module.BenchmarkSeries is not None
    assert analysis_module.PortfolioOption is not None
    assert analysis_module.PortfolioSeriesPoint is not None
    assert analysis_module.AnalysisOverviewDTO is not None
    assert analysis_module.ComparisonViewDTO is not None
    assert analysis_module.AllocationRiskDTO is not None

