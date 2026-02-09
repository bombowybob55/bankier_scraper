"""
Stock Technical Analysis & Sentiment Scoring Tool
==================================================
This script analyzes historical stock data and generates sentiment scores
based on technical indicators: MACD, RSI, Bollinger Bands, and MFI.

Author: Generated for Capital Markets Analysis
Date: February 4, 2026
"""

import sqlite3
import pandas as pd
import numpy as np
import os
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# CONFIGURATION PARAMETERS
# ============================================================================

class Config:
    """Configuration parameters for the analysis"""

    # Database settings
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(BASE_DIR, "historical_data.db")
    
    # Report settings
    REPORT_DIR = os.path.join(BASE_DIR, "Reports", "Technical")

    # Technical indicator parameters
    MACD_FAST = 12
    MACD_SLOW = 26
    MACD_SIGNAL = 9
    RSI_PERIOD = 14
    BB_PERIOD = 20
    BB_STD = 2
    MFI_PERIOD = 14

    # Scoring thresholds
    RSI_OVERSOLD = 30
    RSI_OVERBOUGHT = 70
    MFI_OVERSOLD = 20
    MFI_OVERBOUGHT = 80

    # Minimum data points required
    MIN_DATA_POINTS = 30  # Need at least 30 days for all indicators

# ============================================================================
# TECHNICAL INDICATOR CALCULATIONS
# ============================================================================

def calculate_ema(data, period):
    """
    Calculate Exponential Moving Average

    Args:
        data: pandas Series of prices
        period: int, number of periods

    Returns:
        pandas Series of EMA values
    """
    return data.ewm(span=period, adjust=False).mean()


def calculate_macd(df):
    """
    Calculate MACD (Moving Average Convergence Divergence)

    Formula:
    - MACD Line = EMA(12) - EMA(26)
    - Signal Line = EMA(9) of MACD Line
    - Histogram = MACD Line - Signal Line

    Args:
        df: DataFrame with 'close' column

    Returns:
        dict with macd_line, signal_line, histogram for last day
    """
    try:
        ema_fast = calculate_ema(df['close'], Config.MACD_FAST)
        ema_slow = calculate_ema(df['close'], Config.MACD_SLOW)

        macd_line = ema_fast - ema_slow
        signal_line = calculate_ema(macd_line, Config.MACD_SIGNAL)
        histogram = macd_line - signal_line

        return {
            'macd_line': macd_line.iloc[-1],
            'signal_line': signal_line.iloc[-1],
            'histogram': histogram.iloc[-1]
        }
    except Exception as e:
        print(f"    Error calculating MACD: {e}")
        return None


def calculate_rsi(df):
    """
    Calculate RSI (Relative Strength Index)

    Formula:
    RSI = 100 - (100 / (1 + RS))
    where RS = Average Gain / Average Loss over period

    Args:
        df: DataFrame with 'close' column

    Returns:
        float, RSI value for last day
    """
    try:
        delta = df['close'].diff()

        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)

        avg_gain = gain.ewm(span=Config.RSI_PERIOD, adjust=False).mean()
        avg_loss = loss.ewm(span=Config.RSI_PERIOD, adjust=False).mean()

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi.iloc[-1]
    except Exception as e:
        print(f"    Error calculating RSI: {e}")
        return None


def calculate_bollinger_bands(df):
    """
    Calculate Bollinger Bands

    Formula:
    - Middle Band = 20-day SMA
    - Upper Band = Middle Band + (2 × standard deviation)
    - Lower Band = Middle Band - (2 × standard deviation)

    Args:
        df: DataFrame with 'close' column

    Returns:
        dict with upper, middle, lower bands and current price
    """
    try:
        middle_band = df['close'].rolling(window=Config.BB_PERIOD).mean()
        std = df['close'].rolling(window=Config.BB_PERIOD).std()

        upper_band = middle_band + (Config.BB_STD * std)
        lower_band = middle_band - (Config.BB_STD * std)
        current_price = df['close'].iloc[-1]

        return {
            'upper': upper_band.iloc[-1],
            'middle': middle_band.iloc[-1],
            'lower': lower_band.iloc[-1],
            'current_price': current_price
        }
    except Exception as e:
        print(f"    Error calculating Bollinger Bands: {e}")
        return None


