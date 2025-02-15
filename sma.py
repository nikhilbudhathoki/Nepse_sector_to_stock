import streamlit as st
import sqlite3
import pandas as pd
from sqlite3 import Error

# Constants
DB_NAME = "nepse_data.db"
DATE_COL = "date"
SECTOR_COL = "sector"
SMA_COLUMNS = ["sma_5", "sma_10", "sma_20", "sma_50"]

@st.cache_resource
def create_connection():
    """Create SQLite database connection and initialize tables."""
    conn = None
    try:
        conn = sqlite3.connect(DB_NAME, check_same_thread=False)  # ✅ Fix applied
        conn.execute(f"""CREATE TABLE IF NOT EXISTS sma_data (
                        "{DATE_COL}" DATE,
                        "{SECTOR_COL}" TEXT,
                        "{SMA_COLUMNS[0]}" REAL,
                        "{SMA_COLUMNS[1]}" REAL,
                        "{SMA_COLUMNS[2]}" REAL,
                        "{SMA_COLUMNS[3]}" REAL,
                        PRIMARY KEY ("{DATE_COL}", "{SECTOR_COL}")
                     )""")
        return conn
    except Error as e:
        st.error(f"Database error: {str(e)}")
        return None

@st.cache_data(ttl=0, show_spinner="Loading SMA data...")
def load_sma_data():
    """Load data from SQLite database safely."""
    try:
        with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
            df = pd.read_sql(f'SELECT * FROM sma_data', conn, parse_dates=[DATE_COL])
            return df.sort_values(DATE_COL)
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        return pd.DataFrame(columns=[DATE_COL, SECTOR_COL] + SMA_COLUMNS)

def save_sma_data(edited_df):
    """Save data to SQLite database with transaction."""
    try:
        with sqlite3.connect(DB_NAME, check_same_thread=False) as conn:
            sector = edited_df[SECTOR_COL].iloc[0]
            conn.execute(f'DELETE FROM sma_data WHERE "{SECTOR_COL}" = ?', (sector,))
            edited_df.to_sql('sma_data', conn, if_exists='append', index=False)
            conn.commit()
            st.success("Data saved successfully!")
            return True
    except Exception as e:
        st.error(f"Save error: {str(e)}")
        return False

def main():
    """Main function for Streamlit UI."""
    st.title("SMA Analysis")
    
    sma_data = load_sma_data()
    
    if sma_data.empty:
        st.warning("No SMA data available.")
    else:
        edited_df = st.data_editor(sma_data, num_rows="dynamic")
        
        if st.button("Save Changes"):
            if save_sma_data(edited_df):
                st.rerun()

if __name__ == "__main__":
    main()
