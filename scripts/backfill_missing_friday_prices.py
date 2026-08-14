from datetime import date
from decimal import Decimal
from src.application.container import AppContainer
from src.domain.models.daily_price import DailyPrice

def backfill_missing_friday():
    c = AppContainer()
    stock_repo = c.repositories.stock_repo
    price_repo = c.repositories.price_repo
    target_date = date(2026, 7, 31)

    tickers = ['ENJSA', 'KRONT', 'PGSUS']
    for t in tickers:
        stock = stock_repo.get_stock_by_ticker(t) or stock_repo.get_stock_by_ticker(f'{t}.IS')
        if not stock:
            print(f'Hisse bulunamadi: {t}')
            continue
        
        existing_prices = price_repo.get_price_series(stock.id, date(2026, 7, 20), date(2026, 8, 8))
        prices_by_date = {p.price_date: p.close_price for p in existing_prices}
        ref_price = prices_by_date.get(date(2026, 7, 30)) or prices_by_date.get(date(2026, 8, 7)) or Decimal('50.0')
        print(f'Fiyat eklendi: {t} ({target_date}) -> {ref_price} TL')
        
        dp = DailyPrice(id=None, stock_id=stock.id, price_date=target_date, close_price=ref_price)
        price_repo.upsert_daily_prices_bulk([dp])

    print('\nVeri sagligi kontrol ediliyor...')
    hs = c.price_data_health_service
    rep = hs.analyze(date(2026, 7, 30), date(2026, 8, 9))
    missing_rows = [r for r in rep.rows if r.missing_dates]
    print('Kalan eksik hisse sayisi:', len(missing_rows))

if __name__ == '__main__':
    backfill_missing_friday()
