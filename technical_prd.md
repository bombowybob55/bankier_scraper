<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Product Requirements Document (PRD)

## Stock Technical Analysis \& Sentiment Scoring Tool


***

## 1. Overview

### 1.1 Product Purpose

A Python script that analyzes historical stock data from a SQLite database, calculates key technical indicators, generates a combined sentiment score, and produces a comprehensive report showing bullish/bearish signals for each stock.

### 1.2 Target User

No-code learners and beginner analysts who want to understand stock market sentiment through automated technical analysis without manual calculations.

### 1.3 Success Criteria

- Successfully processes all stocks in the database
- Accurately calculates 4 technical indicators
- Generates clear, actionable sentiment scores
- Produces an easy-to-read report table

***

## 2. Technical Requirements

### 2.1 Input Requirements

**Database Specifications:**

- **File:** `historical_data.db` (SQLite database)
- **Data Coverage:** 2 years of daily historical data
- **Required Fields per Stock:**
    - Date (timestamp/date format)
    - Open price (float)
    - High price (float)
    - Low price (float)
    - Close price (float)
    - Volume (integer)

**Expected Database Schema:**

```sql
-- Example table structure (script should handle variations)
TABLE: stock_data
- ticker (TEXT) - Stock symbol identifier
- date (DATE/TEXT) - Trading date
- open (REAL) - Opening price
- high (REAL) - Highest price
- low (REAL) - Lowest price
- close (REAL) - Closing price
- volume (INTEGER) - Trading volume
```


### 2.2 Technical Indicators Specifications

The script must calculate the following indicators for **the last recorded day** for each stock:

#### 2.2.1 MACD (Moving Average Convergence Divergence)

- **Parameters:** 12-period EMA, 26-period EMA, 9-period Signal line
- **Calculation:**
    - MACD Line = EMA(12) - EMA(26)
    - Signal Line = EMA(9) of MACD Line
    - MACD Histogram = MACD Line - Signal Line
- **Bullish Signal:** MACD Line > Signal Line (or positive histogram)
- **Bearish Signal:** MACD Line < Signal Line (or negative histogram)
- **Output:** MACD value, Signal value, and interpreted signal


#### 2.2.2 RSI (Relative Strength Index)

- **Parameters:** 14-day period
- **Calculation:** RSI = 100 - (100 / (1 + RS)), where RS = Average Gain / Average Loss
- **Bullish Signal:** RSI < 30 (oversold, potential reversal up)
- **Neutral-Bullish:** 30 ≤ RSI < 50
- **Neutral-Bearish:** 50 < RSI ≤ 70
- **Bearish Signal:** RSI > 70 (overbought, potential reversal down)
- **Output:** RSI value and interpreted signal


#### 2.2.3 Bollinger Bands

- **Parameters:** 20-day moving average, 2 standard deviations
- **Calculation:**
    - Middle Band = 20-day SMA
    - Upper Band = Middle Band + (2 × 20-day standard deviation)
    - Lower Band = Middle Band - (2 × 20-day standard deviation)
- **Bullish Signal:** Current price near or below Lower Band
- **Bearish Signal:** Current price near or above Upper Band
- **Neutral:** Price between bands
- **Output:** Upper Band, Middle Band, Lower Band, Current Price Position


#### 2.2.4 MFI (Money Flow Index)

- **Parameters:** 14-day period
- **Calculation:**
    - Typical Price = (High + Low + Close) / 3
    - Money Flow = Typical Price × Volume
    - Money Flow Ratio = 14-day Positive Money Flow / 14-day Negative Money Flow
    - MFI = 100 - (100 / (1 + Money Flow Ratio))
- **Bullish Signal:** MFI < 20 (oversold)
- **Neutral-Bullish:** 20 ≤ MFI < 50
- **Neutral-Bearish:** 50 < MFI ≤ 80
- **Bearish Signal:** MFI > 80 (overbought)
- **Output:** MFI value and interpreted signal


### 2.3 Combined Indicator Methodology

