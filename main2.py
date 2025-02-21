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
    """Save sector data to Supabase with improved error handling"""
    try:
        # Create a copy and convert dates
        save_df = edited_df.copy()
        
        # Convert date column to datetime first
        save_df[SECTOR_DATE_COL] = pd.to_datetime(save_df[SECTOR_DATE_COL])
        
        # Now format as string
        save_df[SECTOR_DATE_COL] = save_df[SECTOR_DATE_COL].dt.strftime('%Y-%m-%d')
        
        # Rename columns to database names
        save_df = save_df.rename(columns=SECTOR_MAPPING)
        
        # Verify all required columns exist
        missing_columns = set(DB_COLUMNS) - set(save_df.columns)
        if missing_columns:
            raise ValueError(f"Missing columns in DataFrame: {missing_columns}")
            
        # Convert to float for numeric columns
        for col in DB_COLUMNS:
            save_df[col] = save_df[col].astype(float)
        
        # Debug: Print the exact data being sent
        st.write("Debug - Data being sent to database:")
        st.write(save_df.head())
        st.write("Column names:", save_df.columns.tolist())
        
        # Convert to records
        records = save_df.to_dict('records')
        
        # Delete existing records
        delete_response = supabase.table('sector_weights').delete().neq('id', 0).execute()
        st.write("Debug - Delete response:", delete_response)
        
        # Insert new records
        for record in records:
            # Debug: Print each record before insertion
            st.write("Debug - Inserting record:", record)
            
            response = supabase.table('sector_weights').insert(record).execute()
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Insert error: {response.error}")
        
        return True
        
    except ValueError as ve:
        st.error(f"Validation error: {str(ve)}")
        return False
    except Exception as e:
        st.error(f"Save error: {str(e)}")
        st.write("Full error:", e)
        st.write("Error type:", type(e).__name__)
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


def handle_data_changes(edited_df, previous_df):
    """Handle CRUD operations by comparing edited data with previous data"""
    try:
        if previous_df is None or previous_df.empty:
            # If no previous data, treat all rows as new
            return handle_create_all(edited_df)
            
        # Convert date columns to datetime for comparison
        edited_df[SECTOR_DATE_COL] = pd.to_datetime(edited_df[SECTOR_DATE_COL])
        previous_df[SECTOR_DATE_COL] = pd.to_datetime(previous_df[SECTOR_DATE_COL])
        
        # Identify deleted rows
        deleted_dates = set(previous_df[SECTOR_DATE_COL]) - set(edited_df[SECTOR_DATE_COL])
        if deleted_dates:
            handle_deletes(deleted_dates)
            
        # Identify new and updated rows
        for idx, row in edited_df.iterrows():
            current_date = row[SECTOR_DATE_COL]
            
            # Check if this is a new row
            if current_date not in previous_df[SECTOR_DATE_COL].values:
                handle_create(row)
            else:
                # Check if row was modified
                prev_row = previous_df[previous_df[SECTOR_DATE_COL] == current_date].iloc[0]
                if not row.equals(prev_row):
                    handle_update(row)
        
        return True
    except Exception as e:
        st.error(f"Error handling data changes: {str(e)}")
        return False

def handle_create_all(df):
    """Handle initial data creation"""
    try:
        save_df = prepare_dataframe_for_save(df)
        records = save_df.to_dict('records')
        
        for record in records:
            response = supabase.table('sector_weights').insert(record).execute()
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Insert error: {response.error}")
        return True
    except Exception as e:
        st.error(f"Error creating records: {str(e)}")
        return False

def handle_create(row):
    """Handle single row creation"""
    try:
        record = prepare_row_for_save(row)
        response = supabase.table('sector_weights').insert(record).execute()
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Insert error: {response.error}")
        st.success(f"Added record for date: {record['date']}")
    except Exception as e:
        st.error(f"Error creating record: {str(e)}")

def handle_update(row):
    """Handle single row update"""
    try:
        record = prepare_row_for_save(row)
        response = supabase.table('sector_weights')\
            .update(record)\
            .eq('date', record['date'])\
            .execute()
        if hasattr(response, 'error') and response.error:
            raise Exception(f"Update error: {response.error}")
        st.success(f"Updated record for date: {record['date']}")
    except Exception as e:
        st.error(f"Error updating record: {str(e)}")

