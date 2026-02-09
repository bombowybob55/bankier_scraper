
import yfinance as yf
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'historical_data_zagr.db')
DAYS_BACK = 730  # 2 years
START_DATE = (datetime.now() - timedelta(days=DAYS_BACK)).strftime('%Y-%m-%d')
END_DATE = datetime.now().strftime('%Y-%m-%d')

# Dow Jones Industrial Average constituents (as of 2024)
# Ticker symbols are Yahoo Finance tickers
TICKERS = {
    # Dow 30 Companies
    'APPLE': 'AAPL',
    'MICROSOFT': 'MSFT',
    'AMAZON': 'AMZN',
    'NVIDIA': 'NVDA',
    'ALPHABET (GOOGLE)': 'GOOGL',
    'TESLA': 'TSLA',
    'META (FACEBOOK)': 'META',
    'BERKSHIRE HATHAWAY': 'BRK-B',
    'UNITEDHEALTH': 'UNH',
    'JOHNSON & JOHNSON': 'JNJ',
    'VISA': 'V',
    'JPMORGAN CHASE': 'JPM',
    'WALMART': 'WMT',
    'CHEVRON': 'CVX',
    'PROCTER & GAMBLE': 'PG',
    'HOME DEPOT': 'HD',
    'MASTERCARD': 'MA',
    'MERCK': 'MRK',
    'COCA-COLA': 'KO',
    'CISCO': 'CSCO',
    'MCDONALDS': 'MCD',
    'DISNEY': 'DIS',
    'VERIZON': 'VZ',
    'NIKE': 'NKE',
    'AMGEN': 'AMGN',
    'CATERPILLAR': 'CAT',
    'SALESFORCE': 'CRM',
    'HONEYWELL': 'HON',
    'AMERICAN EXPRESS': 'AXP',
    'IBM': 'IBM',
    'GOLDMAN SACHS': 'GS',
    'TRAVELERS': 'TRV',
    '3M': 'MMM',
    'BOEING': 'BA',
    'DOW INC': 'DOW'
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
    
    # yfinance returns columns: Open, High, Low, Close, Volume
    # Rename to match our database schema
    df = df.reset_index()  # Date becomes a column
    df = df.rename(columns={
        'Date': 'date',
        'Open': 'open',
        'High': 'high',
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    })
    
    # Convert date to string format and keep only YYYY-MM-DD
    df['date'] = df['date'].astype(str).str[:10]
    
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
    """Fetch data using yfinance"""
    print(f"Fetching {ticker}...", end=" ", flush=True)
    try:
        # Download data from yfinance
        stock = yf.Ticker(ticker)
        df = stock.history(start=START_DATE, end=END_DATE, interval='1d')
        
        if df.empty:
            print(f"❌ No data available")
            return None
        
        print(f"✅ {len(df)} records")
        return df
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return None

def main():
    init_db()
    print("Database initialized.")
    print(f"Downloading data from {START_DATE} to {END_DATE}\n")
    
    unique_tickers = sorted(list(set(TICKERS.values())))
    print(f"Processing {len(unique_tickers)} Dow Jones tickers...\n")
    
    success_count = 0
    fail_count = 0
    
    for name, ticker in TICKERS.items():
        print(f"{name:30} ({ticker:6}): ", end="", flush=True)
        df = fetch_data(ticker)
        if df is not None and not df.empty:
            count = save_to_db(ticker, df)
            print(f"    Saved {count} records")
            success_count += 1
        else:
            print(f"    Failed to fetch/save data")
            fail_count += 1
        
        # Polite delay to avoid rate limiting
        time.sleep(0.5)
        
    print(f"\n{'='*60}")
    print(f"Done. Success: {success_count}, Failed: {fail_count}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
