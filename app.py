import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import logging
from datetime import datetime, timedelta
import plotly.express as px
from supabase import create_client
import json

class SupabaseManager:
    def __init__(self):
        # Initialize Supabase client
        self.supabase = create_client(
           "https://zjxwjeqgkanjcsrgmfri.supabase.co",
           "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s"
        )
        self.create_tables()

    def create_tables(self):
        """
        Create tables if they don't exist.
        Note: You'll need to create these tables in your Supabase dashboard with the following SQL:
        
        CREATE TABLE raw_stock_data (
            id BIGSERIAL PRIMARY KEY,
            date DATE NOT NULL,
            data JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
        );

        CREATE TABLE processed_stock_data (
            id BIGSERIAL PRIMARY KEY,
            date DATE NOT NULL,
            data JSONB NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT TIMEZONE('utc', NOW())
        );

        -- Create unique indexes on date
        CREATE UNIQUE INDEX raw_stock_data_date_idx ON raw_stock_data(date);
        CREATE UNIQUE INDEX processed_stock_data_date_idx ON processed_stock_data(date);
        """
        pass  # Tables should be created via Supabase dashboard

    def save_data(self, df, date, data_type):
        """Save data to Supabase"""
        try:
            table_name = f"{data_type}_stock_data"
            data_json = json.loads(df.to_json(orient='records'))
            
            # Convert date to string format if it's a datetime object
            if isinstance(date, datetime):
                date = date.strftime("%Y-%m-%d")
            
            # Upsert data (insert or update)
            result = self.supabase.table(table_name).upsert({
                'date': date,
                'data': data_json
            }).execute()
            
            return True
        except Exception as e:
            st.error(f"Error saving data to Supabase: {e}")
            return False

    def load_data(self, date, data_type):
    """Load data from Supabase."""
    try:
        table_name = f"{data_type}_stock_data"
        
        # Convert date to string format if it's a datetime object
        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")
        
        # Query data
        result = self.supabase.table(table_name)\
            .select('data')\
            .eq('date', date)\
            .execute()
        
        if result.data and len(result.data) > 0:
            # Convert JSON data back to DataFrame
            return pd.DataFrame(result.data[0]['data'])
        return None
    except Exception as e:
        st.error(f"Error loading data from Supabase: {e}")
        return None

    def get_available_dates(self, data_type):
        """Get all available dates from Supabase"""
        try:
            table_name = f"{data_type}_stock_data"
            
            # Query all dates, ordered by date descending
            result = self.supabase.table(table_name)\
                .select('date')\
                .order('date', desc=True)\
                .execute()
            
            if result.data:
                return [row['date'] for row in result.data]
            return []
        except Exception as e:
            st.error(f"Error getting dates from Supabase: {e}")
            return []

    def delete_data(self, date, data_type):
        """Delete data for a specific date"""
        try:
            table_name = f"{data_type}_stock_data"
            
            # Convert date to string format if it's a datetime object
            if isinstance(date, datetime):
                date = date.strftime("%Y-%m-%d")
            
            # Delete record
            result = self.supabase.table(table_name)\
                .delete()\
                .eq('date', date)\
                .execute()
            
            return True
        except Exception as e:
            st.error(f"Error deleting data from Supabase: {e}")
            return False

# Enhanced Logging Configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    filename='stock_tracker.log',
    filemode='a'
)

# -----------------------------------------------------------------------------
# Stock Data Manager
# -----------------------------------------------------------------------------
class StockDataManager:
    def __init__(self, base_dir='stock_data'):
        self.db_manager = SupabaseManager()
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

    def _create_directories(self):
        """Create directories for storing raw, processed, and historical data."""
        directories = ['raw_data', 'processed_data', 'top_performers', 'historical_analysis']
        for dir_name in directories:
            os.makedirs(os.path.join(self.base_dir, dir_name), exist_ok=True)

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
    def load_stock_data(self, data_type, date):
    """Load stock data from Supabase for a specific date."""
    try:
        # Convert date to string format if it's a datetime object
        if isinstance(date, datetime):
            date = date.strftime("%Y-%m-%d")
        
        # Log the date and data type being queried
        logging.info(f"Loading {data_type} data for date: {date}")
        
        # Load data from Supabase
        df = self.db_manager.load_data(date, data_type)
        
        # Log the result
        if df is not None:
            logging.info(f"Data loaded successfully: {df.shape[0]} rows")
        else:
            logging.warning("No data found for the specified date and type")
        
        return df
    except Exception as e:
        logging.error(f"Error loading stock data: {e}")
        return None

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

            # Filter rows with % change >= threshold and volume above median
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
        """Save stock data to Supabase"""
        if selected_date:
            date_str = selected_date.strftime("%Y-%m-%d")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # Save to Supabase
        return self.db_manager.save_data(df, date_str, data_type)

    def get_available_dates(self, data_type='raw'):
        """Get available dates from Supabase"""
        return self.db_manager.get_available_dates(data_type)

