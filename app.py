import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import logging
from datetime import datetime, timedelta
import plotly.express as px
import sqlite3
from sqlite3 import Error
import hashlib

# Configuration
DATABASE_PATH = "nepse_stock_data.db"  # Persistent SQLite database
LOG_FILE = "stock_tracker.log"  # Log file for debugging
EXCLUDED_SYMBOLS = [
    "SEF", "NICGF", "CMF1", "NBF2", "SIGS2", "CMF2", "NICBF", "NMB50", 
    # Add all your excluded symbols here
]

# Initialize logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    filename=LOG_FILE,
    filemode="a",
)

class StockDataManager:
    def __init__(self):
        """Initialize database and ensure tables exist."""
        self.conn = self._init_db()
        self._create_tables()

    def _init_db(self):
        """Initialize SQLite database connection."""
        try:
            conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
            conn.execute("PRAGMA journal_mode=WAL")  # Enable Write-Ahead Logging for better performance
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance between safety and speed
            return conn
        except Error as e:
            logging.error(f"Database connection error: {e}")
            raise

    def _create_tables(self):
        """Create database tables if they don't exist."""
        try:
            cursor = self.conn.cursor()
            
            # Table for raw stock data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS raw_stock_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    last_traded_price REAL,
                    percent_change REAL,
                    volume INTEGER,
                    date TEXT NOT NULL,
                    UNIQUE(symbol, date)  -- Prevent duplicate entries
                )
            ''')
            
            # Table for processed data
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    symbol TEXT NOT NULL,
                    performance_score REAL,
                    normalized_change REAL,
                    normalized_volume REAL,
                    date TEXT NOT NULL,
                    UNIQUE(symbol, date)  -- Prevent duplicate entries
                )
            ''')
            
            self.conn.commit()
        except Error as e:
            logging.error(f"Database table creation error: {e}")
            raise

    def save_raw_data(self, df, date):
        """Save raw stock data to the database."""
        try:
            df["date"] = date.strftime("%Y-%m-%d")  # Add date column
            df = df.rename(columns={
                "Stock Symbol": "symbol",
                "Last Traded Price": "last_traded_price",
                "% Change": "percent_change",
                "Volume": "volume",
            })
            df[["symbol", "last_traded_price", "percent_change", "volume", "date"]].to_sql(
                "raw_stock_data", self.conn, if_exists="append", index=False
            )
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error saving raw data: {e}")
            return False

    def save_processed_data(self, df, date):
        """Save processed stock data to the database."""
        try:
            df["date"] = date.strftime("%Y-%m-%d")  # Add date column
            df[["symbol", "performance_score", "normalized_change", "normalized_volume", "date"]].to_sql(
                "processed_data", self.conn, if_exists="append", index=False
            )
            self.conn.commit()
            return True
        except Exception as e:
            logging.error(f"Error saving processed data: {e}")
            return False

    def load_data(self, table_name, date):
        """Load data from the database for a specific date."""
        try:
            query = f"SELECT * FROM {table_name} WHERE date = ?"
            df = pd.read_sql_query(query, self.conn, params=(date.strftime("%Y-%m-%d"),))
            return df if not df.empty else None
        except Exception as e:
            logging.error(f"Error loading data from {table_name}: {e}")
            return None

    def get_available_dates(self):
        """Get a list of all available dates in the database."""
        try:
            query = """
                SELECT DISTINCT(date) FROM raw_stock_data
                UNION
                SELECT DISTINCT(date) FROM processed_data
                ORDER BY date DESC
            """
            dates = pd.read_sql_query(query, self.conn)["date"].tolist()
            return [datetime.strptime(d, "%Y-%m-%d").date() for d in dates]
        except Exception as e:
            logging.error(f"Error fetching available dates: {e}")
            return []

    def close(self):
        """Close the database connection."""
        self.conn.close()

def scrape_stock_data():
    """Scrape stock data from Sharesansar."""
    try:
        url = "https://www.sharesansar.com/live-trading"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        date_element = soup.find("span", {"id": "dDate"})
        
        if not date_element:
            logging.error("Trading date not found")
            return None, None

        scraped_date = datetime.strptime(date_element.text.strip(), "%Y-%m-%d %H:%M:%S").date()
        logging.info(f"Scraped Trading Date: {scraped_date}")

        table = soup.find("table", class_="table")
        if not table:
            logging.error("No table found")
            return None, None

        headers = [th.text.strip() for th in table.find("thead").find_all("th")]
        rows = [[td.text.strip() for td in row.find_all("td")] for row in table.find("tbody").find_all("tr")]
        
        df = pd.DataFrame(rows, columns=headers)
        stock_col = [col for col in df.columns if "symbol" in col.lower() or "stock" in col.lower() or "scrip" in col.lower()][0]
        
        # Filter out excluded symbols
        df_filtered = df[~df[stock_col].isin(EXCLUDED_SYMBOLS)].reset_index(drop=True)
        
        return df_filtered, scraped_date

    except Exception as e:
        logging.error(f"Scraping error: {e}")
        return None, None

def main():
    st.title("🚀 NEPSE Stock Performance Analyzer")
    manager = StockDataManager()

    # Sidebar for settings
    st.sidebar.header("Settings")
    available_dates = manager.get_available_dates()
    selected_date = st.sidebar.date_input(
        "Select Date",
        value=available_dates[0] if available_dates else datetime.today() - timedelta(days=1),
        max_value=datetime.today(),
        format="YYYY-MM-DD",
        disabled=not available_dates
    )
    change_threshold = st.sidebar.slider("Minimum Performance Threshold (%)", min_value=1.0, max_value=10.0, value=4.0, step=0.5)

    # Main tabs
    tab1, tab2 = st.tabs(["Fetch & Analyze Data", "View Saved Data"])

    with tab1:
        if st.button("🔄 Fetch & Analyze Stock Data"):
            with st.spinner("Processing stock data..."):
                df_filtered, scraped_date = scrape_stock_data()
                
                if df_filtered is not None:
                    st.subheader("📊 Complete Stock Data (Without Excluded Symbols)")
                    st.dataframe(df_filtered)
                    
                    # Save raw data
                    if manager.save_raw_data(df_filtered, scraped_date):
                        st.success("Raw data saved to database.")
                    
                    # Process and save top performers
                    top_performers = process_stock_data(df_filtered, change_threshold)
                    if not top_performers.empty:
                        if manager.save_processed_data(top_performers, scraped_date):
                            st.success("Processed data saved to database.")
                        
                        st.subheader("🏆 Top Stock Performers")
                        st.dataframe(top_performers)
                        
                        st.subheader("📈 Top Performers Visualization")
                        stock_col = [col for col in top_performers.columns if "symbol" in col.lower() or "stock" in col.lower() or "scrip" in col.lower()][0]
                        fig = px.bar(top_performers.head(10), x=stock_col, y="performance_score", title="Top Performers by Performance Score")
                        st.plotly_chart(fig)
                    else:
                        st.warning(f"No stocks found above {change_threshold}% threshold")
                else:
                    st.error("Failed to fetch stock data")

    with tab2:
        st.subheader("📂 View Saved Data")
        data_type = st.radio("Select Data Type", ["raw", "processed"])

        if available_dates:
            df = manager.load_data("raw_stock_data" if data_type == "raw" else "processed_data", selected_date)
            if df is not None:
                st.subheader(f"📊 {data_type.capitalize()} Data")
                st.dataframe(df)
            else:
                st.warning(f"No {data_type} data found for {selected_date}.")
        else:
            st.warning("No data available in the database.")

    # Close database connection when done
    manager.close()

if __name__ == "__main__":
    main()
