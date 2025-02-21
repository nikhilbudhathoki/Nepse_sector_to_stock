import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client
from datetime import datetime

# Configuration
SECTOR_DATE_COL = 'date'
TABLE_NAME = 'sector_calc'

# Initialize Supabase client with hardcoded credentials
def init_supabase():
    url = "https://zjxwjeqgkanjcsrgmfri.supabase.co"
    key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s"
    return create_client(url, key)

# Sector configurations remain the same
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

def safe_date_conversion(date_str):
    """Safely convert date string to datetime object"""
    try:
        if isinstance(date_str, str):
            return pd.to_datetime(date_str).date()
        elif isinstance(date_str, pd.Timestamp):
            return date_str.date()
        elif isinstance(date_str, datetime):
            return date_str.date()
        return date_str
    except Exception:
        return None

def load_data(supabase):
    """Load data from Supabase"""
    try:
        response = supabase.table(TABLE_NAME).select("*").execute()
        if response.data:
            df = pd.DataFrame(response.data)
            if SECTOR_DATE_COL not in df.columns:
                st.error(f"Required column '{SECTOR_DATE_COL}' not found in the data.")
                return None
            
            df[SECTOR_DATE_COL] = pd.to_datetime(df[SECTOR_DATE_COL], errors='coerce')
            df = df.dropna(subset=[SECTOR_DATE_COL])
            
            numeric_cols = list(SECTOR_MAPPINGS.keys())
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            return df.sort_values(SECTOR_DATE_COL)
        return pd.DataFrame(columns=[SECTOR_DATE_COL] + list(SECTOR_MAPPINGS.keys()))
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

def save_sector_data(supabase, data, date):
    """Create or update sector data for a specific date"""
    try:
        formatted_date = safe_date_conversion(date)
        if formatted_date is None:
            st.error("Invalid date format")
            return False
        
        save_data = {k: float(v) if isinstance(v, (int, float)) else v 
                    for k, v in data.items()}
        save_data[SECTOR_DATE_COL] = formatted_date.strftime('%Y-%m-%d')
        save_data = {k: v for k, v in save_data.items() if pd.notna(v)}
        
        response = supabase.table(TABLE_NAME).upsert(
            save_data,
            on_conflict='date'
        ).execute()
        
        return True
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        return False

def delete_sector_data(supabase, date):
    """Delete sector data for a specific date"""
    try:
        formatted_date = safe_date_conversion(date)
        if formatted_date is None:
            st.error("Invalid date format")
            return False
        
        check_existing = supabase.table(TABLE_NAME)\
            .select("*")\
            .eq(SECTOR_DATE_COL, formatted_date.strftime('%Y-%m-%d'))\
            .execute()
            
        if not check_existing.data:
            st.warning(f"No data found for {formatted_date}")
            return False
            
        response = supabase.table(TABLE_NAME)\
            .delete()\
            .eq(SECTOR_DATE_COL, formatted_date.strftime('%Y-%m-%d'))\
            .execute()
        
        return True if response.data else False
    except Exception as e:
        st.error(f"Error deleting data: {str(e)}")
        return False

def calculate_sector_values(df):
    """Calculate and display sector-specific values"""
    if df is None or df.empty:
        st.warning("No data available for analysis")
        return None
        
    st.header("📈 Sector-Specific Calculations")
    
    try:
        calculations_df = df.copy()
        for col, sector in SECTOR_MAPPINGS.items():
            if col in calculations_df.columns:
                value_col = f"{sector.replace(' ', '_').replace('-', '_')}_Value"
                calculations_df[value_col] = (calculations_df[col] / SECTOR_STOCKS[sector]) * 100
        
        available_sectors = list(SECTOR_STOCKS.keys())
        selected_sectors = st.multiselect(
            "Select Sectors to Display",
            ["All"] + available_sectors,
            default=["Commercial Bank", "Development Bank"]
        )
        
        if "All" in selected_sectors:
            selected_sectors = available_sectors
        
        sector_columns = [f"{sector.replace(' ', '_').replace('-', '_')}_Value" 
                         for sector in selected_sectors]
        available_columns = [col for col in sector_columns if col in calculations_df.columns]
        
        if not available_columns:
            st.error("⚠️ No data available for selected sectors.")
            return None
        
        display_df = calculations_df[[SECTOR_DATE_COL] + available_columns].copy()
        st.write("📊 Calculated Sector Values:")
        st.dataframe(display_df)
        
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
    except Exception as e:
        st.error(f"Error in calculations: {str(e)}")
        return None

