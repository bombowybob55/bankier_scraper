import sqlite3
import pandas as pd

DB_NAME = "historical_data_zagr.db"

def main():
    # connect to SQLite
    conn = sqlite3.connect(DB_NAME)

    # read all data from prices table into a DataFrame
    query = """
        SELECT
            ticker,
            date,
            open,
            high,
            low,
            close,
            volume
        FROM prices
        ORDER BY ticker, date;
    """
    df = pd.read_sql_query(query, conn)

    conn.close()

    # print as a nice table in terminal
    # show all columns, but limit rows so it fits on screen
    with pd.option_context("display.max_rows", 200,
                           "display.max_columns", None,
                           "display.width", 200):
        print(df)

if __name__ == "__main__":
    main()
