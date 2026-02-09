#!/usr/bin/env python3
"""
Diagnostic script to understand why stocks are being filtered out.
"""

import sqlite3
import pandas as pd
import numpy as np

DB_NAME = "historical_data.db"

def calculate_rsi(prices, period=14):
    """Calculate RSI (Relative Strength Index) for given period."""
    delta = prices.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.ewm(com=period-1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period-1, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def diagnose_stocks():
    """Diagnose why stocks are being filtered out."""
    conn = sqlite3.connect(DB_NAME)
    
    # Get list of all tickers
    query = "SELECT DISTINCT ticker FROM prices ORDER BY ticker"
    tickers = pd.read_sql_query(query, conn)['ticker'].tolist()
    
    print(f"Diagnosing {len(tickers)} tickers...")
    print("=" * 100)
    
    stats = {
        'total': 0,
        'insufficient_data': 0,
        'rsi_fail': 0,
        'higher_highs_fail': 0,
        'volume_fail': 0,
        'all_pass': 0
    }
    
    for ticker in tickers[:10]:  # Check first 10 for diagnosis
        query = f"""
            SELECT ticker, date, open, high, low, close, volume
            FROM prices
            WHERE ticker = '{ticker}'
            ORDER BY date
        """
        df = pd.read_sql_query(query, conn)
        
        stats['total'] += 1
        
        print(f"\n{ticker}: {len(df)} days of data")
        
        if len(df) < 200:
            stats['insufficient_data'] += 1
            print(f"  ✗ Insufficient data (need 200, have {len(df)})")
            continue
        
        # Check RSI condition
        rsi_14 = calculate_rsi(df['close'], 14)
        rsi_50 = calculate_rsi(df['close'], 50)
        rsi_150 = calculate_rsi(df['close'], 150)
        rsi_200 = calculate_rsi(df['close'], 200)
        
        current_rsi_14 = rsi_14.iloc[-1]
        current_rsi_50 = rsi_50.iloc[-1]
        current_rsi_150 = rsi_150.iloc[-1]
        current_rsi_200 = rsi_200.iloc[-1]
        
        print(f"  RSI(14)={current_rsi_14:.2f}, RSI(50)={current_rsi_50:.2f}, "
              f"RSI(150)={current_rsi_150:.2f}, RSI(200)={current_rsi_200:.2f}")
        
        condition_a = current_rsi_150 > current_rsi_200
        condition_b = (current_rsi_50 < current_rsi_200) and (current_rsi_14 > current_rsi_50)
        rsi_pass = condition_a or condition_b
        
        if not rsi_pass:
            stats['rsi_fail'] += 1
            print(f"  ✗ RSI condition failed (A={condition_a}, B={condition_b})")
        else:
            print(f"  ✓ RSI condition passed (A={condition_a}, B={condition_b})")
        
        # Check higher highs
        last_high = df.iloc[-1]['high']
        previous_3_days_max = df.iloc[-4:-1]['high'].max()
        higher_highs_pass = last_high > previous_3_days_max
        
        if not higher_highs_pass:
            stats['higher_highs_fail'] += 1
            print(f"  ✗ Higher highs failed (last={last_high:.2f}, prev_3d_max={previous_3_days_max:.2f})")
        else:
            print(f"  ✓ Higher highs passed (last={last_high:.2f} > prev_3d_max={previous_3_days_max:.2f})")
        
        # Check volume
        avg_vol_5d = df.iloc[-5:]['volume'].mean()
        avg_vol_50d = df.iloc[-50:]['volume'].mean()
        volume_pass = avg_vol_5d > avg_vol_50d
        
        if not volume_pass:
            stats['volume_fail'] += 1
            print(f"  ✗ Volume failed (5d={avg_vol_5d:.0f}, 50d={avg_vol_50d:.0f}, ratio={avg_vol_5d/avg_vol_50d:.2f})")
        else:
            print(f"  ✓ Volume passed (5d={avg_vol_5d:.0f} > 50d={avg_vol_50d:.0f}, ratio={avg_vol_5d/avg_vol_50d:.2f})")
        
        if rsi_pass and higher_highs_pass and volume_pass:
            stats['all_pass'] += 1
            print(f"  ✓✓✓ ALL CONDITIONS PASSED!")
    
    conn.close()
    
    print("\n" + "=" * 100)
    print("\nSummary Statistics:")
    print(f"  Total analyzed: {stats['total']}")
    print(f"  Insufficient data: {stats['insufficient_data']}")
    print(f"  RSI failures: {stats['rsi_fail']}")
    print(f"  Higher highs failures: {stats['higher_highs_fail']}")
    print(f"  Volume failures: {stats['volume_fail']}")
    print(f"  All conditions passed: {stats['all_pass']}")

if __name__ == "__main__":
    diagnose_stocks()
