import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import logging
from datetime import datetime, timedelta
import plotly.express as px
import sqlite3
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename='stock_tracker.log', filemode='a')

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
        directories = ['raw_data', 'processed_data', 'top_performers', 'historical_analysis']
        for dir_name in directories:
            os.makedirs(os.path.join(self.base_dir, dir_name), exist_ok=True)

    def scrape_stock_data(self):
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
        try:
            df.columns = df.columns.str.strip()
            
            # Identify the correct % change column
            change_col = [col for col in df.columns if '% change' in col.lower()][0]  # Ensure this matches the column name
            volume_col = [col for col in df.columns if 'volume' in col.lower()][0]
            stock_col = [col for col in df.columns if 'symbol' in col.lower() or 'stock' in col.lower() or 'scrip' in col.lower()][0]

            # Clean and convert % change column to numeric
            df[change_col] = pd.to_numeric(df[change_col].str.replace('%', ''), errors='coerce')
            df[volume_col] = pd.to_numeric(df[volume_col].str.replace(',', ''), errors='coerce')

            # Filter rows with % change > 4% (positive change only)
            high_change_df = df[df[change_col] >= change_threshold]
            
            # Sort by % change in descending order
            high_change_df = high_change_df.sort_values(by=change_col, ascending=False)
            
            # Count the number of stocks with % change > 4%
            num_high_change_stocks = len(high_change_df)
            
            # Calculate the percentage relative to 244 stocks
            percentage_high_change = (num_high_change_stocks / 244) * 100
            
            # Display the result for > 4% change
            st.subheader("Stocks with > 4% Change")
            st.write(f"Number of stocks with > {change_threshold}% change: {num_high_change_stocks}")
            st.write(f"Percentage of stocks with > {change_threshold}% change: {percentage_high_change:.2f}%")

            # Display the sorted table of stocks with > 4% change
            st.write("Stocks with > 4% Change (Sorted by % Change):")
            st.dataframe(high_change_df[[stock_col, change_col, volume_col]])

            # Filter rows with % change < -4% (negative change only)
            low_change_df = df[df[change_col] <= -change_threshold]
            
            # Sort by % change in ascending order (most negative first)
            low_change_df = low_change_df.sort_values(by=change_col, ascending=True)
            
            # Count the number of stocks with % change < -4%
            num_low_change_stocks = len(low_change_df)
            
            # Calculate the percentage relative to 244 stocks
            percentage_low_change = (num_low_change_stocks / 244) * 100
            
            # Display the result for < -4% change
            st.subheader("Stocks with < -4% Change")
            st.write(f"Number of stocks with < -{change_threshold}% change: {num_low_change_stocks}")
            st.write(f"Percentage of stocks with < -{change_threshold}% change: {percentage_low_change:.2f}%")

            # Display the sorted table of stocks with < -4% change
            st.write("Stocks with <= -4% Change (Sorted by % Change):")
            st.dataframe(low_change_df[[stock_col, change_col, volume_col]])

            # Filter rows with % change > 2.5% (positive change only)
            high_change_2_5_df = df[df[change_col] >= 2.5]
            
            # Sort by % change in descending order
            high_change_2_5_df = high_change_2_5_df.sort_values(by=change_col, ascending=False)
            
            # Count the number of stocks with % change > 2.5%
            num_high_change_2_5_stocks = len(high_change_2_5_df)
            
            # Calculate the percentage relative to 244 stocks
            percentage_high_change_2_5 = (num_high_change_2_5_stocks / 244) * 100
            
            # Display the result for > 2.5% change
            st.subheader("Stocks with > 2.5% Change")
            st.write(f"Number of stocks with > 2.5% change: {num_high_change_2_5_stocks}")
            st.write(f"Percentage of stocks with > 2.5% change: {percentage_high_change_2_5:.2f}%")

            # Display the sorted table of stocks with > 2.5% change
            st.write("Stocks with > 2.5% Change (Sorted by % Change):")
            st.dataframe(high_change_2_5_df[[stock_col, change_col, volume_col]])

            # Filter rows with % change < -2.5% (negative change only)
            low_change_2_5_df = df[df[change_col] <= -2.5]
            
            # Sort by % change in ascending order (most negative first)
            low_change_2_5_df = low_change_2_5_df.sort_values(by=change_col, ascending=True)
            
            # Count the number of stocks with % change < -2.5%
            num_low_change_2_5_stocks = len(low_change_2_5_df)
            
            # Calculate the percentage relative to 244 stocks
            percentage_low_change_2_5 = (num_low_change_2_5_stocks / 244) * 100
            
            # Display the result for < -2.5% change
            st.subheader("Stocks with < -2.5% Change")
            st.write(f"Number of stocks with < -2.5% change: {num_low_change_2_5_stocks}")
            st.write(f"Percentage of stocks with < -2.5% change: {percentage_low_change_2_5:.2f}%")

            # Display the sorted table of stocks with < -2.5% change
            st.write("Stocks with < -2.5% Change (Sorted by % Change):")
            st.dataframe(low_change_2_5_df[[stock_col, change_col, volume_col]])

            # Continue with the original processing for top performers
            filtered_df = df[
                (df[change_col] >= change_threshold) & 
                (df[volume_col] > df[volume_col].median())
            ].copy()

            filtered_df['Normalized_Change'] = (filtered_df[change_col] - filtered_df[change_col].min()) / (filtered_df[change_col].max() - filtered_df[change_col].min())
            filtered_df['Normalized_Volume'] = (filtered_df[volume_col] - filtered_df[volume_col].min()) / (filtered_df[volume_col].max() - filtered_df[volume_col].min())
            filtered_df['Performance_Score'] = 0.6 * filtered_df['Normalized_Change'] + 0.4 * filtered_df['Normalized_Volume']

            return filtered_df.sort_values('Performance_Score', ascending=False)

        except Exception as e:
            logging.error(f"Data processing error: {e}")
            return pd.DataFrame()

    def save_stock_data(self, df, data_type='raw', selected_date=None):
        if selected_date:
            date_str = selected_date.strftime("%Y-%m-%d")
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        save_dir = os.path.join(self.base_dir, f'{data_type}_data', date_str)
        os.makedirs(save_dir, exist_ok=True)
        filename = os.path.join(save_dir, 'stock_data.csv' if data_type == 'raw' else 'top_performers.csv')
        df.to_csv(filename, index=False)
        return filename