def calculate_mfi(df):
    """
    Calculate MFI (Money Flow Index)

    Formula:
    - Typical Price = (High + Low + Close) / 3
    - Money Flow = Typical Price × Volume
    - MFI = 100 - (100 / (1 + Money Flow Ratio))

    Args:
        df: DataFrame with 'high', 'low', 'close', 'volume' columns

    Returns:
        float, MFI value for last day
    """
    try:
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        money_flow = typical_price * df['volume']

        positive_flow = []
        negative_flow = []

        for i in range(1, len(typical_price)):
            if typical_price.iloc[i] > typical_price.iloc[i-1]:
                positive_flow.append(money_flow.iloc[i])
                negative_flow.append(0)
            elif typical_price.iloc[i] < typical_price.iloc[i-1]:
                positive_flow.append(0)
                negative_flow.append(money_flow.iloc[i])
            else:
                positive_flow.append(0)
                negative_flow.append(0)

        positive_mf = pd.Series(positive_flow).rolling(window=Config.MFI_PERIOD).sum()
        negative_mf = pd.Series(negative_flow).rolling(window=Config.MFI_PERIOD).sum()

        # Avoid division by zero
        mfr = positive_mf / negative_mf.replace(0, 0.001)
        mfi = 100 - (100 / (1 + mfr))

        return mfi.iloc[-1]
    except Exception as e:
        print(f"    Error calculating MFI: {e}")
        return None

# ============================================================================
# SCORING SYSTEM
# ============================================================================

def score_macd(macd_data):
    """
    Score MACD indicator from -100 to +100

    Logic:
    - Histogram > 0: Bullish (+50 to +100)
    - Histogram < 0: Bearish (-50 to -100)
    """
    if macd_data is None:
        return 0

    histogram = macd_data['histogram']

    if histogram > 0:
        return 100  # Bullish signal
    elif histogram < 0:
        return -100  # Bearish signal
    else:
        return 0


def score_rsi(rsi_value):
    """
    Score RSI indicator from -100 to +100

    Logic:
    - RSI < 30: +100 (oversold, potential reversal up)
    - RSI > 70: -100 (overbought, potential reversal down)
    """
    if rsi_value is None or np.isnan(rsi_value):
        return 0

    if rsi_value < 30:
        return 100
    elif rsi_value < 40:
        return 50
    elif rsi_value < 60:
        return 0
    elif rsi_value < 70:
        return -50
    else:
        return -100


def score_bollinger_bands(bb_data):
    """
    Score Bollinger Bands from -100 to +100

    Logic:
    - Price below lower band: +100 (oversold)
    - Price above upper band: -100 (overbought)
    """
    if bb_data is None:
        return 0

    price = bb_data['current_price']
    upper = bb_data['upper']
    middle = bb_data['middle']
    lower = bb_data['lower']

    if price <= lower:
        return 100
    elif price < middle:
        return 50
    elif price == middle:
        return 0
    elif price < upper:
        return -50
    else:
        return -100


def score_mfi(mfi_value):
    """
    Score MFI indicator from -100 to +100

    Logic:
    - MFI < 20: +100 (oversold)
    - MFI > 80: -100 (overbought)
    """
    if mfi_value is None or np.isnan(mfi_value):
        return 0

    if mfi_value < 20:
        return 100
    elif mfi_value < 40:
        return 50
    elif mfi_value < 60:
        return 0
    elif mfi_value < 80:
        return -50
    else:
        return -100


def calculate_combined_score(macd_score, rsi_score, bb_score, mfi_score):
    """
    Calculate combined sentiment score with 25% weight for each indicator

    Returns:
        tuple: (combined_score, sentiment_label)
    """
    combined = (macd_score * 0.25 + rsi_score * 0.25 + 
                bb_score * 0.25 + mfi_score * 0.25)

    if combined >= 60:
        sentiment = "Strong Bullish"
    elif combined >= 30:
        sentiment = "Bullish"
    elif combined > -30:
        sentiment = "Neutral"
    elif combined > -60:
        sentiment = "Bearish"
    else:
        sentiment = "Strong Bearish"

    return combined, sentiment

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

def connect_to_database(db_path):
    """Connect to SQLite database"""
    try:
        conn = sqlite3.connect(db_path)
        print(f"✓ Successfully connected to {db_path}")
        return conn
    except sqlite3.Error as e:
        print(f"✗ Error connecting to database: {e}")
        return None


def get_stock_list(conn):
    """Get list of unique stock tickers from database"""
    try:
        query = "SELECT DISTINCT ticker FROM prices ORDER BY ticker"
        df = pd.read_sql_query(query, conn)
        return df['ticker'].tolist()
    except Exception as e:
        print(f"Error retrieving stock list: {e}")
        return []


def get_stock_data(conn, ticker):
    """Get historical data for a specific stock"""
    try:
        query = """
        SELECT date, open, high, low, close, volume
        FROM prices
        WHERE ticker = ?
        ORDER BY date ASC
        """
        df = pd.read_sql_query(query, conn, params=(ticker,))
        df['date'] = pd.to_datetime(df['date'])
        return df
    except Exception as e:
        print(f"  Error loading data for {ticker}: {e}")
        return None

# ============================================================================
# MAIN ANALYSIS FUNCTION
# ============================================================================

