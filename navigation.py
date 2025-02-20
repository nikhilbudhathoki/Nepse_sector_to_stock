import streamlit as st
from pos import main as POS
from main2 import main as sector_value_analysis
from main import main as calculator
import app as web_scrapping_app
from sma import main as sma_analysis

# Set page config FIRST and ONLY ONCE

def dashboard():
    col1, col2 = st.columns([1, 3])
    with col1:
        st.image("surakshya.png", use_column_width=True)
    with col2:
        st.header("📌 SURAKSHYA INVESTMENTS")
        st.markdown("""
            **Financial Dashboard**  
            Welcome to the Financial Analysis Suite of Surakdhya Investments!  
            Use the navigation bar to explore different features.
        """)

# Atomic CSS Reset for Streamlit
st.markdown("""
    <style>
    /* Full-width reset */
    .stApp > div,
    .stApp > div > div,
    .main .block-container {
        padding: 0 !important;
        margin: 0 !important;
        max-width: 100% !important;
    }
    
    /* Navigation bar container */
    .nav-container {
        padding: 1rem 2rem;
        background: #f8f9fa;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    
    /* Navigation buttons */
    .stButton > button {
        width: 100% !important;
        padding: 0.75rem !important;
        border-radius: 8px !important;
        transition: all 0.3s !important;
    }
    
    /* Active navigation button */
    .stButton > button[aria-pressed='true'] {
        background: #4CAF50 !important;
        color: white !important;
    }
    
    /* Full-width components */
    .stPlotlyChart,
    .stDataFrame,
    .stDataEditor,
    .stImage {
        width: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    
    /* Column spacing */
    .stHorizontalBlock {
        gap: 1rem;
    }
    
    /* Remove default markdown padding */
    .stMarkdown {
        padding: 0 !important;
    }
    </style>
""", unsafe_allow_html=True)

# Navigation configuration
NAV_ITEMS = {
    0: {"title": "Dashboard", "icon": "🏠"},
    1: {"title": "POS", "icon": "💬"},
    2: {"title": "Sectors", "icon": "📊"},
    3: {"title": "Calculator", "icon": "🧮"},
    4: {"title": "Web Data", "icon": "🌐"},
    5: {"title": "SMA", "icon": "📉"}
}

# Session state initialization
if "current_page" not in st.session_state:
    st.session_state.current_page = 0

# Navigation renderer
def render_nav():
    cols = st.columns(len(NAV_ITEMS) + 2)
    for idx, (key, item) in enumerate(NAV_ITEMS.items()):
        with cols[idx]:
            if st.button(
                f"{item['icon']} {item['title']}",
                key=f"nav_{key}",
                help=item['title'],
                use_container_width=True
            ):
                st.session_state.current_page = key

# Main content renderer
def render_page():
    pages = [
        dashboard,
        lambda: POS(),
        lambda: sector_value_analysis(),
        lambda: calculator(),
        lambda: web_scrapping_app(),
        lambda: sma_analysis()
    ]
    
    container = st.container()
    with container:
        pages[st.session_state.current_page]()
        st.markdown("---")

# App entry point
def main():
    st.markdown("<div class='nav-container'>", unsafe_allow_html=True)
    render_nav()
    st.markdown("</div>", unsafe_allow_html=True)
    render_page()

if __name__ == "__main__":
    main()
