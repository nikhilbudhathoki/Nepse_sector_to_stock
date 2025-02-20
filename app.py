import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime
import streamlit as st
from supabase import create_client
import os
import math

# Initialize Supabase client
SUPABASE_URL = "https://zjxwjeqgkanjcsrgmfri.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s"

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize a directory to save data
DATA_DIR = Path("saved_data")
DATA_DIR.mkdir(exist_ok=True)

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

def save_nepse_data(total_stock):
    try:
        # Check if input is empty or invalid
        if not total_stock or isinstance(total_stock, str) and total_stock.strip() == "":
            raise ValueError("Total stock cannot be empty.")

        # Convert the total_stock to float and round it
        total_stock = float(total_stock)

        # If the input value is NaN, handle it by setting a default value
        if math.isnan(total_stock):
            raise ValueError("Total stock cannot be NaN.")

        # Round and convert it to an integer
        total_stock = int(round(total_stock))

    except ValueError as e:
        # Handle invalid input
        print(f"Error: {e}")
        total_stock = 0  # Default value for invalid input

    # Continue saving the data (with valid total_stock)
    print(f"Total stock value: {total_stock}")

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
    if 'data' not in st.session_state:
        st.session_state.data = {}
        
    sectors = [
        "Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels", 
        "Microfinance", "Investments", "Life insurance", "Non-life insurance", 
        "Others", "Manufacture", "Tradings"
    ]
    
    # Initialize data for each sector if not already present
    for sector in sectors:
        if sector not in st.session_state.data:
            st.session_state.data[sector] = load_sector_data(sector)
    
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
        "date": date,
        "positive_stock": positive_stock,
        "negative_stock": negative_stock,
        "total_stock": total_stock,
        "no_change": no_change,
        "positive_percentage": positive_percentage
    }

def save_sector_data(sector, data_dict):
    """Save sector data to Supabase database."""
    try:
        if "date" not in data_dict:
            st.error("Error: 'date' key is missing in the input data.")
            return False
        
        date_str = data_dict["date"].strftime("%Y-%m-%d")
        
        data_to_save = {
            "sector": sector,
            "date": date_str,
            "positive_stock": float(data_dict["positive_stock"]),
            "negative_stock": float(data_dict["negative_stock"]),
            "no_change": float(data_dict["no_change"]),
            "positive_percentage": float(data_dict["positive_percentage"]),
            "label": get_label(data_dict["positive_percentage"]),
            "total_stock": float(data_dict["total_stock"])
        }
        
        response = supabase.table('sector_data').upsert(data_to_save).execute()
        
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
            st.session_state.data[selected_sector] = load_sector_data(selected_sector)
            
            date = pd.to_datetime(input_data["date"])
            all_sectors = list(st.session_state.data.keys())
            
            all_sectors_have_data = True
            for sector in all_sectors:
                sector_df = st.session_state.data[sector]
                if "Date" in sector_df.columns:
                    sector_dates = pd.to_datetime(sector_df["Date"])
                    if not any(sector_dates == date):
                        all_sectors_have_data = False
                        break
                else:
                    all_sectors_have_data = False
                    break
            
            if all_sectors_have_data:
                total_positive = 0
                for sector in all_sectors:
                    sector_df = st.session_state.data[sector]
                    matching_row = sector_df[pd.to_datetime(sector_df["Date"]) == date]
                    if not matching_row.empty:
                        total_positive += matching_row["No of positive stock"].iloc[0]
                
                save_nepse_data(date, total_positive, total_stock=None)
                st.session_state.nepse_equity = load_nepse_data()
            
            st.success("Data updated successfully! Please update NEPSE Total Stock in the NEPSE Equity tab.")
    except Exception as e:
        st.error(f"Error updating data: {str(e)}")
        st.exception(e)

