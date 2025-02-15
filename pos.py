# Update the `update_data` function to properly aggregate and save NEPSE equity data
def update_data(selected_sector, input_data):
    """Update database with new sector data and auto-calculate NEPSE data."""
    try:
        # Save the sector data first
        if save_sector_data(selected_sector, input_data):
            st.session_state.data[selected_sector] = load_sector_data(selected_sector)
            
            # Aggregate data for NEPSE equity
            date = input_data["date"]
            all_sectors = list(st.session_state.data.keys())
            
            # Initialize totals
            total_positive = 0
            total_stock = 0
            
            # Loop through all sectors to calculate totals
            for sector in all_sectors:
                sector_df = st.session_state.data[sector]
                if not sector_df.empty:
                    # Filter data for the current date
                    date_filter = pd.to_datetime(sector_df["Date"]) == pd.to_datetime(date)
                    if any(date_filter):
                        total_positive += sector_df[date_filter]["No of positive stock"].iloc[0]
                        total_stock += sector_df[date_filter]["No of total stock"].iloc[0]
            
            # Save the aggregated data to the NEPSE equity table
            if total_stock > 0:  # Ensure total_stock is not zero
                save_nepse_data(date, total_positive, total_stock)
                st.session_state.nepse_equity = load_nepse_data()
                st.success("Data updated successfully!")
            else:
                st.warning("Total stock is zero. Cannot calculate NEPSE equity data.")
            
    except Exception as e:
        st.error(f"Error updating data: {e}")

# Update the `plot_nepse_data` function to display the chart
def plot_nepse_data():
    st.subheader("NEPSE Equity Chart")
    if not st.session_state.nepse_equity.empty:
        fig = px.line(
            st.session_state.nepse_equity,
            x="Date",
            y="Total Positive",
            title="NEPSE Equity Trend"
        )
        st.plotly_chart(fig)
    else:
        st.write("No NEPSE equity data available.")

# Update the `display_nepse_equity` function to show the data
def display_nepse_equity():
    st.subheader("NEPSE Equity Data")
    if not st.session_state.nepse_equity.empty:
        st.dataframe(st.session_state.nepse_equity)
    else:
        st.write("No NEPSE equity data available.")

# Update the `main` function to ensure proper data flow
def main():
    st.title("Sector Data Editor")
    sectors = initialize_session()
    
    tab1, tab2, tab3 = st.tabs(["Sector Data Entry", "NEPSE Equity", "Analysis & Charts"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
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
        
        st.subheader(f"Data Editor - {selected_sector}")
        edited_df = st.data_editor(
            st.session_state.data[selected_sector],
            num_rows="dynamic",
            key=f"editor_{selected_sector}",
            hide_index=True
        )
    
    with tab2:
        st.subheader("NEPSE Equity Management")
        display_nepse_equity()
        plot_nepse_data()
    
    with tab3:
        st.subheader("Sector Analysis")
        # Add your analysis and chart code here

if __name__ == "__main__":
    main()