def analyze_stock(conn, ticker):
    """
    Analyze a single stock and return all indicators and scores

    Returns:
        dict with all analysis results or None if error
    """
    try:
        # Get data
        df = get_stock_data(conn, ticker)

        if df is None or len(df) < Config.MIN_DATA_POINTS:
            print(f"  ⚠ {ticker}: Insufficient data (need {Config.MIN_DATA_POINTS} days)")
            return None

        # Calculate indicators
        macd_data = calculate_macd(df)
        rsi_value = calculate_rsi(df)
        bb_data = calculate_bollinger_bands(df)
        mfi_value = calculate_mfi(df)

        # Calculate scores
        macd_score = score_macd(macd_data)
        rsi_score = score_rsi(rsi_value)
        bb_score = score_bollinger_bands(bb_data)
        mfi_score = score_mfi(mfi_value)

        # Combined score
        combined_score, sentiment = calculate_combined_score(
            macd_score, rsi_score, bb_score, mfi_score
        )

        # Prepare result
        result = {
            'ticker': ticker,
            'combined_score': combined_score,
            'sentiment': sentiment,
            'macd_line': macd_data['macd_line'] if macd_data else None,
            'macd_signal': macd_data['signal_line'] if macd_data else None,
            'macd_histogram': macd_data['histogram'] if macd_data else None,
            'macd_score': macd_score,
            'rsi_value': rsi_value,
            'rsi_score': rsi_score,
            'bb_upper': bb_data['upper'] if bb_data else None,
            'bb_middle': bb_data['middle'] if bb_data else None,
            'bb_lower': bb_data['lower'] if bb_data else None,
            'bb_current': bb_data['current_price'] if bb_data else None,
            'bb_score': bb_score,
            'mfi_value': mfi_value,
            'mfi_score': mfi_score,
            'last_close': df['close'].iloc[-1],
            'last_date': df['date'].iloc[-1].strftime('%Y-%m-%d')
        }

        print(f"  ✓ {ticker}: {sentiment} (Score: {combined_score:.1f})")
        return result

    except Exception as e:
        print(f"  ✗ {ticker}: Analysis failed - {e}")
        return None

# ============================================================================
# REPORT GENERATION
# ============================================================================

def generate_report(results):
    """Generate and display formatted report"""

    if not results:
        print("No results to report.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(results)

    # Sort by combined score (descending)
    df = df.sort_values('combined_score', ascending=False)

    # Display header
    print("\n" + "="*80)
    print("STOCK SENTIMENT ANALYSIS REPORT".center(80))
    print("="*80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Total Stocks Analyzed: {len(df)}")
    print("="*80)

    # Display table
    print(f"\n{'Ticker':<10} {'Combined':<12} {'Sentiment':<18} {'MACD':<8} {'RSI':<8} {'BB':<8} {'MFI':<8}")
    print(f"{'':10} {'Score':<12} {'':<18} {'Score':<8} {'Score':<8} {'Score':<8} {'Score':<8}")
    print("-"*80)

    for _, row in df.iterrows():
        print(f"{row['ticker']:<10} {row['combined_score']:>6.1f}      "
              f"{row['sentiment']:<18} {row['macd_score']:>5.0f}    "
              f"{row['rsi_score']:>5.0f}    {row['bb_score']:>5.0f}    "
              f"{row['mfi_score']:>5.0f}")

    print("-"*80)

    # Summary statistics
    print("\nSUMMARY:")
    sentiment_counts = df['sentiment'].value_counts()
    total = len(df)

    for sentiment in ["Strong Bullish", "Bullish", "Neutral", "Bearish", "Strong Bearish"]:
        count = sentiment_counts.get(sentiment, 0)
        pct = (count / total * 100) if total > 0 else 0
        print(f"  {sentiment:<18}: {count:>3} stocks ({pct:>5.1f}%)")

    # Export to CSV
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"techincals_report_{timestamp}.csv"
    
    # Ensure directory exists
    os.makedirs(Config.REPORT_DIR, exist_ok=True)
    report_path = os.path.join(Config.REPORT_DIR, filename)
    
    df.to_csv(report_path, index=False)
    print(f"\n✓ Report exported to: {report_path}")

    return df

# ============================================================================
# MAIN EXECUTION
# ============================================================================

def main():
    """Main execution function"""

    print("\n" + "="*80)
    print("STOCK TECHNICAL ANALYSIS & SENTIMENT SCORING TOOL".center(80))
    print("="*80 + "\n")

    # Connect to database
    conn = connect_to_database(Config.DB_PATH)
    if conn is None:
        print("\n✗ Cannot proceed without database connection.")
        return

    # Get stock list
    print("\nRetrieving stock list...")
    tickers = get_stock_list(conn)

    if not tickers:
        print("✗ No stocks found in database.")
        conn.close()
        return

    print(f"✓ Found {len(tickers)} stocks to analyze\n")

    # Analyze each stock
    print("Analyzing stocks...")
    print("-"*80)
    results = []

    for ticker in tickers:
        result = analyze_stock(conn, ticker)
        if result:
            results.append(result)

    print("-"*80)

    # Generate report
    if results:
        generate_report(results)
    else:
        print("\n✗ No successful analyses to report.")

    # Close database connection
    conn.close()
    print("\n✓ Analysis complete!\n")


if __name__ == "__main__":
    main()
