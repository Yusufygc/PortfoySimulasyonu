from datetime import date
from src.infrastructure.market_data.yfinance_client import YFinanceMarketDataClient

def main():
    client = YFinanceMarketDataClient()
    today = date.today()

    # BIST için bir örnek: AKBNK.IS
    price = client.get_closing_price(stock_id=1, ticker="AKBNK.IS", price_date=today)
    print("AKBNK.IS price:", price)

if __name__ == "__main__":
    main()
