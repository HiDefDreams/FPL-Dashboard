import streamlit as st
import pandas as pd
from fpl_data_handler import FPLDataHandler
from pages.dashboard import main_page
from pages.team_analysis import team_analysis_page

# Page configuration
st.set_page_config(
    page_title="FPL Rolling Points Analysis",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    # Initialize data handler
    fpl_handler = FPLDataHandler()
    
    # Sidebar navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.radio(
        "Go to",
        ["📊 Player Analysis Dashboard", "🏠 Team Analysis"]
    )
    
    # Load or calculate player data (needed for both pages)
    with st.spinner("Loading player data..."):
        # Try to load cached data first - default to 3 weeks for main page
        cache_key = "results_3wk"
        all_players_df = None
        
        if fpl_handler.is_cache_valid(cache_key, max_age_hours=6):
            cached_data = fpl_handler.load_from_cache(cache_key)
            if cached_data and 'data' in cached_data:
                all_players_df = pd.DataFrame(cached_data['data'])
                st.sidebar.success("✅ Using cached player data")
        
        if all_players_df is None or all_players_df.empty:
            # Calculate fresh data
            all_players_df = fpl_handler.calculate_rolling_averages(weeks=3, use_progress=False)
    
    # Show appropriate page based on selection
    if page == "📊 Player Analysis Dashboard":
        main_page(fpl_handler)
    elif page == "🏠 Team Analysis":
        team_analysis_page(fpl_handler, all_players_df)

if __name__ == "__main__":
    main()
    