import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import logging
from datetime import datetime, timedelta
import plotly.express as px

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

    def _create_directories(self):
        """Create necessary directories for data storage"""
        directories = [
            'raw_data', 
            'processed_data', 
            'top_performers', 
            'historical_analysis'
        ]
        for dir_name in directories:
            os.makedirs(os.path.join(self.base_dir, dir_name), exist_ok=True)

    def scrape_stock_data(self):
        """Scrape stock data from Sharesansar and extract the correct date"""
        try:
            url = "https://www.sharesansar.com/live-trading"
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")

            # Extract the trading date from the website
            date_element = soup.find("span", {"id": "dDate"})
            if date_element:
                scraped_date = datetime.strptime(date_element.text.strip(), "%Y-%m-%d %H:%M:%S").date()
                logging.info(f"Scraped Trading Date: {scraped_date}")
            else:
                logging.error("Trading date not found on the page")
                return None, None

            # Extract stock data table
            table = soup.find('table', class_='table')
            if not table:
                logging.error("No table found on the page")
                return None, None

            # Extract headers and rows
            headers = [th.text.strip() for th in table.find('thead').find_all('th')]
            rows = [[td.text.strip() for td in row.find_all('td')] for row in table.find('tbody').find_all('tr')]

            df = pd.DataFrame(rows, columns=headers)
            return df, scraped_date

        except Exception as e:
            logging.error(f"Scraping error: {e}")
            return None, None

    def process_stock_data(self, df, change_threshold=4):
        """Process stock data to filter top performers"""
        try:
            df.columns = df.columns.str.strip()
            
            # Dynamically identify relevant columns
            change_col = [col for col in df.columns if '%' in col or 'change' in col.lower()][0]
            volume_col = [col for col in df.columns if 'volume' in col.lower()][0]
            stock_col = [col for col in df.columns if 'symbol' in col.lower() or 'stock' in col.lower() or 'scrip' in col.lower()][0]

            df[change_col] = pd.to_numeric(df[change_col].str.replace('%', ''), errors='coerce')
            df[volume_col] = pd.to_numeric(df[volume_col].str.replace(',', ''), errors='coerce')

            filtered_df = df[
                (df[change_col] >= change_threshold) & 
                (df[volume_col] > df[volume_col].median())
            ].copy()

            filtered_df['Normalized_Change'] = (filtered_df[change_col] - filtered_df[change_col].min()) / (filtered_df[change_col].max() - filtered_df[change_col].min())
            filtered_df['Normalized_Volume'] = (filtered_df[volume_col] - filtered_df[volume_col].min()) / (filtered_df[volume_col].max() - filtered_df[volume_col].min())
            
            filtered_df['Performance_Score'] = (
                0.6 * filtered_df['Normalized_Change'] + 
                0.4 * filtered_df['Normalized_Volume']
            )

            return filtered_df.sort_values('Performance_Score', ascending=False)

        except Exception as e:
            logging.error(f"Data processing error: {e}")
            return pd.DataFrame()

    def save_stock_data(self, df, data_type='raw', selected_date=None):
        """Save stock data in date-specific directories"""
        if selected_date:
            date_str = selected_date.strftime("%Y-%m-%d")  # Format date as YYYY-MM-DD
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        # Create date-specific directory
        if data_type == 'raw':
            save_dir = os.path.join(self.base_dir, 'raw_data', date_str)
        elif data_type == 'processed':
            save_dir = os.path.join(self.base_dir, 'processed_data', date_str)
        else:
            raise ValueError("Invalid data type")

        os.makedirs(save_dir, exist_ok=True)  # Create directory if it doesn't exist

        # Save file
        filename = os.path.join(save_dir, 'stock_data.csv' if data_type == 'raw' else 'top_performers.csv')
        df.to_csv(filename, index=False)
        return filename

