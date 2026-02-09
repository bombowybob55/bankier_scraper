"""
Configuration File for Stock Analysis Tool
==========================================
Modify these parameters to customize the analysis
"""

# ============================================================================
# DATABASE CONFIGURATION
# ============================================================================

import os

# Path to your SQLite database file
# This resolves to the project root where historical_data.db is located
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, "historical_data.db")

# Output directory for reports
OUTPUT_DIR = os.path.join(BASE_DIR, "Reports", "Technical")

# ============================================================================
# TECHNICAL INDICATOR PARAMETERS
# ============================================================================

# MACD Settings
MACD_FAST = 12      # Fast EMA period (typically 12)
MACD_SLOW = 26      # Slow EMA period (typically 26)
MACD_SIGNAL = 9     # Signal line period (typically 9)

# RSI Settings
RSI_PERIOD = 14     # RSI calculation period (typically 14)

# Bollinger Bands Settings
BB_PERIOD = 20      # Moving average period (typically 20)
BB_STD = 2          # Standard deviation multiplier (typically 2)

# Money Flow Index Settings
MFI_PERIOD = 14     # MFI calculation period (typically 14)

# ============================================================================
# SCORING THRESHOLDS
# ============================================================================

# RSI Thresholds
RSI_OVERSOLD = 30       # Below this is considered oversold
RSI_OVERBOUGHT = 70     # Above this is considered overbought

# MFI Thresholds
MFI_OVERSOLD = 20       # Below this is considered oversold
MFI_OVERBOUGHT = 80     # Above this is considered overbought

# Combined Score Sentiment Thresholds
STRONG_BULLISH_THRESHOLD = 60    # Score >= 60
BULLISH_THRESHOLD = 30           # Score >= 30
BEARISH_THRESHOLD = -30          # Score <= -30
STRONG_BEARISH_THRESHOLD = -60   # Score <= -60

# ============================================================================
# DATA VALIDATION
# ============================================================================

# Minimum number of data points required for analysis
MIN_DATA_POINTS = 30

# ============================================================================
# DISPLAY OPTIONS
# ============================================================================

# Show detailed indicator values in console
SHOW_DETAILED_VALUES = True

# Number of decimal places for rounding
DECIMAL_PLACES = 2
