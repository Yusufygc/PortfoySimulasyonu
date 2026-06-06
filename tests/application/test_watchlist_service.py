import pytest
from src.application.services.watchlist.watchlist_service import WatchlistService
from src.domain.models.watchlist import Watchlist, WatchlistItem
from src.domain.models.stock import Stock


class InMemoryWatchlistRepo:
    def __init__(self):
        self.watchlists = {}
        self.items = {}

    def get_all_watchlists(self):
        return list(self.watchlists.values())

    def get_watchlist_by_id(self, watchlist_id):
        return self.watchlists.get(watchlist_id)

    def create_watchlist(self, watchlist):
        w_id = len(self.watchlists) + 1
        new_w = Watchlist(
            id=w_id,
            name=watchlist.name,
            description=watchlist.description,
            sort_order=watchlist.sort_order,
        )
        self.watchlists[w_id] = new_w
        return new_w

    def update_watchlist(self, watchlist):
        self.watchlists[watchlist.id] = watchlist

    def get_items_by_watchlist_id(self, watchlist_id):
        return [item for item in self.items.values() if item.watchlist_id == watchlist_id]

    def add_item_to_watchlist(self, item):
        item_id = len(self.items) + 1
        new_item = WatchlistItem(
            id=item_id,
            watchlist_id=item.watchlist_id,
            stock_id=item.stock_id,
            notes=item.notes,
        )
        self.items[item_id] = new_item
        return new_item

    def update_item_in_watchlist(self, item):
        self.items[item.id] = item

    def remove_stock_from_watchlist(self, watchlist_id, stock_id):
        for k, v in list(self.items.items()):
            if v.watchlist_id == watchlist_id and v.stock_id == stock_id:
                del self.items[k]

    def is_stock_in_watchlist(self, watchlist_id, stock_id):
        return any(v.watchlist_id == watchlist_id and v.stock_id == stock_id for v in self.items.values())


class InMemoryStockRepo:
    def __init__(self):
        self.stocks = {}

    def get_stock_by_id(self, stock_id):
        return self.stocks.get(stock_id)

    def get_stocks_by_ids(self, stock_ids):
        return [self.stocks[sid] for sid in stock_ids if sid in self.stocks]

    def get_stock_by_ticker(self, ticker):
        for s in self.stocks.values():
            if s.ticker == ticker:
                return s
        return None

    def insert_stock(self, stock):
        s_id = len(self.stocks) + 1
        new_s = Stock(id=s_id, ticker=stock.ticker, name=stock.name, currency_code=stock.currency_code)
        self.stocks[s_id] = new_s
        return new_s


def test_watchlist_service_update_item_notes():
    watchlist_repo = InMemoryWatchlistRepo()
    stock_repo = InMemoryStockRepo()
    service = WatchlistService(watchlist_repo, stock_repo)

    # 1. Watchlist oluştur
    wl = service.create_watchlist("Test Listesi", "Açıklama")
    
    # 2. Stock oluştur ve ekle
    stock = stock_repo.insert_stock(Stock(id=None, ticker="THYAO.IS", name="THY", currency_code="TRY"))
    service.add_stock_to_watchlist(wl.id, stock.id, "İlk not")

    # 3. Listeden hisseleri çek
    stocks_in_list = service.get_watchlist_stocks(wl.id)
    assert len(stocks_in_list) == 1
    assert stocks_in_list[0]["item"].notes == "İlk not"

    # 4. Hisseyi güncelle
    service.update_watchlist_item_notes(wl.id, stock.id, "Güncellenmiş not")

    # 5. Tekrar çek ve kontrol et
    stocks_in_list = service.get_watchlist_stocks(wl.id)
    assert stocks_in_list[0]["item"].notes == "Güncellenmiş not"
