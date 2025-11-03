import streamlit as st
import pandas as pd
from datetime import datetime
from fpl_data_handler import FPLDataHandler
from utils.visualizations import create_visualizations
from utils.helpers import clear_cache, get_cache_info

def main_page(fpl_handler):
    """Main dashboard page"""
    st.title("⚽ FPL Rolling Points Analysis Dashboard")
    st.markdown("Track player performance with rolling averages and advanced metrics")
    
    # Cache management
    st.sidebar.subheader("Data Management")
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🔄 Refresh All Data"):
            st.cache_data.clear()
            clear_cache()
            st.rerun()
    
    with col2:
        if st.button("📊 Force New Analysis"):
            st.rerun()
    
    # Cache info
    cache_size = get_cache_info()
    st.sidebar.info(f"📁 Cached data: {cache_size} files")
    
    # Weeks selection
    weeks = st.sidebar.slider(
        "Rolling Period (Weeks)",
        min_value=2,
        max_value=6,
        value=3,
        help="Number of recent gameweeks to include in rolling average"
    )
    
    # Position filter
    positions = ['All', 'Goalkeeper', 'Defender', 'Midfielder', 'Forward']
    selected_position = st.sidebar.selectbox("Filter by Position", positions)
    
    # Cost filter
    min_cost, max_cost = st.sidebar.slider(
        "Cost Range (£m)",
        min_value=4.0,
        max_value=13.0,
        value=(4.0, 13.0),
        step=0.5
    )
    
    # Minimum minutes filter
    min_minutes = st.sidebar.number_input(
        f"Minimum Minutes (Last {weeks} GWs)",
        min_value=0,
        max_value=270 * weeks,
        value=90,
        step=45
    )
    
    # Main content area
    st.subheader(f"Rolling {weeks}-Week Performance Analysis")
    
    # Try to load cached results first
    cached_results = None
    cache_key = f"results_{weeks}wk"
    if fpl_handler.is_cache_valid(cache_key, max_age_hours=6):
        cached_data = fpl_handler.load_from_cache(cache_key)
        if cached_data and 'data' in cached_data:
            cached_results = pd.DataFrame(cached_data['data'])
    
    if cached_results is not None and not st.sidebar.checkbox("Force new data collection", value=False):
        df = cached_results
        st.success(f"📊 Using cached analysis from {len(df)} players")
    else:
        # Collect new data with progress tracking
        with st.spinner("Starting data collection... This may take 2-3 minutes for the first load."):
            df = fpl_handler.calculate_rolling_averages(weeks=weeks, use_progress=True)
    
    if df.empty:
        st.error("""
        No data available. Possible reasons:
        - FPL API is temporarily down
        - Internet connection issues
        - The season hasn't started
        - Rate limiting by FPL
        """)
        return
    
    # Apply filters
    if selected_position != 'All':
        df = df[df['Position'] == selected_position]
    
    df = df[df['Total_Minutes'] >= min_minutes]
    df = df[df['Cost_Numeric'] >= min_cost]
    df = df[df['Cost_Numeric'] <= max_cost]
    
    # Display summary metrics
    st.subheader("Summary Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Players", len(df))
    with col2:
        avg_points = df[f'Rolling_{weeks}_Week_Avg'].mean()
        st.metric("Average Rolling Points", f"{avg_points:.2f}")
    with col3:
        avg_ppm90 = df['Points_Per_90'].mean()
        st.metric("Average Points/90", f"{avg_ppm90:.2f}")
    with col4:
        if len(df) > 0:
            best_player = df.iloc[0]['Player']
            best_points = df.iloc[0][f'Rolling_{weeks}_Week_Avg']
            st.metric("Top Performer", f"{best_player} ({best_points})")
        else:
            st.metric("Top Performer", "N/A")
    
    # Create and display visualizations
    st.subheader("Performance Visualizations")
    fig1, fig2, fig3 = create_visualizations(df, weeks)
    
    if fig1:
        st.plotly_chart(fig1, use_container_width=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.plotly_chart(fig2, use_container_width=True)
        with col2:
            st.plotly_chart(fig3, use_container_width=True)
    
    # Data table
    st.subheader("Player Data")
    
    # Column configuration for data table
    display_columns = [
        'Player', 'Team', 'Position', 'Cost', 
        f'Rolling_{weeks}_Week_Avg', 'Points_Per_90',
        'Goals', 'Assists', 'Bonus_Points', 'Form', 'Selected_By'
    ]
    
    st.dataframe(
        df[display_columns],
        use_container_width=True,
        height=400
    )
    
    # Export option
    csv = df.to_csv(index=False)
    st.download_button(
        label="📥 Export to CSV",
        data=csv,
        file_name=f"fpl_rolling_{weeks}_week_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv"
    )
    
    return df
    