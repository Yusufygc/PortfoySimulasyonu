from datetime import date
from decimal import Decimal
import yfinance as yf

from src.domain.services_interfaces.i_market_data_client import IMarketDataClient


class YFinanceMarketDataClient(IMarketDataClient):
    """
    IMarketDataClient arayüzünü yfinance modülü ile implement eden sınıf.
    """

    def get_closing_price(self, stock_id, ticker, price_date):
        data = yf.download(
            tickers=ticker,
            start=price_date,
            end=price_date,
            progress=False
        )

        if data.empty:
            raise ValueError(f"{ticker} için {price_date} gün sonu fiyatı bulunamadı.")

        close_val = data["Close"].iloc[0]
        return Decimal(str(float(close_val)))

    def get_closing_prices(self, stock_ids, tickers, price_date):
        # ... toplu çekim için optimize edilmiş bir yapı yazacağız
        pass

    def get_price_series(self, ticker, start_date, end_date):
        # ... tarih aralığı fiyat serisi
        pass
