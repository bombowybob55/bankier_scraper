<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

# Product Requirements Document (PRD)

## Dow Jones Industrial Average Fundamentals Database


***

## 1. Project Overview

### 1.1 Project Name

DJIA Fundamentals Database Builder (`fundaments_djia.py`)

### 1.2 Purpose

Build a comprehensive database of fundamental financial metrics for companies in the Dow Jones Industrial Average (DJIA), sourced from Yahoo Finance, to enable valuation analysis and investment decision-making.

### 1.3 Scope

- Extract company list from existing database (`historical_data_zagr.py`)
- Retrieve fundamental data from Yahoo Finance API
- Calculate key financial metrics and ratios
- Store data in structured format for analysis

***

## 2. Data Source

### 2.1 Input Source

- **Primary Database**: `historical_data_zagr.py` (contains DJIA company tickers)
- **Data Provider**: Yahoo Finance (via `yfinance` library)


### 2.2 Target Companies

All companies present in the DJIA index as stored in `historical_data_zagr.py`

***

## 3. Data Requirements

### 3.1 Company Identification

| Field | Description | Source |
| :-- | :-- | :-- |
| Ticker Symbol | Stock ticker (e.g., AAPL) | `historical_data_zagr.py` |
| Company Name | Full company name | Yahoo Finance |
| Industry | Industry classification | Yahoo Finance |

### 3.2 Raw Data Fields to Download

#### Historical Data

| Field | Description | Period | Yahoo Finance Field |
| :-- | :-- | :-- | :-- |
| Last Year EPS | Earnings per share | 2025 (actual) | `earnings.financials` or `info['trailingEps']` |
| Shares Outstanding | Number of shares | Current | `info['sharesOutstanding']` |
| Market Cap | Market capitalization | Current | `info['marketCap']` |
| Net Debt | Total Debt - Cash | Current | `info['totalDebt']` - `info['totalCash']` |
| Last Year EBITDA | Earnings before interest, taxes, depreciation, amortization | 2025 | `financials` or `info['ebitda']` |

#### Forward Estimates (Analyst Consensus)

| Field | Description | Period | Yahoo Finance Field |
| :-- | :-- | :-- | :-- |
| 2026 EPS Estimate | Analyst consensus EPS | Current Year (2026) | `info['forwardEps']` or `earnings_estimate` |
| 2027 EPS Estimate | Analyst consensus EPS | Next Year (2027) | `earnings_estimate` (next fiscal year) |
| 2026 Revenue Estimate | Analyst consensus Revenue | Current Year (2026) | `revenue_estimate` |
| 2027 Revenue Estimate | Analyst consensus Revenue | Next Year (2027) | `revenue_estimate` (next fiscal year) |
| Current Quarter EPS Estimate | Analyst consensus EPS | Current Quarter | `earnings_estimate` (quarterly) |
| Same Quarter Last Year EPS | Actual EPS | Q1 2025 (or equivalent) | `quarterly_earnings` |


***

## 4. Calculated Metrics

### 4.1 Calculations Required

| Metric | Formula | Description |
| :-- | :-- | :-- |
| **P/E Ratio (2026)** | `Market Cap / (EPS_2026 × Shares Outstanding)` | Forward Price-to-Earnings based on 2026 estimate |
| **EPS CAGR (2025-2027)** | `((EPS_2027 / EPS_2025)^(1/2) - 1) × 100%` | Compound annual growth rate of EPS |
| **Revenue CAGR (2025-2027)** | `((Revenue_2027 / Revenue_2025)^(1/2) - 1) × 100%` | Compound annual growth rate of Revenue |
| **Quarterly EPS Growth** | `((Q_Current_Est / Q_LastYear_Actual) - 1) × 100%` | Year-over-year quarterly EPS growth |
| **Enterprise Value (EV)** | `Market Cap + Net Debt` | Total company valuation |
| **EV/EBITDA** | `EV / EBITDA_2025` | Enterprise value to EBITDA multiple |

### 4.2 Calculation Notes

- All growth rates should be expressed as percentages
- Handle division by zero or missing data gracefully
- CAGR formula: `((End Value / Start Value)^(1/n) - 1) × 100` where n = number of years

***

## 5. Technical Specifications

### 5.1 File Structure

```
fundaments_djia.py
├── Import dependencies (yfinance, pandas, etc.)
├── Load companies from historical_data_zagr.py
├── Data retrieval functions
├── Calculation functions
├── Main execution logic
└── Data export/storage
```


### 5.2 Required Python Libraries

- `yfinance` - Yahoo Finance API access
- `pandas` - Data manipulation
- `numpy` - Numerical calculations
- Standard library imports from `historical_data_zagr.py`


### 5.3 Output Format

**Recommended**: Pandas DataFrame with columns:

```python
columns = [
    'ticker',
    'company_name',
    'industry',
    'shares_outstanding',
    'market_cap',
    'net_debt',
    'eps_2025_actual',
    'eps_2026_estimate',
    'eps_2027_estimate',
    'revenue_2026_estimate',
    'revenue_2027_estimate',
    'current_quarter_eps_estimate',
    'last_year_same_quarter_eps',
    'ebitda_2025',
    'pe_ratio_2026',
    'eps_cagr_2025_2027',
    'revenue_cagr_2025_2027',
    'quarterly_eps_growth',
    'enterprise_value',
    'ev_ebitda'
]
```


