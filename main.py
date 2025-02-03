import streamlit as st
import pandas as pd
import os
import plotly.express as px

# Configuration
SECTOR_FILE = "sector.csv"
SECTOR_DATE_COL = 'DATE'

def load_data(file_path, date_col):
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        return df.dropna(subset=[date_col])
    return None

def save_sector_data(df):
    try:
        df.to_csv(SECTOR_FILE, index=False)
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")

def calculate_sector_values(df):
    st.header("📈 Sector-Specific Calculations")
    
    sector_stocks = {
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
    
    sector_mappings = {
        'CBANK': 'Commercial Bank',
        'DBANK': 'Development Bank',
        'FINANCE': 'Finance',
        'MF': 'Micro Finance',
        'HOTEL': 'Hotels',
        'NON-LIFE': 'Non-Life Insurance',
        'LIFE': 'Life Insurance',
        'OTHERS': 'Others',
        'INV': 'Investment',
        'HYDRO': 'Hydropower',
        'MANU': 'Manufacture',
        'TRADING': 'Trading'
    }
    
    calculations_df = df.copy()
    for col, sector in sector_mappings.items():
        if col in calculations_df.columns:
            value_col = f"{sector.replace(' ', '_').replace('-', '_')}_Value"
            calculations_df[value_col] = (calculations_df[col] / sector_stocks[sector]) * 100
    
    available_sectors = list(sector_stocks.keys())
    selected_sectors = st.multiselect("Select Sectors to Display", ["All"] + available_sectors, default=["Commercial Bank", "Development Bank"])
    
    if "All" in selected_sectors:
        selected_sectors = available_sectors
    
    sector_columns = [f"{sector.replace(' ', '_').replace('-', '_')}_Value" for sector in selected_sectors]
    available_columns = [col for col in sector_columns if col in calculations_df.columns]
    
    if not available_columns:
        st.error("⚠️ No data available for selected sectors.")
        return
    
    display_df = calculations_df[[SECTOR_DATE_COL] + available_columns]
    st.write("📊 Calculated Sector Values:")
    st.dataframe(display_df)
    
    melted_df = display_df.melt(id_vars=[SECTOR_DATE_COL], value_vars=available_columns, var_name="Sector", value_name="Value")
    fig = px.line(melted_df, x=SECTOR_DATE_COL, y="Value", color="Sector", title="📈 Sector-Specific Value Trends Over Time", template="seaborn")
    fig.update_layout(xaxis=dict(rangeslider=dict(visible=True), type='date'), yaxis=dict(fixedrange=False))
    st.plotly_chart(fig, use_container_width=True)
    
    with st.expander("✏️ Edit Sector Values", expanded=False):
        editable_columns = [SECTOR_DATE_COL] + list(sector_mappings.keys())
        editable_df = df[editable_columns].copy()
        edited_data = st.data_editor(editable_df, num_rows="dynamic")
        
        if st.button("💾 Save Edited Data", use_container_width=True):
            df.update(edited_data)
            save_sector_data(df)
            st.success("✅ Sector data updated successfully!")
            st.experimental_rerun()

def main():
    st.title("🚀 NEPSE Advanced Sentiment Dashboard - Sector-Specific Calculations")
    sector_data = load_data(SECTOR_FILE, SECTOR_DATE_COL)
    if sector_data is None:
        st.warning("⚠️ Please upload sector data CSV file.")
        return
    calculate_sector_values(sector_data)

if __name__ == "__main__":
    main()