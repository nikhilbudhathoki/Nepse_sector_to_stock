import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client

# Configuration
SECTOR_DATE_COL = 'date'  # Changed to lowercase to match Supabase convention
from supabase import create_client



# Define allowed sectors with display names and database names mapping
SECTOR_MAPPING = {
    "Hydropower": "hydropower",
    "C. Bank": "c_bank",
    "D. Bank": "d_bank",
    "Finance": "finance",
    "Hotels": "hotels",
    "Microfinance": "microfinance",
    "Investments": "investments",
    "Life insurance": "life_insurance",
    "Non-life insurance": "non_life_insurance",
    "Others": "others",
    "Manufacture": "manufacture",
    "Tradings": "tradings"
}

ALLOWED_SECTORS = list(SECTOR_MAPPING.keys())
DB_COLUMNS = list(SECTOR_MAPPING.values())

# Define allowed sectors
ALLOWED_SECTORS = [
    "Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels",
    "Microfinance", "Investments", "Life insurance", "Non-life insurance",
    "Others", "Manufacture", "Tradings"
]

# Supabase configuration
SUPABASE_URL = "https://zjxwjeqgkanjcsrgmfri.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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
            font-size: 59px !important;
            transform: scale(9.5);
            transform-origin: top left;
            margin-bottom: 950px;
        }
        
        /* Extra specific styling for data editor calendar */
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
        
        /* Make calendar buttons larger */
        div[data-baseweb="calendar"] button {
            width: 50px !important;
            height: 50px !important;
            font-size: 28px !important;
        }
        
        /* Increase the cell size in data editor */
        .stDataEditor td[data-testid="stCellInput"] {
            min-width: 300px !important;
            padding: 20px !important;
            font-size: 18px !important;
        }
        
        /* Ensure calendar stays on top */
        div[data-baseweb="popover"] {
            z-index: 1000 !important;
        }
        
        /* Add more vertical space for the calendar popup */
        .stDataEditor {
            margin-bottom: 300px !important;
        }
    </style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=0, show_spinner="Loading sector data...")
def load_data():
    """Load and process data from Supabase with validation"""
    try:
        response = supabase.table('sector_weights').select('*').order('date').execute()
        
        if not response.data:
            return pd.DataFrame(columns=[SECTOR_DATE_COL] + ALLOWED_SECTORS)
            
        df = pd.DataFrame(response.data)
        
        # Drop the id and created_at columns
        df = df.drop(['id', 'created_at'], axis=1, errors='ignore')
        
        # Convert date column to datetime
        df[SECTOR_DATE_COL] = pd.to_datetime(df[SECTOR_DATE_COL])
        
        # Rename columns from database names to display names
        reverse_mapping = {v: k for k, v in SECTOR_MAPPING.items()}
        df = df.rename(columns=reverse_mapping)
        
        # Ensure all sectors exist with default values
        for sector in ALLOWED_SECTORS:
            if sector not in df.columns:
                df[sector] = 0.0
                
        return df.sort_values(SECTOR_DATE_COL)
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        st.write("Full error:", e)  # Debug line
        return None

def save_sector_data(edited_df):
    """Save sector data to Supabase"""
    try:
        # Create a copy and convert dates
        save_df = edited_df.copy()
        save_df[SECTOR_DATE_COL] = save_df[SECTOR_DATE_COL].apply(lambda x: x.strftime('%Y-%m-%d'))
        
        # Rename columns to database names
        save_df = save_df.rename(columns=SECTOR_MAPPING)
        
        # Convert to float for numeric columns
        for col in DB_COLUMNS:
            save_df[col] = save_df[col].astype(float)
        
        # Convert to records
        records = save_df.to_dict('records')
        
        # Debug output
        st.write("Debug - First record to be saved:", records[0])
        
        # Delete existing records
        supabase.table('sector_weights').delete().neq('id', 0).execute()
        
        # Insert new records
        for record in records:
            response = supabase.table('sector_weights').insert(record).execute()
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Insert error: {response.error}")
        
        return True
    except Exception as e:
        st.error(f"Save error: {str(e)}")
        st.write("Full error:", e)  # Debug line
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
    
    # Add connection status indicator
    try:
        supabase.table('sector_weights').select('date').limit(1).execute()
        st.sidebar.success('🟢 Connected to database')
    except Exception as e:
        st.sidebar.error('🔴 Database connection failed')
        st.error(f"Database connection error: {str(e)}")
        return
    
    # Load sector data
    sector_data = load_data()
    
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