def load_saved_data(data_type='raw'):
    """Load previously saved data based on type (raw or processed) and date"""
    try:
        if data_type == 'raw':
            data_dir = os.path.join('stock_data', 'raw_data')
        elif data_type == 'processed':
            data_dir = os.path.join('stock_data', 'processed_data')
        else:
            raise ValueError("Invalid data type")

        # List all available dates (subdirectories)
        available_dates = [d for d in os.listdir(data_dir) if os.path.isdir(os.path.join(data_dir, d))]
        if not available_dates:
            st.warning(f"No {data_type} data files found.")
            return None

        # Let user select a date
        selected_date = st.selectbox(f"Select a date for {data_type} data", available_dates)

        # Load the file for the selected date
        file_path = os.path.join(data_dir, selected_date, 'stock_data.csv' if data_type == 'raw' else 'top_performers.csv')
        if not os.path.exists(file_path):
            st.warning(f"No data found for the selected date: {selected_date}")
            return None

        df = pd.read_csv(file_path)
        return df

    except Exception as e:
        st.error(f"Error loading {data_type} data: {e}")
        return None

def main():
    
    st.title("🚀 NEPSE Stock Performance Analyzer")

    # Sidebar for global settings
    st.sidebar.header("Stock Analysis Settings")
    selected_date = st.sidebar.date_input("Select Date", value=datetime.today() - timedelta(days=1), max_value=datetime.today())
    change_threshold = st.sidebar.slider("Minimum Performance Threshold (%)", min_value=1.0, max_value=10.0, value=4.0, step=0.5)

    # Tabs for navigation
    tab1, tab2 = st.tabs(["Fetch & Analyze Data", "View Saved Data"])

    manager = StockDataManager()

    # Tab 1: Fetch & Analyze Data
    with tab1:
        if st.button("🔄 Fetch & Analyze Stock Data"):
            with st.spinner('Processing stock data...'):
                df, scraped_date = manager.scrape_stock_data()
                
                if df is not None:
                    manager.save_stock_data(df, 'raw', scraped_date)
                    st.subheader("📊 Complete Stock Data")
                    st.dataframe(df)
                    
                    top_performers = manager.process_stock_data(df, change_threshold)
                    if not top_performers.empty:
                        manager.save_stock_data(top_performers, 'processed', scraped_date)
                        st.subheader("🏆 Top Stock Performers")
                        st.dataframe(top_performers)

                        # Visualize top performers
                        st.subheader("📈 Top Performers Visualization")
                        stock_col = [col for col in top_performers.columns if 'symbol' in col.lower() or 'stock' in col.lower() or 'scrip' in col.lower()][0]
                        fig = px.bar(top_performers.head(10), x=stock_col, y='Performance_Score', title="Top Performers by Performance Score")
                        st.plotly_chart(fig)
                    else:
                        st.warning(f"No stocks found above {change_threshold}% threshold")
                else:
                    st.error("Failed to fetch stock data")

    # Tab 2: View Saved Data
    with tab2:
        st.subheader("📂 View Saved Data")
        data_type = st.radio("Select Data Type", ['raw', 'processed'])

        df = load_saved_data(data_type)
        if df is not None:
            st.subheader(f"📊 {data_type.capitalize()} Data")
            st.dataframe(df)

            if data_type == 'processed':
                st.subheader("🏆 Top Performers")
                top_performers = df.head(10)  # Display top 10 performers
                st.dataframe(top_performers)

                # Visualize top performers
                st.subheader("📈 Top Performers Visualization")
                stock_col = [col for col in top_performers.columns if 'symbol' in col.lower() or 'stock' in col.lower() or 'scrip' in col.lower()][0]
                fig = px.bar(top_performers, x=stock_col, y='Performance_Score', title="Top Performers by Performance Score")
                st.plotly_chart(fig)

    # Logs section
    if st.sidebar.checkbox("Show Detailed Logs"):
        try:
            with open('stock_tracker.log', 'r') as log_file:
                st.text(log_file.read())
        except FileNotFoundError:
            st.error("Log file not found")

if __name__ == "__main__":
    main()