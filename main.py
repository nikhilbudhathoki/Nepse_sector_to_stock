import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
SECTOR_DATE_COL = 'date'
TABLE_NAME = 'sector_calc'

# Initialize Supabase client
def init_supabase():
    url = "https://zjxwjeqgkanjcsrgmfri.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s"
    if not url or not key:
        st.error("Missing Supabase credentials. Please check your .env file.")
        return None
    return create_client(url, key)

# Sector configurations
SECTOR_STOCKS = {
    'Commercial Bank': 19,
    'Development Bank': 15,
    'Finance': 15,
    'Micro Finance': 50,
    'Hotels': 6,
    'Non-Life Insurance': 12,
    'Life Insurance': 12,
    'Others': 6,
    'Investment': 7,
    'Hydropower': 91,
    'Manufacture': 9,
    'Trading': 2
}

SECTOR_MAPPINGS = {
    'cbank': 'Commercial Bank',
    'dbank': 'Development Bank',
    'finance': 'Finance',
    'mf': 'Micro Finance',
    'hotel': 'Hotels',
    'non_life': 'Non-Life Insurance',
    'life': 'Life Insurance',
    'others': 'Others',
    'inv': 'Investment',
    'hydro': 'Hydropower',
    'manu': 'Manufacture',
    'trading': 'Trading'
}

def load_data(supabase):
    """Load data from Supabase"""
    try:
        response = supabase.table(TABLE_NAME).select("*").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df[SECTOR_DATE_COL] = pd.to_datetime(df[SECTOR_DATE_COL])
            return df.sort_values(SECTOR_DATE_COL)
        return pd.DataFrame(columns=[SECTOR_DATE_COL] + list(SECTOR_MAPPINGS.keys()))
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def save_sector_data(supabase, data, date):
    """Create or update sector data for a specific date"""
    try:
        # Convert date to string format
        data[SECTOR_DATE_COL] = date.strftime('%Y-%m-%d')
        
        # Upsert data
        response = supabase.table(TABLE_NAME).upsert(data).execute()
        return True
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        return False

def delete_sector_data(supabase, date):
    """Delete sector data for a specific date"""
    try:
        response = supabase.table(TABLE_NAME)\
            .delete()\
            .eq(SECTOR_DATE_COL, date.strftime('%Y-%m-%d'))\
            .execute()
        return True
    except Exception as e:
        st.error(f"Error deleting data: {str(e)}")
        return False

def calculate_sector_values(df):
    """Calculate and display sector-specific values"""
    st.header("📈 Sector-Specific Calculations")
    
    calculations_df = df.copy()
    for col, sector in SECTOR_MAPPINGS.items():
        if col in calculations_df.columns:
            value_col = f"{sector.replace(' ', '_').replace('-', '_')}_Value"
            calculations_df[value_col] = (calculations_df[col] / SECTOR_STOCKS[sector]) * 100
    
    # Sector selection
    available_sectors = list(SECTOR_STOCKS.keys())
    selected_sectors = st.multiselect(
        "Select Sectors to Display",
        ["All"] + available_sectors,
        default=["Commercial Bank", "Development Bank"]
    )
    
    if "All" in selected_sectors:
        selected_sectors = available_sectors
    
    # Prepare data for display
    sector_columns = [f"{sector.replace(' ', '_').replace('-', '_')}_Value" 
                     for sector in selected_sectors]
    available_columns = [col for col in sector_columns if col in calculations_df.columns]
    
    if not available_columns:
        st.error("⚠️ No data available for selected sectors.")
        return
    
    # Display data and chart
    display_df = calculations_df[[SECTOR_DATE_COL] + available_columns]
    st.write("📊 Calculated Sector Values:")
    st.dataframe(display_df)
    
    # Create interactive plot
    melted_df = display_df.melt(
        id_vars=[SECTOR_DATE_COL],
        value_vars=available_columns,
        var_name="Sector",
        value_name="Value"
    )
    fig = px.line(
        melted_df,
        x=SECTOR_DATE_COL,
        y="Value",
        color="Sector",
        title="📈 Sector-Specific Value Trends Over Time",
        template="seaborn"
    )
    fig.update_layout(
        xaxis=dict(rangeslider=dict(visible=True), type='date'),
        yaxis=dict(fixedrange=False)
    )
    st.plotly_chart(fig, use_container_width=True)
    
    return calculations_df

def data_editor_section(supabase, df):
    """Data editor section with CRUD operations"""
    with st.expander("✏️ Edit Sector Values", expanded=False):
        # Create new entry section
        st.subheader("Add New Entry")
        col1, col2 = st.columns(2)
        with col1:
            new_date = st.date_input("Select Date", datetime.now())
        with col2:
            if st.button("➕ Add New Entry", use_container_width=True):
                new_data = {
                    SECTOR_DATE_COL: new_date,
                    **{sector: 0.0 for sector in SECTOR_MAPPINGS.keys()}
                }
                if save_sector_data(supabase, new_data, new_date):
                    st.success("✅ New entry added successfully!")
                    st.experimental_rerun()

        # Edit existing entries
        st.subheader("Edit Existing Entries")
        editable_columns = [SECTOR_DATE_COL] + list(SECTOR_MAPPINGS.keys())
        edited_df = df[editable_columns].copy() if not df.empty else pd.DataFrame(columns=editable_columns)
        edited_data = st.data_editor(
            edited_df,
            num_rows="dynamic",
            key="sector_editor"
        )

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Changes", use_container_width=True):
                for idx, row in edited_data.iterrows():
                    save_sector_data(supabase, row.to_dict(), row[SECTOR_DATE_COL])
                st.success("✅ Changes saved successfully!")
                st.experimental_rerun()
        
        with col2:
            if st.button("🗑️ Delete Selected Entry", use_container_width=True):
                if 'sector_editor' in st.session_state and st.session_state.sector_editor["edited_rows"]:
                    selected_date = edited_data.iloc[
                        st.session_state.sector_editor["edited_rows"][0]
                    ][SECTOR_DATE_COL]
                    if delete_sector_data(supabase, selected_date):
                        st.success(f"✅ Data for {selected_date.strftime('%Y-%m-%d')} deleted successfully!")
                        st.experimental_rerun()

def main():
    st.title("🚀 NEPSE Advanced Sentiment Dashboard - Sector-Specific Calculations")
    
    # Initialize Supabase client
    supabase = init_supabase()
    if not supabase:
        return
    
    # Load data
    sector_data = load_data(supabase)
    if sector_data is None:
        st.error("Failed to load data from database.")
        return
    
    if sector_data.empty:
        st.info("📝 No data available. Start by adding sector data using the editor below.")
    
    # Calculate and display sector values
    calculations_df = calculate_sector_values(sector_data)
    
    # Data editor section
    data_editor_section(supabase, sector_data)

if __name__ == "__main__":
    main()
