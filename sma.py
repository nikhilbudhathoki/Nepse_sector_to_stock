import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime
from sqlite3 import Error

# Configuration
DATE_COL = 'DATE'
SECTOR_COL = 'SECTOR'
SMA_COLUMNS = ['10_SMA', '20_SMA', '50_SMA', '200_SMA']
ALLOWED_SECTORS = [
    "Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels",
    "Microfinance", "Investments", "Life insurance", "Non-life insurance",
    "Others", "Manufacture", "Tradings"
]

# Database setup
DB_NAME = "sma_data.db"

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
        .stDateInput, .stSelectbox {
            margin-bottom: 20px;
        }
        .stDataEditor {
            margin-bottom: 30px;
        }
        .stPlotlyChart {
            margin-top: 20px;
        }
        h2 {
            color: #2E86C1;
            border-bottom: 2px solid #2E86C1;
            padding-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)

# Database connection with proper error handling
def create_connection():
    """Create SQLite database connection and initialize tables."""
    try:
        conn = sqlite3.connect(DB_NAME)
        # Create table with quoted column names to prevent SQL injection
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS sma_data (
            "{DATE_COL}" DATE,
            "{SECTOR_COL}" TEXT,
            "{SMA_COLUMNS[0]}" REAL,
            "{SMA_COLUMNS[1]}" REAL,
            "{SMA_COLUMNS[2]}" REAL,
            "{SMA_COLUMNS[3]}" REAL,
            PRIMARY KEY ("{DATE_COL}", "{SECTOR_COL}")
        )
        """
        conn.execute(create_table_sql)
        conn.commit()
        return conn
    except Error as e:
        st.error(f"Database error: {str(e)}")
        return None

# Load data from SQLite with improved error handling
@st.cache_data(ttl=0, show_spinner="Loading SMA data...")
def load_sma_data():
    """Load data from SQLite database."""
    conn = create_connection()
    if conn is None:
        return pd.DataFrame(columns=[DATE_COL, SECTOR_COL] + SMA_COLUMNS)
    
    try:
        # Use quoted column names in SQL query
        query = f'SELECT "{DATE_COL}", "{SECTOR_COL}", ' + \
                ', '.join(f'"{col}"' for col in SMA_COLUMNS) + \
                ' FROM sma_data'
        df = pd.read_sql(query, conn, parse_dates=[DATE_COL])
        return df.sort_values(DATE_COL)
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        return pd.DataFrame(columns=[DATE_COL, SECTOR_COL] + SMA_COLUMNS)
    finally:
        conn.close()

# Save data to SQLite with improved error handling
def save_sma_data(edited_df):
    """Save data to SQLite database with transaction."""
    if edited_df.empty:
        st.warning("No data to save.")
        return False
    
    conn = create_connection()
    if conn is None:
        return False

    try:
        with conn:  # Use context manager for automatic transaction handling
            # Delete existing sector data
            sector = edited_df[SECTOR_COL].iloc[0]
            conn.execute(f'DELETE FROM sma_data WHERE "{SECTOR_COL}" = ?', (sector,))
            
            # Ensure date column is in datetime format
            edited_df[DATE_COL] = pd.to_datetime(edited_df[DATE_COL])
            
            # Insert new data
            edited_df.to_sql('sma_data', conn, if_exists='append', index=False)
            
        st.success("Data saved successfully!")
        return True
    except Exception as e:
        st.error(f"Save error: {str(e)}")
        return False
    finally:
        conn.close()

# Create SMA time series chart with improved styling
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
        hovermode='x unified',
        xaxis_title="Date",
        yaxis_title="SMA Value",
        template="plotly_white"
    )
    return fig

# Create SMA comparison charts with improved error handling
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
                showlegend=False,
                template="plotly_white"
            )
            charts.append(fig)
        else:
            charts.append(None)
    return charts

def main():
    st.title("📈 NEPSE SMA Analysis")
    
    # Load data with error handling
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
            st.info(f"No SMA data available for {selected_sector}. Add data using the editor.")

    with col2:
        st.subheader("SMA Data Editor")
        st.markdown(f"**Editing data for sector: {selected_sector}**")
        
        with st.expander("Edit SMA Values", expanded=True):
            edited_sector_data = st.data_editor(
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
                key='sma_editor'
            )
            
            if not edited_sector_data.empty:
                edited_sector_data[SECTOR_COL] = selected_sector
                
                if st.button("💾 Save SMA Data", type="primary"):
                    if save_sma_data(edited_sector_data):
                        st.cache_data.clear()
                        st.rerun()

    # Comparison Section
    st.markdown("---")
    st.subheader("📊 Sector Comparison View")
    
    # Date range selector with error handling
    min_date = sma_data[DATE_COL].min() if not sma_data.empty else datetime.today()
    max_date = sma_data[DATE_COL].max() if not sma_data.empty else datetime.today()
    
    comparison_dates = st.date_input(
        "Select Date Range for Comparison",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    if len(comparison_dates) == 2:
        start_date, end_date = comparison_dates
        filtered_data = sma_data[
            (sma_data[DATE_COL] >= pd.to_datetime(start_date)) &
            (sma_data[DATE_COL] <= pd.to_datetime(end_date))
        ]
    else:
        filtered_data = sma_data
    
    st.write("### SMA Trends Across All Sectors")
    comparison_charts = create_comparison_charts(filtered_data)
    
    cols = st.columns(3)
    for i, (sector, chart) in enumerate(zip(ALLOWED_SECTORS, comparison_charts)):
        with cols[i % 3]:
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            else:
                st.info(f"No data available for {sector}")
            st.markdown(f"<center><strong>{sector}</strong></center>", unsafe_allow_html=True)

if __name__ == "__main__":
    main()
