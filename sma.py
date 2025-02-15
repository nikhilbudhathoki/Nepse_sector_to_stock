import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# Supabase Credentials
SUPABASE_URL = "https://zjxwjeqgkanjcsrgmfri.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpqeHdqZXFna2FuamNzcmdtZnJpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Mzk2MDk0NTcsImV4cCI6MjA1NTE4NTQ1N30.z_L9UjokkUpBZoqAQj1OOR23MvvDWG1erHDNcr4dY6s"

# Initialize Supabase client
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

TABLE_NAME = "sma_data"

st.set_page_config(page_title="NEPSE SMA Analysis", page_icon="📈", layout="wide")


# 🔹 Fetch data from Supabase
@st.cache_data(ttl=0)
def fetch_data():
    try:
        response = supabase.table(TABLE_NAME).select("*").execute()
        data = response.data
        df = pd.DataFrame(data) if data else pd.DataFrame()
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()


# 🔹 Insert new data
def insert_data(date, sector, sma_10, sma_20, sma_50, sma_200):
    try:
        data = {
            "date": date,
            "sector": sector,
            "10_SMA": sma_10,
            "20_SMA": sma_20,
            "50_SMA": sma_50,
            "200_SMA": sma_200,
        }
        supabase.table(TABLE_NAME).insert(data).execute()
        st.success("✅ Data inserted successfully!")
    except Exception as e:
        st.error(f"Error inserting data: {e}")


# 🔹 Update data
def update_data(updated_df):
    try:
        for _, row in updated_df.iterrows():
            data = {
                "10_SMA": row["10_SMA"],
                "20_SMA": row["20_SMA"],
                "50_SMA": row["50_SMA"],
                "200_SMA": row["200_SMA"],
            }
            supabase.table(TABLE_NAME).update(data).eq("id", row["id"]).execute()
        st.success("✅ Data updated successfully!")
    except Exception as e:
        st.error(f"Error updating data: {e}")


# 🔹 Delete data
def delete_data(record_id):
    try:
        supabase.table(TABLE_NAME).delete().eq("id", record_id).execute()
        st.warning(f"🗑️ Record {record_id} deleted successfully!")
    except Exception as e:
        st.error(f"Error deleting data: {e}")


# 📌 Main UI
def main():
    st.title("📈 NEPSE SMA Data Manager")

    df = fetch_data()

    if df.empty:
        st.warning("No data found in the database.")
    else:
        df = df.sort_values("date", ascending=False)

    # 📍 Section 1: Data Table
    st.subheader("📊 Current SMA Data")
    if not df.empty:
        st.dataframe(df)

    # 📍 Section 2: Edit Data
    if not df.empty:
        st.subheader("📝 Edit SMA Data")
        edited_df = st.data_editor(df, num_rows="dynamic", key="sma_editor")
        if st.button("💾 Save Changes"):
            update_data(edited_df)
            st.cache_data.clear()
            st.experimental_rerun()

    # 📍 Section 3: Insert New Data
    st.subheader("➕ Add New SMA Entry")
    col1, col2 = st.columns(2)
    date = col1.date_input("📅 Date")
    sector = col2.text_input("🏢 Sector")

    sma_10 = st.number_input("📈 10_SMA", value=0.0, step=0.01)
    sma_20 = st.number_input("📈 20_SMA", value=0.0, step=0.01)
    sma_50 = st.number_input("📈 50_SMA", value=0.0, step=0.01)
    sma_200 = st.number_input("📈 200_SMA", value=0.0, step=0.01)

    if st.button("📤 Save Data"):
        insert_data(str(date), sector, sma_10, sma_20, sma_50, sma_200)
        st.cache_data.clear()
        st.experimental_rerun()

    # 📍 Section 4: Delete Data
    st.subheader("🗑️ Delete SMA Data")
    if not df.empty:
        record_id = st.selectbox("Select Record to Delete", df["id"])
        if st.button("❌ Delete Record"):
            delete_data(record_id)
            st.cache_data.clear()
            st.experimental_rerun()

    # 📍 Section 5: SMA Visualization
    st.subheader("📈 SMA Trend Analysis")
    if not df.empty:
        sectors = df["sector"].unique()
        selected_sector = st.selectbox("Select a sector to view trends", sectors)

        df_sector = df[df["sector"] == selected_sector].sort_values("date")

        fig = px.line(
            df_sector,
            x="date",
            y=["10_SMA", "20_SMA", "50_SMA", "200_SMA"],
            labels={"value": "SMA Value", "variable": "SMA Type"},
            title=f"SMA Trends for {selected_sector}",
        )
        st.plotly_chart(fig, use_container_width=True)


if __name__ == "__main__":
    main()
