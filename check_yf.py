import yfinance as yf
merko = yf.Ticker("MERKO.IS")
hist = merko.history(start="2026-04-25", end="2026-05-15")
print(hist[['Close']])

