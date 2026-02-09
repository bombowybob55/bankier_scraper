
import yfinance as yf
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import time
import os

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, 'historical_data_zagr.db')
DEFAULT_DAYS_BACK = 30  # For tickers with no data in DB

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

def get_latest_date_for_ticker(ticker):
    """Get the latest date stored in DB for a given ticker"""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT MAX(date) FROM prices WHERE ticker = ?", (ticker,))
    res = c.fetchone()
    conn.close()
    if res and res[0]:
        return res[0]
    return None

def save_to_db(ticker, df):
    """Save dataframe to database"""
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
            print(f"[{ticker}] Error inserting row for {row['date']}: {e}")
            
    conn.commit()
    conn.close()
    return records

def fetch_data(ticker, start_date, end_date):
    """
    Fetch data using yfinance for the specified date range
    start_date and end_date should be datetime objects or YYYY-MM-DD strings
    """
    print(f"Fetching {ticker} from {start_date} to {end_date}...")
    try:
        stock = yf.Ticker(ticker)
        df = stock.history(start=start_date, end=end_date, interval='1d')
        
        if df.empty:
            print(f"No data for {ticker}")
            return None
        
        return df
        
    except Exception as e:
        print(f"Error fetching {ticker}: {e}")
        return None

def main():
    init_db()
    
    unique_tickers = sorted(list(set(TICKERS.values())))
    print(f"Checking updates for {len(unique_tickers)} tickers...")
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    success_count = 0
    up_to_date_count = 0
    fail_count = 0
    
    for ticker in unique_tickers:
        latest_date_str = get_latest_date_for_ticker(ticker)
        
        if latest_date_str:
            # latest_date_str might be YYYY-MM-DD or YYYY-MM-DD HH:MM:SS+ZZ:ZZ
            # Start from the day after the latest date
            latest_date = datetime.strptime(latest_date_str[:10], '%Y-%m-%d')
            start_date = (latest_date + timedelta(days=1)).strftime('%Y-%m-%d')
            
            # Check if we're already up to date
            if start_date >= end_date:
                print(f"{ticker} is already up to date (latest: {latest_date_str})")
                up_to_date_count += 1
                continue
        else:
            # Fallback for new tickers
            start_date = (datetime.now() - timedelta(days=DEFAULT_DAYS_BACK)).strftime('%Y-%m-%d')
            print(f"No existing data for {ticker}, starting from {start_date}")

        df = fetch_data(ticker, start_date, end_date)
        
        if df is not None and not df.empty:
            count = save_to_db(ticker, df)
            if count > 0:
                print(f"✅ Saved/Updated {count} records for {ticker}")
                success_count += 1
            else:
                print(f"{ticker} is already up to date.")
                up_to_date_count += 1
        elif df is not None and df.empty:
            print(f"{ticker} returned empty data.")
            up_to_date_count += 1
        else:
            print(f"❌ Failed to fetch data for {ticker}")
            fail_count += 1
        
        # Polite delay to avoid rate limiting
        time.sleep(0.5)
        
    print(f"\n{'='*60}")
    print(f"Done.")
    print(f"Success (New/Updated): {success_count}")
    print(f"Up to date: {up_to_date_count}")
    print(f"Failed: {fail_count}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
