"""De-kümülasyon (_discrete/_ttm) ve TTM tabanlı ROE/ROA için elle hesaplanmış beklenen değer testleri.

İş Yatırım verisi YTD kümülatiftir: 2024/6 = Ocak-Haziran toplamı. Eksik çeyrek veya
ardışık olmayan dönemler TTM'i şişirmemeli; ROE/ROA çeyrekler arası karşılaştırılabilir
olmalıdır (son 12 ay net kâr bazında).
"""
from __future__ import annotations

import pytest

from src.application.services.analysis.financials import metrics

NET_KAR = "DÖNEM KARI (ZARARI)"

# YTD kümülatif net kâr. Diskret çeyrekler (elle):
#   2023: Q1=10, Q2=25-10=15, Q3=45-25=20, Q4=70-45=25
#   2024: Q1=20, Q2=50-20=30
NET_KAR_YTD = {
    "2023/3": 10.0, "2023/6": 25.0, "2023/9": 45.0, "2023/12": 70.0,
    "2024/3": 20.0, "2024/6": 50.0,
}
OZKAYNAK = {
    "2023/3": 200.0, "2023/6": 250.0, "2023/9": 300.0, "2023/12": 350.0,
    "2024/3": 400.0, "2024/6": 500.0,
}
TOPLAM_VARLIK = {p: 2 * v for p, v in OZKAYNAK.items()}

ALL_PERIODS = ["2024/6", "2024/3", "2023/12", "2023/9", "2023/6", "2023/3"]


def _data(periods: list[str]) -> dict:
    return {
        "ticker": "TEST",
        "periods": periods,
        "sections": {
            "gelir": {NET_KAR: {p: NET_KAR_YTD[p] for p in periods}},
            "bilanco": {
                "Özkaynaklar": {p: OZKAYNAK[p] for p in periods},
                "TOPLAM VARLIKLAR": {p: TOPLAM_VARLIK[p] for p in periods},
            },
        },
    }


class TestDiscrete:
    def test_missing_previous_quarter_of_same_year_returns_none(self):
        periods = ["2024/6", "2023/12", "2023/9", "2023/6"]  # 2024/3 yok

        assert metrics._discrete(NET_KAR_YTD, "2024/6", periods) is None

    def test_consecutive_quarters_are_deaccumulated(self):
        assert metrics._discrete(NET_KAR_YTD, "2024/6", ALL_PERIODS) == pytest.approx(30.0)
        assert metrics._discrete(NET_KAR_YTD, "2024/3", ALL_PERIODS) == pytest.approx(20.0)
        assert metrics._discrete(NET_KAR_YTD, "2023/12", ALL_PERIODS) == pytest.approx(25.0)


class TestTtm:
    def test_missing_quarter_gives_no_ttm(self):
        periods = ["2024/6", "2023/12", "2023/9", "2023/6"]  # 2024/3 yok

        assert metrics._ttm(NET_KAR_YTD, "2024/6", periods) is None

    def test_ttm_sums_last_four_discrete_quarters(self):
        # 2024/6: 2023Q3 20 + 2023Q4 25 + 2024Q1 20 + 2024Q2 30 = 95
        assert metrics._ttm(NET_KAR_YTD, "2024/6", ALL_PERIODS) == pytest.approx(95.0)
        # 2024/3: 15 + 20 + 25 + 20 = 80
        assert metrics._ttm(NET_KAR_YTD, "2024/3", ALL_PERIODS) == pytest.approx(80.0)
        # 2023/12: 10 + 15 + 20 + 25 = 70 (yıllık YTD ile aynı)
        assert metrics._ttm(NET_KAR_YTD, "2023/12", ALL_PERIODS) == pytest.approx(70.0)

    def test_year_gap_in_list_order_gives_no_ttm(self):
        series = {"2024/3": 20.0, "2022/12": 70.0, "2022/9": 45.0, "2022/6": 25.0, "2022/3": 10.0}
        periods = ["2024/3", "2022/12", "2022/9", "2022/6", "2022/3"]  # 2023 tamamen yok

        assert metrics._ttm(series, "2024/3", periods) is None

    def test_ascending_period_order_still_uses_previous_quarters(self):
        periods = list(reversed(ALL_PERIODS))

        assert metrics._ttm(NET_KAR_YTD, "2024/6", periods) == pytest.approx(95.0)

    def test_compute_metrics_ttm_none_when_quarter_missing(self):
        result = metrics.compute_metrics(_data(["2024/6", "2023/12", "2023/9", "2023/6"]))

        assert result["net_kar_ceyrek"]["2024/6"] is None
        assert result["net_kar_ttm"]["2024/6"] is None


class TestTtmBasedReturns:
    def test_roe_and_roa_use_trailing_twelve_month_net_profit(self):
        result = metrics.compute_metrics(_data(ALL_PERIODS))

        # 2024/6: TTM 95 / özkaynak 500 = %19 ; 95 / varlık 1000 = %9,5
        assert result["roe"]["2024/6"] == pytest.approx(19.0)
        assert result["roa"]["2024/6"] == pytest.approx(9.5)
        # 2024/3 (Q1): TTM 80 / 400 = %20 ; 80 / 800 = %10 (YTD 20/400=%5 değil)
        assert result["roe"]["2024/3"] == pytest.approx(20.0)
        assert result["roa"]["2024/3"] == pytest.approx(10.0)
        # 2023/12: TTM 70 / 350 = %20 ; 70 / 700 = %10
        assert result["roe"]["2023/12"] == pytest.approx(20.0)
        assert result["roa"]["2023/12"] == pytest.approx(10.0)

    def test_interim_period_without_ttm_has_no_roe(self):
        result = metrics.compute_metrics(_data(ALL_PERIODS))

        # 2023/9 için 2022 verisi yok: TTM hesaplanamaz, 9 aylık YTD kullanılmaz.
        assert result["roe"]["2023/9"] is None
        assert result["roa"]["2023/9"] is None

    def test_year_end_falls_back_to_annual_ytd(self):
        # Yalnız yıllık dönem: 12 aylık YTD = son 12 ay. 70 / 350 = %20 ; 70 / 700 = %10
        result = metrics.compute_metrics(_data(["2023/12"]))

        assert result["net_kar_ttm"]["2023/12"] is None
        assert result["roe"]["2023/12"] == pytest.approx(20.0)
        assert result["roa"]["2023/12"] == pytest.approx(10.0)
