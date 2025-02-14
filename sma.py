import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os
import psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlparse

# Configuration
DATE_COL = 'DATE'
SECTOR_COL = 'SECTOR'
SMA_COLUMNS = ['10_SMA', '20_SMA', '50_SMA', '200_SMA']
ALLOWED_SECTORS = [
    "Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels",
    "Microfinance", "Investments", "Life insurance", "Non-life insurance",
    "Others", "Manufacture", "Tradings"
]

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://localhost:5432/your_local_db')

# Parse database URL
parsed_url = urlparse(DATABASE_URL)
DB_CONFIG = {
    'dbname': parsed_url.path[1:],
    'user': parsed_url.username,
    'password': parsed_url.password,
    'host': parsed_url.hostname,
    'port': parsed_url.port
}

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
        .stAlert {
            background-color: #f8f9fa;
            border-radius: 4px;
            padding: 1rem;
            margin-bottom: 1rem;
        }
        .sector-label {
            text-align: center;
            font-weight: bold;
            margin-top: 0.5rem;
        }
        .chart-container {
            background-color: white;
            border-radius: 8px;
            padding: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
    </style>
""", unsafe_allow_html=True)

# Health check endpoint
@st.cache_data
def health_check():
    """Health check endpoint for monitoring."""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

def init_db():
    """Initialize database and create tables if they don't exist."""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Create table with proper PostgreSQL syntax
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS sma_data (
            {DATE_COL} DATE,
            {SECTOR_COL} TEXT,
            "10_SMA" DOUBLE PRECISION,
            "20_SMA" DOUBLE PRECISION,
            "50_SMA" DOUBLE PRECISION,
            "200_SMA" DOUBLE PRECISION,
            PRIMARY KEY ({DATE_COL}, {SECTOR_COL})
        );
        
        -- Create index for better query performance
        CREATE INDEX IF NOT EXISTS idx_sma_sector ON sma_data ({SECTOR_COL});
        CREATE INDEX IF NOT EXISTS idx_sma_date ON sma_data ({DATE_COL});
        """
        cur.execute(create_table_sql)
        conn.commit()
        return True
    except Exception as e:
        st.error(f"Database initialization error: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

@st.cache_resource
def get_db_connection():
    """Create and return a database connection."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        st.error(f"Database connection error: {str(e)}")
        return None

@st.cache_data(ttl=0, show_spinner="Loading SMA data...")
def load_sma_data():
    """Load data from PostgreSQL database."""
    conn = get_db_connection()
    if conn is None:
        return pd.DataFrame(columns=[DATE_COL, SECTOR_COL] + SMA_COLUMNS)
    
    try:
        query = f"""
        SELECT {DATE_COL}, {SECTOR_COL}, "10_SMA", "20_SMA", "50_SMA", "200_SMA"
        FROM sma_data
        ORDER BY {DATE_COL}
        """
        df = pd.read_sql_query(query, conn)
        df[DATE_COL] = pd.to_datetime(df[DATE_COL])
        return df
    except Exception as e:
        st.error(f"Data loading error: {str(e)}")
        return pd.DataFrame(columns=[DATE_COL, SECTOR_COL] + SMA_COLUMNS)
    finally:
        conn.close()

def save_sma_data(edited_df):
    """Save data to PostgreSQL database."""
    if edited_df.empty:
        st.warning("No data to save.")
        return False
    
    conn = get_db_connection()
    if conn is None:
        return False

    try:
        cur = conn.cursor()
        
        # Delete existing sector data
        sector = edited_df[SECTOR_COL].iloc[0]
        cur.execute(f"DELETE FROM sma_data WHERE {SECTOR_COL} = %s", (sector,))
        
        # Prepare data for insertion
        columns = [DATE_COL, SECTOR_COL] + SMA_COLUMNS
        values = [tuple(row) for row in edited_df[columns].values]
        
        # Use execute_values for efficient bulk insert
        insert_query = f"""
        INSERT INTO sma_data ({', '.join(f'"{col}"' for col in columns)})
        VALUES %s
        """
        execute_values(cur, insert_query, values)
        
        conn.commit()
        st.success("Data saved successfully!")
        return True
    except Exception as e:
        conn.rollback()
        st.error(f"Save error: {str(e)}")
        return False
    finally:
        conn.close()

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
        template="plotly_white",
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(255, 255, 255, 0.8)"
        )
    )
    
    # Add range slider
    fig.update_xaxes(rangeslider_visible=True)
    
    return fig

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
                template="plotly_white",
                xaxis_title="Date",
                yaxis_title="SMA Value"
            )
            charts.append(fig)
        else:
            charts.append(None)
    return charts

def calculate_statistics(data, sector):
    """Calculate and return key statistics for a sector."""
    if data.empty:
        return None
    
    sector_data = data[data[SECTOR_COL] == sector]
    if sector_data.empty:
        return None
    
    latest_data = sector_data.iloc[-1]
    
    stats = {
        "Latest Date": latest_data[DATE_COL].strftime("%Y-%m-%d"),
        "10 Day SMA": f"{latest_data['10_SMA']:.2f}",
        "20 Day SMA": f"{latest_data['20_SMA']:.2f}",
        "50 Day SMA": f"{latest_data['50_SMA']:.2f}",
        "200 Day SMA": f"{latest_data['200_SMA']:.2f}",
    }
    
    return stats

def main():
    # Check for health check request
    if st.query_params.get("health") == "check":
        st.json(health_check())
        st.stop()
    
    st.title("📈 NEPSE SMA Analysis")
    
    # Initialize database
    if not init_db():
        st.error("Failed to initialize database. Please check your database configuration.")
        return
    
    # Load data
    sma_data = load_sma_data()
    
    # Sector selection
    selected_sector = st.selectbox(
        "Choose Sector",
        ALLOWED_SECTORS,
        index=0,
        key='sector_selector'
    )
    
    # Main layout
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("SMA Chart")
        chart = create_sma_chart(sma_data, selected_sector)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
            
            # Display statistics
            stats = calculate_statistics(sma_data, selected_sector)
            if stats:
                st.subheader("Latest Statistics")
                for key, value in stats.items():
                    st.metric(key, value)
        else:
            st.info(f"No SMA data available for {selected_sector}. Add data using the editor.")

    with col2:
        st.subheader("SMA Data Editor")
        st.markdown(f"**Editing data for sector: {selected_sector}**")
        
        # Filter data for the selected sector
        sector_data = sma_data[sma_data[SECTOR_COL] == selected_sector].copy()
        
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
    
    # Date range selector
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
                with st.container():
                    st.plotly_chart(chart, use_container_width=True)
                    st.markdown(f"<div class='sector-label'>{sector}</div>", unsafe_allow_html=True)
            else:
                st.info(f"No data available for {sector}")

if __name__ == "__main__":
    main()
