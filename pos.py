import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path
from datetime import datetime

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

# Initialize a directory to save data
DATA_DIR = Path("saved_data")
DATA_DIR.mkdir(exist_ok=True)

def save_data():
    """Save all sector data and NEPSE data to CSV files."""
    try:
        for sector, df in st.session_state.data.items():
            df.to_csv(DATA_DIR / f"{sector}_data.csv", index=False)
        st.session_state.nepse_equity.to_csv(DATA_DIR / "nepse_equity.csv", index=False)
    except Exception as e:
        st.error(f"Error saving data: {e}")

def load_data():
    """Load saved data from CSV files."""
    sectors = [
        "Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels", 
        "Microfinance", "Investments", "Life insurance", "Non-life insurance", 
        "Others", "Manufacture", "Tradings"
    ]
    
    loaded_data = {}
    for sector in sectors:
        file_path = DATA_DIR / f"{sector}_data.csv"
        try:
            if file_path.exists():
                loaded_data[sector] = pd.read_csv(file_path)
                loaded_data[sector]["Date"] = pd.to_datetime(loaded_data[sector]["Date"])
            else:
                loaded_data[sector] = pd.DataFrame(columns=[
                    "Date", "No of positive stock", "No of negative stock", 
                    "No of total stock", "No of No change", "Positive %", "Label"
                ])
        except Exception as e:
            st.error(f"Error loading {sector} data: {e}")
            loaded_data[sector] = pd.DataFrame(columns=[
                "Date", "No of positive stock", "No of negative stock", 
                "No of total stock", "No of No change", "Positive %", "Label"
            ])
    
    nepse_file = DATA_DIR / "nepse_equity.csv"
    try:
        if nepse_file.exists():
            nepse_data = pd.read_csv(nepse_file)
            nepse_data["Date"] = pd.to_datetime(nepse_data["Date"])
        else:
            nepse_data = pd.DataFrame(columns=["Date", "Positive Change %", "Label"])
    except Exception as e:
        st.error(f"Error loading NEPSE data: {e}")
        nepse_data = pd.DataFrame(columns=["Date", "Positive Change %", "Label"])
    
    return loaded_data, nepse_data

def initialize_session():
    """Initialize session state with saved data."""
    if 'data' not in st.session_state or 'nepse_equity' not in st.session_state:
        loaded_data, nepse_data = load_data()
        st.session_state.data = loaded_data
        st.session_state.nepse_equity = nepse_data
    return list(st.session_state.data.keys())

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

def update_data(selected_sector, input_data):
    """Update session state with new data and auto-calculate labels."""
    try:
        new_row = pd.DataFrame({
            "Date": [pd.to_datetime(input_data["date"])],
            "No of positive stock": [input_data["positive_stock"]],
            "No of negative stock": [input_data["negative_stock"]],
            "No of total stock": [input_data["total_stock"]],
            "No of No change": [input_data["no_change"]],
            "Positive %": [input_data["positive_percentage"]],
            "Label": [get_label(input_data["positive_percentage"])]
        })
        
        st.session_state.data[selected_sector] = pd.concat(
            [st.session_state.data[selected_sector], new_row], 
            ignore_index=True
        ).drop_duplicates(subset=["Date"], keep="last")
        
        # Update NEPSE Equity data
        date = input_data["date"]
        all_sectors_have_data = all(
            pd.to_datetime(date) in pd.to_datetime(df["Date"]).values 
            for df in st.session_state.data.values()
        )
        
        if all_sectors_have_data:
            total_positive = sum(
                df[pd.to_datetime(df["Date"]) == pd.to_datetime(date)]["No of positive stock"].iloc[0]
                for df in st.session_state.data.values()
            )
            nepse_percentage = (total_positive / 244) * 100
            
            nepse_row = pd.DataFrame({
                "Date": [pd.to_datetime(date)],
                "Positive Change %": [nepse_percentage],
                "Label": [get_label(nepse_percentage)]
            })
            
            st.session_state.nepse_equity = pd.concat(
                [st.session_state.nepse_equity, nepse_row], 
                ignore_index=True
            ).drop_duplicates(subset=["Date"], keep="last")
        
        save_data()
        st.success("Data updated successfully!")
        
    except Exception as e:
        st.error(f"Error updating data: {e}")

def display_data_editor(selected_sector):
    """Display unified data editor with automatic label updates."""
    st.subheader(f"Data Editor - {selected_sector}")
    
    df = st.session_state.data[selected_sector].copy()
    df = df.sort_values("Date", ascending=False)
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        key=f"editor_{selected_sector}",
        hide_index=True
    )
    
    if not edited_df.equals(df):
        edited_df["Label"] = edited_df["Positive %"].apply(get_label)
        st.session_state.data[selected_sector] = edited_df
        save_data()

def display_nepse_equity():
    """Display NEPSE data editor with automatic label updates."""
    st.subheader("NEPSE Equity Data")
    
    df = st.session_state.nepse_equity.copy()
    df = df.sort_values("Date", ascending=False)
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        key="editor_nepse",
        hide_index=True
    )
    
    if not edited_df.equals(df):
        edited_df["Label"] = edited_df["Positive Change %"].apply(get_label)
        st.session_state.nepse_equity = edited_df
        save_data()

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

def main():
    
    st.title("Sector Data Editor")
    sectors = initialize_session()
    
    # Layout with tabs
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
            st.download_button(
                label="📥 Download Sector Data",
                data=st.session_state.data[selected_sector].to_csv(index=False).encode('utf-8'),
                file_name=f"{selected_sector}_data.csv",
                mime='text/csv',
            )
        
        display_data_editor(selected_sector)
    
    with tab2:
        st.subheader("NEPSE Equity Management")
        col1, _ = st.columns([2, 1])
        
        with col1:
            st.download_button(
                label="📥 Download NEPSE Data",
                data=st.session_state.nepse_equity.to_csv(index=False).encode('utf-8'),
                file_name="nepse_equity_data.csv",
                mime='text/csv',
            )
        
        display_nepse_equity()
        plot_nepse_data()
    
    with tab3:
        st.subheader("Sector Analysis")
        
        # Controls for both charts
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
        
        # Create two columns for side-by-side charts
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
                    
                    # Update layout for better readability
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
                    
                    # Update layout for better readability
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

if __name__ == "__main__":
    main()
