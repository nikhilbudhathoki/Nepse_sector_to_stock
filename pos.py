import pandas as pd
import plotly.express as px
import streamlit as st
from supabase import create_client, Client
from datetime import datetime

# Initialize Supabase client
SUPABASE_URL = 'https://zjxwjeqgkanjcsrgmfri.supabase.co'
SUPABASE_KEY = 'YOUR_SUPABASE_KEY'  # Replace securely in production
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Label calculation function
def get_label(value):
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
    try:
        supabase.table('pos').upsert({
            "sector": sector,
            "date": data_dict["date"].strftime("%Y-%m-%d"),
            "positive_stock": float(data_dict["positive_stock"]),
            "negative_stock": float(data_dict["negative_stock"]),
            "no_change": float(data_dict["no_change"]),
            "positive_percentage": float(data_dict["positive_percentage"]),
            "label": get_label(data_dict["positive_percentage"])
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error saving sector data: {e}")
        return False

# Save NEPSE data to Supabase
def save_nepse_data(date, total_positive, total_stock):
    try:
        positive_change = (total_positive / total_stock * 100) if total_stock else None
        label = get_label(positive_change) if positive_change is not None else "unknown"
        
        supabase.table('nepse_equity').upsert({
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
    try:
        response = supabase.table('pos').select("*").eq("sector", sector).order("date", desc=True).execute()
        if response.data is None:
            return pd.DataFrame()
        
        df = pd.DataFrame(response.data)
        df["Date"] = pd.to_datetime(df["date"])
        df["total_stock"] = df["positive_stock"] + df["negative_stock"] + df["no_change"]
        df = df.drop(columns=["date"]).rename(columns={
            "positive_stock": "No of positive stock",
            "negative_stock": "No of negative stock",
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
    try:
        response = supabase.table('nepse_equity').select("*").order("date", desc=True).execute()
        if response.data is None:
            return pd.DataFrame()
        
        df = pd.DataFrame(response.data)
        df["Date"] = pd.to_datetime(df["date"])
        df = df.drop(columns=["date"]).rename(columns={
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
    sectors = ["Hydropower", "C. Bank", "D. Bank", "Finance", "Hotels", "Microfinance", "Investments", "Life insurance", "Non-life insurance", "Others", "Manufacture", "Tradings"]
    if 'data' not in st.session_state:
        st.session_state.data = {sector: load_sector_data(sector) for sector in sectors}
    if 'nepse_equity' not in st.session_state:
        st.session_state.nepse_equity = load_nepse_data()
    return sectors

# Update data
def update_data(selected_sector, input_data):
    try:
        input_data["total_stock"] = input_data["positive_stock"] + input_data["negative_stock"] + input_data["no_change"]
        if save_sector_data(selected_sector, input_data):
            st.session_state.data[selected_sector] = load_sector_data(selected_sector)
            date = input_data["date"]
            total_positive = sum(
                st.session_state.data[sector].loc[
                    st.session_state.data[sector]["Date"] == date, "No of positive stock"
                ].sum() for sector in st.session_state.data.keys()
            )
            total_stock = sum(
                st.session_state.data[sector].loc[
                    st.session_state.data[sector]["Date"] == date, "total_stock"
                ].sum() for sector in st.session_state.data.keys()
            )
            save_nepse_data(date, total_positive, total_stock)
            st.session_state.nepse_equity = load_nepse_data()
            st.success("Data updated successfully!")
    except Exception as e:
        st.error(f"Error updating data: {e}")

# User input
def get_user_input():
    date = st.date_input("Date")
    positive_stock = st.number_input("No of positive stock", min_value=0.0, format="%.2f")
    negative_stock = st.number_input("No of negative stock", min_value=0.0, format="%.2f")
    no_change = st.number_input("No of No change", min_value=0.0, format="%.2f")
    if (positive_stock + negative_stock + no_change) == 0:
        st.warning("Total stock cannot be zero.")
        return None
    return {
        "date": date,
        "positive_stock": positive_stock,
        "negative_stock": negative_stock,
        "no_change": no_change,
        "positive_percentage": (positive_stock / (positive_stock + negative_stock + no_change) * 100)
    }

# Main function
def main():
    st.title("Sector Data Editor")
    sectors = initialize_session()
    selected_sector = st.selectbox("Select Sector", sectors)
    input_data = get_user_input()
    if input_data and st.button("Add/Update Data", type="primary"):
        update_data(selected_sector, input_data)
    st.subheader(f"Data - {selected_sector}")
    st.dataframe(st.session_state.data[selected_sector])

if __name__ == "__main__":
    main()
