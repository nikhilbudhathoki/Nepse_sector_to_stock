import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# Configuration
SECTOR_FILE = "sector.csv"
SECTOR_DATE_COL = 'DATE'

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

# Enhanced CSS with much larger calendar and fixed zoom issues
st.markdown("""
    <style>
        /* General date input styling */
        .stDateInput {
            min-width: 4000px !important;
        }
        
        /* Main view calendar styling */
        div[data-baseweb="calendar"] {
            font-size: 59px !important;  /* Increased font size */
            transform: scale(9.5);  /* Increased scale */
            transform-origin: top left;
            margin-bottom: 950px;  /* Increased margin */
        }
        
        /* Extra specific styling for data editor calendar */
        .stDataEditor div[data-baseweb="calendar"] {
            font-size: 58px !important;  /* Increased font size */
            transform: scale(9.0) !important;  /* Increased scale */
            transform-origin: top left;
            background-color: white;
            padding: 90px;  /* Increased padding */
            border-radius: 52px;
            box-shadow: 0 6px 12px rgba(0, 0, 0, 0.15);
            z-index: 1000;
            position: relative;
            margin: 30px 0 200px 0;  /* Increased margin */
        }
        
        /* Make calendar buttons larger */
        div[data-baseweb="calendar"] button {
            width: 50px !important;  /* Increased button width */
            height: 50px !important;  /* Increased button height */
            font-size: 28px !important;  /* Increased font size */
        }
        
        /* Increase the cell size in data editor */
        .stDataEditor td[data-testid="stCellInput"] {
            min-width: 300px !important;  /* Increased cell width */
            padding: 20px !important;  /* Increased padding */
            font-size: 18px !important;  /* Increased font size */
        }
        
        /* Ensure calendar stays on top */
        div[data-baseweb="popover"] {
            z-index: 1000 !important;
        }
        
        /* Add more vertical space for the calendar popup */
        .stDataEditor {
            margin-bottom: 300px !important;  /* Increased margin */
        }
    </style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=0, show_spinner="Loading sector data...")
def load_data(file_path):
    """Load and process data from CSV file with validation"""
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=[SECTOR_DATE_COL] + ALLOWED_SECTORS)
        df[SECTOR_DATE_COL] = pd.to_datetime(df[SECTOR_DATE_COL])
        return df
    
    df = pd.read_csv(file_path)
    
    if SECTOR_DATE_COL not in df.columns:
        st.error("Data validation failed: DATE column missing")
        return None
    
    try:
        valid_columns = [SECTOR_DATE_COL] + [col for col in ALLOWED_SECTORS if col in df.columns]
        df = df[valid_columns]
        
        for sector in ALLOWED_SECTORS:
            if sector not in df.columns:
                df[sector] = 0.0
        
        df[SECTOR_DATE_COL] = pd.to_datetime(df[SECTOR_DATE_COL], errors='coerce')
        return df.dropna(subset=[SECTOR_DATE_COL]).sort_values(SECTOR_DATE_COL)
    except Exception as e:
        st.error(f"Data processing error: {str(e)}")
        return None

def save_sector_data(edited_df):
    """Safely save sector data"""
    try:
        save_columns = [SECTOR_DATE_COL] + ALLOWED_SECTORS
        edited_df = edited_df[save_columns]
        
        temp_file = f"temp_sector_{datetime.now().timestamp()}.csv"
        edited_df.to_csv(temp_file, index=False)
        os.replace(temp_file, SECTOR_FILE)
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
    sector_data = load_data(SECTOR_FILE)
    
    if sector_data is None or sector_data.empty:
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
        # Add extra spacing for calendar
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
        
        # Add extra spacing after editor
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
