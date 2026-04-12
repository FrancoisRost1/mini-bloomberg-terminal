"""Quick probe: does FMP stable/stock-news work on Starter tier?"""

import os
import requests

key = os.environ.get("FMP_API_KEY", "")
if not key:
    print("FMP_API_KEY not set")
    raise SystemExit(1)

url = f"https://financialmodelingprep.com/stable/stock-news?tickers=AAPL&apikey={key}&limit=5"
r = requests.get(url, timeout=10)
print(f"Status: {r.status_code}")
print(f"Body:   {r.text[:500]}")