#### 2.3.1 Scoring System

Each technical indicator receives a score from -100 to +100:

- **-100:** Strong Bearish
- **-50:** Bearish
- **0:** Neutral
- **+50:** Bullish
- **+100:** Strong Bullish


#### 2.3.2 Individual Indicator Scoring Rules

**MACD Scoring:**

- Histogram > 0 and increasing: +100
- Histogram > 0 and decreasing: +50
- Histogram = 0: 0
- Histogram < 0 and decreasing: -100
- Histogram < 0 and increasing: -50

**RSI Scoring:**

- RSI < 30: +100 (oversold, bullish reversal)
- 30 ≤ RSI < 40: +50
- 40 ≤ RSI < 60: 0
- 60 ≤ RSI < 70: -50
- RSI ≥ 70: -100 (overbought, bearish reversal)

**Bollinger Bands Scoring:**

- Price below Lower Band: +100
- Price between Lower Band and Middle: +50
- Price at Middle Band: 0
- Price between Middle and Upper Band: -50
- Price above Upper Band: -100

**MFI Scoring:**

- MFI < 20: +100 (oversold)
- 20 ≤ MFI < 40: +50
- 40 ≤ MFI < 60: 0
- 60 ≤ MFI < 80: -50
- MFI ≥ 80: -100 (overbought)


#### 2.3.3 Combined Score Calculation

```
Combined Score = (MACD_Score × 0.25) + (RSI_Score × 0.25) + (BB_Score × 0.25) + (MFI_Score × 0.25)
```

**Weight Distribution:** Each indicator contributes 25% to the final score.

#### 2.3.4 Final Sentiment Classification

- **Strong Bullish:** Combined Score ≥ 60
- **Bullish:** 30 ≤ Combined Score < 60
- **Neutral:** -30 < Combined Score < 30
- **Bearish:** -60 < Combined Score ≤ -30
- **Strong Bearish:** Combined Score ≤ -60

***

## 3. Functional Requirements

### 3.1 Core Functions

#### Function 1: Database Connection

```python
def connect_to_database(db_path)
```

- Open connection to `historical_data.db`
- Validate database exists and is accessible
- Return connection object
- **Error Handling:** Exit gracefully if database not found


#### Function 2: Data Extraction

```python
def get_stock_list(connection)
```

- Retrieve unique list of all stock tickers
- Return list of tickers

```python
def get_stock_data(connection, ticker)
```

- Extract all historical data for a specific stock
- Sort by date ascending
- Return pandas DataFrame


#### Function 3: Technical Indicator Calculations

```python
def calculate_macd(df)
```

- Calculate MACD line, Signal line, Histogram
- Return values for last day

```python
def calculate_rsi(df)
```

- Calculate 14-day RSI
- Return value for last day

```python
def calculate_bollinger_bands(df)
```

- Calculate Upper, Middle, Lower bands
- Return bands and current price position for last day

```python
def calculate_mfi(df)
```

- Calculate 14-day Money Flow Index
- Return value for last day


#### Function 4: Scoring System

```python
def score_indicator(indicator_name, value, additional_params)
```

- Apply scoring rules for each indicator
- Return score (-100 to +100)

```python
def calculate_combined_score(macd_score, rsi_score, bb_score, mfi_score)
```

- Apply 25% weight to each indicator
- Return combined score and sentiment label


#### Function 5: Report Generation

```python
def generate_report(results)
```

- Create formatted table with all stocks
- Include: Ticker, Combined Score, Sentiment, MACD, RSI, BB, MFI
- Sort by Combined Score (descending)
- Export to CSV and display in console


### 3.2 Data Validation

- Verify minimum data points available (at least 26 days for MACD)
- Handle missing data gracefully
- Skip stocks with insufficient data and log warning

***

## 4. Output Requirements

### 4.1 Report Format

**Console Output (Table View):**

