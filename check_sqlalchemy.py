from sqlalchemy import create_engine, text
import pandas as pd

try:
    engine = create_engine("mysql+mysqlconnector://root:Suqili20yh@localhost:3306/portfoySim")
    
    with engine.connect() as conn:
        # Find MERKO stock id
        res = conn.execute(text("SELECT id, ticker, name FROM stocks WHERE ticker LIKE '%MERKO%'"))
        stock = res.fetchone()
        if not stock:
            print("MERKO not found in stocks table")
        else:
            stock_id = stock.id
            ticker = stock.ticker
            print(f"MERKO found: id={stock_id}, ticker={ticker}")
            
            # Print trades
            print("\n--- TRADES ---")
            df_trades = pd.read_sql(text(f"SELECT id, stock_id, trade_date, side, quantity, price, total_amount, notes FROM trades WHERE stock_id = {stock_id} ORDER BY trade_date"), conn)
            print(df_trades.to_string())
            
            # Print corporate actions
            print("\n--- CORPORATE ACTIONS ---")
            try:
                df_ca = pd.read_sql(text(f"SELECT * FROM corporate_actions WHERE stock_id = {stock_id} ORDER BY ex_date"), conn)
                print(df_ca.to_string())
            except Exception as e:
                print(f"Error fetching corporate actions: {e}")
                
            # Print daily prices around the action date
            print("\n--- DAILY PRICES AROUND 2026-05-05 ---")
            try:
                df_prices = pd.read_sql(text(f"SELECT price_date, close_price FROM daily_prices WHERE stock_id = {stock_id} AND price_date BETWEEN '2026-04-25' AND '2026-05-15' ORDER BY price_date"), conn)
                print(df_prices.to_string())
            except Exception as e:
                print(f"Error fetching daily prices: {e}")
                
except Exception as e:
    print(f"Error: {e}")
