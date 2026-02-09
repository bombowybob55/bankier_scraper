import os
import glob
import re
import pandas as pd
from datetime import datetime

def parse_report_file(filepath):
    """
    Parses a single sentiment report file to extract date and sentiment counts.
    """
    data = {
        'date': None,
        'bullish': 0,
        'bearish': 0,
        'neutral': 0
    }
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        for line in lines:
            line = line.strip()
            
            # Extract Date (Old & New format)
            if line.startswith("Data raportu:"):
                date_str = line.split("Data raportu:")[1].strip()
                try:
                    data['date'] = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
            elif line.startswith("Data:"):
                date_str = line.split("Data:")[1].strip()
                try:
                    data['date'] = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
                except ValueError:
                    continue
            
            # Extract Counts (Old format)
            if "Spółek z sentmentem BULLISH/POZYTYWNYM:" in line:
                try:
                    data['bullish'] = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
            elif "Spółek z sentmentem BEARISH/NEGATYWNYM:" in line:
                try:
                    data['bearish'] = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
            elif "Spółek z sentmentem NEUTRALNYM:" in line:
                try:
                    data['neutral'] = int(line.split(":")[-1].strip())
                except ValueError:
                    pass
            
            # Extract Counts (New format: BULLISH: 9 | BEARISH: 2 | NEUTRAL: 51)
            if line.startswith("BULLISH:") and "BEARISH:" in line and "NEUTRAL:" in line:
                parts = line.split("|")
                for part in parts:
                    part = part.strip()
                    if part.startswith("BULLISH:"):
                        data['bullish'] = int(part.split(":")[1].strip())
                    elif part.startswith("BEARISH:"):
                        data['bearish'] = int(part.split(":")[1].strip())
                    elif part.startswith("NEUTRAL:"):
                        data['neutral'] = int(part.split(":")[1].strip())

        if data['date'] is None:
            return None
            
        return data

    except Exception as e:
        print(f"Error parsing {filepath}: {e}")
        return None

def main():
    print("📊 GENERATING SENTIMENT TIMELINE\n")
    
    # Find all report files
    # Find all report files
    # Base directory is one level up from this script (bankier_scraper/)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    reports_dir = os.path.join(base_dir, 'Reports', 'Sentiment')
    
    if not os.path.exists(reports_dir):
        print(f"❌ Reports directory not found: {reports_dir}")
        return

    print(f"Searching for reports in: {reports_dir}")
    
    # Match both old (wig20_mwig40) and new naming conventions
    pattern = os.path.join(reports_dir, "sentiment_report_*.txt")
    report_files = glob.glob(pattern)
    
    if not report_files:
        print("❌ No report files found.")
        return

    print(f"found {len(report_files)} reports.")

    results = []
    for filepath in report_files:
        parsed_data = parse_report_file(filepath)
        if parsed_data:
            results.append(parsed_data)
    
    if not results:
        print("❌ No valid data found in reports.")
        return

    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Sort by date
    df = df.sort_values('date').reset_index(drop=True)
    
    # Format date for display
    df['date_display'] = df['date'].dt.strftime('%Y-%m-%d %H:%M')
    
    # Display results
    print("\nTimeline of Sentiment Analysis Results:")
    print("=" * 60)
    print(f"{'Date':<20} | {'Bullish':<8} | {'Bearish':<8} | {'Neutral':<8}")
    print("-" * 60)
    
    for _, row in df.iterrows():
        print(f"{row['date_display']:<20} | {row['bullish']:<8} | {row['bearish']:<8} | {row['neutral']:<8}")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
