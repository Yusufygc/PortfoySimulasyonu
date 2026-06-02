from datetime import date
from decimal import Decimal
from types import SimpleNamespace

from scripts.merko_bedelsiz_artirimi import _find_existing_merko_action
from src.domain.models.corporate_action import ActionType, CorporateAction


def test_merko_script_finds_existing_action_with_rounded_ratio():
    action = CorporateAction(
        id=1,
        stock_id=47,
        action_type=ActionType.BEDELSIZ,
        ex_date=date(2026, 5, 5),
        ratio=Decimal("6.38340000"),
        subscription_price=None,
        announcement_date=None,
        notes=None,
        applied=True,
    )
    container = SimpleNamespace(
        corporate_action_service=SimpleNamespace(
            get_by_stock=lambda stock_id: [action] if stock_id == 47 else []
        )
    )

    assert _find_existing_merko_action(container, 47) is action
