import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import logging
from datetime import datetime, timedelta
import plotly.express as px
from supabase import create_client, Client

# Supabase Configuration
SUPABASE_URL = 'https://zjxwjeqgkanjcsrgmfri.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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
        """Save stock data to CSV files."""
        if selected_date:
            date_str = selected_date.strftime("%Y-%m-%d")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        save_dir = os.path.join(self.base_dir, f'{data_type}_data', date_str)
        os.makedirs(save_dir, exist_ok=True)
        filename = os.path.join(save_dir, 'stock_data.csv' if data_type == 'raw' else 'top_performers.csv')
        df.to_csv(filename, index=False)
        return filename

def load_sector_data():
    """Load sector data from Supabase database."""
    try:
        response = supabase.table('pos').select("*").execute()
        df = pd.DataFrame(response.data)
        
        if df.empty:
            st.warning("No sector data available.")
            return pd.DataFrame()
        
        df["Date"] = pd.to_datetime(df["date"])
        df["total_stock"] = df["positive_stock"] + df["negative_stock"] + df["no_change"]
        
        return df
    except Exception as e:
        st.error(f"Error loading sector data: {e}")
        return pd.DataFrame()
def load_saved_data(data_type='raw'):
    """Load saved data from CSV files."""
    try:
        data_dir = os.path.join('stock_data', f'{data_type}_data')
        available_dates = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
        
        if not available_dates:
            st.warning(f"No {data_type} data files found.")
            return None

        selected_date = st.selectbox(f"Select a date for {data_type} data", available_dates)
        file_path = os.path.join(data_dir, selected_date, 'stock_data.csv' if data_type == 'raw' else 'top_performers.csv')
        
        if not os.path.exists(file_path):
            st.warning(f"No data found for the selected date: {selected_date}")
            return None

        return pd.read_csv(file_path)

    except Exception as e:
        st.error(f"Error loading {data_type} data: {e}")
        return None

# Add this to your POS page implementation
def POS():
    st.title("Sector Data Analysis")
    
    # Add connection to sector data entry database
    sector_df = load_sector_data()  # Use existing load_sector_data function
    if not sector_df.empty:
        st.subheader("Sector Data from Database")
        st.dataframe(sector_df)
        
        # Add analysis of sector data
        st.subheader("Sector Performance Metrics")
        fig = px.bar(sector_df, 
                    x="sector", 
                    y="positive_percentage", 
                    color="label",
                    title="Sector Performance by Positive Percentage")
        st.plotly_chart(fig)
        
        # Add date filter for historical analysis
        selected_date = st.selectbox("Select Date", pd.to_datetime(sector_df["Date"]).dt.date.unique())
        filtered_data = sector_df[pd.to_datetime(sector_df["Date"]).dt.date == selected_date]
        
        st.subheader(f"Sector Status on {selected_date}")
        cols = st.columns(3)
        cols[0].metric("Total Sectors", len(filtered_data))
        cols[1].metric("Strong Sectors", len(filtered_data[filtered_data["label"] == "strong"]))
        cols[2].metric("Weak Sectors", len(filtered_data[filtered_data["label"] == "weak"]))
        
    else:
        st.warning("No sector data available in database")

    # Add integration with saved stock data
    st.subheader("Cross-Analysis with Stock Data")
    data_type = st.radio("Select Stock Data Type", ['raw', 'processed'], key='pos_analysis')
    stock_df = load_saved_data(data_type)
    
    if stock_df is not None:
        st.subheader(f"Combined Analysis with {data_type.capitalize()} Stock Data")
        combined_df = pd.merge(sector_df, stock_df, left_on="date", right_on="Date")
        st.dataframe(combined_df)

def main():
    st.title("🚀 NEPSE Stock Performance Analyzer")

    st.sidebar.header("Stock Analysis Settings")
    selected_date = st.sidebar.date_input("Select Date", value=datetime.today() - timedelta(days=1), max_value=datetime.today())
    change_threshold = st.sidebar.slider("Minimum Performance Threshold (%)", min_value=1.0, max_value=10.0, value=4.0, step=0.5)

    tab1, tab2, tab3 = st.tabs(["Fetch & Analyze Data", "View Saved Data", "Sector Data Analysis"])
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

        df = load_saved_data(data_type)
        if df is not None:
            st.subheader(f"📊 {data_type.capitalize()} Data")
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
                    low_change_df = df[df[change_col] <= -neg_th]
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

    with tab3:
        st.subheader("📊 Sector Data Analysis")
        sector_df = load_sector_data()
        
        if not sector_df.empty:
            st.subheader("Sector Data Overview")
            st.dataframe(sector_df)

            st.subheader("📈 Sector Performance Visualization")
            fig = px.bar(sector_df, x="sector", y="positive_percentage", title="Sector Performance by Positive Percentage")
            st.plotly_chart(fig)
        else:
            st.warning("No sector data available.")

    if st.sidebar.checkbox("Show Detailed Logs"):
        try:
            with open('stock_tracker.log', 'r') as log_file:
                st.text(log_file.read())
        except FileNotFoundError:
            st.error("Log file not found")

if __name__ == "__main__":
    main()
