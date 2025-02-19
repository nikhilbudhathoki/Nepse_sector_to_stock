import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime
import streamlit as st
from supabase import create_client
import os

# Initialize Supabase client
SUPABASE_URL = "https://zjxwjeqgkanjcsrgmfri.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s"


# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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

# Initialize a directory to save data
DATA_DIR = Path("saved_data")
DATA_DIR.mkdir(exist_ok=True)

def save_data():
    """Save all sector data and NEPSE data to CSV files."""
    try:
        for sector, df in st.session_state.data.items():
            df.to_csv(DATA_DIR / f"{sector}_data.csv", index=False)
        st.session_state.nepse_equity.to_csv(DATA_DIR / "nepse_equity.csv", index=False)
    except Exception as e:
        st.error(f"Error saving data: {e}")

def load_data():
    """Load saved data from CSV files."""
    sectors = [
        "Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels", 
        "Microfinance", "Investments", "Life insurance", "Non-life insurance", 
        "Others", "Manufacture", "Tradings"
    ]
    
    loaded_data = {}
    for sector in sectors:
        file_path = DATA_DIR / f"{sector}_data.csv"
        try:
            if file_path.exists():
                loaded_data[sector] = pd.read_csv(file_path)
                loaded_data[sector]["Date"] = pd.to_datetime(loaded_data[sector]["Date"])
            else:
                loaded_data[sector] = pd.DataFrame(columns=[
                    "Date", "No of positive stock", "No of negative stock", 
                    "No of total stock", "No of No change", "Positive %", "Label"
                ])
        except Exception as e:
            st.error(f"Error loading {sector} data: {e}")
            loaded_data[sector] = pd.DataFrame(columns=[
                "Date", "No of positive stock", "No of negative stock", 
                "No of total stock", "No of No change", "Positive %", "Label"
            ])
    
    nepse_file = DATA_DIR / "nepse_equity.csv"
    try:
        if nepse_file.exists():
            nepse_data = pd.read_csv(nepse_file)
            nepse_data["Date"] = pd.to_datetime(nepse_data["Date"])
            # Ensure required columns exist
            for col in ["Total Positive", "Total Stock"]:
                if col not in nepse_data.columns:
                    nepse_data[col] = None
        else:
            nepse_data = pd.DataFrame(columns=[
                "Date", "Total Positive", "Total Stock", "Positive Change %", "Label"
            ])
    except Exception as e:
        st.error(f"Error loading NEPSE data: {e}")
        nepse_data = pd.DataFrame(columns=[
            "Date", "Total Positive", "Total Stock", "Positive Change %", "Label"
        ])
    
    return loaded_data, nepse_data

def initialize_session():
    """Initialize session state with saved data."""
    if 'data' not in st.session_state or 'nepse_equity' not in st.session_state:
        loaded_data, nepse_data = load_data()
        st.session_state.data = loaded_data
        st.session_state.nepse_equity = nepse_data
    return list(st.session_state.data.keys())

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
def save_sector_data(sector, data_dict):
    """Save sector data to Supabase database."""
    try:
        # Ensure the date is in the correct format
        if "date" not in data_dict:
            st.error("Error: 'date' key is missing in the input data.")
            return False
        
        # Convert date to string format (YYYY-MM-DD)
        date_str = data_dict["date"].strftime("%Y-%m-%d")
        
        # Prepare data for Supabase
        data_to_save = {
            "sector": sector,
            "date": date_str,  # Use the formatted date string
            "positive_stock": float(data_dict["positive_stock"]),
            "negative_stock": float(data_dict["negative_stock"]),
            "no_change": float(data_dict["no_change"]),
            "positive_percentage": float(data_dict["positive_percentage"]),
            "label": get_label(data_dict["positive_percentage"]),
            "total_stock": float(data_dict["total_stock"])
        }
        
        # Save data to Supabase
        response = supabase.table('sector_data').upsert(data_to_save).execute()
        
        # Check if the operation was successful
        if response.data:
            st.success(f"Data saved successfully for {sector} on {date_str}!")
            return True
        else:
            st.error("Failed to save data: No response data from Supabase.")
            return False
    except Exception as e:
        st.error(f"Error saving sector data: {e}")
        return False


