import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client
from datetime import datetime

# Initialize Supabase client
SUPABASE_URL = 'https://zjxwjeqgkanjcsrgmfri.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s'
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Label calculation function
def get_label(value):
    """Determine label based on threshold values."""
    if value is None or pd.isna(value):
        return "unknown"
    if value >= 60:
        return "strong"
    elif value >= 50:
        return "mid"
    else:
        return "weak"

# Save sector data to Supabase
def save_sector_data(sector, data_dict):
    """Save sector data to Supabase database."""
    try:
        response = supabase.table('pos').upsert({
            "sector": sector,
            "date": data_dict["date"].strftime("%Y-%m-%d"),
            "positive_stock": data_dict["positive_stock"],
            "negative_stock": data_dict["negative_stock"],
            "total_stock": data_dict["total_stock"],
            "no_change": data_dict["no_change"],
            "positive_percentage": data_dict["positive_percentage"],
            "label": get_label(data_dict["positive_percentage"])
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving sector data: {e}")
        return False

# Save NEPSE data to Supabase
def save_nepse_data(date, total_positive, total_stock=None):
    """Save NEPSE equity data to Supabase database."""
    try:
        positive_change = (total_positive / total_stock * 100) if total_stock else None
        label = get_label(positive_change) if positive_change is not None else "unknown"
        
        response = supabase.table('nepse_equity').upsert({
            "date": date.strftime("%Y-%m-%d"),
            "total_positive": total_positive,
            "total_stock": total_stock,
            "positive_change_percentage": positive_change,
            "label": label
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving NEPSE data: {e}")
        return False

# Load sector data from Supabase
def load_sector_data(sector):
    """Load sector data from Supabase database."""
    try:
        response = supabase.table('pos').select("*").eq("sector", sector).order("date", desc=True).execute()
        df = pd.DataFrame(response.data)
        df["Date"] = pd.to_datetime(df["date"])
        df = df.drop(columns=["date"])
        df = df.rename(columns={
            "positive_stock": "No of positive stock",
            "negative_stock": "No of negative stock",
            "total_stock": "No of total stock",
            "no_change": "No of No change",
            "positive_percentage": "Positive %",
            "label": "Label"
        })
        return df
    except Exception as e:
        st.error(f"Error loading sector data: {e}")
        return pd.DataFrame()

# Load NEPSE data from Supabase
def load_nepse_data():
    """Load NEPSE equity data from Supabase database."""
    try:
        response = supabase.table('nepse_equity').select("*").order("date", desc=True).execute()
        df = pd.DataFrame(response.data)
        df["Date"] = pd.to_datetime(df["date"])
        df = df.drop(columns=["date"])
        df = df.rename(columns={
            "total_positive": "Total Positive",
            "total_stock": "Total Stock",
            "positive_change_percentage": "Positive Change %",
            "label": "Label"
        })
        return df
    except Exception as e:
        st.error(f"Error loading NEPSE data: {e}")
        return pd.DataFrame()

# Initialize session state
def initialize_session():
    """Initialize session state with data from Supabase database."""
    sectors = [
        "Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels", 
        "Microfinance", "Investments", "Life insurance", "Non-life insurance", 
        "Others", "Manufacture", "Tradings"
    ]
    
    if 'data' not in st.session_state:
        st.session_state.data = {sector: load_sector_data(sector) for sector in sectors}
    
    if 'nepse_equity' not in st.session_state:
        st.session_state.nepse_equity = load_nepse_data()
    
    return sectors

# Update data in Supabase
def update_data(selected_sector, input_data):
    """Update database with new sector data and auto-calculate NEPSE data."""
    try:
        # Save sector data
        if save_sector_data(selected_sector, input_data):
            # Reload sector data
            st.session_state.data[selected_sector] = load_sector_data(selected_sector)
            
            # Update NEPSE Equity data
            date = input_data["date"]
            all_sectors = list(st.session_state.data.keys())
            all_sectors_have_data = all(
                any(pd.to_datetime(date) == pd.to_datetime(row["Date"]) 
                    for _, row in st.session_state.data[sector].iterrows())
                for sector in all_sectors
            )
            
            if all_sectors_have_data:
                total_positive = sum(
                    st.session_state.data[sector][
                        pd.to_datetime(st.session_state.data[sector]["Date"]) == pd.to_datetime(date)
                    ]["No of positive stock"].iloc[0]
                    for sector in all_sectors
                )
                
                save_nepse_data(date, total_positive)
                st.session_state.nepse_equity = load_nepse_data()
            
            st.success("Data updated successfully! Please update NEPSE Total Stock in the NEPSE Equity tab.")
            
    except Exception as e:
        st.error(f"Error updating data: {e}")

# Display data editor
def display_data_editor(selected_sector):
    """Display unified data editor with automatic label updates."""
    st.subheader(f"Data Editor - {selected_sector}")
    
    df = st.session_state.data[selected_sector].copy()
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        key=f"editor_{selected_sector}",
        hide_index=True
    )
    
    if not edited_df.equals(df):
        # Update database with edited data
        for _, row in edited_df.iterrows():
            data_dict = {
                "date": row["Date"],
                "positive_stock": row["No of positive stock"],
                "negative_stock": row["No of negative stock"],
                "total_stock": row["No of total stock"],
                "no_change": row["No of No change"],
                "positive_percentage": row["Positive %"]
            }
            save_sector_data(selected_sector, data_dict)
        
        # Reload data
        st.session_state.data[selected_sector] = load_sector_data(selected_sector)
        st.rerun()

# Display NEPSE equity editor
def display_nepse_equity():
    """Display NEPSE data editor with automatic updates."""
    st.subheader("NEPSE Equity Data")
    
    df = st.session_state.nepse_equity.copy()
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        key="editor_nepse",
        hide_index=True,
        column_config={
            "Date": st.column_config.DateColumn(disabled=True),
            "Total Positive": st.column_config.NumberColumn(disabled=True),
            "Total Stock": st.column_config.NumberColumn(
                "Total Stock (Required)", 
                min_value=1,
                help="Enter total number of stocks for NEPSE calculation"
            ),
            "Positive Change %": st.column_config.NumberColumn(
                format="%.2f%%",
                disabled=True
            ),
            "Label": st.column_config.TextColumn(disabled=True)
        }
    )
    
    if not edited_df.equals(df):
        for _, row in edited_df.iterrows():
            save_nepse_data(
                row["Date"],
                row["Total Positive"],
                row["Total Stock"]
            )
        
        st.session_state.nepse_equity = load_nepse_data()
        st.rerun()

# Plot NEPSE data
def plot_nepse_data():
    """Plot NEPSE Equity data separately."""
    try:
        nepse_data = st.session_state.nepse_equity.copy()
        if not nepse_data.empty:
            fig = px.line(
                nepse_data,
                x="Date",
                y="Positive Change %",
                title="NEPSE Equity Performance Over Time",
                labels={"Positive Change %": "Positive Change Percentage", "Date": "Date"},
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
    except Exception as e:
        st.error(f"Error plotting NEPSE data: {e}")

# Get user input for sector data
def get_user_input():
    """Get user input for sectoral data entry."""
    col1, col2 = st.columns(2)
    
    with col1:
        date = st.date_input("Date")
        positive_stock = st.number_input("No of positive stock", min_value=0)
        negative_stock = st.number_input("No of negative stock", min_value=0)
    
    with col2:
        total_stock = st.number_input("No of total stock", min_value=0)
        no_change = st.number_input("No of No change", min_value=0)
    
    if total_stock == 0:
        st.warning("Total stock cannot be zero. Please enter a valid number.")
        return None
    
    positive_percentage = (positive_stock / total_stock * 100) if total_stock > 0 else 0
    
    return {
        "date": date,
        "positive_stock": positive_stock,
        "negative_stock": negative_stock,
        "total_stock": total_stock,
        "no_change": no_change,
        "positive_percentage": positive_percentage
    }

# Main function
def main():
    st.title("Sector Data Editor")
    sectors = initialize_session()
    
    tab1, tab2, tab3 = st.tabs(["Sector Data Entry", "NEPSE Equity", "Analysis & Charts"])
    
    with tab1:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            selected_sector = st.selectbox("Select Sector", sectors)
            input_data = get_user_input()
            
            if input_data:
                st.info(f"Calculated Positive %: {input_data['positive_percentage']:.2f}%")
                if st.button("Add/Update Data", type="primary"):
                    update_data(selected_sector, input_data)
        
        with col2:
            sector_data = load_sector_data(selected_sector)
            st.download_button(
                label="📥 Download Sector Data",
                data=sector_data.to_csv(index=False).encode('utf-8'),
                file_name=f"{selected_sector}_data.csv",
                mime='text/csv',
            )
        
        display_data_editor(selected_sector)
    
    with tab2:
        st.subheader("NEPSE Equity Management")
        col1, _ = st.columns([2, 1])
        
        with col1:
            nepse_data = load_nepse_data()
            st.download_button(
                label="📥 Download NEPSE Data",
                data=nepse_data.to_csv(index=False).encode('utf-8'),
                file_name="nepse_equity_data.csv",
                mime='text/csv',
            )
        
        display_nepse_equity()
        plot_nepse_data()
    
    with tab3:
        st.subheader("Sector Analysis")
        
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            selected_sectors_1 = st.multiselect(
                "Select Sectors for Chart 1",
                sectors,
                default=sectors[:3],
                key="chart1_sectors"
            )
        
        with col2:
            selected_sectors_2 = st.multiselect(
                "Select Sectors for Chart 2",
                sectors,
                default=sectors[3:6],
                key="chart2_sectors"
            )
        
        with col3:
            include_nepse = st.checkbox("Include NEPSE Equity", value=True)
        
        chart_col1, chart_col2 = st.columns(2)
        
        with chart_col1:
            if selected_sectors_1:
                try:
                    sector_data = []
                    for sector in selected_sectors_1:
                        df = st.session_state.data[sector].copy()
                        df["Sector"] = sector
                        sector_data.append(df)
                    
                    sector_data = pd.concat(sector_data, ignore_index=True)
                    
                    if include_nepse:
                        nepse_data = st.session_state.nepse_equity.copy()
                        nepse_data["Sector"] = "NEPSE Equity"
                        nepse_data = nepse_data.rename(columns={"Positive Change %": "Positive %"})
                        sector_data = pd.concat([sector_data, nepse_data], ignore_index=True)
                    
                    fig1 = px.line(
                        sector_data,
                        x="Date",
                        y="Positive %",
                        color="Sector",
                        title="Chart 1: Sector Performance",
                        labels={"Positive %": "Positive Percentage", "Date": "Date"},
                        markers=True
                    )
                    
                    fig1.update_layout(
                        legend=dict(
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.01
                        ),
                        margin=dict(l=10, r=10, t=40, b=10)
                    )
                    
                    st.plotly_chart(fig1, use_container_width=True)
                except Exception as e:
                    st.error(f"Error plotting Chart 1: {e}")
        
        with chart_col2:
            if selected_sectors_2:
                try:
                    sector_data = []
                    for sector in selected_sectors_2:
                        df = st.session_state.data[sector].copy()
                        df["Sector"] = sector
                        sector_data.append(df)
                    
                    sector_data = pd.concat(sector_data, ignore_index=True)
                    
                    if include_nepse:
                        nepse_data = st.session_state.nepse_equity.copy()
                        nepse_data["Sector"] = "NEPSE Equity"
                        nepse_data = nepse_data.rename(columns={"Positive Change %": "Positive %"})
                        sector_data = pd.concat([sector_data, nepse_data], ignore_index=True)
                    
                    fig2 = px.line(
                        sector_data,
                        x="Date",
                        y="Positive %",
                        color="Sector",
                        title="Chart 2: Sector Performance",
                        labels={"Positive %": "Positive Percentage", "Date": "Date"},
                        markers=True
                    )
                    
                    fig2.update_layout(
                        legend=dict(
                            yanchor="top",
                            y=0.99,
                            xanchor="left",
                            x=0.01
                        ),
                        margin=dict(l=10, r=10, t=40, b=10)
                    )
                    
                    st.plotly_chart(fig2, use_container_width=True)
                except Exception as e:
                    st.error(f"Error plotting Chart 2: {e}")

# Run the app
if __name__ == "__main__":
    main()