# -----------------------------------------------------------------------------
# Streamlit App
# -----------------------------------------------------------------------------
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
                    raw_filename = manager.save_stock_data(df_filtered, 'raw', scraped_date)
                    st.success(f"Raw data saved to: {raw_filename}")
                    
                    # Process and save top performers
                    top_performers = manager.process_stock_data(df_filtered, change_threshold)
                    if not top_performers.empty:
                        processed_filename = manager.save_stock_data(top_performers, 'processed', scraped_date)
                        st.success(f"Processed data saved to: {processed_filename}")
                        
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
            
            # Convert selected date string to datetime object
            selected_date = datetime.strptime(selected_date_str, "%Y-%m-%d").date()
            
            # Load data for the selected date
            df = manager.load_stock_data(data_type, selected_date)
            if df is not None:
                st.subheader(f"📊 {data_type.capitalize()} Data for {selected_date_str}")
                st.dataframe(df)

                if data_type == 'raw':
                    # Enhanced analysis for historical raw data
                    st.subheader("🔍 Detailed Historical Analysis")

                    # Dynamically identify columns
                    stock_col = [col for col in df.columns if 'symbol' in col.lower() or 'stock' in col.lower() or 'scrip' in col.lower()][0]
                    change_col = [col for col in df.columns if '% change' in col.lower()][0]
                    volume_col = [col for col in df.columns if 'volume' in col.lower()][0]

                    # Clean and convert columns
                    df[change_col] = pd.to_numeric(df[change_col].astype(str).str.replace('%', ''), errors='coerce')
                    df[volume_col] = pd.to_numeric(df[volume_col].astype(str).str.replace(',', ''), errors='coerce')

                    # Analysis sections
                    analysis_thresholds = [
                        (4.0, -4.0, "4%"),
                        (2.5, -2.5, "2.5%")
                    ]

                    for pos_th, neg_th, label in analysis_thresholds:
                        # Positive change analysis
                        high_change_df = df[df[change_col] >= pos_th]
                        num_high = len(high_change_df)
                        pct_high = (num_high / 244) * 100
                        
                        st.subheader(f"Stocks with > {label} Change")
                        cols = st.columns(2)
                        cols[0].metric(f"Stocks > {label}", num_high)
                        cols[1].metric(f"Percentage > {label}", f"{pct_high:.2f}%")
                        st.dataframe(
                            high_change_df[[stock_col, change_col, volume_col]]
                            .sort_values(change_col, ascending=False)
                            .style.format({change_col: "{:.2f}%", volume_col: "{:,}"})
                        )

                        # Negative change analysis
                        low_change_df = df[df[change_col] <= neg_th]
                        num_low = len(low_change_df)
                        pct_low = (num_low / 244) * 100
                        
                        st.subheader(f"Stocks with < -{label} Change")
                        cols = st.columns(2)
                        cols[0].metric(f"Stocks < -{label}", num_low)
                        cols[1].metric(f"Percentage < -{label}", f"{pct_low:.2f}%")
                        st.dataframe(
                            low_change_df[[stock_col, change_col, volume_col]]
                            .sort_values(change_col, ascending=True)
                            .style.format({change_col: "{:.2f}%", volume_col: "{:,}"})
                        )

                    # Performance score calculation
                    filtered_df = df[
                        (df[change_col] >= 4) & 
                        (df[volume_col] > df[volume_col].median())
                    ].copy()
                    if not filtered_df.empty:
                        filtered_df['Normalized_Change'] = (filtered_df[change_col] - filtered_df[change_col].min()) / (filtered_df[change_col].max() - filtered_df[change_col].min())
                        filtered_df['Normalized_Volume'] = (filtered_df[volume_col] - filtered_df[volume_col].min()) / (filtered_df[volume_col].max() - filtered_df[volume_col].min())
                        filtered_df['Performance_Score'] = 0.6 * filtered_df['Normalized_Change'] + 0.4 * filtered_df['Normalized_Volume']

                        st.subheader("🏆 Historical Top Performers")
                        top_performers = filtered_df.sort_values('Performance_Score', ascending=False).head(10)
                        st.dataframe(top_performers)

                elif data_type == 'processed':
                    st.subheader("🏆 Top Performers")
                    top_performers = df.head(10)
                    st.dataframe(top_performers)

                    st.subheader("📈 Performance Distribution")
                    fig = px.histogram(df, x='Performance_Score', nbins=20, title="Performance Score Distribution")
                    st.plotly_chart(fig)

    if st.sidebar.checkbox("Show Detailed Logs"):
        try:
            with open('stock_tracker.log', 'r') as log_file:
                st.text(log_file.read())
        except FileNotFoundError:
            st.error("Log file not found")

if __name__ == "__main__":
    main()
