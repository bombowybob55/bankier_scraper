-- Database Schema for Stock Analysis Tool
-- ==========================================
-- Use this to create your database structure

CREATE TABLE IF NOT EXISTS stock_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker TEXT NOT NULL,
    date DATE NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume INTEGER NOT NULL,
    UNIQUE(ticker, date)
);

-- Create index for faster queries
CREATE INDEX IF NOT EXISTS idx_ticker ON stock_data(ticker);
CREATE INDEX IF NOT EXISTS idx_date ON stock_data(date);

-- Example data insertion (replace with your actual data)
-- INSERT INTO stock_data (ticker, date, open, high, low, close, volume)
-- VALUES ('AAPL', '2024-01-01', 150.0, 152.0, 149.0, 151.0, 1000000);
