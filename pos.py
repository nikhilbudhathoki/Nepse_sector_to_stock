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


import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client

# Configuration
SECTOR_DATE_COL = 'DATE'


# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Define allowed sectors
ALLOWED_SECTORS = [
    "Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels",
    "Microfinance", "Investments", "Life insurance", "Non-life insurance",
    "Others", "Manufacture", "Tradings"
]

# Set page config
st.set_page_config(
    page_title="NEPSE Sector Analysis",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS (same as original)
st.markdown("""
    <style>
        .stDateInput {
            min-width: 4000px !important;
        }
        
        div[data-baseweb="calendar"] {
            font-size: 59px !important;
            transform: scale(9.5);
            transform-origin: top left;
            margin-bottom: 950px;
        }
        
        .stDataEditor div[data-baseweb="calendar"] {
            font-size: 58px !important;
            transform: scale(9.0) !important;
            transform-origin: top left;
            background-color: white;
            padding: 90px;
            border-radius: 52px;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            position: relative;
            margin: 30px 0 200px 0;
        }
        
        div[data-baseweb="calendar"] button {
            width: 50px !important;
            height: 50px !important;
            font-size: 28px !important;
        }
        
        .stDataEditor td[data-testid="stCellInput"] {
            min-width: 300px !important;
            padding: 20px !important;
            font-size: 18px !important;
        }
        
        div[data-baseweb="popover"] {
            z-index: 1000 !important;
        }
        
        .stDataEditor {
            margin-bottom: 300px !important;
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=0, show_spinner="Loading sector data...")
def load_data():
    """Load and process data from Supabase with validation"""
    try:
        response = supabase.table('sector_weights').select("*").execute()
        if not response.data:
            return pd.DataFrame(columns=[SECTOR_DATE_COL] + ALLOWED_SECTORS)
        
        df = pd.DataFrame(response.data)
        df[SECTOR_DATE_COL] = pd.to_datetime(df['date'])
        
        # Rename columns to match expected format
        for sector in ALLOWED_SECTORS:
            if f"{sector.lower()}_weight" in df.columns:
                df[sector] = df[f"{sector.lower()}_weight"]
        
        # Select only required columns
        df = df[[SECTOR_DATE_COL] + ALLOWED_SECTORS]
        
        return df.sort_values(SECTOR_DATE_COL)
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        return pd.DataFrame(columns=[SECTOR_DATE_COL] + ALLOWED_SECTORS)

def save_sector_data(edited_df):
    """Safely save sector data to Supabase"""
    try:
        # Convert DataFrame to Supabase format
        records = []
        for _, row in edited_df.iterrows():
            record = {
                'date': row[SECTOR_DATE_COL].strftime('%Y-%m-%d'),
                **{f"{sector.lower()}_weight": float(row[sector]) 
                   for sector in ALLOWED_SECTORS}
            }
            records.append(record)
        
        # Delete existing data and insert new data
        supabase.table('sector_weights').delete().neq('id', 0).execute()
        supabase.table('sector_weights').insert(records).execute()
        
        return True
    except Exception as e:
        st.error(f"Save error: {str(e)}")
        return False

def create_sector_chart(data, selected_date):
    """Create sector bar chart for selected date"""
    df_filtered = data[data[SECTOR_DATE_COL].dt.date == selected_date]
    
    if df_filtered.empty:
        return None
    
    plot_data = df_filtered.melt(
        id_vars=[SECTOR_DATE_COL],
        value_vars=ALLOWED_SECTORS,
        var_name="Sector",
        value_name="Weight"
    )
    
    fig = px.bar(
        plot_data,
        x="Sector",
        y="Weight",
        title=f"Sector Weights on {selected_date}",
        labels={"Weight": "Weight (%)"},
        text_auto=True,
        color="Sector"
    )
    fig.update_layout(
        showlegend=False,
        height=600,
        title_x=0.5,
        title_font_size=20
    )
    fig.update_traces(textposition='outside')
    return fig

def create_sector_time_series(data, selected_sector):
    """Create time series chart for selected sector"""
    if selected_sector not in data.columns:
        return None
    
    fig = px.line(
        data,
        x=SECTOR_DATE_COL,
        y=selected_sector,
        title=f"{selected_sector} Weight Over Time",
        labels={selected_sector: "Weight (%)", SECTOR_DATE_COL: "Date"}
    )
    fig.update_layout(
        height=600,
        title_x=0.5,
        title_font_size=20
    )
    return fig

def main():
    st.title("📊 NEPSE Sector Analysis")
    
    # Load sector data
    sector_data = load_data()
    
    if sector_data.empty:
        st.warning("⚠️ No sector data available. Please add data using the editor below.")
        sector_data = pd.DataFrame(columns=[SECTOR_DATE_COL] + ALLOWED_SECTORS)
    
    # Create two columns for the date selectors
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 View Sector Metrics")
        if not sector_data.empty and SECTOR_DATE_COL in sector_data.columns:
            view_date = st.date_input(
                "Select Date to View Metrics",
                value=sector_data[SECTOR_DATE_COL].max().date() if not sector_data.empty else datetime.now().date(),
                min_value=sector_data[SECTOR_DATE_COL].min().date() if not sector_data.empty else None,
                max_value=sector_data[SECTOR_DATE_COL].max().date() if not sector_data.empty else None,
                key="view_date"
            )
            
            # Create and display chart
            chart = create_sector_chart(sector_data, view_date)
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            else:
                st.warning(f"⚠️ No data available for {view_date}")
    
    with col2:
        st.subheader("📉 View Sector Over Time")
        selected_sector = st.selectbox(
            "Select Sector to View Over Time",
            ALLOWED_SECTORS,
            key="selected_sector"
        )
        
        # Create and display time series chart
        time_series_chart = create_sector_time_series(sector_data, selected_sector)
        if time_series_chart:
            st.plotly_chart(time_series_chart, use_container_width=True)
        else:
            st.warning(f"⚠️ No data available for {selected_sector}")
    
    # Data editor section
    st.markdown("---")
    with st.expander("✏️ Edit Sector Weights", expanded=True):
        st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True)
        
        edited_data = st.data_editor(
            sector_data,
            num_rows="dynamic",
            column_config={
                SECTOR_DATE_COL: st.column_config.DateColumn(
                    "Date",
                    format="YYYY-MM-DD",
                    required=True,
                    width="large"
                ),
                **{col: st.column_config.NumberColumn(
                    col,
                    format="%.2f %%",
                    min_value=0.0,
                    max_value=100.0,
                    required=True,
                    width="medium"
                ) for col in ALLOWED_SECTORS}
            },
            height=400
        )
        
        st.markdown("<div style='height: 200px'></div>", unsafe_allow_html=True)
        
        if st.button("💾 Save Changes", type="primary"):
            if edited_data[SECTOR_DATE_COL].duplicated().any():
                st.error("Duplicate dates found. Please ensure unique dates.")
            elif save_sector_data(edited_data):
                st.success("Data saved successfully! Refreshing...")
                st.cache_data.clear()
                st.rerun()

if __name__ == "__main__":
    main()
