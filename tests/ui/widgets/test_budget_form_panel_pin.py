from decimal import Decimal

from src.domain.models.budget import Budget, BudgetItem, BudgetPinnedItem
from src.ui.shared.locale_tr import L10N
from src.ui.widgets.planning.panels.budget_form_panel import BudgetFormPanel


def test_budget_form_panel_marks_pinned_rows(qapp):
    panel = BudgetFormPanel()
    panel.set_pinned_items(
        [
            BudgetPinnedItem(
                id=1,
                item_type="income",
                name="Salary",
                default_amount=Decimal("3000.00"),
            )
        ]
    )

    panel.load(
        Budget(
            id=None,
            month="2026-02",
            items=[
                BudgetItem(id=None, budget_id=None, item_type="income", name="Salary", amount=Decimal("3000.00")),
                BudgetItem(id=None, budget_id=None, item_type="expense", name="Rent", amount=Decimal("1250.00")),
            ],
        )
    )

    assert panel._income_rows[0].btn_pin.isChecked()
    assert not panel._expense_rows[0].btn_pin.isChecked()


def test_budget_form_panel_emits_pin_toggle_with_default_name(qapp):
    panel = BudgetFormPanel()
    emitted = []
    panel.pin_toggle_requested.connect(lambda *args: emitted.append(args))

    row = panel._add_row("", 1250.0, "expense")
    row.btn_pin.click()

    assert emitted == [("expense", "Gider", 1250.0, True)]


def test_budget_form_panel_formats_savings_target_with_turkish_grouping(qapp):
    panel = BudgetFormPanel()

    panel.spin_target.setValue(300000)

    assert panel.spin_target.text() == "300.000,00TL"
    assert panel.spin_target.value() == 300000.0


def test_budget_form_panel_goal_status_card_reserves_wrapped_value_height(qapp):
    panel = BudgetFormPanel()

    panel.card_goal.set_value(L10N.HEDEFE_ULASILIYOR)
    panel.card_goal.set_value_state("positive")

    value_label = panel.card_goal.get_value_label()
    assert value_label.wordWrap()
    assert value_label.property("cssState") == "positive"
    assert value_label.minimumHeight() >= value_label.fontMetrics().lineSpacing() * 2
