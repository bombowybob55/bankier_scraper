"""
Foreign Stock Technical Backtest Tool
======================================
This script evaluates technical sentiment over the last 30 trading days
and aggregates the results to identify sustained bullish or bearish trends.

Logic:
- Bullish/Strong Bullish: +1
- Neutral: 0
- Bearish/Strong Bearish: -1
"""

import sqlite3
import pandas as pd
import numpy as np
import os
from datetime import datetime
import warnings

warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION
# ============================================================================

class Config:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "historical_data_zagr.db")
    
    # Technical indicator parameters
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    RSI_PERIOD = 14
    BB_PERIOD = 20
    BB_STD = 2
    MFI_PERIOD = 14

    # Minimum data points required for a single prediction
    MIN_DATA_POINTS = 30 
    
    # Backtest duration
    BACKTEST_DAYS = 30

# ============================================================================
# TECHNICAL INDICATORS (Ported from stock_analysis_zagr.py)
# ============================================================================

def calculate_ema(data, period):
    return data.ewm(span=period, adjust=False).mean()

def calculate_macd(df):
    try:
        ema_fast = calculate_ema(df['close'], Config.MACD_FAST)
        ema_slow = calculate_ema(df['close'], Config.MACD_SLOW)
        macd_line = ema_fast - ema_slow
        signal_line = calculate_ema(macd_line, Config.MACD_SIGNAL)
        histogram = macd_line - signal_line
        return {'histogram': histogram.iloc[-1]}
    except: return None

def calculate_rsi(df):
    try:
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        avg_gain = gain.ewm(span=Config.RSI_PERIOD, adjust=False).mean()
        avg_loss = loss.ewm(span=Config.RSI_PERIOD, adjust=False).mean()
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]
    except: return None

def calculate_bollinger_bands(df):
    try:
        middle_band = df['close'].rolling(window=Config.BB_PERIOD).mean()
        std = df['close'].rolling(window=Config.BB_PERIOD).std()
        upper_band = middle_band + (Config.BB_STD * std)
        lower_band = middle_band - (Config.BB_STD * std)
        current_price = df['close'].iloc[-1]
        return {'upper': upper_band.iloc[-1], 'middle': middle_band.iloc[-1], 'lower': lower_band.iloc[-1], 'current_price': current_price}
    except: return None

def calculate_mfi(df):
    try:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']
        positive_flow = []
        negative_flow = []
        for i in range(1, len(typical_price)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.append(money_flow.iloc[i]); negative_flow.append(0)
            elif typical_price.iloc[i] < typical_price.iloc[i-1]:
                positive_flow.append(0); negative_flow.append(money_flow.iloc[i])
            else:
                positive_flow.append(0); negative_flow.append(0)
        pos_mf = pd.Series(positive_flow).rolling(window=Config.MFI_PERIOD).sum()
        neg_mf = pd.Series(negative_flow).rolling(window=Config.MFI_PERIOD).sum()
        mfr = pos_mf / neg_mf.replace(0, 0.001)
        mfi = 100 - (100 / (1 + mfr))
        return mfi.iloc[-1]
    except: return None

# ============================================================================
# SCORING
# ============================================================================

def score_macd(macd_data):
    if not macd_data: return 0
    return 100 if macd_data['histogram'] > 0 else -100

def score_rsi(rsi):
    if rsi is None or np.isnan(rsi): return 0
    if rsi < 30: return 100
    if rsi < 40: return 50
    if rsi < 60: return 0
    if rsi < 70: return -50
    return -100

def score_bb(bb):
    if not bb: return 0
    p, l, m, u = bb['current_price'], bb['lower'], bb['middle'], bb['upper']
    if p <= l: return 100
    if p < m: return 50
    if p == m: return 0
    if p < u: return -50
    return -100

def score_mfi(mfi):
    if mfi is None or np.isnan(mfi): return 0
    if mfi < 20: return 100
    if mfi < 40: return 50
    if mfi < 60: return 0
    if mfi < 80: return -50
    return -100

def get_sentiment(df):
    m_score = score_macd(calculate_macd(df))
    r_score = score_rsi(calculate_rsi(df))
    b_score = score_bb(calculate_bollinger_bands(df))
    i_score = score_mfi(calculate_mfi(df))
    
    combined = (m_score + r_score + b_score + i_score) / 4.0
    
    if combined >= 30: return 1   # Bullish
    if combined <= -30: return -1 # Bearish
    return 0                      # Neutral

# ============================================================================
# BACKTEST ENGINE
# ============================================================================

def run_backtest(conn, ticker):
    query = "SELECT high, low, close, volume FROM prices WHERE ticker = ? ORDER BY date ASC"
    df = pd.read_sql_query(query, conn, params=(ticker,))
    
    if len(df) < Config.MIN_DATA_POINTS + Config.BACKTEST_DAYS:
        return None

    results = []
    # Slide through the last 30 days
    # Total length L. Last index is L-1.
    # Prediction for day i uses index 0 to i.
    for i in range(len(df) - Config.BACKTEST_DAYS, len(df)):
        window = df.iloc[:i+1]
        results.append(get_sentiment(window))
        
    return {
        'ticker': ticker,
        'total_score': sum(results),
        'bullish_days': results.count(1),
        'neutral_days': results.count(0),
        'bearish_days': results.count(-1),
        'days_tested': len(results)
    }

def main():
    if not os.path.exists(Config.DB_PATH):
        print(f"Error: Database not found at {Config.DB_PATH}")
        return

    conn = sqlite3.connect(Config.DB_PATH)
    tickers = pd.read_sql_query("SELECT DISTINCT ticker FROM prices ORDER BY ticker", conn)['ticker'].tolist()
    
    print(f"\nEvaluating {len(tickers)} stocks over the last {Config.BACKTEST_DAYS} trading days...")
    print("-" * 80)
    
    backtest_results = []
    for ticker in tickers:
        res = run_backtest(conn, ticker)
        if res:
            backtest_results.append(res)
            print(f"  ✓ {ticker}: Total Score {res['total_score']:+3} (B:{res['bullish_days']} N:{res['neutral_days']} Br:{res['bearish_days']})")
        else:
            print(f"  ⚠ {ticker}: Insufficient data for 30-day backtest")
            
    conn.close()
    
    if not backtest_results:
        print("\nNo results to display.")
        return

    df_res = pd.DataFrame(backtest_results).sort_values('total_score', ascending=False)
    
    print("\n" + "="*80)
    print(f"BACKTEST SUMMARY (LAST {Config.BACKTEST_DAYS} TRADING DAYS)".center(80))
    print("="*80)
    print(f"{'Ticker':<10} {'Total Score':<15} {'Bullish':<10} {'Neutral':<10} {'Bearish':<10}")
    print("-" * 80)
    
    for _, row in df_res.iterrows():
        print(f"{row['ticker']:<10} {row['total_score']:>11} {row['bullish_days']:>10} {row['neutral_days']:>10} {row['bearish_days']:>10}")
    
    print("-" * 80)
    print(f"Evaluation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)

if __name__ == "__main__":
    main()
