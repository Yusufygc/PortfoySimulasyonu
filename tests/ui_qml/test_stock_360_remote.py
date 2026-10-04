"""Stock 360 uzak veri akışı (katalog keşfi, arka plan çekimi) ve bölünmüş hesap yardımcıları."""
from __future__ import annotations

from types import SimpleNamespace

from src.ui_qml.controllers import stock_360_calc as calc
from src.ui_qml.controllers import stock_360_remote as remote


class _Service:
    def __init__(self, catalog=None, stocks=None, financials=None, shareholders=None, fin_exc=None):
        self._catalog, self._stocks = catalog, stocks or []
        self._financials, self._shareholders, self._fin_exc = financials, shareholders, fin_exc
        self.force_flags = []

    def get_catalog_tickers(self):
        return self._catalog

    def get_all_stocks(self):
        return self._stocks

    def get_financials(self, ticker, n_quarters=12):
        if self._fin_exc:
            raise self._fin_exc
        return self._financials

    def get_shareholders(self, ticker, force_refresh=False):
        self.force_flags.append(force_refresh)
        return self._shareholders


def _container(service):
    return SimpleNamespace(stock_360_service=service)


def test_rank_tickers_puts_candidates_first_and_caps_at_twelve():
    tickers = ["ZZZ", "THYAO", "AAA", "BIMAS"] + [f"T{i}" for i in range(20)]
    ranked = remote.rank_tickers(tickers)
    assert ranked[:2] == ["BIMAS", "THYAO"]
    assert len(ranked) == 12


def test_discover_prefers_catalog_then_stored_stocks_then_defaults():
    assert remote.discover_available_stocks(_container(_Service(catalog=["AAA", "BIMAS"]))) == ["BIMAS", "AAA"]
    stocks = [SimpleNamespace(ticker="XYZ.IS"), SimpleNamespace(ticker=None)]
    assert remote.discover_available_stocks(_container(_Service(catalog=[], stocks=stocks))) == ["XYZ"]
    assert remote.discover_available_stocks(_container(_Service(catalog=[]))) == remote.DEFAULT_CANDIDATES
    assert remote.discover_available_stocks(None) == remote.DEFAULT_CANDIDATES


def test_discover_falls_back_when_catalog_lookup_raises():
    class Broken(_Service):
        def get_catalog_tickers(self):
            raise RuntimeError("katalog yok")

    assert remote.discover_available_stocks(_container(Broken())) == remote.DEFAULT_CANDIDATES


def test_fetch_remote_data_without_service_returns_empty_result():
    result = remote.fetch_remote_data(None, "BIMAS", 8, False)
    assert result.as_tuple() == ("BIMAS", None, None, "", "", "")
    assert result.temp_files == []


def test_fetch_remote_data_reports_financial_error_but_still_fetches_shareholders():
    service = _Service(fin_exc=RuntimeError("ağ"), shareholders=[])
    result = remote.fetch_remote_data(service, "BIMAS", 8, True)
    assert result.error == "Finansal veriler alınamadı (ağ)"
    assert result.financials is None
    assert service.force_flags == [True]


def test_fetch_remote_data_writes_html_and_tracks_temp_files(monkeypatch, tmp_path):
    monkeypatch.setattr(remote, "generate_financials_html", lambda metrics, n_periods: f"<fin {n_periods}>")
    monkeypatch.setattr(remote, "generate_shareholders_html", lambda ticker, snaps: "<sh>")
    written = []

    def fake_write(prefix, ticker, html):
        path = str(tmp_path / f"{prefix}_{ticker}.html")
        written.append((prefix, html))
        return f"file:///{prefix}", path

    monkeypatch.setattr(remote, "write_temp_html", fake_write)
    service = _Service(financials={"periods": ["2026/3", "2025/12", "2025/9"]}, shareholders=[object()])
    all_periods = remote.fetch_remote_data(service, "BIMAS", 0, False)
    assert written[0] == ("fin_0", "<fin 3>")
    assert all_periods.fin_html_url == "file:///fin_0" and all_periods.sh_html_url == "file:///sh"
    assert len(all_periods.temp_files) == 2


def test_prior_year_period_and_series_fallback():
    assert calc._prior_year_period("2026/3") == "2025/3"
    assert calc._series_with_fallback({"b": {"x": 1}}, "a", "b") == {"x": 1}


def test_dupont_derived_from_statements_when_ttm_missing():
    metrics = {
        "satis_ceyrek": {"2026/3": 100.0}, "net_kar_ceyrek": {"2026/3": 10.0},
        "toplam_varlik": {"2026/3": 400.0}, "ozkaynak": {"2026/3": 100.0},
    }
    data = calc.compute_dupont_data(metrics, ["2026/3"])
    assert data["netMargin"] == "%10.00"
    assert data["assetTurnover"] == "1.00x"
    assert data["financialLeverage"] == "4.00x"
    assert data["roe"] == "%40.00"  # %10 marj x 1.0 devir x 4.0 kaldıraç
    assert data["piotroskiStatus"] == "Yüksek Finansal Güç"  # varsayılan skor 7