def display_data_editor(selected_sector):
    """Display unified data editor with automatic label updates and deletion."""
    if selected_sector not in st.session_state.data:
        st.session_state.data[selected_sector] = load_sector_data(selected_sector)
    
    st.subheader(f"Data Editor - {selected_sector}")
    
    df = st.session_state.data[selected_sector].copy()
    
    required_columns = [
        "Date", "No of positive stock", "No of negative stock",
        "No of total stock", "No of No change", "Positive %", "Label"
    ]
    
    if df is None or df.empty:
        df = pd.DataFrame(columns=required_columns)
    
    for col in required_columns:
        if col not in df.columns:
            df[col] = None
    
    if not df.empty and "Date" in df.columns and df["Date"].notna().any():
        df = df.sort_values("Date", ascending=False)
    
    try:
        edited_df = st.data_editor(
            df,
            num_rows="dynamic",
            key=f"editor_{selected_sector}",
            hide_index=True,
            column_config={
                "Date": st.column_config.DateColumn("Date"),
                "No of positive stock": st.column_config.NumberColumn("Positive Stocks", min_value=0),
                "No of negative stock": st.column_config.NumberColumn("Negative Stocks", min_value=0),
                "No of total stock": st.column_config.NumberColumn("Total Stocks", min_value=0),
                "No of No change": st.column_config.NumberColumn("No Change", min_value=0),
                "Positive %": st.column_config.NumberColumn("Positive %", format="%.2f%%", disabled=True),
                "Label": st.column_config.TextColumn("Label", disabled=True)
            }
        )
        
        deleted_rows = set(df.index) - set(edited_df.index)
        if deleted_rows:
            deletion_successful = False
            for idx in deleted_rows:
                row = df.loc[idx]
                if pd.notna(row["Date"]):
                    date_str = row["Date"].strftime("%Y-%m-%d") if isinstance(row["Date"], (datetime, pd.Timestamp)) else row["Date"]
                    response = supabase.table('sector_data')\
                        .delete()\
                        .eq('sector', selected_sector)\
                        .eq('date', date_str)\
                        .execute()
                    
                    if response.data:
                        st.success(f"Data deleted for {selected_sector} on {date_str}")
                        deletion_successful = True
                    else:
                        st.error(f"Failed to delete data for {selected_sector} on {date_str}")
            
            if deletion_successful:
                st.session_state.data[selected_sector] = load_sector_data(selected_sector)
                st.rerun()
        
        if not edited_df.equals(df):
            mask = (edited_df["No of total stock"].notna()) & (edited_df["No of total stock"] > 0)
            edited_df.loc[mask, "Positive %"] = (
                edited_df.loc[mask, "No of positive stock"] / 
                edited_df.loc[mask, "No of total stock"] * 100
            )
            
            edited_df["Label"] = edited_df["Positive %"].apply(get_label)
            
            for _, row in edited_df.iterrows():
                if pd.notna(row["Date"]) and pd.notna(row["No of total stock"]):
                    data_dict = {
                        "date": row["Date"],
                        "positive_stock": row["No of positive stock"],
                        "negative_stock": row["No of negative stock"],
                        "no_change": row["No of No change"],
                        "positive_percentage": row["Positive %"],
                        "total_stock": row["No of total stock"]
                    }
                    save_sector_data(selected_sector, data_dict)
            
            st.session_state.data[selected_sector] = load_sector_data(selected_sector)
            st.success("Data updated successfully!")
            
    except Exception as e:
        st.error(f"Error in data editor: {e}")
        st.exception(e)

def load_nepse_data():
    """Load NEPSE equity data from Supabase."""
    try:
        response = supabase.table('nepse_equity').select("*").execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            column_mapping = {
                'date': 'Date',
                'total_positive': 'Total Positive',
                'total_stock': 'Total Stock',
                'positive_change_percentage': 'Positive Change %',
                'label': 'Label'
            }
            df = df.rename(columns=column_mapping)
            df["Date"] = pd.to_datetime(df["Date"])
            return df
        else:
            return pd.DataFrame(columns=[
                "Date", "Total Positive", "Total Stock", "Positive Change %", "Label"
            ])
    except Exception as e:
        st.error(f"Error loading NEPSE data: {e}")
        return pd.DataFrame(columns=[
            "Date", "Total Positive", "Total Stock", "Positive Change %", "Label"
        ])

[Previous code remains the same until display_nepse_equity function...]