def update_data(selected_sector, input_data):
    """Update database with new sector data and auto-calculate NEPSE data."""
    try:
        if save_sector_data(selected_sector, input_data):
            # Reload sector data after saving
            st.session_state.data[selected_sector] = load_sector_data(selected_sector)
            
            date = input_data["date"]
            all_sectors = list(st.session_state.data.keys())
            
            # Check if all sectors have data for this date
            all_sectors_have_data = all(
                any(pd.to_datetime(date) == pd.to_datetime(row["date"]) 
                for _, row in st.session_state.data[sector].iterrows())
                for sector in all_sectors
            )
            
            if all_sectors_have_data:
                # Calculate total positive from all sectors
                total_positive = sum(
                    st.session_state.data[sector][
                        pd.to_datetime(st.session_state.data[sector]["date"]) == pd.to_datetime(date)
                    ]["positive_stock"].iloc[0]
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
def load_nepse_data():
    """Load NEPSE equity data from Supabase."""
    try:
        # Fetch data from Supabase
        response = supabase.table('nepse_data').select("*").execute()
        
        # Convert the response to a DataFrame
        if response.data:
            df = pd.DataFrame(response.data)
            df["date"] = pd.to_datetime(df["date"])  # Ensure the date column is in datetime format
            return df
        else:
            return pd.DataFrame(columns=[
                "date", "total_positive", "total_stock", "positive_change_percentage", "label"
            ])
    except Exception as e:
        st.error(f"Error loading NEPSE data: {e}")
        return pd.DataFrame(columns=[
            "date", "total_positive", "total_stock", "positive_change_percentage", "label"
        ])

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
def load_sector_data(sector):
    """Load data for a specific sector from Supabase."""
    try:
        # Fetch data from Supabase
        response = supabase.table('sector_data').select("*").eq('sector', sector).execute()
        
        # Convert the response to a DataFrame
        if response.data:
            df = pd.DataFrame(response.data)
            df["date"] = pd.to_datetime(df["date"])  # Ensure the date column is in datetime format
            return df
        else:
            return pd.DataFrame(columns=[
                "date", "positive_stock", "negative_stock", "no_change", 
                "positive_percentage", "label", "total_stock"
            ])
    except Exception as e:
        st.error(f"Error loading data for {sector}: {e}")
        return pd.DataFrame(columns=[
            "date", "positive_stock", "negative_stock", "no_change", 
            "positive_percentage", "label", "total_stock"
        ])

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
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            selected_sectors_1 = st.multiselect(
                "Select Sectors for Chart 1",
                sectors,
                default=sectors[:3],
                key="chart1_sectors"
            )
        
        with col2:
            selected_sectors_2 = st.multiselect(
                "Select Sectors for Chart 2",
                sectors,
                default=sectors[3:6],
                key="chart2_sectors"
            )
        
        with col3:
            include_nepse = st.checkbox("Include NEPSE Equity", value=True)
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            if selected_sectors_1:
                try:
                    sector_data = []
                    for sector in selected_sectors_1:
                        df = st.session_state.data[sector].copy()
                        df["Sector"] = sector
                        sector_data.append(df)
                    
                    sector_data = pd.concat(sector_data, ignore_index=True)
                    
                    if include_nepse:
                        nepse_data = st.session_state.nepse_equity.copy()
                        nepse_data["Sector"] = "NEPSE Equity"
                        nepse_data = nepse_data.rename(columns={"Positive Change %": "Positive %"})
                        sector_data = pd.concat([sector_data, nepse_data], ignore_index=True)
                    
                    fig1 = px.line(
                        sector_data,
                        x="Date",
                        y="Positive %",
                        color="Sector",
                        title="Chart 1: Sector Performance",
                        labels={"Positive %": "Positive Percentage", "Date": "Date"},
                        markers=True
                    )
                    
                    fig1.update_layout(
                        legend=dict(
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.01
                        ),
                        margin=dict(l=10, r=10, t=40, b=10)
                    )
                    
                    st.plotly_chart(fig1, use_container_width=True)
                except Exception as e:
                    st.error(f"Error plotting Chart 1: {e}")
        
        with chart_col2:
            if selected_sectors_2:
                try:
                    sector_data = []
                    for sector in selected_sectors_2:
                        df = st.session_state.data[sector].copy()
                        df["Sector"] = sector
                        sector_data.append(df)
                    
                    sector_data = pd.concat(sector_data, ignore_index=True)
                    
                    if include_nepse:
                        nepse_data = st.session_state.nepse_equity.copy()
                        nepse_data["Sector"] = "NEPSE Equity"
                        nepse_data = nepse_data.rename(columns={"Positive Change %": "Positive %"})
                        sector_data = pd.concat([sector_data, nepse_data], ignore_index=True)
                    
                    fig2 = px.line(
                        sector_data,
                        x="Date",
                        y="Positive %",
                        color="Sector",
                        title="Chart 2: Sector Performance",
                        labels={"Positive %": "Positive Percentage", "Date": "Date"},
                        markers=True
                    )
                    
                    fig2.update_layout(
                        legend=dict(
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.01
                        ),
                        margin=dict(l=10, r=10, t=40, b=10)
                    )
                    
                    st.plotly_chart(fig2, use_container_width=True)
                except Exception as e:
                    st.error(f"Error plotting Chart 2: {e}")

if __name__ == "__main__":
    main()
