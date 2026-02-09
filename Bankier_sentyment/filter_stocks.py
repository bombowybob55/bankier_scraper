#!/usr/bin/env python3
"""
Stock Filtering Script
Filters stocks based on RSI trends, price momentum, and volume patterns.
"""

import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime

DB_NAME = "historical_data.db"

def calculate_rsi(prices, period=14):
    """
    Calculate RSI (Relative Strength Index) for given period.
    
    Args:
        prices: Series of closing prices
        period: RSI period (default 14)
    
    Returns:
        Series with RSI values
    """
    # Calculate price changes
    delta = prices.diff()
    
    # Separate gains and losses
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    
    # Calculate average gain and loss using exponential moving average
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    
    # Calculate RS and RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def check_higher_highs(df):
    """
    Check if last day's high is above the highest high of previous 3 days.
    
    Args:
        df: DataFrame with 'high' column, sorted by date
    
    Returns:
        Boolean indicating if condition is met
    """
    if len(df) < 4:
        return False
    
    last_high = df.iloc[-1]['high']
    previous_3_days_max = df.iloc[-4:-1]['high'].max()
    
    return last_high > previous_3_days_max

def check_volume_trend(df):
    """
    Check if average volume (last 5 days) > average volume (last 50 days).
    
    Args:
        df: DataFrame with 'volume' column, sorted by date
    
    Returns:
        Boolean indicating if condition is met
    """
    if len(df) < 50:
        return False
    
    avg_volume_5d = df.iloc[-5:]['volume'].mean()
    avg_volume_50d = df.iloc[-50:]['volume'].mean()
    
    return avg_volume_5d > avg_volume_50d

def check_rsi_condition(df):
    """
    Check RSI condition (adjusted for available data):
    RSI(100) > RSI(120) OR (RSI(50) < RSI(120) AND RSI(14) > RSI(50))
    
    Note: Original criteria used RSI(150) and RSI(200), but database only has ~120 days.
    Adjusted to RSI(100) and RSI(120) to work with available data.
    
    Args:
        df: DataFrame with 'close' column, sorted by date
    
    Returns:
        Boolean indicating if condition is met
    """
    # Need at least 120 days of data
    if len(df) < 120:
        return False
    
    # Calculate RSI for different periods (adjusted for available data)
    rsi_14 = calculate_rsi(df['close'], 14)
    rsi_50 = calculate_rsi(df['close'], 50)
    rsi_100 = calculate_rsi(df['close'], 100)
    rsi_120 = calculate_rsi(df['close'], 120)
    
    # Get the most recent RSI values
    current_rsi_14 = rsi_14.iloc[-1]
    current_rsi_50 = rsi_50.iloc[-1]
    current_rsi_100 = rsi_100.iloc[-1]
    current_rsi_120 = rsi_120.iloc[-1]
    
    # Check if any value is NaN
    if pd.isna(current_rsi_14) or pd.isna(current_rsi_50) or pd.isna(current_rsi_100) or pd.isna(current_rsi_120):
        return False
    
    # Condition A: RSI(100) > RSI(120)
    condition_a = current_rsi_100 > current_rsi_120
    
    # Condition B: RSI(50) < RSI(120) AND RSI(14) > RSI(50)
    condition_b = (current_rsi_50 < current_rsi_120) and (current_rsi_14 > current_rsi_50)
    
    return condition_a or condition_b

def filter_stocks():
    """
    Main function to filter stocks based on all criteria.
    """
    # Connect to database
    conn = sqlite3.connect(DB_NAME)
    
    # Get list of all tickers
    query = "SELECT DISTINCT ticker FROM prices ORDER BY ticker"
    tickers = pd.read_sql_query(query, conn)['ticker'].tolist()
    
    print(f"Analyzing {len(tickers)} tickers...")
    print("=" * 80)
    
    filtered_stocks = []
    
    for ticker in tickers:
        # Load data for this ticker
        query = f"""
            SELECT ticker, date, open, high, low, close, volume
            FROM prices
            WHERE ticker = '{ticker}'
            ORDER BY date
        """
        df = pd.read_sql_query(query, conn)
        
        if len(df) < 120:
            continue  # Skip if insufficient data
        
        # Check all three conditions
        rsi_pass = check_rsi_condition(df)
        higher_highs_pass = check_higher_highs(df)
        volume_pass = check_volume_trend(df)
        
        if rsi_pass and higher_highs_pass and volume_pass:
            # Get latest values for reporting
            latest = df.iloc[-1]
            avg_vol_5d = df.iloc[-5:]['volume'].mean()
            avg_vol_50d = df.iloc[-50:]['volume'].mean()
            
            filtered_stocks.append({
                'ticker': ticker,
                'last_close': latest['close'],
                'last_high': latest['high'],
                'last_date': latest['date'],
                'avg_vol_5d': int(avg_vol_5d),
                'avg_vol_50d': int(avg_vol_50d),
                'vol_ratio': avg_vol_5d / avg_vol_50d
            })
            
            print(f"✓ {ticker:8s} - Close: {latest['close']:7.2f} | "
                  f"Vol 5d/50d: {avg_vol_5d/avg_vol_50d:.2f}x | "
                  f"Date: {latest['date']}")
    
    conn.close()
    
    print("=" * 80)
    print(f"\nFound {len(filtered_stocks)} stocks meeting all criteria:")
    print()
    
    if filtered_stocks:
        # Create summary DataFrame
        summary_df = pd.DataFrame(filtered_stocks)
        summary_df = summary_df.sort_values('vol_ratio', ascending=False)
        
        print(summary_df.to_string(index=False))
        
        # Save to CSV
        output_file = f"filtered_stocks_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        summary_df.to_csv(output_file, index=False)
        print(f"\n✓ Results saved to: {output_file}")
    else:
        print("No stocks met all criteria.")
    
    return filtered_stocks

if __name__ == "__main__":
    filter_stocks()
