
import requests

tickers_to_check = {
    'CD PROJEKT': ['CDR', 'CDR.PL'],
    'GREENX': ['GRX', 'GRX.PL', 'GREENX'],
    'VISTULA': ['VRG', 'VRG.PL'],
}

def check_stooq(ticker):
    url = f"https://stooq.pl/q/d/l/?s={ticker}&i=d"
    print(f"Checking {url}...")
    try:
        r = requests.get(url, timeout=5)
        print(f"Status: {r.status_code}")
        if r.status_code == 200:
            content = r.text
            print(f"Content start: {content[:100]}")
            if content.startswith("Date,Open"):
                return True
            if "No data" in content:
                print("Stooq says No data")
    except Exception as e:
        print(f"Error: {e}")
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
