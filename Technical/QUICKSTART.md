# 🚀 QUICK START GUIDE

## Step-by-Step Instructions for Complete Beginners

### Step 1: Install Python
If you don't have Python installed:
- Visit: https://www.python.org/downloads/
- Download Python 3.8 or higher
- During installation, CHECK the box "Add Python to PATH"

### Step 2: Open Terminal/Command Prompt
- **Windows:** Press `Win + R`, type `cmd`, press Enter
- **Mac:** Press `Cmd + Space`, type `terminal`, press Enter
- **Linux:** Press `Ctrl + Alt + T`

### Step 3: Navigate to Project Folder
```bash
cd path/to/your/stock-analysis-folder
```

### Step 4: Install Dependencies
```bash
pip install -r requirements.txt
```

Expected output:
```
Successfully installed pandas-2.x.x numpy-1.x.x tabulate-0.x.x
```

### Step 5: Create Sample Database (for testing)
```bash
python create_sample_database.py
```

This creates `historical_data.db` with sample stock data.

### Step 6: Run the Analysis
```bash
python stock_analysis.py
```

You should see:
```
================================================================================
           STOCK TECHNICAL ANALYSIS & SENTIMENT SCORING TOOL
================================================================================

✓ Successfully connected to historical_data.db

Retrieving stock list...
✓ Found 5 stocks to analyze

Analyzing stocks...
--------------------------------------------------------------------------------
  ✓ AAPL: Bullish (Score: 45.0)
  ✓ GOOGL: Neutral (Score: -5.0)
  ...
```

### Step 7: View Results
- **Console:** Results are displayed in your terminal
- **CSV File:** Open `stock_sentiment_report_[timestamp].csv` in Excel

---

## Using Your Own Database

If you have real stock data:

1. **Replace** `historical_data.db` with your database
2. **Ensure** your database has this structure:
   ```
   Table: stock_data
   Columns: ticker, date, open, high, low, close, volume
   ```
3. Run: `python stock_analysis.py`

---

## Troubleshooting

### "Python is not recognized..."
- Python not installed or not in PATH
- Reinstall Python and check "Add to PATH"

### "No module named 'pandas'"
- Dependencies not installed
- Run: `pip install -r requirements.txt`

### "Database not found"
- Database file missing
- Run: `python create_sample_database.py` (for test data)
- Or place your `historical_data.db` in the same folder

### "Insufficient data" warnings
- Stock needs 30+ days of data
- Normal for recently added stocks

---

## What to Do Next

1. ✅ Run the analysis on sample data
2. ✅ Open the CSV in Excel and explore
3. ✅ Read `INTERPRETATION_GUIDE.md` to understand results
4. ✅ Try adjusting parameters in `config.py`
5. ✅ Get real historical data and analyze actual stocks

---

## Need Help?

1. Read the comments in `stock_analysis.py` - they explain everything
2. Check `README.md` for detailed documentation
3. Review `INTERPRETATION_GUIDE.md` to understand indicators

Happy analyzing! 📊