def load_saved_data(data_type='raw'):
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
                    
                    top_performers = manager.process_stock_data(df_filtered, change_threshold)
                    if not top_performers.empty:
                        manager.save_stock_data(top_performers, 'processed', scraped_date)
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
                # Reuse the process_stock_data method to analyze historical raw data
                st.subheader("🔍 Analyze Historical Data")

                # Ensure the DataFrame has the required columns
                if '% Change' not in df.columns:
                    st.error("The loaded data does not contain a '% Change' column. Please check the data format.")
                else:
                    # Identify columns dynamically
                    stock_col = [col for col in df.columns if 'symbol' in col.lower() or 'stock' in col.lower() or 'scrip' in col.lower()][0]
                    change_col = [col for col in df.columns if '% change' in col.lower()][0]
                    volume_col = [col for col in df.columns if 'volume' in col.lower()][0]

                    # Clean and convert % change and volume columns
                    if df[change_col].dtype == 'object':  # Check if the column is of string type
                        df[change_col] = pd.to_numeric(df[change_col].str.replace('%', ''), errors='coerce')
                    else:
                        df[change_col] = pd.to_numeric(df[change_col], errors='coerce')

                    if df[volume_col].dtype == 'object':  # Check if the column is of string type
                        df[volume_col] = pd.to_numeric(df[volume_col].str.replace(',', ''), errors='coerce')
                    else:
                        df[volume_col] = pd.to_numeric(df[volume_col], errors='coerce')

                    # Display stocks with > 4% change
                    high_change_df = df[df[change_col] >= 4]
                    num_high_change_stocks = len(high_change_df)
                    percentage_high_change = (num_high_change_stocks / 244) * 100
                    st.subheader("Stocks with > 4% Change")
                    st.write(f"Number of stocks with > 4% change: {num_high_change_stocks}")
                    st.write(f"Percentage of stocks with > 4% change: {percentage_high_change:.2f}%")
                    st.write("Stocks with > 4% Change (Sorted by % Change):")
                    st.dataframe(high_change_df[[stock_col, change_col, volume_col]].sort_values(change_col, ascending=False))

                    # Display stocks with < -4% change
                    low_change_df = df[df[change_col] <= -4]
                    num_low_change_stocks = len(low_change_df)
                    percentage_low_change = (num_low_change_stocks / 244) * 100
                    st.subheader("Stocks with < -4% Change")
                    st.write(f"Number of stocks with < -4% change: {num_low_change_stocks}")
                    st.write(f"Percentage of stocks with < -4% change: {percentage_low_change:.2f}%")
                    st.write("Stocks with <= -4% Change (Sorted by % Change):")
                    st.dataframe(low_change_df[[stock_col, change_col, volume_col]].sort_values(change_col, ascending=True))

                    # Display stocks with > 2.5% change
                    high_change_2_5_df = df[df[change_col] >= 2.5]
                    num_high_change_2_5_stocks = len(high_change_2_5_df)
                    percentage_high_change_2_5 = (num_high_change_2_5_stocks / 244) * 100
                    st.subheader("Stocks with > 2.5% Change")
                    st.write(f"Number of stocks with > 2.5% change: {num_high_change_2_5_stocks}")
                    st.write(f"Percentage of stocks with > 2.5% change: {percentage_high_change_2_5:.2f}%")
                    st.write("Stocks with > 2.5% Change (Sorted by % Change):")
                    st.dataframe(high_change_2_5_df[[stock_col, change_col, volume_col]].sort_values(change_col, ascending=False))

                    # Display stocks with < -2.5% change
                    low_change_2_5_df = df[df[change_col] <= -2.5]
                    num_low_change_2_5_stocks = len(low_change_2_5_df)
                    percentage_low_change_2_5 = (num_low_change_2_5_stocks / 244) * 100
                    st.subheader("Stocks with < -2.5% Change")
                    st.write(f"Number of stocks with < -2.5% change: {num_low_change_2_5_stocks}")
                    st.write(f"Percentage of stocks with < -2.5% change: {percentage_low_change_2_5:.2f}%")
                    st.write("Stocks with < -2.5% Change (Sorted by % Change):")
                    st.dataframe(low_change_2_5_df[[stock_col, change_col, volume_col]].sort_values(change_col, ascending=True))

                    # Calculate performance scores for top performers
                    filtered_df = df[
                        (df[change_col] >= 4) &  # Use fixed threshold for consistency
                        (df[volume_col] > df[volume_col].median())
                    ].copy()
                    filtered_df['Normalized_Change'] = (filtered_df[change_col] - filtered_df[change_col].min()) / (filtered_df[change_col].max() - filtered_df[change_col].min())
                    filtered_df['Normalized_Volume'] = (filtered_df[volume_col] - filtered_df[volume_col].min()) / (filtered_df[volume_col].max() - filtered_df[volume_col].min())
                    filtered_df['Performance_Score'] = 0.6 * filtered_df['Normalized_Change'] + 0.4 * filtered_df['Normalized_Volume']

                    # Display top performers
                    st.subheader("🏆 Top Performers (Historical)")
                    top_performers = filtered_df.sort_values('Performance_Score', ascending=False).head(10)
                    st.dataframe(top_performers)

                    # Visualize top performers
                    st.subheader("📊 Top Performers Visualization (Historical)")
                    fig = px.bar(top_performers, x=stock_col, y='Performance_Score', title="Top Performers by Performance Score")
                    st.plotly_chart(fig)
            elif data_type == 'processed':
                # Display processed data directly
                st.subheader("🏆 Top Performers")
                top_performers = df.head(10)
                st.dataframe(top_performers)

                st.subheader("📈 Top Performers Visualization")
                stock_col = [col for col in top_performers.columns if 'symbol' in col.lower() or 'stock' in col.lower() or 'scrip' in col.lower()][0]
                fig = px.bar(top_performers, x=stock_col, y='Performance_Score', title="Top Performers by Performance Score")
                st.plotly_chart(fig)
    if st.sidebar.checkbox("Show Detailed Logs"):
        try:
            with open('stock_tracker.log', 'r') as log_file:
                st.text(log_file.read())
        except FileNotFoundError:
            st.error("Log file not found")

if __name__ == "__main__":
    main()
