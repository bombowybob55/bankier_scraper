# Stock Technical Analysis & Sentiment Scoring Tool

A Python tool that analyzes historical stock data using technical indicators (MACD, RSI, Bollinger Bands, MFI) and generates a combined sentiment score to identify bullish/bearish signals.

## 📋 Features

- **Automated Technical Analysis**: Calculates 4 key technical indicators for each stock
- **Combined Sentiment Score**: Weighted scoring system (25% each indicator)
- **Comprehensive Reports**: Console display + CSV export with all metrics
- **Beginner-Friendly**: Clear output with sentiment labels
- **Batch Processing**: Analyzes all stocks in your database automatically

## 🚀 Quick Start

### Prerequisites

- Python 3.8 or higher
- SQLite database with historical stock data (2 years recommended)

### Installation

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Prepare your database:**
   - Ensure you have `historical_data.db` in the same folder as the script
   - Database should contain a table (e.g., `stock_data`) with columns:
     - `ticker` (stock symbol)
     - `date` (trading date)
     - `open`, `high`, `low`, `close` (prices)
     - `volume` (trading volume)

3. **Run the analysis:**
```bash
python stock_analysis.py
```

## 📊 What the Tool Does

### Technical Indicators Calculated

1. **MACD (12/26/9)** - Moving Average Convergence Divergence
   - Measures momentum and trend direction
   - Bullish when MACD line crosses above signal line

2. **RSI (14-day)** - Relative Strength Index
   - Identifies overbought (>70) and oversold (<30) conditions
   - Oscillates between 0 and 100

3. **Bollinger Bands (20-day, 2 std)** - Volatility Indicator
   - Shows price volatility and potential reversals
   - Bullish when price touches lower band

4. **MFI (14-day)** - Money Flow Index
   - Volume-weighted RSI
   - Identifies overbought (>80) and oversold (<20) with volume

### Scoring System

Each indicator is scored from **-100 (bearish) to +100 (bullish)**:

- **MACD**: +100 if histogram > 0, -100 if < 0
- **RSI**: +100 if < 30 (oversold), -100 if > 70 (overbought)
- **Bollinger Bands**: +100 if price below lower band, -100 if above upper band
- **MFI**: +100 if < 20 (oversold), -100 if > 80 (overbought)

**Combined Score** = (MACD × 0.25) + (RSI × 0.25) + (BB × 0.25) + (MFI × 0.25)

### Sentiment Classification

- **Strong Bullish**: Score ≥ 60
- **Bullish**: Score 30 to 59
- **Neutral**: Score -29 to 29
- **Bearish**: Score -30 to -59
- **Strong Bearish**: Score ≤ -60

## 📈 Output Example

### Console Output
```
================================================================================
                    STOCK SENTIMENT ANALYSIS REPORT                    
================================================================================
Analysis Date: 2026-02-04 15:30:00
Total Stocks Analyzed: 50
================================================================================

Ticker     Combined     Sentiment          MACD     RSI      BB       MFI     
           Score                           Score    Score    Score    Score   
--------------------------------------------------------------------------------
AAPL       75.0         Strong Bullish     100      100      50       50      
GOOGL      45.0         Bullish            50       50       50       30      
MSFT       -15.0        Neutral            -50      0        -10      0       
TSLA       -65.0        Strong Bearish     -100     -70      -50      -40     
--------------------------------------------------------------------------------

SUMMARY:
  Strong Bullish    :  12 stocks ( 24.0%)
  Bullish           :  15 stocks ( 30.0%)
  Neutral           :  10 stocks ( 20.0%)
  Bearish           :   8 stocks ( 16.0%)
  Strong Bearish    :   5 stocks ( 10.0%)

✓ Report exported to: stock_sentiment_report_20260204_153000.csv
```

### CSV Export

The tool automatically creates a detailed CSV file with columns:
- Ticker, Combined Score, Sentiment
- MACD Line, Signal, Histogram, Score
- RSI Value, Score
- Bollinger Bands (Upper, Middle, Lower, Current Price), Score
- MFI Value, Score
- Last Close Price, Last Date

