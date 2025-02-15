import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import datetime

# Initialize Supabase client
SUPABASE_URL = 'https://zjxwjeqgkanjcsrgmfri.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

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

def save_sector_data(sector, data_dict):
    """Save sector data to Supabase database."""
    try:
        # Ensure the date is in the correct format
        if "date" not in data_dict:
            st.error("Error: 'date' key is missing in the input data.")
            return False
        
        # Convert date to string format (YYYY-MM-DD)
        date_str = data_dict["date"].strftime("%Y-%m-%d")
        
        # Save data to Supabase
        response = supabase.table('pos').upsert({
            "sector": sector,
            "date": date_str,  # Use the formatted date string
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

def load_sector_data(sector):
    """Load sector data from Supabase database."""
    try:
        response = supabase.table('sector_data').select("*").eq("sector", sector).order("date", desc=True).execute()
        df = pd.DataFrame(response.data)
        
        if df.empty:
            return pd.DataFrame()
        
        if 'date' not in df.columns:
            st.error(f"Critical Error: 'date' column missing in 'sector_data' table for {sector}")
            return pd.DataFrame()
        
        try:
            df["Date"] = pd.to_datetime(df["date"])
        except Exception as e:
            st.error(f"Invalid date format in 'sector_data' table for {sector}: {e}")
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
    """Load NEPSE equity data from Supabase database with improved error handling."""
    try:
        response = supabase.table('nepse_equity').select("*").order("date", desc=True).execute()
        
        if not response.data:
            st.warning("No data available in 'nepse_equity' table.")
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=[
                "Date", "Total Positive", "Total Stock", 
                "Positive Change %", "Label"
            ])

        df = pd.DataFrame(response.data)
        
        # Ensure date column exists
        if 'date' not in df.columns:
            st.error("Error: 'date' column is missing in the retrieved data.")
            return pd.DataFrame(columns=[
                "Date", "Total Positive", "Total Stock", 
                "Positive Change %", "Label"
            ])

        # Convert date column
        df["Date"] = pd.to_datetime(df["date"])
        df = df.drop(columns=["date"])
        
        # Rename columns
        df = df.rename(columns={
            "total_positive": "Total Positive",
            "total_stock": "Total Stock",
            "positive_change_percentage": "Positive Change %",
            "label": "Label"
        })
        
        return df
    except Exception as e:
        st.error(f"Error loading NEPSE data: {e}")
        return pd.DataFrame(columns=[
            "Date", "Total Positive", "Total Stock", 
            "Positive Change %", "Label"
        ])

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

def get_user_input():
    """Get user input for sectoral data entry."""
    col1, col2 = st.columns(2)
    
    with col1:
        date = st.date_input("Date")
        positive_stock = st.number_input("No of positive stock", min_value=0)
        negative_stock = st.number_input("No of negative stock", min_value=0)
    
    with col2:
        total_stock = st.number_input("No of total stock", min_value=0)
        no_change = st.number_input("No of No change", min_value=0)
    
    if total_stock == 0:
        st.warning("Total stock cannot be zero. Please enter a valid number.")
        return None
    
    positive_percentage = (positive_stock / total_stock * 100) if total_stock > 0 else 0
    
    return {
        "date": date,  # Ensure this key is included
        "positive_stock": positive_stock,
        "negative_stock": negative_stock,
        "total_stock": total_stock,
        "no_change": no_change,
        "positive_percentage": positive_percentage
    }

def update_data(selected_sector, input_data):
    """Update database with new sector data and auto-calculate NEPSE data."""
    try:
        if "date" not in input_data:
            st.error("Error: 'date' key is missing in the input data.")
            return False
        
        if save_sector_data(selected_sector, input_data):
            st.session_state.data[selected_sector] = load_sector_data(selected_sector)
            
            date = input_data["date"]
            all_sectors = list(st.session_state.data.keys())
            
            # Check if all sectors have data for this date
            all_sectors_have_data = all(
                any(pd.to_datetime(date) == pd.to_datetime(row["Date"]) 
                for _, row in st.session_state.data[sector].iterrows())
                for sector in all_sectors
            )
            
            if all_sectors_have_data:
                # Calculate total positive from all sectors
                total_positive = sum(
                    st.session_state.data[sector][
                        pd.to_datetime(st.session_state.data[sector]["Date"]) == pd.to_datetime(date)
                    ]["No of positive stock"].iloc[0]
                    for sector in all_sectors
                )
                
                # Create/update NEPSE entry with None for Total Stock (to be filled by user)
                save_nepse_data(date, total_positive, total_stock=None)
                st.session_state.nepse_equity = load_nepse_data()
            
            st.success("Data updated successfully! Please update NEPSE Total Stock in the NEPSE Equity tab.")
            
    except Exception as e:
        st.error(f"Error updating data: {e}")

def display_data_editor(selected_sector):
    """Display unified data editor with automatic label updates."""
    st.subheader(f"Data Editor - {selected_sector}")
    
    df = st.session_state.data[selected_sector].copy()
    df = df.sort_values("Date", ascending=False)
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        key=f"editor_{selected_sector}",
        hide_index=True
    )
    
    if not edited_df.equals(df):
        # Ensure all required columns are present
        required_columns = ["Date", "No of positive stock", "No of negative stock", 
                            "No of total stock", "No of No change", "Positive %", "Label"]
        if all(col in edited_df.columns for col in required_columns):
            # Update labels
            edited_df["Label"] = edited_df["Positive %"].apply(get_label)
            
            # Save each row to Supabase
            for _, row in edited_df.iterrows():
                data_dict = {
                    "date": row["Date"],
                    "positive_stock": row["No of positive stock"],
                    "negative_stock": row["No of negative stock"],
                    "no_change": row["No of No change"],
                    "positive_percentage": row["Positive %"],
                    "total_stock": row["No of total stock"]
                }
                save_sector_data(selected_sector, data_dict)
            
            # Update session state
            st.session_state.data[selected_sector] = edited_df
            st.success("Data updated successfully!")
        else:
            st.error("Error: Edited data is missing required columns. Please check your input.")

