import streamlit as st
from main3 import main as sentiment_analysis
from main2 import main as sector_value_analysis
from main import main as calculator
from app import main as web_scrapping_app

def dashboard():
    st.header("📌 SURAKSHYA INVESTMENTS \nFinancial Dashboard")
    st.write("Welcome to the Financial Analysis Suite of Surakdhya Investments! Use the navigation bar to explore different features.")
    st.image("https://via.placeholder.com/800x300?text=Financial+Dashboard")

# Custom CSS for styling
st.markdown("""
    <style>
    .nav-button {
        padding: 0.75rem 1.5rem;
        border-radius: 10px;
        transition: all 0.3s;
        margin: 0 0.5rem;
    }
    .nav-button:hover {
        transform: scale(1.05);
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    }
    .active-nav {
        background-color: #4CAF50;
        color: white !important;
    }
    .stRadio > div {flex-direction: row !important;}
    .st-emotion-cache-1v0mbdj {margin: auto;}
    </style>
""", unsafe_allow_html=True)

# Initialize session state
if "slide" not in st.session_state:
    st.session_state.slide = 0

# Navigation configuration
NAV_ITEMS = {
    0: {"title": "📌 Dashboard", "icon": "🏠"},
    1: {"title": "📈 Sentiment Analysis", "icon": "💬"},
    2: {"title": "🏦 Sector Analysis", "icon": "📊"},
    3: {"title": "🌐 Calculator", "icon": "🕷️"},
    4: {"title": "🔍 Web Scraping App", "icon": "🌍"}
}

def render_navigation():
    cols = st.columns([1, 3, 1])
    with cols[1]:
        st.title("Financial Analysis Suite")
    
    nav_cols = st.columns(len(NAV_ITEMS) + 2)
    for idx, (key, item) in enumerate(NAV_ITEMS.items()):
        with nav_cols[idx]:
            is_active = key == st.session_state.slide
            btn_style = "nav-button active-nav" if is_active else "nav-button"
            if st.button(
                f"{item['icon']} {item['title']}",
                key=f"nav_{key}",
                use_container_width=True
            ):
                st.session_state.slide = key
    
    with nav_cols[-1]:
        st.markdown(f"**Step {st.session_state.slide}/{len(NAV_ITEMS) - 1}**")
        st.progress((st.session_state.slide / (len(NAV_ITEMS) - 1)))

def render_content():
    if st.session_state.slide == 0:
        dashboard()
    elif st.session_state.slide == 1:
        st.header("Sentiment Analysis Insights")
        sentiment_analysis()
    elif st.session_state.slide == 2:
        st.header("Sector Valuation Metrics")
        sector_value_analysis()
    elif st.session_state.slide == 3:
        st.header("Web Data Acquisition")
        calculator()
    elif st.session_state.slide == 4:
        st.header("Web Scraping Application")
        web_scrapping_app()

def render_footer():
    col1, col2, col3 = st.columns([2, 6, 2])
    with col1:
        if st.session_state.slide > 0:
            st.button("◀ Previous Section", on_click=lambda: st.session_state.update(slide=st.session_state.slide-1))
    with col3:
        if st.session_state.slide < len(NAV_ITEMS) - 1:
            st.button("Next Section ▶", on_click=lambda: st.session_state.update(slide=st.session_state.slide+1))

def main():
    render_navigation()
    st.markdown("---")
    render_content()
    st.markdown("---")
    render_footer()

if __name__ == "__main__":
    main()
