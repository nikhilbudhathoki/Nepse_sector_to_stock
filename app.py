import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import logging
from datetime import datetime, timedelta
import plotly.express as px
import sqlite3

# Enhanced Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='stock_tracker.log',
    filemode='a'
)

class StockDataManager:
    def __init__(self, base_dir='stock_data'):
        self.base_dir = base_dir
        self._create_directories()
        self.excluded_symbols = [
            "SEF", "NICGF", "CMF1", "NBF2", "SIGS2", "CMF2", "NICBF", "NMB50", "SFMF", "LUK", "SLCF", 
            "KEF", "SBCF", "PSF", "NIBSF2", "NICSF", "RMF1", "MMF1", "NBF3", "NICFC", "KDBY", "GIBF1",
            "NSIF2", "NIBLGF", "SAGF", "SFEF", "PRSF", "RMF2", "SIGS3", "C30MF", "LVF2", "H8020",
            "NICGF2", "KSY", "NIBLSTF", "MNMF1",
            # Debentures
            "NICAD85/86", "SAND2085", "NMBD2085", "NIBD2082", "NBBD2085", "SBLD83", "MBLD2085",
            "NICD83/84", "NICAD8283", "SBLD2082", "HBLD83", "PBLD86", "SRBLD83", "LBLD86", "ICFCD83",
            "GWFD83", "KBLD86", "ADBLD83", "CIZBD86", "SBIBD86", "NBLD82", "PBLD84", "SBLD84", "SBD87",
            "NIBD84", "MFLD85", "NCCD86", "KSBBLD87", "NBLD87", "ADBLB", "BOKD86", "PBLD87", "NMBD87/88",
            "NMBEB92/93", "MND84/85", "LBLD88", "PBD85", "SDBD87", "MBLD87", "NICD88", "RBBD83", 
            "GBILD86/87", "JBBD87", "NBLD85", "ADBLB86", "ADBLB87", "GBBBD85", "CBLD88", "EBLD86",
            "CCBD88", "PBD88", "SBLD89", "NMBUR93/94", "SBD89", "SBID83", "PBD84", "EBLD85", "KBLD89",
            "BOKD86KA", "HBLD86", "NIFRAUR85/86", "EBLEB89", "GBILD84/85", "SCBD", "NMBD89/90",
            "MLBLD89", "LBBLD89", "SBID89", "KBLD90", "CIZBD90", "NABILD87", "NIMBD90","GBBD85","HEIP","HIDCLP","KSBBLP","NIMBPO","RBCLPO","SGICP"
        ]
        self.db_path = os.path.join(self.base_dir, 'stock_data.db')
        self._initialize_db()

    def _create_directories(self):
        """Create directories for storing raw, processed, and historical data."""
        directories = ['raw_data', 'processed_data', 'top_performers', 'historical_analysis']
        for dir_name in directories:
            os.makedirs(os.path.join(self.base_dir, dir_name), exist_ok=True)

    def _initialize_db(self):
        """Initialize the SQLite database and create tables if they don't exist."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS raw_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    data TEXT NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS processed_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    performance_score REAL NOT NULL
                )
            ''')
            conn.commit()

    def scrape_stock_data(self):
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

            table = soup.find('table', class_='table')
            if not table:
                logging.error("No table found")
                return None, None

            headers = [th.text.strip() for th in table.find('thead').find_all('th')]
            rows = [[td.text.strip() for td in row.find_all('td')] for row in table.find('tbody').find_all('tr')]
            
            df = pd.DataFrame(rows, columns=headers)
            stock_col = [col for col in df.columns if 'symbol' in col.lower() or 'stock' in col.lower() or 'scrip' in col.lower()][0]
            
            # Filter out excluded symbols
            df_filtered = df[~df[stock_col].isin(self.excluded_symbols)].reset_index(drop=True)
            
            return df_filtered, scraped_date

        except Exception as e:
            logging.error(f"Scraping error: {e}")
            return None, None

    def process_stock_data(self, df, change_threshold=4):
        """Process stock data to identify top performers."""
        try:
            df.columns = df.columns.str.strip()
            
            # Identify the correct % change column
            change_col = [col for col in df.columns if '% change' in col.lower()][0]
            volume_col = [col for col in df.columns if 'volume' in col.lower()][0]
            stock_col = [col for col in df.columns if 'symbol' in col.lower() or 'stock' in col.lower() or 'scrip' in col.lower()][0]

            # Clean and convert % change and volume columns
            df[change_col] = pd.to_numeric(df[change_col].str.replace('%', ''), errors='coerce')
            df[volume_col] = pd.to_numeric(df[volume_col].str.replace(',', ''), errors='coerce')

            # Filter rows with % change > threshold
            filtered_df = df[
                (df[change_col] >= change_threshold) & 
                (df[volume_col] > df[volume_col].median())
            ].copy()

            # Normalize data and calculate performance score
            filtered_df['Normalized_Change'] = (filtered_df[change_col] - filtered_df[change_col].min()) / (filtered_df[change_col].max() - filtered_df[change_col].min())
            filtered_df['Normalized_Volume'] = (filtered_df[volume_col] - filtered_df[volume_col].min()) / (filtered_df[volume_col].max() - filtered_df[volume_col].min())
            filtered_df['Performance_Score'] = 0.6 * filtered_df['Normalized_Change'] + 0.4 * filtered_df['Normalized_Volume']

            return filtered_df.sort_values('Performance_Score', ascending=False)

        except Exception as e:
            logging.error(f"Data processing error: {e}")
            return pd.DataFrame()

    def save_stock_data(self, df, data_type='raw', selected_date=None):
        """Save stock data to SQLite database."""
        if selected_date:
            date_str = selected_date.strftime("%Y-%m-%d")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if data_type == 'raw':
                for _, row in df.iterrows():
                    cursor.execute('''
                        INSERT INTO raw_data (date, symbol, data)
                        VALUES (?, ?, ?)
                    ''', (date_str, row['Symbol'], row.to_json()))
            elif data_type == 'processed':
                for _, row in df.iterrows():
                    cursor.execute('''
                        INSERT INTO processed_data (date, symbol, performance_score)
                        VALUES (?, ?, ?)
                    ''', (date_str, row['Symbol'], row['Performance_Score']))
            conn.commit()

    def load_stock_data(self, data_type='raw', selected_date=None):
        """Load stock data from SQLite database."""
        try:
            if isinstance(selected_date, str):  # Convert string to datetime if needed
                selected_date = datetime.strptime(selected_date, "%Y-%m-%d").date()
            
            if selected_date:
                date_str = selected_date.strftime("%Y-%m-%d")
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if data_type == 'raw':
                    cursor.execute('''
                        SELECT data FROM raw_data WHERE date = ?
                    ''', (date_str,))
                    rows = cursor.fetchall()
                    if rows:
                        df = pd.concat([pd.read_json(row[0], typ='series').to_frame().T for row in rows], ignore_index=True)
                        return df
                elif data_type == 'processed':
                    cursor.execute('''
                        SELECT symbol, performance_score FROM processed_data WHERE date = ?
                    ''', (date_str,))
                    rows = cursor.fetchall()
                    if rows:
                        df = pd.DataFrame(rows, columns=['Symbol', 'Performance_Score'])
                        return df
            return None
        except Exception as e:
            logging.error(f"Error loading data: {e}")
            return None

    def get_available_dates(self, data_type='raw'):
        """Get a list of available dates for which data is saved."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            if data_type == 'raw':
                cursor.execute('''
                    SELECT DISTINCT date FROM raw_data ORDER BY date DESC
                ''')
            elif data_type == 'processed':
                cursor.execute('''
                    SELECT DISTINCT date FROM processed_data ORDER BY date DESC
                ''')
            rows = cursor.fetchall()
            return [row[0] for row in rows]

