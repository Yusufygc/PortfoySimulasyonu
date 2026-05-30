from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.application.container import AppContainer


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete a stock and all dependent records.")
    parser.add_argument("--ticker", required=True, help="Ticker to purge, for example THYAO or THYAO.IS")
    args = parser.parse_args()

    container = AppContainer()
    result = container.portfolio_maintenance_service.purge_stock_by_ticker(args.ticker)
    print(f"ticker={result.ticker}")
    print(f"stock_ids={list(result.stock_ids)}")
    print(f"deleted_trades={result.deleted_trades}")
    print(f"deleted_daily_prices={result.deleted_daily_prices}")
    print(f"deleted_watchlist_items={result.deleted_watchlist_items}")
    print(f"deleted_model_portfolio_trades={result.deleted_model_portfolio_trades}")
    print(f"deleted_corporate_actions={result.deleted_corporate_actions}")
    print(f"deleted_stocks={result.deleted_stocks}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