```
===== STOCK SENTIMENT ANALYSIS REPORT =====
Date: [Last recorded date in database]
Total Stocks Analyzed: [N]

┌──────────┬──────────────┬────────────────┬────────┬───────┬──────┬───────┐
│ Ticker   │ Combined     │ Sentiment      │ MACD   │ RSI   │ BB   │ MFI   │
│          │ Score        │                │ Score  │ Score │ Score│ Score │
├──────────┼──────────────┼────────────────┼────────┼───────┼──────┼───────┤
│ AAPL     │ +75.00       │ Strong Bullish │ +100   │ +50   │ +100 │ +50   │
│ GOOGL    │ +45.00       │ Bullish        │ +50    │ +50   │ +50  │ +30   │
│ MSFT     │ -15.00       │ Neutral        │ -50    │ 0     │ -10  │ 0     │
│ TSLA     │ -65.00       │ Strong Bearish │ -100   │ -70   │ -50  │ -40   │
└──────────┴──────────────┴────────────────┴────────┴───────┴──────┴───────┘
```

**CSV Export:** `stock_sentiment_report_[YYYYMMDD].csv`

Columns:

1. Ticker
2. Combined_Score
3. Sentiment
4. MACD_Value (actual MACD line value)
5. MACD_Signal (actual signal line value)
6. MACD_Score
7. RSI_Value
8. RSI_Score
9. BB_Upper
10. BB_Middle
11. BB_Lower
12. BB_Current_Price
13. BB_Score
14. MFI_Value
15. MFI_Score
16. Last_Close_Price
17. Last_Date

### 4.2 Additional Outputs

**Summary Statistics (Console):**

```
SUMMARY:
- Strong Bullish: [N] stocks ([X]%)
- Bullish: [N] stocks ([X]%)
- Neutral: [N] stocks ([X]%)
- Bearish: [N] stocks ([X]%)
- Strong Bearish: [N] stocks ([X]%)
```

**Log File:** `analysis_log.txt`

- Timestamp of analysis
- Database path and records processed
- Any warnings or errors encountered
- Stocks skipped (with reason)

***

## 5. Technical Stack

### 5.1 Required Libraries

```python
# Core libraries
import sqlite3          # Database connection
import pandas as pd     # Data manipulation
import numpy as np      # Numerical calculations

# Technical indicators (choose one approach):
# Option 1: Use specialized library
import ta               # Technical Analysis library

# Option 2: Manual calculation (for learning)
# All indicators calculated from scratch using pandas

# Reporting
from tabulate import tabulate  # Console table formatting
import csv              # CSV export
from datetime import datetime  # Timestamp handling
```


### 5.2 Installation Commands

```bash
pip install pandas numpy ta tabulate
```


***

## 6. Usage Requirements

### 6.1 Command Line Interface

```bash
python stock_analysis.py
```

**Optional Arguments (Future Enhancement):**

```bash
python stock_analysis.py --db path/to/database.db --output reports/
```


### 6.2 Configuration

Create a `config.py` file for easy parameter adjustment:

```python
# config.py
DB_PATH = "historical_data.db"
OUTPUT_DIR = "reports/"

# Technical Indicator Parameters
MACD_FAST = 12
MACD_SLOW = 26
MACD_SIGNAL = 9
RSI_PERIOD = 14
BB_PERIOD = 20
BB_STD = 2
MFI_PERIOD = 14

# Scoring Thresholds (customizable)
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
MFI_OVERSOLD = 20
MFI_OVERBOUGHT = 80
```


***

## 7. Error Handling \& Edge Cases

### 7.1 Error Scenarios

1. **Database not found:** Display error message and exit
2. **Insufficient data:** Skip stock, log warning (need minimum 26 days)
3. **Missing columns:** Validate schema, display helpful error
4. **Calculation errors:** Catch exceptions, mark indicator as "N/A"
5. **Division by zero:** Handle in RSI/MFI calculations with conditional checks

### 7.2 Data Quality Checks

- Verify date column is properly formatted
- Check for null values in OHLCV data
- Ensure volume is non-negative
- Validate price data (High ≥ Low, Close between High/Low)

