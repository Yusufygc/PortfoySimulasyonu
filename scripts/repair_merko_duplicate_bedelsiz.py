"""Repair duplicate MERKO.IS bedelsiz application in the local database."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config.settings_loader import load_app_settings
from src.infrastructure.db.sqlalchemy.database_engine import SQLAlchemyEngineProvider


STOCK_ID = 47
TICKER = "MERKO.IS"
EX_DATE = date(2026, 5, 5)
KEEP_ACTION_ID = 1
DELETE_ACTION_ID = 2
DELETE_TRADE_ID = 69
DELETE_TRADE_QTY = 366208
PRICE_ADJUSTMENT_FACTOR = Decimal("0.1354392622")
PRICE_ADJUSTMENT_COUNT = 107
RATIO_TOLERANCE = Decimal("0.0001")
EXPECTED_RATIOS = (Decimal("6.38340000"), Decimal("6.38338340"))
PRICE_RESTORES = {
    date(2026, 5, 1): (Decimal("0.2836"), Decimal("2.0939")),
    date(2026, 5, 4): (Decimal("0.2834"), Decimal("2.0925")),
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Repair duplicate MERKO.IS bedelsiz records")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--apply", action="store_true", help="Apply the repair transaction")
    mode.add_argument("--dry-run", action="store_true", help="Show intended repair without writing")
    parser.add_argument(
        "--backup-dir",
        default=str(ROOT / "backups"),
        help="Directory for JSON backup written before --apply",
    )
    return parser.parse_args()


def _to_decimal(value: Any) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _row_dict(row) -> dict[str, Any] | None:
    return dict(row._mapping) if row is not None else None


def _fetch_one(conn, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    return _row_dict(conn.exec_driver_sql(sql, params).first())


def _fetch_all(conn, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    return [dict(row._mapping) for row in conn.exec_driver_sql(sql, params).all()]


def _json_default(value: Any) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _ratio_is_expected(value: Any) -> bool:
    ratio = _to_decimal(value)
    return any(abs(ratio - expected) <= RATIO_TOLERANCE for expected in EXPECTED_RATIOS)


def _validate_state(conn) -> tuple[bool, list[str]]:
    errors: list[str] = []
    stock = _fetch_one(conn, "SELECT id, ticker FROM stocks WHERE id = %s", (STOCK_ID,))
    if stock is None or stock["ticker"] != TICKER:
        errors.append(f"Expected stock {STOCK_ID}/{TICKER}, found {stock}")

    keep_action = _fetch_one(
        conn,
        "SELECT * FROM corporate_actions WHERE id = %s AND stock_id = %s",
        (KEEP_ACTION_ID, STOCK_ID),
    )
    delete_action = _fetch_one(
        conn,
        "SELECT * FROM corporate_actions WHERE id = %s AND stock_id = %s",
        (DELETE_ACTION_ID, STOCK_ID),
    )
    delete_trade = _fetch_one(
        conn,
        "SELECT * FROM trades WHERE id = %s AND stock_id = %s",
        (DELETE_TRADE_ID, STOCK_ID),
    )

    if keep_action is None:
        errors.append(f"Canonical action id={KEEP_ACTION_ID} not found")
    elif not _is_bedelsiz_action(keep_action):
        errors.append(f"Canonical action id={KEEP_ACTION_ID} does not match MERKO bedelsiz")

    duplicate_present = delete_action is not None or delete_trade is not None
    if not duplicate_present:
        return False, errors

    if delete_action is None:
        errors.append(f"Duplicate action id={DELETE_ACTION_ID} not found")
    elif not _is_bedelsiz_action(delete_action):
        errors.append(f"Duplicate action id={DELETE_ACTION_ID} does not match MERKO bedelsiz")

    if delete_trade is None:
        errors.append(f"Duplicate trade id={DELETE_TRADE_ID} not found")
    else:
        if str(delete_trade["side"]) != "BUY":
            errors.append(f"Duplicate trade side is not BUY: {delete_trade['side']}")
        if _to_decimal(delete_trade["price"]) != Decimal("0.0000"):
            errors.append(f"Duplicate trade price is not zero: {delete_trade['price']}")
        if int(delete_trade["quantity"]) != DELETE_TRADE_QTY:
            errors.append(f"Duplicate trade quantity mismatch: {delete_trade['quantity']}")

    for price_date, (current_value, _restore_value) in PRICE_RESTORES.items():
        price = _fetch_one(
            conn,
            "SELECT close_price FROM daily_prices WHERE stock_id = %s AND price_date = %s",
            (STOCK_ID, price_date),
        )
        if price is None:
            errors.append(f"Price row missing for {price_date}")
            continue
        if _to_decimal(price["close_price"]) != current_value:
            errors.append(
                f"Price row {price_date} expected {current_value}, found {price['close_price']}"
            )

    return True, errors


def _is_bedelsiz_action(row: dict[str, Any]) -> bool:
    return (
        str(row["action_type"]) == "BEDELSIZ"
        and row["ex_date"] == EX_DATE
        and bool(row["applied"])
        and _ratio_is_expected(row["ratio"])
    )


def _write_backup(conn, backup_dir: Path) -> Path:
    backup_dir.mkdir(parents=True, exist_ok=True)
    path = backup_dir / f"merko_duplicate_bedelsiz_{datetime.now():%Y%m%d_%H%M%S}.json"
    payload = {
        "created_at": datetime.now(),
        "stock_id": STOCK_ID,
        "ticker": TICKER,
        "corporate_actions": _fetch_all(
            conn,
            "SELECT * FROM corporate_actions WHERE stock_id = %s ORDER BY id",
            (STOCK_ID,),
        ),
        "trades": _fetch_all(
            conn,
            "SELECT * FROM trades WHERE stock_id = %s ORDER BY trade_date, id",
            (STOCK_ID,),
        ),
        "daily_prices": _fetch_all(
            conn,
            """
            SELECT * FROM daily_prices
            WHERE stock_id = %s AND price_date BETWEEN '2026-04-20' AND '2026-05-08'
            ORDER BY price_date
            """,
            (STOCK_ID,),
        ),
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
    return path


def _print_plan(conn, duplicate_present: bool) -> None:
    actions = _fetch_all(
        conn,
        """
        SELECT id, action_type, ex_date, ratio, applied, prices_adjusted,
               price_adjustment_factor, price_adjustment_count
        FROM corporate_actions
        WHERE stock_id = %s
        ORDER BY id
        """,
        (STOCK_ID,),
    )
    trades = _fetch_all(
        conn,
        """
        SELECT id, trade_date, side, quantity, price
        FROM trades
        WHERE stock_id = %s
        ORDER BY trade_date, id
        """,
        (STOCK_ID,),
    )
    prices = _fetch_all(
        conn,
        """
        SELECT price_date, close_price
        FROM daily_prices
        WHERE stock_id = %s AND price_date IN ('2026-05-01', '2026-05-04')
        ORDER BY price_date
        """,
        (STOCK_ID,),
    )
    print("Current MERKO actions:", actions)
    print("Current MERKO trades:", trades)
    print("Double-adjusted prices:", prices)
    if duplicate_present:
        print("Repair will delete trade id=69 and action id=2, then restore 2026-05-01/2026-05-04 prices.")


def _apply_repair(conn) -> None:
    for price_date, (current_value, restore_value) in PRICE_RESTORES.items():
        result = conn.exec_driver_sql(
            """
            UPDATE daily_prices
            SET close_price = %s
            WHERE stock_id = %s AND price_date = %s AND close_price = %s
            """,
            (restore_value, STOCK_ID, price_date, current_value),
        )
        if result.rowcount != 1:
            raise RuntimeError(f"Price restore failed for {price_date}: rowcount={result.rowcount}")

    result = conn.exec_driver_sql("DELETE FROM trades WHERE id = %s AND stock_id = %s", (DELETE_TRADE_ID, STOCK_ID))
    if result.rowcount != 1:
        raise RuntimeError(f"Duplicate trade delete failed: rowcount={result.rowcount}")

    result = conn.exec_driver_sql(
        "DELETE FROM corporate_actions WHERE id = %s AND stock_id = %s",
        (DELETE_ACTION_ID, STOCK_ID),
    )
    if result.rowcount != 1:
        raise RuntimeError(f"Duplicate action delete failed: rowcount={result.rowcount}")

    result = conn.exec_driver_sql(
        """
        UPDATE corporate_actions
        SET prices_adjusted = 1,
            prices_adjusted_at = COALESCE(prices_adjusted_at, NOW()),
            price_adjustment_factor = %s,
            price_adjustment_count = %s
        WHERE id = %s AND stock_id = %s
        """,
        (PRICE_ADJUSTMENT_FACTOR, PRICE_ADJUSTMENT_COUNT, KEEP_ACTION_ID, STOCK_ID),
    )
    if result.rowcount != 1:
        raise RuntimeError(f"Canonical action update failed: rowcount={result.rowcount}")


def main() -> int:
    args = _parse_args()
    apply_changes = bool(args.apply)
    provider = SQLAlchemyEngineProvider(load_app_settings().db)
    try:
        with provider._engine.begin() as conn:
            duplicate_present, errors = _validate_state(conn)
            _print_plan(conn, duplicate_present)
            if errors:
                print("Validation failed:")
                for error in errors:
                    print(f"- {error}")
                return 2
            if not duplicate_present:
                print("No duplicate MERKO bedelsiz state detected; nothing to repair.")
                return 0
            if not apply_changes:
                print("Dry run only. Re-run with --apply to repair.")
                return 0

            backup_path = _write_backup(conn, Path(args.backup_dir))
            print(f"Backup written: {backup_path}")
            _apply_repair(conn)
            print("MERKO duplicate bedelsiz repair applied.")
            return 0
    finally:
        provider.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
