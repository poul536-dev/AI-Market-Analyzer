import yfinance as yf

tickers = {
    "IBOV": "^BVSP",
    "WIN_PROXY": "YMH25",  
    "WDO_PROXY": "USDBRL=X",
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "DOW": "^DJI",
    "VIX": "^VIX",
    "OIL": "CL=F",
    "DXY": "DX-Y.NYB",
    "US10Y": "^TNX",
    "USDBRL": "USDBRL=X",
}

for name, ticker in tickers.items():
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="5d", interval="1d")
        if not hist.empty:
            last = hist.iloc[-1]
            print(f"{name} ({ticker}): Close={last['Close']:.2f}, Vol={last.get('Volume', 0):.0f}, Rows={len(hist)}")
        else:
            print(f"{name} ({ticker}): EMPTY")
    except Exception as e:
        print(f"{name} ({ticker}): ERROR - {e}")
