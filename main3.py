import streamlit as st
import pandas as pd
import plotly.express as px
import os

# Configuration
PERSISTENT_FILE = "nepse_data.csv"

# Set up page config


# Initialize session state for data persistence
if 'raw_data' not in st.session_state:
    st.session_state.raw_data = None

# Load NEPSE data from persistent storage
def load_nepse_data():
    """Load NEPSE data from persistent storage"""
    if os.path.exists(PERSISTENT_FILE):
        df = pd.read_csv(PERSISTENT_FILE)
        df['DATE'] = pd.to_datetime(df['DATE'], errors='coerce')
        return df.dropna(subset=['DATE'])
    return None

# Save NEPSE data to persistent storage
def save_nepse_data(df):
    """Save NEPSE data to persistent storage"""
    df.to_csv(PERSISTENT_FILE, index=False)

# Categorize sentiment based on positive values
def categorize_sentiment(positive):
    """Categorize sentiment based on positive values"""
    if positive >= 60:
        return "Strong"
    elif positive >= 50:
        return "Mid"
    else:
        return "Weak"

# Main function
def main():
    st.title("🚀 NEPSE Advanced Sentiment Dashboard")

    # File uploader
    uploaded_file = st.file_uploader("📤 Upload NEPSE Data", type=['csv'])

    # Load data into session state
    if uploaded_file:
        st.session_state.raw_data = pd.read_csv(uploaded_file)
    elif st.session_state.raw_data is None:
        st.session_state.raw_data = load_nepse_data()

    if st.session_state.raw_data is None:
        st.warning("Please upload a CSV file to begin analysis")
        return

    # Ensure 'Positive' column exists and is numeric
    if 'Positive' in st.session_state.raw_data.columns:
        st.session_state.raw_data['Positive'] = pd.to_numeric(
            st.session_state.raw_data['Positive'], errors='coerce'
        )
        st.session_state.raw_data['sentiment_strength'] = st.session_state.raw_data['Positive'].apply(
            categorize_sentiment
        )

    # Data editor
    with st.expander("✏️ Data Editor", expanded=False):
        edited_data = st.data_editor(
            st.session_state.raw_data.drop(columns=['sentiment_strength'], errors='ignore'),
            num_rows="dynamic"
        )

        # Save button
        if st.button("💾 Update Dataset"):
            st.session_state.raw_data = edited_data
            save_nepse_data(st.session_state.raw_data)
            st.success("✅ Dataset updated successfully!")
            st.rerun()  # Force rerun to update visualizations immediately

    # Display analysis sections
    col1, col2 = st.columns(2)

    with col1:
        st.write("📊 Sentiment Distribution")
        if 'sentiment_strength' in st.session_state.raw_data.columns:
            fig = px.pie(
                st.session_state.raw_data,
                names='sentiment_strength',
                title="Sentiment Strength Distribution"
            )
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.write("📈 Positive Sentiment Timeline")
        if 'Positive' in st.session_state.raw_data.columns:
            fig = px.line(
                st.session_state.raw_data,
                x='DATE',
                y='Positive',
                title="Positive Sentiment Over Time",
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)

    # Detailed sentiment analysis
    st.write("🔍 Detailed Sentiment Analysis")
    if 'sentiment_strength' in st.session_state.raw_data.columns:
        st.dataframe(
            st.session_state.raw_data[['DATE', 'Positive', 'sentiment_strength']].sort_values('DATE', ascending=False),
            height=300,
            use_container_width=True
        )

if __name__ == "__main__":
    main()