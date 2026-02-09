
import requests

tickers_to_check = {
    'GREENX': ['GRX', 'GREENX', 'GNX'],
    'VISTULA': ['VRG', 'VTL'],
    'ZABKA': ['ZAB'],
    'PEPCO': ['PCO', 'PEPCO'],
    'PGNIG': ['PGN'],
    'TAURON': ['TPE']
}

def check_stooq(ticker):
    url = f"https://stooq.pl/q/d/l/?s={ticker}&i=d"
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            content = r.text
            if "No data" in content: # Stooq returns a page with "No data" or sometimes a csv with just headers if invalid?
                # Actually stooq returns a csv. If empty or invalid symbol, it might return something else.
                # If symbol is invalid, Stooq often redirects or returns the HTML page of the quote.
                # If it's a CSV download link, it should return CSV.
                pass
            
            # Check if it looks like a CSV (starts with Date,Open,High...)
            if content.startswith("Date,Open,High,Low,Close,Volume"):
                if len(content.splitlines()) > 1:
                    return True
    except:
        pass
    return False

for name, candidates in tickers_to_check.items():
    found = False
    for t in candidates:
        if check_stooq(t):
            print(f"{name}: Found as {t}")
            found = True
            break
    if not found:
        print(f"{name}: Not found")
