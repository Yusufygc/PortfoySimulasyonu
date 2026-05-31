class MarketDataUnavailableError(Exception):
    """
    Market data endpoints (e.g., YFinance, EVDS, Investing) are unreachable
    or returned unparseable/invalid data.
    """
    pass

class DatabaseSchemaError(Exception):
    """
    Veritabani şeması ile beklenen şema uyuşmadığında (örn. eksik kolon, tablo vs.) fırlatılır.
    """
    pass