## ⚙️ Customization

Edit `stock_analysis.py` or create a separate `config.py` to modify:

### Change Indicator Parameters
```python
# In the Config class
MACD_FAST = 12       # Change to 10 for faster signals
RSI_PERIOD = 14      # Change to 7 for more sensitive RSI
BB_PERIOD = 20       # Change to 50 for longer-term bands
MFI_PERIOD = 14      # Change to 10 for more volatile signals
```

### Adjust Scoring Thresholds
```python
RSI_OVERSOLD = 30    # Lower to 20 for stronger oversold signal
RSI_OVERBOUGHT = 70  # Raise to 80 for stronger overbought signal
```

### Change Database Path
```python
DB_PATH = "path/to/your/database.db"
```

## 🎓 Understanding the Results

### For Beginners

**What is sentiment?**
- **Bullish** = Positive outlook, prices may go up
- **Bearish** = Negative outlook, prices may go down
- **Neutral** = No clear direction

**How to use this tool:**
1. Use it as a **screening tool** to identify interesting stocks
2. **Strong Bullish** stocks might be worth investigating for buying
3. **Strong Bearish** stocks might indicate selling pressure
4. Always combine with other research (fundamentals, news, etc.)

**Important Warnings:**
⚠️ This tool uses ONLY technical analysis
⚠️ Past performance does not guarantee future results
⚠️ Always do additional research before trading
⚠️ Consider consulting a financial advisor
⚠️ Only invest money you can afford to lose

## 📁 Project Structure

```
stock-analysis/
│
├── stock_analysis.py          # Main analysis script
├── config.py                  # Configuration parameters (optional)
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── historical_data.db         # Your database (you provide this)
└── stock_sentiment_report_*.csv  # Generated reports
```

## 🔧 Troubleshooting

### "Database not found" error
- Ensure `historical_data.db` is in the same folder as the script
- Or update `DB_PATH` in the Config class

### "Insufficient data" warnings
- Stock needs at least 30 days of data for all indicators
- This is normal for newly listed stocks

### Import errors
- Run: `pip install -r requirements.txt`
- Ensure you're using Python 3.8+

### Calculation errors
- Check your database schema matches expected columns
- Verify data quality (no missing values, correct data types)

## 📚 Database Schema Expected

```sql
CREATE TABLE stock_data (
    ticker TEXT,
    date DATE,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume INTEGER
);
```

## 🔬 Technical Details

### Calculation Methods

**EMA (Exponential Moving Average):**
- Uses pandas `.ewm()` method with `adjust=False`
- Gives more weight to recent prices

**RSI Calculation:**
- Wilder's smoothing method via EMA
- Handles edge cases (division by zero)

**MFI Calculation:**
- Typical Price = (High + Low + Close) / 3
- Money Flow = Typical Price × Volume
- Separates positive/negative flows based on price direction

**Bollinger Bands:**
- Uses simple moving average (SMA)
- Standard deviation calculated over same period

## 📝 Version History

- **v1.0** (2026-02-04): Initial release
  - Core technical indicators
  - Combined scoring system
  - Console + CSV reporting

## 🤝 Contributing

This is a learning tool for beginners. Feel free to:
- Modify calculations for your needs
- Add new indicators
- Improve visualization
- Create your own scoring weights

## 📄 License

This tool is provided as-is for educational purposes.
No warranty or guarantee of accuracy is provided.

## 💡 Tips for No-Code Learners

**Running the script:**
```bash
# Windows Command Prompt
python stock_analysis.py

# Mac/Linux Terminal
python3 stock_analysis.py
```

**Viewing the CSV:**
- Open with Excel, Google Sheets, or any spreadsheet program
- Sort by "combined_score" to see strongest signals first

**Next Steps:**
1. Start with a small database (5-10 stocks)
2. Verify calculations match a trading platform
3. Understand each indicator before trusting the combined score
4. Keep learning about technical analysis!

---

**Questions or Issues?**
Review the code comments - they explain each function in detail.
