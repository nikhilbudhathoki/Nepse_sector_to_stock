import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# Configuration
SMA_FILE = "sma_data.csv"
DATE_COL = 'DATE'
SECTOR_COL = 'SECTOR'
SMA_COLUMNS = ['10_SMA', '20_SMA', '50_SMA', '200_SMA']

# Define allowed sectors
ALLOWED_SECTORS = [
    "Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels",
    "Microfinance", "Investments", "Life insurance", "Non-life insurance",
    "Others", "Manufacture", "Tradings"
]

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

@st.cache_data(ttl=0, show_spinner="Loading SMA data...")
def load_sma_data(file_path):
    """Load and process SMA data from CSV"""
    if not os.path.exists(file_path):
        df = pd.DataFrame(columns=[DATE_COL, SECTOR_COL] + SMA_COLUMNS)
        df[DATE_COL] = pd.to_datetime(df[DATE_COL])
        return df
    
    try:
        df = pd.read_csv(file_path)
        required_columns = [DATE_COL, SECTOR_COL] + SMA_COLUMNS
        
        # Validate columns
        missing_cols = [col for col in required_columns if col not in df.columns]
        if missing_cols:
            st.error(f"Missing columns in SMA data: {', '.join(missing_cols)}")
            return pd.DataFrame(columns=required_columns)
        
        df[DATE_COL] = pd.to_datetime(df[DATE_COL], errors='coerce')
        return df.dropna(subset=[DATE_COL]).sort_values(DATE_COL)
    except Exception as e:
        st.error(f"SMA data loading error: {str(e)}")
        return pd.DataFrame(columns=required_columns)

def save_sma_data(edited_df):
    """Save SMA data with validation"""
    try:
        # Check for required columns
        required_columns = [DATE_COL, SECTOR_COL] + SMA_COLUMNS
        missing_cols = [col for col in required_columns if col not in edited_df.columns]
        if missing_cols:
            st.error(f"Missing columns: {', '.join(missing_cols)}")
            return False
        
        # Check for duplicates
        if edited_df.duplicated(subset=[DATE_COL, SECTOR_COL]).any():
            st.error("Duplicate entries found (same date and sector combination)")
            return False
        
        # Save to temporary file first
        temp_file = f"temp_sma_{datetime.now().timestamp()}.csv"
        edited_df.to_csv(temp_file, index=False)
        os.replace(temp_file, SMA_FILE)
        return True
    except Exception as e:
        st.error(f"Save error: {str(e)}")
        return False

def create_sma_chart(data, selected_sector):
    """Create SMA time series chart for selected sector"""
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

def create_comparison_charts(data):
    """Create SMA comparison charts for all sectors"""
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

def main():
    st.title("📈 NEPSE SMA Analysis")
    
    # Load data
    sma_data = load_sma_data(SMA_FILE)
    
    # Sector selection
    selected_sector = st.selectbox(
        "Choose Sector",
        ALLOWED_SECTORS,
        index=0,
        key='sector_selector'
    )
    
    # Filter data for the selected sector
    sector_data = sma_data[sma_data[SECTOR_COL] == selected_sector]
    
    # Main layout
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.subheader("SMA Chart")
        # Display chart for the selected sector
        chart = create_sma_chart(sma_data, selected_sector)
        if chart:
            st.plotly_chart(chart, use_container_width=True)
        else:
            st.warning(f"No SMA data available for {selected_sector}")

    with col2:
        st.subheader("SMA Data Editor")
        st.markdown(f"**Editing data for sector: {selected_sector}**")
        
        # Data editor for the selected sector
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
            
            # Add the sector column back to the edited data
            edited_sector_data[SECTOR_COL] = selected_sector
            
            if st.button("💾 Save SMA Data", type="primary"):
                # Merge edited sector data with the rest of the data
                other_sectors_data = sma_data[sma_data[SECTOR_COL] != selected_sector]
                updated_data = pd.concat([other_sectors_data, edited_sector_data], ignore_index=True)
                
                if save_sma_data(updated_data):
                    st.success("SMA data saved successfully!")
                    st.cache_data.clear()
                    st.rerun()

    # Comparison Section
    st.markdown("---")
    st.subheader("📊 Sector Comparison View")
    
    # Date range selector for comparison
    min_date = sma_data[DATE_COL].min() if not sma_data.empty else datetime.today()
    max_date = sma_data[DATE_COL].max() if not sma_data.empty else datetime.today()
    
    comparison_dates = st.date_input(
        "Select Date Range for Comparison",
        value=[min_date, max_date],
        min_value=min_date,
        max_value=max_date
    )
    
    # Filter data for date range
    if len(comparison_dates) == 2:
        start_date, end_date = comparison_dates
        filtered_data = sma_data[
            (sma_data[DATE_COL] >= pd.to_datetime(start_date)) &
            (sma_data[DATE_COL] <= pd.to_datetime(end_date))
        ]
    else:
        filtered_data = sma_data
    
    # Create comparison charts
    st.write("### SMA Trends Across All Sectors")
    comparison_charts = create_comparison_charts(filtered_data)
    
    # Display in a grid (3 columns)
    cols = st.columns(3)
    col_idx = 0
    
    for sector, chart in zip(ALLOWED_SECTORS, comparison_charts):
        with cols[col_idx]:
            if chart:
                st.plotly_chart(chart, use_container_width=True)
            else:
                st.warning(f"No data for {sector}")
            
            # Add sector label
            st.markdown(f"<center><strong>{sector}</strong></center>", unsafe_allow_html=True)
        
        col_idx = (col_idx + 1) % 3

if __name__ == "__main__":
    main()
