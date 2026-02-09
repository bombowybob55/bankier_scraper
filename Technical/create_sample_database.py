"""
Sample Database Creator
=======================
This script creates a sample database with dummy stock data for testing.
Run this if you don't have historical_data.db yet.

Usage: python create_sample_database.py
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_sample_database():
    """Create a sample database with 3 stocks and 2 years of data"""

    print("Creating sample database...")

    # Connect to database
    conn = sqlite3.connect('historical_data.db')
    cursor = conn.cursor()

    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stock_data (
            ticker TEXT NOT NULL,
            date DATE NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume INTEGER NOT NULL,
            UNIQUE(ticker, date)
        )
    """)

    # Sample tickers
    tickers = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN']

    # Generate 2 years of data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=730)  # 2 years
    dates = pd.date_range(start=start_date, end=end_date, freq='D')

    # Remove weekends (approximate)
    dates = [d for d in dates if d.weekday() < 5]

    total_records = 0

    for ticker in tickers:
        print(f"  Generating data for {ticker}...")

        # Starting price (random between 50-300)
        base_price = np.random.uniform(50, 300)

        # Generate realistic price movements
        np.random.seed(hash(ticker) % 1000)  # Consistent data per ticker

        daily_returns = np.random.normal(0.0005, 0.02, len(dates))  # Small daily changes

        # Add trend component (some stocks trending up, some down)
        trend = np.random.choice([-0.0001, 0.0001, 0.0002])

        prices = [base_price]
        for ret in daily_returns:
            new_price = prices[-1] * (1 + ret + trend)
            prices.append(max(new_price, 1.0))  # Ensure price stays positive

        prices = prices[1:]  # Remove initial price

        # Generate OHLC data
        for i, date in enumerate(dates):
            close_price = prices[i]

            # Generate open, high, low around close
            daily_volatility = np.random.uniform(0.005, 0.03)

            open_price = close_price * (1 + np.random.uniform(-daily_volatility, daily_volatility))
            high_price = max(open_price, close_price) * (1 + np.random.uniform(0, daily_volatility))
            low_price = min(open_price, close_price) * (1 - np.random.uniform(0, daily_volatility))

            # Generate volume (millions of shares)
            volume = int(np.random.uniform(1_000_000, 50_000_000))

            # Insert into database
            cursor.execute("""
                INSERT OR IGNORE INTO stock_data 
                (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                ticker,
                date.strftime('%Y-%m-%d'),
                round(open_price, 2),
                round(high_price, 2),
                round(low_price, 2),
                round(close_price, 2),
                volume
            ))

            total_records += 1

    # Commit and close
    conn.commit()

    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_ticker ON stock_data(ticker)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON stock_data(date)")
    conn.commit()

    # Print summary
    cursor.execute("SELECT COUNT(DISTINCT ticker) FROM stock_data")
    stock_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM stock_data")
    record_count = cursor.fetchone()[0]

    cursor.execute("SELECT MIN(date), MAX(date) FROM stock_data")
    date_range = cursor.fetchone()

    conn.close()

    print("\n" + "="*60)
    print("✓ Sample database created successfully!")
    print("="*60)
    print(f"  Database: historical_data.db")
    print(f"  Stocks: {stock_count}")
    print(f"  Total records: {record_count}")
    print(f"  Date range: {date_range[0]} to {date_range[1]}")
    print("="*60)
    print("\nYou can now run: python stock_analysis.py")
    print("="*60)

if __name__ == "__main__":
    create_sample_database()
