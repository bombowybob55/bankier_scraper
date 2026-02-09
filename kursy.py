
import requests
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import io
import time

# Configuration
DB_NAME = 'historical_data.db'
DAYS_BACK = 730  # 2 years
START_DATE = (datetime.now() - timedelta(days=DAYS_BACK)).strftime('%Y%m%d')
END_DATE = datetime.now().strftime('%Y%m%d')

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
            print(f"Error inserting row for {ticker}: {e}")
            
    conn.commit()
    conn.close()
    return records

def fetch_data(ticker):
    url = f"https://stooq.pl/q/d/l/?s={ticker}&d1={START_DATE}&d2={END_DATE}&i=d"
    print(f"Fetching {ticker} from {url}...")
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
    print("Database initialized.")
    
    unique_tickers = sorted(list(set(TICKERS.values())))
    print(f"Processing {len(unique_tickers)} tickers...")
    
    success_count = 0
    fail_count = 0
    
    for ticker in unique_tickers:
        df = fetch_data(ticker)
        if df is not None and not df.empty:
            count = save_to_db(ticker, df)
            print(f"Saved {count} records for {ticker}")
            success_count += 1
        else:
            print(f"Failed to fetch/save data for {ticker}")
            fail_count += 1
        
        # Polite delay
        time.sleep(0.5)
        
    print(f"\nDone. Success: {success_count}, Failed: {fail_count}")

if __name__ == "__main__":
    main()