def main():
    st.title("🚀 NEPSE Stock Performance Analyzer")

    st.sidebar.header("Stock Analysis Settings")
    selected_date = st.sidebar.date_input("Select Date", value=datetime.today() - timedelta(days=1), max_value=datetime.today())
    change_threshold = st.sidebar.slider("Minimum Performance Threshold (%)", min_value=1.0, max_value=10.0, value=4.0, step=0.5)

    tab1, tab2 = st.tabs(["Fetch & Analyze Data", "View Saved Data"])
    manager = StockDataManager()

    with tab1:
        if st.button("🔄 Fetch & Analyze Stock Data"):
            with st.spinner('Processing stock data...'):
                df_filtered, scraped_date = manager.scrape_stock_data()
                
                if df_filtered is not None:
                    st.subheader("📊 Complete Stock Data (Without Excluded Symbols)")
                    st.dataframe(df_filtered)
                    
                    # Save raw data
                    manager.save_stock_data(df_filtered, 'raw', scraped_date)
                    st.success(f"Raw data saved to database.")
                    
                    # Process and save top performers
                    top_performers = manager.process_stock_data(df_filtered, change_threshold)
                    if not top_performers.empty:
                        manager.save_stock_data(top_performers, 'processed', scraped_date)
                        st.success(f"Processed data saved to database.")
                        
                        st.subheader("🏆 Top Stock Performers")
                        st.dataframe(top_performers)
                        
                        st.subheader("📈 Top Performers Visualization")
                        stock_col = [col for col in top_performers.columns if 'symbol' in col.lower() or 'stock' in col.lower() or 'scrip' in col.lower()][0]
                        fig = px.bar(top_performers.head(10), x=stock_col, y='Performance_Score', title="Top Performers by Performance Score")
                        st.plotly_chart(fig)
                    else:
                        st.warning(f"No stocks found above {change_threshold}% threshold")
                else:
                    st.error("Failed to fetch stock data")

    with tab2:
        st.subheader("📂 View Saved Data")
        data_type = st.radio("Select Data Type", ['raw', 'processed'])

        # Get available dates for the selected data type
        available_dates = manager.get_available_dates(data_type)
        if not available_dates:
            st.warning(f"No {data_type} data found.")
        else:
            # Add a date selector
            selected_date_str = st.selectbox(f"Select a date for {data_type} data", available_dates)
            
            # Load data for the selected date
            df = manager.load_stock_data(data_type, selected_date_str)
            if df is not None:
                st.subheader(f"📊 {data_type.capitalize()} Data for {selected_date_str}")
                st.dataframe(df)

if __name__ == "__main__":
    main()