***

## 6. Implementation Approach

### 6.1 Step-by-Step Process

**Step 1**: Load Company List

```python
# Import or read company tickers from historical_data_zagr.py
# Expected format: List of ticker symbols (e.g., ['AAPL', 'MSFT', ...])
```

**Step 2**: Data Retrieval Function

```python
def get_fundamental_data(ticker):
    """
    Retrieve all required fundamental data for a single ticker
    Returns: dict with all raw data fields
    """
    # Use yfinance to download data
    # Extract required fields from ticker.info, ticker.financials, etc.
```

**Step 3**: Calculation Function

```python
def calculate_metrics(raw_data):
    """
    Calculate all derived metrics from raw data
    Returns: dict with calculated fields
    """
    # Implement formulas from section 4.1
```

**Step 4**: Main Loop

```python
# Iterate through all companies
# Collect data and calculations
# Store in DataFrame
```

**Step 5**: Export Results

```python
# Save to CSV or pickle for later use
# Display summary statistics
```


### 6.2 Error Handling

- **Missing data**: Set value to `None` or `np.nan` with warning message
- **API failures**: Retry mechanism with exponential backoff
- **Invalid calculations**: Catch division errors, log issues
- **Quarter matching**: Use fiscal quarter mapping if calendar quarters don't align

***

## 7. Data Quality Considerations

### 7.1 Validation Checks

- [ ] All tickers successfully retrieved
- [ ] No negative market caps or shares outstanding
- [ ] EPS estimates are reasonable (not extreme outliers)
- [ ] Quarterly data matches fiscal calendar
- [ ] CAGR calculations are within reasonable bounds (-100% to +500%)


### 7.2 Known Limitations

1. **Yahoo Finance API limitations**:
    - Some analyst estimates may not be available for all companies
    - Quarterly data may have reporting lag
    - Free tier may have rate limits
2. **Data accuracy**:
    - Analyst estimates are projections and may change
    - Net debt calculation requires both debt and cash data
    - Industry classification may vary by provider
3. **Temporal considerations**:
    - Current date: February 9, 2026
    - Q1 2026 data may not be finalized
    - 2025 full-year data should be available

***

## 8. Success Criteria

### 8.1 Functional Requirements ✓

- [ ] Successfully extracts all company tickers from `historical_data_zagr.py`
- [ ] Downloads all required data fields from Yahoo Finance
- [ ] Calculates all 6 derived metrics correctly
- [ ] Produces structured output (DataFrame or CSV)
- [ ] Handles missing data gracefully


### 8.2 Data Completeness

- **Target**: ≥90% data completeness across all fields
- **Minimum**: ≥80% of companies have complete fundamental data


### 8.3 Performance

- **Execution time**: <5 minutes for all DJIA companies (~30 stocks)
- **Memory usage**: <500 MB

***

## 9. User Guide (For No-Code Learners)

### 9.1 How to Use the Script

**Simple Execution**:

```python
# Just run the script:
python fundaments_djia.py

# Output will be saved as: djia_fundamentals.csv
```

**What You'll Get**:

- A CSV file with all fundamental data
- Console output showing progress
- Summary statistics of the dataset


### 9.2 Understanding the Output

**Key Metrics Explained**:

- **P/E Ratio**: Lower = cheaper relative to earnings (typical range: 10-30)
- **EPS CAGR**: Higher = faster earnings growth (>15% is strong)
- **EV/EBITDA**: Lower = potentially undervalued (typical range: 8-15)
- **Quarterly Growth**: Positive = beating last year's performance

***

## 10. Future Enhancements (Out of Scope for V1)

- Add dividend yield and payout ratio
- Include price momentum indicators
- Implement automated data refresh
- Build visualization dashboard
- Add peer comparison within industries
- Historical trend analysis

***

## 11. Appendix

### 11.1 Yahoo Finance Field Mapping Reference

```python
# Key yfinance attributes:
ticker = yf.Ticker("AAPL")

# info dictionary keys:
ticker.info['industry']              # Industry
ticker.info['marketCap']             # Market Cap
ticker.info['sharesOutstanding']     # Shares Outstanding
ticker.info['totalDebt']             # Total Debt
ticker.info['totalCash']             # Cash
ticker.info['forwardEps']            # Forward EPS estimate

# Other attributes:
ticker.earnings                      # Annual earnings
ticker.quarterly_earnings            # Quarterly earnings
ticker.financials                    # Financial statements
ticker.earnings_estimate             # Analyst estimates (if available)
```


### 11.2 Fiscal vs Calendar Quarters

Note: Some companies use fiscal years that don't align with calendar years. The script should detect fiscal year-end and map quarters accordingly.

***

## Document Control

| Version | Date | Author | Changes |
| :-- | :-- | :-- | :-- |
| 1.0 | Feb 9, 2026 | PRD Generator | Initial version |

**Status**: Ready for Development
**Priority**: High
**Complexity**: Medium

***

**Next Steps**:

1. Review and approve PRD
2. Begin implementation of `fundaments_djia.py`
3. Test with subset of tickers first
4. Validate calculations against known values
5. Full deployment