def display_nepse_equity():
    """Display NEPSE data editor with full CRUD functionality."""
    st.subheader("NEPSE Equity Data")
    
    df = load_nepse_data()
    
    if df.empty:
        df = pd.DataFrame(columns=["Date", "Total Positive", "Total Stock", "Positive Change %", "Label"])
    
    if "Date" in df.columns and not df.empty:
        df = df.sort_values("Date", ascending=False)
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        key="editor_nepse",
        hide_index=True,
        column_config={
            "Date": st.column_config.DateColumn(
                "Date",
                help="Select date"
            ),
            "Total Positive": st.column_config.NumberColumn(
                "Total Positive",
                help="Number of positive stocks",
                min_value=0
            ),
            "Total Stock": st.column_config.NumberColumn(
                "Total Stock", 
                help="Enter total number of stocks",
                min_value=1
            ),
            "Positive Change %": st.column_config.NumberColumn(
                "Positive Change %",
                format="%.2f%%",
                disabled=True
            ),
            "Label": st.column_config.TextColumn(
                "Label",
                disabled=True
            )
        }
    )
    
    # Handle deletions and updates
    deleted_rows = set(df.index) - set(edited_df.index)
    if deleted_rows:
        for idx in deleted_rows:
            row = df.loc[idx]
            if pd.notna(row["Date"]):
                date_str = row["Date"].strftime("%Y-%m-%d")
                if delete_nepse_data(date_str):
                    st.success(f"Deleted data for {date_str}")
                else:
                    st.error(f"Failed to delete data for {date_str}")
    
    if not edited_df.equals(df):
        for _, row in edited_df.iterrows():
            if pd.notna(row["Date"]) and pd.notna(row["Total Stock"]) and pd.notna(row["Total Positive"]):
                if row["Total Stock"] > 0:
                    positive_change = (row["Total Positive"] / row["Total Stock"]) * 100
                    label = get_label(positive_change)
                    
                    data_to_save = {
                        "date": row["Date"].strftime("%Y-%m-%d") if isinstance(row["Date"], (datetime, pd.Timestamp)) else row["Date"],
                        "total_positive": int(row["Total Positive"]),
                        "total_stock": int(row["Total Stock"]),
                        "positive_change_percentage": float(positive_change),
                        "label": label
                    }
                    
                    response = supabase.table('nepse_equity').upsert(data_to_save).execute()
                    
                    if response.data:
                        st.success(f"Updated data for {data_to_save['date']}")
                    else:
                        st.error(f"Failed to update data for {data_to_save['date']}")
        
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

def load_sector_data(sector):
    """Load data for a specific sector from Supabase."""
    try:
        response = supabase.table('sector_data').select("*").eq('sector', sector).execute()
        
        if response.data:
            df = pd.DataFrame(response.data)
            column_mapping = {
                'date': 'Date',
                'positive_stock': 'No of positive stock',
                'negative_stock': 'No of negative stock',
                'no_change': 'No of No change',
                'total_stock': 'No of total stock',
                'positive_percentage': 'Positive %',
                'label': 'Label'
            }
            df = df.rename(columns=column_mapping)
            df["Date"] = pd.to_datetime(df["Date"])
            return df
        else:
            return pd.DataFrame(columns=[
                "Date", "No of positive stock", "No of negative stock",
                "No of total stock", "No of No change", "Positive %", "Label"
            ])
    except Exception as e:
        st.error(f"Error loading data for {sector}: {e}")
        return pd.DataFrame(columns=[
            "Date", "No of positive stock", "No of negative stock",
            "No of total stock", "No of No change", "Positive %", "Label"
        ])

def delete_sector_data(sector, date):
    """Delete sector data from Supabase for a specific date."""
    try:
        if isinstance(date, (datetime, pd.Timestamp)):
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = pd.to_datetime(date).strftime("%Y-%m-%d")
        
        response = supabase.table('sector_data')\
            .delete()\
            .eq('sector', sector)\
            .eq('date', date_str)\
            .execute()
        
        if response.data:
            st.success(f"Successfully deleted {sector} data for {date_str}")
            return True
        else:
            st.error(f"No data found for {sector} on {date_str}")
            return False
            
    except Exception as e:
        st.error(f"Error deleting {sector} data for {date_str}: {str(e)}")
        return False

def delete_nepse_data(date):
    """Delete NEPSE data from Supabase for a specific date."""
    try:
        if isinstance(date, (datetime, pd.Timestamp)):
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = date
            
        response = supabase.table('nepse_equity').delete().eq('date', date_str).execute()
        return bool(response.data)
    except Exception as e:
        st.error(f"Error deleting NEPSE data: {e}")
        return False

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
