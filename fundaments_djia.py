
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import time
import os
import sys

# Add the directory containing kursy_zagr.py to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from kursy_zagr import TICKERS
except ImportError:
    print("Error: Could not import TICKERS from kursy_zagr.py")
    sys.exit(1)

# Configuration
OUTPUT_FILE = "djia_fundamentals.csv"
CURRENT_YEAR = datetime.datetime.now().year

def get_fundamental_data(ticker_symbol):
    """
    Retrieve all required fundamental data for a single ticker
    """
    print(f"Fetching data for {ticker_symbol}...", end=" ", flush=True)
    try:
        ticker = yf.Ticker(ticker_symbol)
        info = ticker.info
        
        # Helper to safely get value from dict or None
        def get_val(key, default=None):
            return info.get(key, default)

        data = {}
        data['ticker'] = ticker_symbol
        data['company_name'] = get_val('longName')
        data['industry'] = get_val('industry')
        data['shares_outstanding'] = get_val('sharesOutstanding')
        data['market_cap'] = get_val('marketCap')
        
        # Debt and Cash
        total_debt = get_val('totalDebt')
        total_cash = get_val('totalCash')
        data['net_debt'] = (total_debt - total_cash) if (total_debt is not None and total_cash is not None) else None
        
        # Earnings - Actuals
        data['eps_2025_actual'] = get_val('trailingEps') # Proxy for "Last Year" (2025)
        
        # Earnings - Estimates (Targeting 2026 and 2027)
        # 0y = Current Fiscal Year (approx 2026), +1y = Next Fiscal Year (approx 2027)
        eps_2026 = None
        eps_2027 = None
        
        try:
            est = ticker.earnings_estimate
            if est is not None and not est.empty:
                # Transpose if needed, or access by index
                # Structure is typically rows: 0q, +1q, 0y, +1y, +5y, -5y
                if '0y' in est.index and 'avg' in est.columns:
                    eps_2026 = est.loc['0y', 'avg']
                if '+1y' in est.index and 'avg' in est.columns:
                    eps_2027 = est.loc['+1y', 'avg']
        except Exception as e_est:
            # Fallback will handle it
            pass
            
        # Fallbacks if earnings_estimate failed or was empty
        if eps_2026 is None:
            eps_2026 = get_val('epsCurrentYear')
            
        if eps_2027 is None:
            eps_2027 = get_val('epsForward') # often next fiscal year estimate
            
        data['eps_2026_estimate'] = eps_2026
        data['eps_2027_estimate'] = eps_2027
        
        data['ebitda_2025'] = get_val('ebitda') # TTM EBITDA usually
        
        print("Done.")
        return data
    except Exception as e:
        print(f"Error: {e}")
        return None

def calculate_metrics(df):
    """
    Calculate derived metrics
    """
    # EV = Market Cap + Net Debt
    df['enterprise_value'] = df['market_cap'] + df['net_debt']
    
    # EV/EBITDA
    df['ev_ebitda'] = df['enterprise_value'] / df['ebitda_2025']
    
    # PE 2026
    # Price = Market Cap / Shares Outstanding
    current_price = df['market_cap'] / df['shares_outstanding']
    df['pe_ratio_2026'] = current_price / df['eps_2026_estimate']
    
    # EPS CAGR (2025-2027)
    # Formula: ((EPS_2027 / EPS_2025)^(1/2) - 1) * 100
    # Use abs for base to avoid complex numbers if EPS is negative, though CAGR on neg earnings is undefined/messy.
    # We will just apply formula where both are positive for safety.
    
    def calculate_cagr(row):
        start = row['eps_2025_actual']
        end = row['eps_2027_estimate']
        if pd.notnull(start) and pd.notnull(end) and start > 0 and end > 0:
            return ((end / start) ** 0.5 - 1) * 100
        return None

    df['eps_cagr_2025_2027'] = df.apply(calculate_cagr, axis=1)

    return df

def main():
    print("Starting DJIA Fundamentals Database Builder...")
    
    all_data = []
    
    # Iterate through all tickers
    for name, ticker in TICKERS.items():
        data = get_fundamental_data(ticker)
        if data:
            all_data.append(data)
        time.sleep(0.5) # Rate limiting
        
    if not all_data:
        print("No data collected.")
        return

    df = pd.DataFrame(all_data)
    
    # Calculate metrics
    print("\nCalculating metrics...")
    df = calculate_metrics(df)
    
    # Define column order (reordering and selecting existing columns)
    cols = [
        'ticker', 'company_name', 'industry', 'market_cap', 'shares_outstanding', 
        'net_debt', 'enterprise_value', 'eps_2025_actual', 'eps_2026_estimate', 'eps_2027_estimate',
        'ebitda_2025', 'pe_ratio_2026', 'eps_cagr_2025_2027', 'ev_ebitda'
    ]
    
    # Filter for columns that actually exist in df
    cols = [c for c in cols if c in df.columns]
    
    df = df[cols]
    
    print(f"\nSaving to {OUTPUT_FILE}...")
    df.to_csv(OUTPUT_FILE, index=False)
    print("Success!")
    print(df.head())

if __name__ == "__main__":
    main()