***

## 8. Performance Requirements

### 8.1 Execution Time

- Target: < 5 seconds for 100 stocks
- Target: < 30 seconds for 1000 stocks


### 8.2 Memory Usage

- Process stocks sequentially to minimize memory footprint
- Clear DataFrame after each stock analysis

***

## 9. Example Workflow

```
1. START
   ↓
2. Connect to historical_data.db
   ↓
3. Get list of all unique stock tickers
   ↓
4. FOR EACH stock:
   a. Load 2 years of historical data
   b. Calculate MACD (last day value)
   c. Calculate RSI (last day value)
   d. Calculate Bollinger Bands (last day values)
   e. Calculate MFI (last day value)
   f. Score each indicator (-100 to +100)
   g. Calculate combined score (25% each)
   h. Determine sentiment label
   i. Store results
   ↓
5. Sort results by Combined Score (descending)
   ↓
6. Display formatted table in console
   ↓
7. Export to CSV with timestamp
   ↓
8. Display summary statistics
   ↓
9. END
```


***

## 10. Acceptance Criteria

### 10.1 Must Have (MVP)

- ✅ Successfully connects to SQLite database
- ✅ Calculates all 4 technical indicators correctly
- ✅ Generates combined score with 25% weighting
- ✅ Produces console table report
- ✅ Exports CSV file with all details
- ✅ Handles basic errors gracefully


### 10.2 Should Have

- ✅ Summary statistics display
- ✅ Log file generation
- ✅ Configurable parameters via config file
- ✅ Data validation checks


### 10.3 Nice to Have (Future Enhancements)

- 📊 Graphical output (charts for each stock)
- 📧 Email report delivery
- 🔄 Automated daily scheduling
- 📈 Historical trend comparison
- 🎯 Alert system for strong signals
- 🌐 Web dashboard interface

***

## 11. Testing Requirements

### 11.1 Unit Tests

- Test each indicator calculation with known values
- Verify scoring logic for boundary conditions
- Test database connection handling


### 11.2 Integration Tests

- Run on sample database with 5-10 stocks
- Verify CSV output format
- Confirm all stocks processed


### 11.3 Validation

- Compare indicator calculations with trading platform (e.g., TradingView)
- Verify mathematical accuracy of combined scoring

***

## 12. Documentation Requirements

### 12.1 Code Documentation

- Docstrings for all functions
- Inline comments for complex calculations
- Type hints for function parameters


### 12.2 User Documentation

- README.md with:
    - Installation instructions
    - Usage examples
    - Parameter explanations
    - Interpretation guide for beginners
    - FAQ section


### 12.3 Beginner's Guide

Include explanations:

- What each indicator measures
- How to interpret sentiment scores
- Limitations of technical analysis
- Risk warnings

***

## 13. Deliverables

1. ✅ `stock_analysis.py` - Main script
2. ✅ `config.py` - Configuration file
3. ✅ `requirements.txt` - Dependencies list
4. ✅ `README.md` - User documentation
5. ✅ `example_output.csv` - Sample report
6. ✅ `INTERPRETATION_GUIDE.md` - Beginner's guide to results

***

## 14. Timeline (Suggested for Development)

- **Week 1:** Database connection + data extraction functions
- **Week 2:** Individual indicator calculations
- **Week 3:** Scoring system + combined indicator
- **Week 4:** Report generation + CSV export
- **Week 5:** Error handling + testing + documentation

***

## 15. Success Metrics

- **Accuracy:** Indicator calculations match industry standards
- **Reliability:** Handles 99% of stocks without errors
- **Usability:** Beginner can run script and understand output
- **Performance:** Processes 500 stocks in under 1 minute

***

**Document Version:** 1.0
**Created:** February 4, 2026
**Status:** Ready for Development

This PRD provides a complete blueprint for building your stock technical analysis tool. Each section is designed to guide a no-code learner through understanding what needs to be built, while providing developers with exact specifications for implementation.

