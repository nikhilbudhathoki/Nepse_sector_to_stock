import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# Initialize Supabase client
SUPABASE_URL = 'https://zjxwjeqgkanjcsrgmfri.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Label calculation function
def get_label(value):
    """Determine label based on threshold values."""
    if value is None or pd.isna(value):
        return "unknown"
    if value >= 60:
        return "strong"
    elif value >= 50:
        return "mid"
    else:
        return "weak"

# Save sector data to Supabase
def save_sector_data(sector, data_dict):
    """Save sector data to Supabase database."""
    try:
        response = supabase.table('pos').upsert({
            "sector": sector,
            "date": data_dict["date"].strftime("%Y-%m-%d"),
            "positive_stock": float(data_dict["positive_stock"]),
            "negative_stock": float(data_dict["negative_stock"]),
            "no_change": float(data_dict["no_change"]),
            "positive_percentage": float(data_dict["positive_percentage"]),
            "label": get_label(data_dict["positive_percentage"]),
            "total_stock": float(data_dict["total_stock"])
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving sector data: {e}")
        return False

# Save NEPSE data to Supabase
def save_nepse_data(date, total_positive, total_stock=None):
    """Save NEPSE equity data to Supabase database."""
    try:
        positive_change = (total_positive / total_stock * 100) if total_stock else None
        label = get_label(positive_change) if positive_change is not None else "unknown"
        
        response = supabase.table('nepse_equity').upsert({
            "date": date.strftime("%Y-%m-%d"),
            "total_positive": total_positive,
            "total_stock": total_stock,
            "positive_change_percentage": positive_change,
            "label": label
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving NEPSE data: {e}")
        return False

# Load sector data from Supabase
def load_sector_data(sector):
    """Load sector data from Supabase database."""
    try:
        response = supabase.table('pos').select("*").eq("sector", sector).order("date", desc=True).execute()
        df = pd.DataFrame(response.data)
        
        if df.empty:
            return pd.DataFrame()
        
        if 'date' not in df.columns:
            st.error(f"Critical Error: 'date' column missing in 'pos' table for {sector}")
            return pd.DataFrame()
        
        try:
            df["Date"] = pd.to_datetime(df["date"])
        except Exception as e:
            st.error(f"Invalid date format in 'pos' table for {sector}: {e}")
            return pd.DataFrame()
        
        df["total_stock"] = df["positive_stock"] + df["negative_stock"] + df["no_change"]
        
        df = df.drop(columns=["date"]).rename(columns={
            "positive_stock": "No of positive stock",
            "negative_stock": "No of negative stock",
            "no_change": "No of No change",
            "positive_percentage": "Positive %",
            "label": "Label",
            "total_stock": "No of total stock"
        })
        return df
        
    except Exception as e:
        st.error(f"Error loading sector data: {e}")
        return pd.DataFrame()

def load_nepse_data():
    """Load NEPSE equity data from Supabase database."""
    try:
        response = supabase.table('nepse_equity').select("*").order("date", desc=True).execute()
        st.write("Raw Response from Supabase:", response)
        
        if not response.data:
            st.warning("No data available in 'nepse_equity' table.")
            return pd.DataFrame()

        df = pd.DataFrame(response.data)
        st.write("Converted DataFrame:", df)

        if 'date' not in df.columns:
            st.error("Error: 'date' column is missing in the retrieved data.")
            return pd.DataFrame()

        df["Date"] = pd.to_datetime(df["date"])
        df = df.drop(columns=["date"])
        df = df.rename(columns={
            "total_positive": "Total Positive",
            "total_stock": "Total Stock",
            "positive_change_percentage": "Positive Change %",
            "label": "Label"
        })
        return df
    except Exception as e:
        st.error(f"Error loading NEPSE data: {e}")
        return pd.DataFrame()

# Initialize session state
def initialize_session():
    """Initialize session state with data from Supabase database."""
    sectors = [
        "Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels", 
        "Microfinance", "Investments", "Life insurance", "Non-life insurance", 
        "Others", "Manufacture", "Tradings"
    ]
    
    if 'data' not in st.session_state:
        st.session_state.data = {}
        for sector in sectors:
            df = load_sector_data(sector)
            if not df.empty:
                st.session_state.data[sector] = df
            else:
                st.session_state.data[sector] = pd.DataFrame()
    
    if 'nepse_equity' not in st.session_state:
        st.session_state.nepse_equity = load_nepse_data()
    
    return sectors

# Update data in Supabase
def update_data(selected_sector, input_data):
    """Update database with new sector data and auto-calculate NEPSE data."""
    try:
        # Save the sector data first
        if save_sector_data(selected_sector, input_data):
            st.session_state.data[selected_sector] = load_sector_data(selected_sector)
            
            # Aggregate data for NEPSE equity
            date = input_data["date"]
            all_sectors = list(st.session_state.data.keys())
            
            # Initialize totals
            total_positive = 0
            total_stock = 0
            
            # Loop through all sectors to calculate totals
            for sector in all_sectors:
                sector_df = st.session_state.data[sector]
                if not sector_df.empty:
                    # Filter data for the current date
                    date_filter = pd.to_datetime(sector_df["Date"]) == pd.to_datetime(date)
                    if any(date_filter):
                        total_positive += sector_df[date_filter]["No of positive stock"].iloc[0]
                        total_stock += sector_df[date_filter]["No of total stock"].iloc[0]
            
            # Save the aggregated data to the NEPSE equity table
            if total_stock > 0:  # Ensure total_stock is not zero
                save_nepse_data(date, total_positive, total_stock)
                st.session_state.nepse_equity = load_nepse_data()
                st.success("Data updated successfully!")
            else:
                st.warning("Total stock is zero. Cannot calculate NEPSE equity data.")
            
    except Exception as e:
        st.error(f"Error updating data: {e}")

# Get user input for sector data
def get_user_input():
    """Get user input for sectoral data entry."""
    col1, col2 = st.columns(2)
    
    with col1:
        date = st.date_input("Date")
        positive_stock = st.number_input("No of positive stock", min_value=0.0, format="%.2f")
        negative_stock = st.number_input("No of negative stock", min_value=0.0, format="%.2f")
    
    with col2:
        no_change = st.number_input("No of No change", min_value=0.0, format="%.2f")
        total_stock = st.number_input("No of total stock", min_value=0.0, format="%.2f")
    
    if total_stock == 0:
        st.warning("Total stock cannot be zero. Please enter valid numbers.")
        return None
    
    positive_percentage = (positive_stock / total_stock * 100)
    
    return {
        "date": date,
        "positive_stock": positive_stock,
        "negative_stock": negative_stock,
        "no_change": no_change,
        "positive_percentage": positive_percentage,
        "total_stock": total_stock
    }

# Placeholder functions for NEPSE Equity Management (as referenced in tab2)
def display_nepse_equity():
    st.subheader("NEPSE Equity Data")
    if not st.session_state.nepse_equity.empty:
        st.dataframe(st.session_state.nepse_equity)
    else:
        st.write("No NEPSE equity data available.")

def plot_nepse_data():
    st.subheader("NEPSE Equity Chart")
    if not st.session_state.nepse_equity.empty:
        fig = px.line(
            st.session_state.nepse_equity,
            x="Date",
            y="Total Positive",
            title="NEPSE Equity Trend"
        )
        st.plotly_chart(fig)
    else:
        st.write("No NEPSE equity data available.")

# Main function
def main():
    st.title("Sector Data Editor")
    sectors = initialize_session()
    
    tab1, tab2, tab3 = st.tabs(["Sector Data Entry", "NEPSE Equity", "Analysis & Charts"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            selected_sector = st.selectbox("Select Sector", sectors)
            input_data = get_user_input()
            
            if input_data:
                st.info(f"Calculated Positive %: {input_data['positive_percentage']:.2f}%")
                if st.button("Add/Update Data", type="primary"):
                    update_data(selected_sector, input_data)
        
        with col2:
            sector_data = load_sector_data(selected_sector)
            st.download_button(
                label="📥 Download Sector Data",
                data=sector_data.to_csv(index=False).encode('utf-8'),
                file_name=f"{selected_sector}_data.csv",
                mime='text/csv',
            )
        
        st.subheader(f"Data Editor - {selected_sector}")
        edited_df = st.data_editor(
            st.session_state.data[selected_sector],
            num_rows="dynamic",
            key=f"editor_{selected_sector}",
            hide_index=True
        )
    
    with tab2:
        st.subheader("NEPSE Equity Management")
        display_nepse_equity()
        plot_nepse_data()
    
    with tab3:
        st.subheader("Sector Analysis")
        # Add your analysis and chart code here
if __name__ == "__main__":
    main()