def handle_deletes(deleted_dates):
    """Handle deletion of rows"""
    try:
        for date in deleted_dates:
            formatted_date = date.strftime('%Y-%m-%d')
            response = supabase.table('sector_weights')\
                .delete()\
                .eq('date', formatted_date)\
                .execute()
            if hasattr(response, 'error') and response.error:
                raise Exception(f"Delete error: {response.error}")
            st.success(f"Deleted record for date: {formatted_date}")
    except Exception as e:
        st.error(f"Error deleting records: {str(e)}")

def prepare_dataframe_for_save(df):
    """Prepare DataFrame for saving to database"""
    save_df = df.copy()
    save_df[SECTOR_DATE_COL] = pd.to_datetime(save_df[SECTOR_DATE_COL])
    save_df[SECTOR_DATE_COL] = save_df[SECTOR_DATE_COL].dt.strftime('%Y-%m-%d')
    save_df = save_df.rename(columns=SECTOR_MAPPING)
    
    for col in DB_COLUMNS:
        save_df[col] = save_df[col].astype(float)
    
    return save_df

def prepare_row_for_save(row):
    """Prepare single row for saving to database"""
    record = row.copy()
    record[SECTOR_DATE_COL] = pd.to_datetime(record[SECTOR_DATE_COL]).strftime('%Y-%m-%d')
    
    # Convert to dictionary and rename columns
    record_dict = record.to_dict()
    renamed_dict = {SECTOR_MAPPING.get(k, k): v for k, v in record_dict.items()}
    
    return renamed_dict
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
    
    # Store the current state of data before editing
    if 'previous_data' not in st.session_state:
        st.session_state.previous_data = sector_data.copy()
    
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
    
    # Add summary statistics
    st.markdown("---")
    if not sector_data.empty:
        with st.expander("📊 Summary Statistics", expanded=False):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric(
                    "Total Records",
                    len(sector_data),
                    "Available Dates"
                )
                
            with col2:
                date_range = f"{sector_data[SECTOR_DATE_COL].min().strftime('%Y-%m-%d')} to {sector_data[SECTOR_DATE_COL].max().strftime('%Y-%m-%d')}"
                st.metric(
                    "Date Range",
                    date_range
                )
                
            with col3:
                total_weight = sector_data[ALLOWED_SECTORS].sum(axis=1).mean()
                st.metric(
                    "Avg Total Weight",
                    f"{total_weight:.2f}%"
                )
    
    # Data editor section
    st.markdown("---")
    with st.expander("✏️ Edit Sector Weights", expanded=True):
        st.markdown("<div style='height: 40px'></div>", unsafe_allow_html=True)
        
        # Add instructions
        st.info("""
        📝 Instructions:
        - Add new row: Click '+' at bottom
        - Edit: Click cell to modify
        - Delete: Select row(s) and press 'Delete' key
        - All changes saved automatically
        """)
        
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
            height=400,
            key="sector_editor",
            use_container_width=True
        )
        
        # Add data validation feedback
        if not edited_data.empty:
            total_weights = edited_data[ALLOWED_SECTORS].sum(axis=1)
            invalid_dates = edited_data[total_weights < 99.9][SECTOR_DATE_COL].tolist()
            
            if invalid_dates:
                st.warning(f"⚠️ Total weights less than 100% for dates: {', '.join([d.strftime('%Y-%m-%d') for d in invalid_dates])}")
        
        st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("💾 Save Changes", type="primary", use_container_width=True):
                if edited_data[SECTOR_DATE_COL].duplicated().any():
                    st.error("❌ Duplicate dates found. Please ensure unique dates.")
                elif handle_data_changes(edited_data, st.session_state.previous_data):
                    st.success("✅ All changes saved successfully! Refreshing...")
                    st.session_state.previous_data = edited_data.copy()
                    st.cache_data.clear()
                    st.rerun()
        
        with col2:
            # Add download button for current data
            if not edited_data.empty:
                csv = edited_data.to_csv(index=False)
                st.download_button(
                    label="📥 Download Data as CSV",
                    data=csv,
                    file_name="sector_weights.csv",
                    mime="text/csv",
                    use_container_width=True
                )
    
    # Add footer
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <small>Last updated: {}</small>
        </div>
        """.format(datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()
