# tests/domain/test_corporate_action.py

import pytest
from datetime import date
from decimal import Decimal

from src.domain.models.corporate_action import ActionType, CorporateAction


# ══════════════════════════════════════════════════════════
#  Factory metot testleri
# ══════════════════════════════════════════════════════════

class TestCreateBedelsiz:

    def test_normal_creation(self):
        action = CorporateAction.create_bedelsiz(
            stock_id=1,
            ex_date=date(2026, 3, 15),
            ratio=Decimal("0.50"),
        )
        assert action.action_type == ActionType.BEDELSIZ
        assert action.ratio == Decimal("0.50")
        assert action.subscription_price is None
        assert action.applied is False
        assert action.id is None

    def test_with_optional_fields(self):
        action = CorporateAction.create_bedelsiz(
            stock_id=5,
            ex_date=date(2026, 6, 1),
            ratio=Decimal("1.00"),
            announcement_date=date(2026, 5, 15),
            notes="Akbank %100 bedelsiz",
        )
        assert action.announcement_date == date(2026, 5, 15)
        assert action.notes == "Akbank %100 bedelsiz"

    def test_ratio_zero_raises(self):
        with pytest.raises(ValueError, match="sıfırdan büyük"):
            CorporateAction.create_bedelsiz(
                stock_id=1,
                ex_date=date(2026, 1, 1),
                ratio=Decimal("0"),
            )

    def test_ratio_negative_raises(self):
        with pytest.raises(ValueError):
            CorporateAction.create_bedelsiz(
                stock_id=1,
                ex_date=date(2026, 1, 1),
                ratio=Decimal("-0.10"),
            )


class TestCreateBedelli:

    def test_normal_creation(self):
        action = CorporateAction.create_bedelli(
            stock_id=2,
            ex_date=date(2026, 4, 10),
            ratio=Decimal("0.20"),
            subscription_price=Decimal("1.00"),
        )
        assert action.action_type == ActionType.BEDELLI
        assert action.ratio == Decimal("0.20")
        assert action.subscription_price == Decimal("1.00")
        assert action.applied is False

    def test_zero_subscription_price_raises(self):
        with pytest.raises(ValueError, match="kullanım fiyatı"):
            CorporateAction.create_bedelli(
                stock_id=1,
                ex_date=date(2026, 1, 1),
                ratio=Decimal("0.20"),
                subscription_price=Decimal("0"),
            )

    def test_negative_subscription_price_raises(self):
        with pytest.raises(ValueError):
            CorporateAction.create_bedelli(
                stock_id=1,
                ex_date=date(2026, 1, 1),
                ratio=Decimal("0.20"),
                subscription_price=Decimal("-1.00"),
            )

    def test_zero_ratio_raises(self):
        with pytest.raises(ValueError, match="sıfırdan büyük"):
            CorporateAction.create_bedelli(
                stock_id=1,
                ex_date=date(2026, 1, 1),
                ratio=Decimal("0"),
                subscription_price=Decimal("1.00"),
            )


# ══════════════════════════════════════════════════════════
#  ratio_percent testi
# ══════════════════════════════════════════════════════════

def test_ratio_percent():
    action = CorporateAction.create_bedelsiz(
        stock_id=1, ex_date=date(2026, 1, 1), ratio=Decimal("0.25")
    )
    assert action.ratio_percent == Decimal("25.00")


# ══════════════════════════════════════════════════════════
#  calculate_new_shares — BİST küsurat kuralı (floor)
# ══════════════════════════════════════════════════════════

class TestCalculateNewShares:

    def test_exact_division(self):
        # 100 lot, %50 → 50 yeni lot
        action = CorporateAction.create_bedelsiz(
            stock_id=1, ex_date=date(2026, 1, 1), ratio=Decimal("0.50")
        )
        assert action.calculate_new_shares(100) == 50

    def test_floor_rounding(self):
        # 100 lot, %33 → 33 (küsurat atılır)
        action = CorporateAction.create_bedelsiz(
            stock_id=1, ex_date=date(2026, 1, 1), ratio=Decimal("0.33")
        )
        assert action.calculate_new_shares(100) == 33

    def test_small_position_may_yield_zero(self):
        # 1 lot, %50 → int(0.50) = 0 (çok küçük pozisyon)
        action = CorporateAction.create_bedelsiz(
            stock_id=1, ex_date=date(2026, 1, 1), ratio=Decimal("0.50")
        )
        assert action.calculate_new_shares(1) == 0

    def test_full_100_percent_bedelsiz(self):
        # 200 lot, %100 → 200 yeni lot
        action = CorporateAction.create_bedelsiz(
            stock_id=1, ex_date=date(2026, 1, 1), ratio=Decimal("1.00")
        )
        assert action.calculate_new_shares(200) == 200

    def test_bedelli_new_shares(self):
        action = CorporateAction.create_bedelli(
            stock_id=1, ex_date=date(2026, 1, 1),
            ratio=Decimal("0.20"), subscription_price=Decimal("1.00")
        )
        # 500 lot * 0.20 = 100 yeni lot
        assert action.calculate_new_shares(500) == 100


# ══════════════════════════════════════════════════════════
#  theoretical_price — BİST teorik baz fiyat
# ══════════════════════════════════════════════════════════

class TestTheoreticalPrice:

    def test_bedelsiz_50_percent(self):
        # Eski fiyat 10 TL, %50 bedelsiz → 10 / 1.50 ≈ 6.6667
        action = CorporateAction.create_bedelsiz(
            stock_id=1, ex_date=date(2026, 1, 1), ratio=Decimal("0.50")
        )
        result = action.theoretical_price(Decimal("10"))
        expected = Decimal("10") / Decimal("1.50")
        assert abs(result - expected) < Decimal("0.0001")

    def test_bedelsiz_100_percent(self):
        # %100 bedelsiz → fiyat yarıya düşer
        action = CorporateAction.create_bedelsiz(
            stock_id=1, ex_date=date(2026, 1, 1), ratio=Decimal("1.00")
        )
        result = action.theoretical_price(Decimal("20"))
        assert abs(result - Decimal("10")) < Decimal("0.0001")

    def test_bedelli_formula(self):
        # P=15 TL, oran=%20, K=1 TL
        # Teorik = (1 * 15 + 0.20 * 1) / (1 + 0.20) = 15.20 / 1.20 ≈ 12.6667
        action = CorporateAction.create_bedelli(
            stock_id=1, ex_date=date(2026, 1, 1),
            ratio=Decimal("0.20"), subscription_price=Decimal("1.00")
        )
        result = action.theoretical_price(Decimal("15"))
        expected = (Decimal("15") + Decimal("0.20") * Decimal("1")) / Decimal("1.20")
        assert abs(result - expected) < Decimal("0.0001")

    def test_bedelli_high_subscription_price(self):
        # P=50 TL, oran=%25, K=10 TL
        # Teorik = (50 + 0.25 * 10) / 1.25 = 52.50 / 1.25 = 42.00
        action = CorporateAction.create_bedelli(
            stock_id=1, ex_date=date(2026, 1, 1),
            ratio=Decimal("0.25"), subscription_price=Decimal("10.00")
        )
        result = action.theoretical_price(Decimal("50"))
        assert abs(result - Decimal("42")) < Decimal("0.0001")