def display_nepse_equity():
    """Display NEPSE data editor with automatic updates."""
    st.subheader("NEPSE Equity Data")
    
    df = st.session_state.nepse_equity.copy()
    df = df.sort_values("Date", ascending=False)
    
    # Ensure column order and existence
    required_columns = ["Date", "Total Positive", "Total Stock", "Positive Change %", "Label"]
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    
    edited_df = st.data_editor(
        df[required_columns],
        num_rows="dynamic",
        key="editor_nepse",
        hide_index=True,
        column_config={
            "Date": st.column_config.DateColumn(disabled=True),
            "Total Positive": st.column_config.NumberColumn(disabled=True),
            "Total Stock": st.column_config.NumberColumn(
                "Total Stock (Required)", 
                min_value=1,
                help="Enter total number of stocks for NEPSE calculation"
            ),
            "Positive Change %": st.column_config.NumberColumn(
                format="%.2f%%",
                disabled=True
            ),
            "Label": st.column_config.TextColumn(disabled=True)
        }
    )
    
    # Calculate values
    mask = (edited_df["Total Stock"].notna()) & (edited_df["Total Stock"] > 0)
    edited_df["Positive Change %"] = (edited_df["Total Positive"] / edited_df["Total Stock"]) * 100
    edited_df["Label"] = edited_df["Positive Change %"].apply(get_label)
    
    # Handle invalid/missing values
    edited_df.loc[~mask, "Positive Change %"] = None
    edited_df.loc[~mask, "Label"] = "unknown"
    
    if not edited_df.equals(df):
        # Save updated data to Supabase
        for _, row in edited_df.iterrows():
            save_nepse_data(
                date=row["Date"],
                total_positive=row["Total Positive"],
                total_stock=row["Total Stock"]
            )
        st.session_state.nepse_equity = load_nepse_data()
        st.rerun()


def plot_nepse_data():
    """Plot NEPSE Equity data separately."""
    try:
        nepse_data = st.session_state.nepse_equity.copy()
        if not nepse_data.empty:
            fig = px.line(
                nepse_data,
                x="Date",
                y="Positive Change %",
                title="NEPSE Equity Performance Over Time",
                labels={"Positive Change %": "Positive Change Percentage", "Date": "Date"},
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error plotting NEPSE data: {e}")

def main():
    st.title("Sector Data Editor")
    sectors = initialize_session()
    
    tab1, tab2, tab3 = st.tabs(["Sector Data Entry", "NEPSE Equity", "Analysis & Charts"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            selected_sector = st.selectbox("Select Sector", sectors)
            input_data = get_user_input()
            
            if input_data:
                st.info(f"Calculated Positive %: {input_data['positive_percentage']:.2f}%")
                if st.button("Add/Update Data", type="primary"):
                    update_data(selected_sector, input_data)
        
        with col2:
            st.download_button(
                label="📥 Download Sector Data",
                data=st.session_state.data[selected_sector].to_csv(index=False).encode('utf-8'),
                file_name=f"{selected_sector}_data.csv",
                mime='text/csv',
            )
        
        display_data_editor(selected_sector)
    
    with tab2:
        st.subheader("NEPSE Equity Management")
        col1, _ = st.columns([2, 1])
        
        with col1:
            st.download_button(
                label="📥 Download NEPSE Data",
                data=st.session_state.nepse_equity.to_csv(index=False).encode('utf-8'),
                file_name="nepse_equity_data.csv",
                mime='text/csv',
            )
        
        display_nepse_equity()
        plot_nepse_data()
    
    with tab3:
        st.subheader("Sector Analysis")
        # ... (keep your existing chart code here)

if __name__ == "__main__":
    main()