def data_editor_section(supabase, df):
    """Data editor section with improved CRUD operations"""
    with st.expander("✏️ Edit Sector Values", expanded=False):
        st.subheader("Add New Entry")
        col1, col2 = st.columns(2)
        
        with col1:
            new_date = st.date_input("Select Date", datetime.now())
        
        with st.form(key="new_entry_form"):
            cols = st.columns(3)
            new_values = {}
            
            for idx, (key, sector) in enumerate(SECTOR_MAPPINGS.items()):
                col_idx = idx % 3
                with cols[col_idx]:
                    new_values[key] = st.number_input(
                        f"{sector}",
                        value=0.0,
                        format="%.2f",
                        key=f"new_{key}"
                    )
            
            submit_button = st.form_submit_button(label="➕ Add New Entry")
            if submit_button:
                existing_data = supabase.table(TABLE_NAME)\
                    .select("*")\
                    .eq(SECTOR_DATE_COL, new_date.strftime('%Y-%m-%d'))\
                    .execute()
                
                if existing_data.data:
                    st.error(f"Entry for {new_date} already exists. Please use the edit section below.")
                else:
                    new_data = {
                        SECTOR_DATE_COL: new_date,
                        **new_values
                    }
                    if save_sector_data(supabase, new_data, new_date):
                        st.success("✅ New entry added successfully!")
                        st.experimental_rerun()

        st.subheader("Edit Existing Entries")
        if df is not None and not df.empty:
            df_sorted = df.sort_values(SECTOR_DATE_COL, ascending=False)
            editable_columns = [SECTOR_DATE_COL] + list(SECTOR_MAPPINGS.keys())
            edited_df = df_sorted[editable_columns].copy()
            
            selected_indices = st.multiselect(
                "Select rows to delete:",
                options=edited_df.index.tolist(),
                format_func=lambda x: f"{edited_df.loc[x, SECTOR_DATE_COL].strftime('%Y-%m-%d')}"
            )
            
            edited_data = st.data_editor(
                edited_df,
                key=f"sector_editor_{df.shape[0]}",
                disabled=[SECTOR_DATE_COL],
                hide_index=True
            )

            col1, col2 = st.columns(2)
            
            with col1:
                if st.button("💾 Save Changes", use_container_width=True):
                    changes_made = False
                    for idx, row in edited_data.iterrows():
                        original_row = df_sorted.loc[idx]
                        if not row.equals(original_row):
                            if save_sector_data(supabase, row.to_dict(), row[SECTOR_DATE_COL]):
                                changes_made = True
                    
                    if changes_made:
                        st.success("✅ Changes saved successfully!")
                        st.experimental_rerun()
                    else:
                        st.info("No changes detected.")
            
            with col2:
                if selected_indices and st.button("🗑️ Delete Selected Rows", use_container_width=True):
                    success = True
                    for idx in selected_indices:
                        date_to_delete = edited_df.loc[idx, SECTOR_DATE_COL]
                        if not delete_sector_data(supabase, date_to_delete):
                            success = False
                            st.error(f"Failed to delete entry for {date_to_delete}")
                    
                    if success:
                        st.success("✅ Selected entries deleted successfully!")
                        st.experimental_rerun()
        else:
            st.info("No existing entries to edit.")

def main():
    st.title("🚀 NEPSE Advanced Sentiment Dashboard - Sector-Specific Calculations")
    
    supabase = init_supabase()
    if not supabase:
        return
    
    sector_data = load_data(supabase)
    if sector_data is None:
        st.error("Failed to load data from database.")
        return
    
    if sector_data.empty:
        st.info("📝 No data available. Start by adding sector data using the editor below.")
    
    calculations_df = calculate_sector_values(sector_data)
    data_editor_section(supabase, sector_data)

if __name__ == "__main__":
    main()
