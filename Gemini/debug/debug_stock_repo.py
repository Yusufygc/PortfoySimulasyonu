from config.settings_loader import load_settings
from src.infrastructure.db.mysql_connection import MySQLConnectionProvider
from src.infrastructure.db.stock_repository import MySQLStockRepository
from src.domain.models.stock import Stock

def main():
    cfg = load_settings()
    cp = MySQLConnectionProvider(cfg)
    repo = MySQLStockRepository(cp)

    # Basit: bir adet test hissesi ekle
    s = Stock(id=None, ticker="TEST.IS", name="Test Hisse", currency_code="TRY")
    s_saved = repo.insert_stock(s)
    print("Inserted stock:", s_saved)

    all_stocks = repo.get_all_stocks()
    print("All stocks:")
    for st in all_stocks:
        print(st)

if __name__ == "__main__":
    main()
