import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client, Client

# Configuration
DATE_COL = 'date'        # Changed from 'DATE' to 'date'
SECTOR_COL = 'sector'      # Changed from 'SECTOR' to 'sector'
SMA_COLUMNS = ['10_SMA', '20_SMA', '50_SMA', '200_SMA']
ALLOWED_SECTORS = [
    "Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels",
    "Microfinance", "Investments", "Life insurance", "Non-life insurance",
    "Others", "Manufacture", "Tradings"
]

# Supabase setup (ensure your table "sma_data" in Supabase has columns: 
# date (DATE PRIMARY KEY), sector (TEXT NOT NULL), 10_SMA, 20_SMA, 50_SMA, 200_SMA)
SUPABASE_URL = "https://zjxwjeqgkanjcsrgmfri.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s"
TABLE_NAME = "sma_data"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Set page config
st.set_page_config(
    page_title="NEPSE SMA Analysis",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for better UI
st.markdown("""
    <style>
        /* General styling */
        .stDateInput, .stSelectbox {
            margin-bottom: 20px;
        }
        
        /* Data editor styling */
        .stDataEditor {
            margin-bottom: 30px;
        }
        
        /* Chart styling */
        .stPlotlyChart {
            margin-top: 20px;
        }
        
        /* Section headers */
        h2 {
            color: #2E86C1;
            border-bottom: 2px solid #2E86C1;
            padding-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# "Connection" to Supabase – returns the Supabase client.
@st.cache_resource
def create_connection():
    """Return the Supabase client (used as a connection)."""
    return supabase

@st.cache_data(ttl=0, show_spinner="Loading SMA data...")
def load_sma_data():
    """Load data from Supabase database with improved error handling."""
    try:
        client = create_connection()
        response = client.table(TABLE_NAME).select("*").execute()
        
        # Debugging: Log the raw response
        st.write("Supabase response:", response)

        # Extract data
        data = response.data
        if not data:
            st.warning("No data returned from Supabase.")
            return pd.DataFrame(columns=[DATE_COL, SECTOR_COL] + SMA_COLUMNS)
        
        # Convert to DataFrame
        df = pd.DataFrame(data)

        # Debugging: Check available columns
        st.write("Available columns:", df.columns.tolist())

        # Ensure 'date' column exists
        if DATE_COL not in df.columns:
            st.error(f"Column '{DATE_COL}' not found in data. Available columns: {df.columns.tolist()}")
            return pd.DataFrame(columns=[DATE_COL, SECTOR_COL] + SMA_COLUMNS)

        # Convert 'date' column to datetime format
        df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors="coerce")  # Converts errors to NaT
        
        # Check if conversion worked
        if df[DATE_COL].isna().sum() > 0:
            st.warning(f"Some dates could not be parsed. Check your Supabase data: {df[df[DATE_COL].isna()]}")
        
        return df.sort_values(DATE_COL)
    
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        return pd.DataFrame(columns=[DATE_COL, SECTOR_COL] + SMA_COLUMNS)

# Save data to Supabase
def save_sma_data(edited_df):
    """Save data to Supabase database with better error handling and validation."""
    try:
        client = create_connection()
        sector = edited_df[SECTOR_COL].iloc[0]
        
        # Ensure the DATE_COL column is in datetime format
        if not pd.api.types.is_datetime64_any_dtype(edited_df[DATE_COL]):
            edited_df[DATE_COL] = pd.to_datetime(edited_df[DATE_COL])
        
        # Convert dates to string format for Supabase
        edited_df = edited_df.copy()
        edited_df[DATE_COL] = edited_df[DATE_COL].dt.strftime("%Y-%m-%d")
        
        # Prepare data for insert
        data = edited_df.to_dict(orient="records")
        
        # Begin transaction-like operation
        # First delete existing records
        delete_response = client.table(TABLE_NAME)\
            .delete()\
            .eq(SECTOR_COL, sector)\
            .execute()
        
        # Then insert new records
        insert_response = client.table(TABLE_NAME)\
            .insert(data)\
            .execute()
        
        if insert_response.data:
            st.success(f"Successfully updated {sector} data!")
            return True
        else:
            st.error("Failed to save data: No response from database")
            return False
            
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        return False

# Create SMA time series chart
def create_sma_chart(data, selected_sector):
    """Create SMA time series chart for selected sector."""
    df_filtered = data[data[SECTOR_COL] == selected_sector]
    if df_filtered.empty:
        return None
    fig = px.line(
        df_filtered,
        x=DATE_COL,
        y=SMA_COLUMNS,
        title=f"SMA Analysis for {selected_sector}",
        labels={'value': 'SMA Value', DATE_COL: 'Date'},
        markers=True
    )
    fig.update_layout(
        height=600,
        title_x=0.5,
        legend_title='SMA Periods',
        hovermode='x unified'
    )
    return fig

# Create SMA comparison charts for all sectors
def create_comparison_charts(data):
    """Create SMA comparison charts for all sectors."""
    charts = []
    for sector in ALLOWED_SECTORS:
        sector_df = data[data[SECTOR_COL] == sector]
        if not sector_df.empty:
            fig = px.line(
                sector_df,
                x=DATE_COL,
                y=SMA_COLUMNS,
                title=f"{sector} SMA Trends",
                labels={'value': 'SMA Value', DATE_COL: 'Date'},
                markers=True
            )
            fig.update_layout(
                height=300,
                title_x=0.5,
                legend_title='SMA Periods',
                margin=dict(l=20, r=20, t=40, b=20),
                showlegend=False
            )
            charts.append(fig)
        else:
            charts.append(None)
    return charts

def delete_sma_data(sector, date):
    """Delete specific SMA data entry."""
    try:
        client = create_connection()
        
        # Ensure date is in correct format
        if isinstance(date, (datetime, pd.Timestamp)):
            date_str = date.strftime("%Y-%m-%d")
        else:
            date_str = pd.to_datetime(date).strftime("%Y-%m-%d")
        
        # Delete specific record
        response = client.table(TABLE_NAME)\
            .delete()\
            .eq(SECTOR_COL, sector)\
            .eq(DATE_COL, date_str)\
            .execute()
        
        if response.data:
            st.success(f"Successfully deleted {sector} data for {date_str}")
            return True
        else:
            st.error(f"No data found for {sector} on {date_str}")
            return False
            
    except Exception as e:
        st.error(f"Error deleting data: {str(e)}")
        return False
def display_sma_editor(sector_data, selected_sector):
    """Display enhanced SMA data editor with deletion and update capabilities."""
    try:
        edited_df = st.data_editor(
            sector_data,
            num_rows="dynamic",
            column_config={
                DATE_COL: st.column_config.DateColumn(
                    "Date",
                    format="YYYY-MM-DD",
                    required=True
                ),
                **{
                    sma: st.column_config.NumberColumn(
                        sma.replace('_', ' '),
                        help=f"{sma.split('_')[0]} days simple moving average",
                        min_value=0.0,
                        format="%.2f",
                        required=True
                    ) for sma in SMA_COLUMNS
                }
            },
            height=600,
            key='sma_editor',
            hide_index=True
        )
        
        # Handle deletions
        deleted_rows = set(sector_data.index) - set(edited_df.index)
        if deleted_rows:
            deletion_successful = False
            for idx in deleted_rows:
                row = sector_data.loc[idx]
                if pd.notna(row[DATE_COL]):
                    if delete_sma_data(selected_sector, row[DATE_COL]):
                        deletion_successful = True
            
            if deletion_successful:
                st.cache_data.clear()
                st.rerun()
        
        # Handle updates
        if not edited_df.equals(sector_data):
            edited_df[SECTOR_COL] = selected_sector
            if save_sma_data(edited_df):
                st.cache_data.clear()
                st.rerun()
        
        return edited_df
        
    except Exception as e:
        st.error(f"Error in data editor: {str(e)}")
        st.exception(e)
        return sector_data
# Main app function
def main():
    st.title("📈 NEPSE SMA Analysis")
    
    # Load data
    sma_data = load_sma_data()
    
    # Sector selection
    selected_sector = st.selectbox(
        "Choose Sector",
        ALLOWED_SECTORS,
        index=0,
        key='sector_selector'
    )
    
    # Filter data for the selected sector
    sector_data = sma_data[sma_data[SECTOR_COL] == selected_sector].copy()
    
    # Main layout
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("SMA Chart")
        chart = create_sma_chart(sma_data, selected_sector)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.warning(f"No SMA data available for {selected_sector}")
    
    with col2:
        st.subheader("SMA Data Editor")
        st.markdown(f"**Editing data for sector: {selected_sector}**")
        
        with st.expander("Edit SMA Values", expanded=True):
            # Use the new display_sma_editor function
            edited_sector_data = display_sma_editor(sector_data, selected_sector)
            
            # Download button for sector data
            if not sector_data.empty:
                st.download_button(
                    label="📥 Download Sector Data",
                    data=sector_data.to_csv(index=False).encode('utf-8'),
                    file_name=f"{selected_sector}_sma_data.csv",
                    mime='text/csv',
                )
    
      # Comparison Section
    st.markdown("---")
    st.subheader("📊 Sector Comparison View")
    
    # Enhanced date range selector with validation
    min_date = sma_data[DATE_COL].min() if not sma_data.empty else datetime.today()
    max_date = sma_data[DATE_COL].max() if not sma_data.empty else datetime.today()
    
    col1, col2 = st.columns([2, 1])
    with col1:
        comparison_dates = st.date_input(
            "Select Date Range for Comparison",
            value=[min_date, max_date],
            min_value=min_date,
            max_value=max_date
        )
    
    with col2:
        # Add download button for complete dataset
        if not sma_data.empty:
            st.download_button(
                label="📥 Download Complete Dataset",
                data=sma_data.to_csv(index=False).encode('utf-8'),
                file_name="complete_sma_data.csv",
                mime='text/csv',
                help="Download the complete SMA data for all sectors"
            )

    # Improved data filtering with error handling
    try:
        if len(comparison_dates) == 2:
            start_date, end_date = comparison_dates
            filtered_data = sma_data[
                (sma_data[DATE_COL] >= pd.to_datetime(start_date)) &
                (sma_data[DATE_COL] <= pd.to_datetime(end_date))
            ]
            
            if filtered_data.empty:
                st.warning(f"No data available for the selected date range: {start_date} to {end_date}")
                filtered_data = sma_data
        else:
            filtered_data = sma_data
            
    except Exception as e:
        st.error(f"Error filtering data: {str(e)}")
        filtered_data = sma_data

    # Enhanced comparison charts
    st.write("### SMA Trends Across All Sectors")
    
    # Add chart controls
    chart_col1, chart_col2 = st.columns([2, 1])
    with chart_col1:
        selected_smas = st.multiselect(
            "Select SMAs to Display",
            SMA_COLUMNS,
            default=SMA_COLUMNS,
            help="Choose which SMA periods to show in the charts"
        )
    
    with chart_col2:
        chart_height = st.slider(
            "Chart Height",
            min_value=200,
            max_value=400,
            value=300,
            step=50,
            help="Adjust the height of individual charts"
        )

    # Create improved comparison charts
    def create_enhanced_comparison_charts(data, selected_smas, height):
        """Create enhanced SMA comparison charts with selected periods."""
        charts = []
        for sector in ALLOWED_SECTORS:
            sector_df = data[data[SECTOR_COL] == sector]
            if not sector_df.empty:
                fig = px.line(
                    sector_df,
                    x=DATE_COL,
                    y=selected_smas,
                    title=f"{sector} SMA Trends",
                    labels={'value': 'SMA Value', DATE_COL: 'Date'},
                    markers=True
                )
                fig.update_layout(
                    height=height,
                    title_x=0.5,
                    legend_title='SMA Periods',
                    margin=dict(l=20, r=20, t=40, b=20),
                    showlegend=True,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    ),
                    hovermode='x unified'
                )
                charts.append((sector, fig))
            else:
                charts.append((sector, None))
        return charts

    # Display enhanced comparison charts
    comparison_charts = create_enhanced_comparison_charts(filtered_data, selected_smas, chart_height)
    
    # Create grid layout
    cols = st.columns(3)
    col_idx = 0
    
    for sector, chart in comparison_charts:
        with cols[col_idx]:
            if chart:
                st.plotly_chart(chart, use_container_width=True)
                
                # Add sector statistics
                sector_df = filtered_data[filtered_data[SECTOR_COL] == sector]
                if not sector_df.empty:
                    with st.expander(f"{sector} Statistics"):
                        latest_date = sector_df[DATE_COL].max()
                        latest_data = sector_df[sector_df[DATE_COL] == latest_date]
                        
                        st.write("Latest Values:")
                        for sma in selected_smas:
                            st.write(f"{sma.replace('_', ' ')}: {latest_data[sma].iloc[0]:.2f}")
            else:
                st.warning(f"No data available for {sector}")
            
            # Add sector label with styling
            st.markdown(
                f"""
                <div style='text-align: center; padding: 10px; 
                background-color: #f0f2f6; border-radius: 5px;'>
                    <strong>{sector}</strong>
                </div>
                """, 
                unsafe_allow_html=True
            )
            
        col_idx = (col_idx + 1) % 3

    # Add data insights section
    st.markdown("---")
    st.subheader("📈 Data Insights")
    
    # Calculate and display insights
    if not filtered_data.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.write("### Latest SMA Trends")
            latest_date = filtered_data[DATE_COL].max()
            latest_data = filtered_data[filtered_data[DATE_COL] == latest_date]
            
            for sector in ALLOWED_SECTORS:
                sector_latest = latest_data[latest_data[SECTOR_COL] == sector]
                if not sector_latest.empty:
                    with st.expander(f"{sector} Latest Trends"):
                        sma_values = sector_latest[selected_smas].iloc[0]
                        for sma, value in sma_values.items():
                            st.write(f"{sma.replace('_', ' ')}: {value:.2f}")
        
        with col2:
            st.write("### Data Coverage")
            for sector in ALLOWED_SECTORS:
                sector_data = filtered_data[filtered_data[SECTOR_COL] == sector]
                if not sector_data.empty:
                    date_range = f"{sector_data[DATE_COL].min().strftime('%Y-%m-%d')} to {sector_data[DATE_COL].max().strftime('%Y-%m-%d')}"
                    st.write(f"{sector}: {date_range}")

if __name__ == "__main__":
    main()
