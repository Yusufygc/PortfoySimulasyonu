"""KAP shareholder provider parser birim testleri (ağ erişimi yok)."""
from __future__ import annotations

from decimal import Decimal

import pytest

from src.infrastructure.corporate_actions.kap_shareholder_provider import (
    _parse_bist_companies,
    _parse_creation_date,
    _parse_decimal,
    _parse_history,
)


class TestParseDecimal:
    def test_tr_thousands_with_decimal(self):
        assert _parse_decimal("69.600.000,12") == Decimal("69600000.12")

    def test_tr_thousands_no_decimal(self):
        assert _parse_decimal("69.600.000") == Decimal("69600000")

    def test_simple_pct(self):
        assert _parse_decimal("19,33") == Decimal("19.33")

    def test_integer_100(self):
        assert _parse_decimal("100") == Decimal("100")

    def test_none(self):
        assert _parse_decimal(None) is None

    def test_empty(self):
        assert _parse_decimal("") is None

    def test_dash(self):
        assert _parse_decimal("-") is None


class TestParseCreationDate:
    def test_date_only(self):
        d = _parse_creation_date("28/03/2026")
        assert d.year == 2026 and d.month == 3 and d.day == 28

    def test_with_time(self):
        d = _parse_creation_date("27/01/2026 12:08:24")
        assert d.year == 2026 and d.month == 1 and d.day == 27

    def test_invalid(self):
        assert _parse_creation_date("garbage") is None

    def test_empty(self):
        assert _parse_creation_date("") is None


class TestParseHistory:
    def test_multiple_snapshots_newest_first(self):
        raw = [
            {
                "value": [
                    {"shareholder": "A", "shareInCapital": "100", "ratioInCapital": "50", "votingRightRatio": "60"},
                    {"shareholder": "TOPLAM", "shareInCapital": "200", "ratioInCapital": "100", "votingRightRatio": "100"},
                ],
                "creationDate": "01/01/2025",
            },
            {
                "value": [
                    {"shareholder": "A", "shareInCapital": "120", "ratioInCapital": "55", "votingRightRatio": "65"},
                ],
                "creationDate": "01/06/2025",
            },
        ]
        snaps = _parse_history(raw)
        assert len(snaps) == 2
        assert snaps[0].creation_date.month == 6  # en yeni önce
        assert snaps[1].creation_date.month == 1

    def test_total_row_detected(self):
        raw = [{
            "value": [
                {"shareholder": "DİĞER", "shareInCapital": "50", "ratioInCapital": "50", "votingRightRatio": "50"},
                {"shareholder": "Total", "shareInCapital": "100", "ratioInCapital": "100", "votingRightRatio": "100"},
            ],
            "creationDate": "01/01/2024",
        }]
        snap = _parse_history(raw)[0]
        assert snap.rows[0].is_total is False
        assert snap.rows[1].is_total is True

    def test_skips_invalid_dates(self):
        raw = [
            {"value": [{"shareholder": "A", "shareInCapital": "1", "ratioInCapital": "1", "votingRightRatio": "1"}], "creationDate": "garbage"},
            {"value": [{"shareholder": "B", "shareInCapital": "1", "ratioInCapital": "1", "votingRightRatio": "1"}], "creationDate": "01/01/2024"},
        ]
        snaps = _parse_history(raw)
        assert len(snaps) == 1

    def test_empty_input(self):
        assert _parse_history([]) == []


class TestParseBistCompanies:
    def test_extracts_basic_record(self):
        html = (
            'foo{"mkkMemberOid":"4028e4a140f2ed71014106890fae0138",'
            '"kapMemberTitle":"FORD OTOMOTİV SANAYİ A.Ş.",'
            '"stockCode":"FROTO","cityName":"İSTANBUL"}bar'
        )
        out = _parse_bist_companies(html)
        assert "FROTO" in out
        assert out["FROTO"]["mkkMemberOid"] == "4028e4a140f2ed71014106890fae0138"
        assert "FORD" in out["FROTO"]["kapMemberTitle"]

    def test_empty_html(self):
        assert _parse_bist_companies("") == {}
