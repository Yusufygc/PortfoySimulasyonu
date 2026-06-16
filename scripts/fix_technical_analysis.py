import sys
import os
from datetime import date

# Add project root to path
ROOT = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.application.container import AppContainer
from src.infrastructure.db.sqlalchemy.orm_models import ORMDailyPrice, ORMGoldenCrossEvent
from src.application.services.market.price_data_health_service import PRICE_SCOPE_ALL_BIST

def run_fix():
    print(f"--- Running Fix Technical Analysis ---")
    print(f"Database Config: {os.environ.get('PORTFOYSIM_ENV', 'production')}")
    
    container = AppContainer()
    
    # 1. Delete daily prices with source='yfinance'
    with container.conn_provider.get_session() as session:
        print("1. Deleting daily prices where source = 'yfinance'...")
        deleted_prices = session.query(ORMDailyPrice).filter(ORMDailyPrice.source == 'yfinance').delete()
        print(f"   Deleted {deleted_prices} daily price records.")
        
        # 2. Delete all golden cross events
        print("2. Deleting all golden cross events...")
        deleted_events = session.query(ORMGoldenCrossEvent).delete()
        print(f"   Deleted {deleted_events} golden cross events.")
        
        session.commit()

    # 3. Trigger Price update / backfill
    print("3. Updating/Backfilling missing price data from yfinance (adjusted)...")
    health_service = container.price_data_health_service
    today = date.today()
    
    # Find last completed trading day
    from src.ui.main_window import last_completed_trading_day
    target_date = last_completed_trading_day(
        today,
        getattr(container, "trading_calendar", None),
    )
    print(f"   Target date for update: {target_date}")
    
    update_res = health_service.update_from_latest_to_today(target_date, PRICE_SCOPE_ALL_BIST)
    print(f"   Price Update Completed: {update_res.updated_count} tickers updated, skipped={update_res.skipped_holiday_count}")

    # 4. Recalculate all cross events using EMA
    print("4. Recalculating all Golden/Death Cross events using EMA...")
    scan_res = container.technical_analysis_service.scan_all(target_date)
    print(f"   Scan Completed: {scan_res.scanned_count} scanned, {scan_res.new_event_count} new cross events, {scan_res.skipped_count} skipped.")

if __name__ == "__main__":
    run_fix()
