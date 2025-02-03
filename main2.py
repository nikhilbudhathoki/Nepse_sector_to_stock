import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Configuration
SECTOR_FILE = "sector.csv"
SECTOR_DATE_COL = 'DATE'

# Set page config

# Load data function
@st.cache_data
def load_data(file_path, date_col):
    """Load and process data from CSV file"""
    if os.path.exists(file_path):
        df = pd.read_csv(file_path)
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        return df.dropna(subset=[date_col])
    return None

def save_sector_data(df):
    """Safely save sector data to file"""
    try:
        temp_file = "temp_sector.csv"
        df.to_csv(temp_file, index=False)
        os.replace(temp_file, SECTOR_FILE)
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")

# Load sector data
sector_data = load_data(SECTOR_FILE, SECTOR_DATE_COL)

st.title("📊 NEPSE Sector Analysis")
def main():
    st.title("📊 NEPSE Sector Analysis")
    if sector_data is None:
        st.warning("⚠️ Please upload sector data CSV file.")
    else:
        available_sectors = ["All Sectors"] + sector_data.columns[1:].tolist()
        selected_sectors = st.multiselect(
            "Select Sectors for Comparison",
            available_sectors,
            default=["All Sectors"]
        )
        
        selected_date = st.date_input(
            "📅 Select Date",
            sector_data[SECTOR_DATE_COL].max().date(),
            format="YYYY-MM-DD"
        )
        
        if "All Sectors" in selected_sectors:
            selected_sectors = sector_data.columns[1:].tolist()
        
        df_filtered = sector_data[sector_data[SECTOR_DATE_COL].dt.date == selected_date][['DATE'] + selected_sectors]
        
        if df_filtered.empty:
            st.warning("⚠️ No data available for the selected date.")
        else:
            fig = px.bar(
                df_filtered.melt(id_vars=[SECTOR_DATE_COL], var_name="Sector", value_name="Weight"),
                x="Sector", y="Weight",
                title=f"📊 Sector Weights on {selected_date}",
                template="seaborn"
            )
            
            fig.update_layout(
                xaxis=dict(fixedrange=False),
                yaxis=dict(fixedrange=False)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("✏️ Edit Sector Weights", expanded=False):
            edited_data = st.data_editor(
                sector_data,
                num_rows="dynamic",
                column_config={
                    SECTOR_DATE_COL: st.column_config.DateColumn(
                        "Date",
                        format="YYYY-MM-DD",
                        step=1
                    )
                }
            )
            if st.button("💾 Save Sector Data"):
                save_sector_data(edited_data)
                st.cache_data.clear()  # Clear cached data
                st.success("✅ Sector data updated successfully!")
                st.experimental_rerun()  # Force rerun
                
if __name__ == "__main__":
    main()