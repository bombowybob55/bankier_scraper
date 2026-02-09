
import requests

tickers_to_check = {
    'ZABKA': ['ZAB'],
    'PEPCO': ['PCO', 'PEPCO'],
    'POLENERGIA': ['PEP'],
    'LPP': ['LPP'],
    'ALIOR': ['ALR'],
    'ALLEGRO': ['ALE']
}

def check_stooq(ticker):
    url = f"https://stooq.pl/q/d/l/?s={ticker}&i=d"
    print(f"Checking {ticker}...")
    try:
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            content = r.text
            if content.startswith("Data,Otwarcie"):
                print(f"Success for {ticker}")
                return True
            else:
                print(f"Failed {ticker}: {content[:50]}")
    except Exception as e:
        print(f"Error: {e}")
    return False

for name, candidates in tickers_to_check.items():
    for t in candidates:
        check_stooq(t)
