
import requests
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import io
import time

# Configuration
DB_NAME = 'historical_data.db'
DEFAULT_DAYS_BACK = 30 # For tickers with no data in DB

# Ticker Mapping (Name -> Stooq Ticker)
TICKERS = {
    # WIG20
    'ALIOR': 'ALR',
    'ALLEGRO': 'ALE',
    'BUDIMEX': 'BDX',
    'CCC': 'CCC',
    'CD PROJEKT': 'CDR',
    'DINO': 'DNP',
    'GRUPA KĘTY': 'KTY',
    'KGHM': 'KGH',
    'KRUK': 'KRU',
    'LPP': 'LPP',
    'MBANK': 'MBK',
    'ORANGE POLSKA': 'OPL',
    'PEKAO': 'PEO',
    'PEPCO': 'PCO',
    'PGE': 'PGE',
    'PKN ORLEN': 'PKN',
    'PKO BP': 'PKO',
    'PZU': 'PZU',
    'SANTANDER': 'SPL',
    'TAURON': 'TPE',
    'ENEA': 'ENA',
    'ŻABKA': 'ZAB',
    
    # mWIG40
    '11 BIT STUDIOS': '11B',
    'ABPL': 'ABE',
    'AMREST': 'EAT',
    'ASBIS': 'ASB',
    'ASSECO POLAND': 'ACP',
    'ASSECOSEE': 'ASE',
    'AUTOPARTN': 'APR',
    'BENEFIT': 'BFT',
    'BNP PARIBAS BANK POLSKA': 'BNP',
    'CYBERFLKS': 'CBF',
    'CYFROWY POLSAT': 'CPS',
    'DEVELIA': 'DVL',
    'DIAG': 'DIA',
    'DOMDEV': 'DOM',
    'EUROCASH': 'EUR',
    'GPW': 'GPW',
    'GREENX': 'GRX',
    'GRUPAAZOTY': 'ATT',
    'GRUPRACUJ': 'GPP',
    'HANDLOWY': 'BHW',
    'HUUUGE': 'HUG',
    'ING BANK ŚLĄSKI': 'ING',
    'INTERCARS': 'CAR',
    'JSW': 'JSW',
    'LUBAWA': 'LBW',
    'MILLENNIUM': 'MIL',
    'MIRBUD': 'MRB',
    'MOBRUK': 'MBR',
    'NEUCA': 'NEU',
    'NEWAG': 'NWG',
    'PEP': 'PEP',
    'PLAYWAY': 'PLW',
    'RAINBOW': 'RBW',
    'SYNEKTIK': 'SNT',
    'TEXT': 'TXT',
    'TSGAMES': 'TEN',
    'VERCOM': 'VRC',
    'VISTULA GROUP': 'VRG',
    'VOXEL': 'VOX',
    'WIRTUALNA': 'WPL',
    'XTB': 'XTB'
}

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS prices (
            ticker TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            PRIMARY KEY (ticker, date)
        )
    ''')
    conn.commit()
    conn.close()

def get_latest_date_for_ticker(ticker):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT MAX(date) FROM prices WHERE ticker = ?", (ticker,))
    res = c.fetchone()
    conn.close()
    if res and res[0]:
        return res[0]
    return None

def save_to_db(ticker, df):
    conn = sqlite3.connect(DB_NAME)
    # Stooq PL columns: Data,Otwarcie,Najwyzszy,Najnizszy,Zamkniecie,Wolumen
    # Rename to English
    df = df.rename(columns={
        'Data': 'date',
        'Otwarcie': 'open',
        'Najwyzszy': 'high',
        'Najnizszy': 'low',
        'Zamkniecie': 'close',
        'Wolumen': 'volume'
    })
    
    # Add ticker column
    df['ticker'] = ticker
    
    # Ensure correct types
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)
    
    records = 0
    for _, row in df.iterrows():
        try:
            conn.execute('''
                INSERT OR REPLACE INTO prices (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (row['ticker'], row['date'], row['open'], row['high'], row['low'], row['close'], row['volume']))
            records += 1
        except Exception as e:
            print(f"[{ticker}] Error inserting row for {row['date']}: {e}")
            
    conn.commit()
    conn.close()
    return records

def fetch_data(ticker, start_date, end_date):
    """
    start_date and end_date in YYYYMMDD format
    """
    url = f"https://stooq.pl/q/d/l/?s={ticker}&d1={start_date}&d2={end_date}&i=d"
    print(f"Fetching {ticker} from {start_date} to {end_date}...")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            content = r.text
            if "Brak danych" in content:
                print(f"No data for {ticker}")
                return None
            
            # Stooq returns CSV.
            try:
                df = pd.read_csv(io.StringIO(content))
                # Validate columns
                if 'Data' not in df.columns:
                     # Check if maybe English headers?
                     if 'Date' in df.columns:
                         df = df.rename(columns={'Date': 'Data', 'Open': 'Otwarcie', 'High': 'Najwyzszy', 'Low': 'Najnizszy', 'Close': 'Zamkniecie', 'Volume': 'Wolumen'})
                     else:
                        print(f"Unexpected headers for {ticker}: {df.columns}")
                        return None
                return df
            except Exception as e:
                print(f"CSV parsing error for {ticker}: {e}")
        else:
            print(f"HTTP Error {r.status_code} for {ticker}")
    except Exception as e:
        print(f"Connection error for {ticker}: {e}")
    return None

def main():
    init_db()
    
    unique_tickers = sorted(list(set(TICKERS.values())))
    print(f"Checking updates for {len(unique_tickers)} tickers...")
    
    end_date = datetime.now().strftime('%Y%m%d')
    
    success_count = 0
    up_to_date_count = 0
    fail_count = 0
    
    for ticker in unique_tickers:
        latest_date_str = get_latest_date_for_ticker(ticker)
        
        if latest_date_str:
            # latest_date_str is YYYY-MM-DD
            start_date = latest_date_str.replace('-', '')
            # If start_date is already today, we might still want to refresh it 
            # but let's see if it's strictly necessary.
            # Stooq data for today might be incomplete until EOD.
        else:
            # Fallback for new tickers
            start_date = (datetime.now() - timedelta(days=DEFAULT_DAYS_BACK)).strftime('%Y%m%d')
            print(f"No existing data for {ticker}, starting from {start_date}")

        # If latest date in DB is already today's date, and it's before market close, 
        # we might want to skip or re-fetch. 
        # For now, always fetch from latest_date to end_date.
        
        df = fetch_data(ticker, start_date, end_date)
        
        if df is not None and not df.empty:
            count = save_to_db(ticker, df)
            if count > 0:
                print(f"Saved/Updated {count} records for {ticker}")
                success_count += 1
            else:
                print(f"{ticker} is already up to date.")
                up_to_date_count += 1
        elif df is not None and df.empty:
            print(f"{ticker} returned empty data.")
            up_to_date_count += 1
        else:
            print(f"Failed to fetch data for {ticker}")
            fail_count += 1
        
        # Polite delay
        time.sleep(0.5)
        
    print(f"\nDone.")
    print(f"Success (New/Updated): {success_count}")
    print(f"Up to date: {up_to_date_count}")
    print(f"Failed: {fail_count}")

if __name__ == "__main__":
    main()
