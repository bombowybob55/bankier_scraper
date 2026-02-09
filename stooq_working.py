import requests
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import io
import time


# Configuration
DB_NAME = 'historical_data.db'
DAYS_BACK = 180  # Approx 6 months
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
    'PGNIG': 'PGN',  # Merged with PKN Orlen in 2023, may not return data
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
    """Initialize SQLite database with prices table."""
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
    print(f"Database '{DB_NAME}' initialized.")


def save_to_db(ticker, df):
    """Save DataFrame to SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    
    # Add ticker column
    df['ticker'] = ticker
    
    # Ensure correct data types
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce').fillna(0).astype(int)
    df['open'] = pd.to_numeric(df['open'], errors='coerce')
    df['high'] = pd.to_numeric(df['high'], errors='coerce')
    df['low'] = pd.to_numeric(df['low'], errors='coerce')
    df['close'] = pd.to_numeric(df['close'], errors='coerce')
    
    records = 0
    for _, row in df.iterrows():
        try:
            conn.execute('''
                INSERT OR REPLACE INTO prices (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                row['ticker'], 
                row['date'], 
                row['open'], 
                row['high'], 
                row['low'], 
                row['close'], 
                row['volume']
            ))
            records += 1
        except Exception as e:
            print(f"  Error inserting row for {ticker} on {row['date']}: {e}")
            
    conn.commit()
    conn.close()
    return records


def fetch_data(ticker):
    """Fetch historical data from Stooq for a given ticker."""
    # CRITICAL FIX: Polish stocks use lowercase ticker WITHOUT .pl suffix
    # Examples: cdr, pko, pkn (not cdr.pl, pko.pl, pkn.pl)
    ticker_lower = ticker.lower()
    url = f"https://stooq.pl/q/d/l/?s={ticker_lower}&d1={START_DATE}&d2={END_DATE}&i=d"
    print(f"Fetching {ticker}...", end=" ")
    
    try:
        r = requests.get(url, timeout=10)
        
        if r.status_code == 200:
            content = r.text
            
            # Check for "no data" message
            if "Brak danych" in content:
                print(f"No data (ticker may be delisted)")
                return None
            
            # Check if response is too short (error)
            if len(content) < 100:
                print(f"Response too short ({len(content)} chars)")
                return None
            
            # Check for HTML error page
            if "<html" in content.lower():
                print(f"HTML page returned (invalid ticker?)")
                return None
            
            try:
                # Parse CSV from response
                df = pd.read_csv(io.StringIO(content))
                
                # Check if we got valid data
                if df.empty or len(df) == 0:
                    print(f"Empty DataFrame")
                    return None
                
                # Handle both Polish and English column names
                if 'Data' in df.columns:  # Polish headers
                    df = df.rename(columns={
                        'Data': 'date',
                        'Otwarcie': 'open',
                        'Najwyzszy': 'high',
                        'Najnizszy': 'low',
                        'Zamkniecie': 'close',
                        'Wolumen': 'volume'
                    })
                elif 'Date' in df.columns:  # English headers
                    df = df.rename(columns={
                        'Date': 'date',
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume'
                    })
                else:
                    print(f"Unexpected headers: {df.columns.tolist()}")
                    return None
                
                # Validate required columns exist
                required_cols = ['date', 'open', 'high', 'low', 'close', 'volume']
                if not all(col in df.columns for col in required_cols):
                    print(f"Missing required columns")
                    return None
                
                # Standardize date format
                df['date'] = pd.to_datetime(df['date'], errors='coerce').dt.strftime('%Y-%m-%d')
                
                # Remove rows with invalid dates
                df = df.dropna(subset=['date'])
                
                if df.empty:
                    print(f"No valid data after parsing")
                    return None
                
                print(f"✓ {len(df)} rows")
                return df
                
            except Exception as e:
                print(f"CSV parsing error: {e}")
                return None
        else:
            print(f"HTTP Error {r.status_code}")
            return None
            
    except requests.exceptions.Timeout:
        print(f"Timeout")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Connection error: {e}")
        return None


def main():
    """Main execution function."""
    print("=" * 60)
    print("Stooq Polish Stock Data Fetcher")
    print("=" * 60)
    print(f"Date range: {START_DATE} to {END_DATE}")
    print(f"Database: {DB_NAME}")
    print("=" * 60)
    
    # Initialize database
    init_db()
    
    # Get unique tickers (avoid duplicates)
    unique_tickers = sorted(list(set(TICKERS.values())))
    print(f"\nProcessing {len(unique_tickers)} unique tickers...")
    print("Using lowercase tickers WITHOUT .pl suffix\n")
    
    success_count = 0
    fail_count = 0
    total_records = 0
    
    for i, ticker in enumerate(unique_tickers, 1):
        print(f"[{i}/{len(unique_tickers)}] ", end="")
        
        df = fetch_data(ticker)
        
        if df is not None and not df.empty:
            count = save_to_db(ticker, df)
            total_records += count
            success_count += 1
        else:
            fail_count += 1
        
        # Polite delay to avoid overwhelming the server
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Successfully fetched: {success_count} tickers")
    print(f"Failed: {fail_count} tickers")
    print(f"Total records saved: {total_records}")
    print(f"Database: {DB_NAME}")
    print("=" * 60)


if __name__ == "__main__":
    main()
