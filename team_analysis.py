import streamlit as st
import pandas as pd
from fpl_data_handler import FPLDataHandler

def analyze_team_performance(team_id, all_players_df, weeks=3):
    """Analyze a specific FPL team and compare with alternatives"""
    fpl_handler = FPLDataHandler()
    
    st.subheader(f"🔍 Analyzing Team #{team_id}")
    
    # Get team data
    with st.spinner("Fetching team data..."):
        team_data = fpl_handler.get_team_data(team_id)
    
    if not team_data:
        st.error(f"Could not fetch team data for ID {team_id}. Please check the team ID and try again.")
        return
    
    # Get player details from picks
    team_players = []
    bootstrap_data = fpl_handler.get_bootstrap_data()
    if not bootstrap_data:
        st.error("Could not load FPL data.")
        return
        
    teams = {team['id']: team['name'] for team in bootstrap_data['teams']}
    positions = {1: 'Goalkeeper', 2: 'Defender', 3: 'Midfielder', 4: 'Forward'}
    
    for pick in team_data['picks']:
        player_id = pick['element']
        player_data = next((p for p in bootstrap_data['elements'] if p['id'] == player_id), None)
        
        if player_data:
            # Find this player in our rolling averages data
            if 'Player_ID' in all_players_df.columns:
                player_rolling_data = all_players_df[all_players_df['Player_ID'] == player_id]
            else:
                # Fallback: try to match by player name and team
                player_name = player_data['web_name']
                team_name = teams[player_data['team']]
                player_rolling_data = all_players_df[
                    (all_players_df['Player'] == player_name) & 
                    (all_players_df['Team'] == team_name)
                ]
            
            if not player_rolling_data.empty:
                player_row = player_rolling_data.iloc[0]
                
                # Get the correct rolling average column name based on weeks
                rolling_avg_col = f'Rolling_{weeks}_Week_Avg'
                
                # Check if the column exists, if not use a default value
                if rolling_avg_col in player_row:
                    rolling_avg = player_row[rolling_avg_col]
                else:
                    # Try to find any rolling average column as fallback
                    rolling_cols = [col for col in player_row.index if col.startswith('Rolling_') and col.endswith('_Week_Avg')]
                    if rolling_cols:
                        rolling_avg = player_row[rolling_cols[0]]
                    else:
                        rolling_avg = 0
                
                team_players.append({
                    'Player': player_data['web_name'],
                    'Player_ID': player_id,
                    'Team': teams[player_data['team']],
                    'Position': positions[player_data['element_type']],
                    'Cost': f"£{player_data['now_cost']/10:.1f}m",
                    'Cost_Numeric': player_data['now_cost']/10,
                    'Rolling_Avg': rolling_avg,
                    'Points_Per_90': player_row['Points_Per_90'] if 'Points_Per_90' in player_row else 0,
                    'Form': player_row['Form'] if 'Form' in player_row else 0,
                    'Selected_By': player_row['Selected_By'] if 'Selected_By' in player_row else 0,
                    'Is_Captain': pick['is_captain'],
                    'Is_Vice_Captain': pick['is_vice_captain'],
                    'Multiplier': pick['multiplier']
                })
            else:
                # Player not found in rolling data, use basic info
                team_players.append({
                    'Player': player_data['web_name'],
                    'Player_ID': player_id,
                    'Team': teams[player_data['team']],
                    'Position': positions[player_data['element_type']],
                    'Cost': f"£{player_data['now_cost']/10:.1f}m",
                    'Cost_Numeric': player_data['now_cost']/10,
                    'Rolling_Avg': 0,
                    'Points_Per_90': 0,
                    'Form': float(player_data['form']) if player_data['form'] else 0,
                    'Selected_By': float(player_data['selected_by_percent']) if player_data['selected_by_percent'] else 0,
                    'Is_Captain': pick['is_captain'],
                    'Is_Vice_Captain': pick['is_vice_captain'],
                    'Multiplier': pick['multiplier']
                })
    
    if not team_players:
        st.error("No player data found for this team.")
        return
    
    team_df = pd.DataFrame(team_players)
    
    # Display team summary
    st.subheader("📊 Team Summary")
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        avg_rolling = team_df['Rolling_Avg'].mean()
        st.metric("Avg Rolling Points", f"{avg_rolling:.2f}")
    with col2:
        total_cost = team_df['Cost_Numeric'].sum()
        st.metric("Total Cost", f"£{total_cost:.1f}m")
    with col3:
        captain_df = team_df[team_df['Is_Captain']]
        captain = captain_df['Player'].iloc[0] if not captain_df.empty else "None"
        st.metric("Captain", captain)
    with col4:
        team_size = len(team_df)
        st.metric("Squad Size", team_size)
    
    # Display team players
    st.subheader("👥 Your Team Players")
    
    # Create a display DataFrame with role indicators
    display_df = team_df.copy()
    display_df['Role'] = ''
    display_df.loc[display_df['Is_Captain'], 'Role'] = '©'
    display_df.loc[display_df['Is_Vice_Captain'], 'Role'] = 'VC'
    
    # Columns to display
    display_cols = ['Player', 'Role', 'Team', 'Position', 'Cost', 'Rolling_Avg', 'Points_Per_90', 'Form', 'Selected_By']
    
    # Display the dataframe
    st.dataframe(
        display_df[display_cols],
        use_container_width=True
    )
    
    # Show captain info separately
    captain_info = team_df[team_df['Is_Captain']][['Player', 'Rolling_Avg']]
    vice_captain_info = team_df[team_df['Is_Vice_Captain']][['Player', 'Rolling_Avg']]
    
    if not captain_info.empty:
        st.info(f"**Captain**: {captain_info['Player'].iloc[0]} (Rolling Avg: {captain_info['Rolling_Avg'].iloc[0]})")
    if not vice_captain_info.empty:
        st.info(f"**Vice Captain**: {vice_captain_info['Player'].iloc[0]} (Rolling Avg: {vice_captain_info['Rolling_Avg'].iloc[0]})")
    
    # Calculate fixture difficulties for all teams first
    fixtures = fpl_handler.get_fixtures()
    team_difficulties = {}
    
    if fixtures:
        current_gw = next((event['id'] for event in bootstrap_data['events'] if event['is_current']), None)
        
        if current_gw:
            upcoming_gws = range(current_gw + 1, min(current_gw + 4, 39))  # Next 3 GWs
            
            for team_id, team_name in teams.items():
                team_fixtures = [
                    f for f in fixtures 
                    if (f['team_a'] == team_id or f['team_h'] == team_id) and 
                    f['event'] in upcoming_gws and f.get('finished', False) is False
                ]
                
                if team_fixtures:
                    total_difficulty = 0
                    for fixture in team_fixtures:
                        # Determine if home or away and get difficulty
                        if fixture['team_h'] == team_id:
                            difficulty = fixture['team_h_difficulty']
                        else:
                            difficulty = fixture['team_a_difficulty']
                        total_difficulty += difficulty
                    
                    avg_difficulty = total_difficulty / len(team_fixtures)
                    team_difficulties[team_name] = {
                        'avg_difficulty': avg_difficulty,
                        'color': '🟢' if avg_difficulty <= 2 else '🟡' if avg_difficulty <= 3 else '🔴',
                        'fixture_count': len(team_fixtures)
                    }
                else:
                    team_difficulties[team_name] = {
                        'avg_difficulty': 'N/A',
                        'color': '⚫',
                        'fixture_count': 0
                    }
    
    # Position-wise analysis and alternatives
    st.subheader("🔄 Position-wise Alternatives")
    
    for position in ['Goalkeeper', 'Defender', 'Midfielder', 'Forward']:
        position_players = team_df[team_df['Position'] == position]
        all_position_players = all_players_df[all_players_df['Position'] == position]
        
        if len(position_players) > 0:
            st.write(f"**{position}s**")
            
            # Create comparison table with detailed alternatives
            comparison_data = []
            
            for _, team_player in position_players.iterrows():
                player_name = team_player['Player']
                player_rolling = team_player['Rolling_Avg']
                player_cost = team_player['Cost_Numeric']
                player_team = team_player['Team']
                
                # Get the correct rolling average column for comparison
                rolling_avg_col = f'Rolling_{weeks}_Week_Avg'
                
                # Check if the column exists in the comparison data
                if rolling_avg_col in all_position_players.columns:
                    # Find better alternatives (higher rolling avg, same or lower cost)
                    alternatives = all_position_players[
                        (all_position_players[rolling_avg_col] > player_rolling) & 
                        (all_position_players['Cost_Numeric'] <= player_cost)  # Same or lower cost only
                    ].head(5)  # Show more alternatives
                else:
                    # If the specific weeks column doesn't exist, use any available rolling average
                    rolling_cols = [col for col in all_position_players.columns if col.startswith('Rolling_') and col.endswith('_Week_Avg')]
                    if rolling_cols:
                        # Use the first available rolling average column
                        alt_rolling_col = rolling_cols[0]
                        alternatives = all_position_players[
                            (all_position_players[alt_rolling_col] > player_rolling) & 
                            (all_position_players['Cost_Numeric'] <= player_cost)
                        ].head(5)
                    else:
                        alternatives = pd.DataFrame()
                
                # Prepare alternatives with fixture information
                alternative_details = []
                for _, alt_row in alternatives.iterrows():
                    alt_team = alt_row['Team']
                    alt_difficulty = team_difficulties.get(alt_team, {'avg_difficulty': 'N/A', 'color': '⚫'})
                    
                    alternative_details.append({
                        'Player': alt_row['Player'],
                        'Team': alt_team,
                        'Cost': f"£{alt_row['Cost_Numeric']:.1f}m",
                        'Rolling_Avg': alt_row[rolling_avg_col] if rolling_avg_col in alt_row else alt_row.get(alt_rolling_col, 'N/A'),
                        'Fixture_Difficulty': alt_difficulty['avg_difficulty'],
                        'Difficulty_Color': alt_difficulty['color'],
                        'Form': alt_row.get('Form', 0),
                        'Points_Per_90': alt_row.get('Points_Per_90', 0)
                    })
                
                # Sort alternatives by fixture difficulty (easier fixtures first)
                if alternative_details:
                    # Convert N/A to a high number for sorting
                    for alt in alternative_details:
                        if alt['Fixture_Difficulty'] == 'N/A':
                            alt['_sort_difficulty'] = 999
                        else:
                            alt['_sort_difficulty'] = alt['Fixture_Difficulty']
                    
                    alternative_details.sort(key=lambda x: x['_sort_difficulty'])
                    
                    # Remove temporary sort key
                    for alt in alternative_details:
                        del alt['_sort_difficulty']
                
                comparison_data.append({
                    'Your_Player': player_name,
                    'Your_Team': player_team,
                    'Your_Rolling_Avg': player_rolling,
                    'Your_Cost': f"£{player_cost:.1f}m",
                    'Your_Form': team_player['Form'],
                    'Your_Fixture_Difficulty': team_difficulties.get(player_team, {'avg_difficulty': 'N/A', 'color': '⚫'})['avg_difficulty'],
                    'Your_Difficulty_Color': team_difficulties.get(player_team, {'color': '⚫'})['color'],
                    'Alternatives_Count': len(alternative_details),
                    'Top_Alternative': alternative_details[0]['Player'] if alternative_details else "None",
                    'Top_Alternative_Team': alternative_details[0]['Team'] if alternative_details else "N/A",
                    'Top_Alternative_Cost': alternative_details[0]['Cost'] if alternative_details else "N/A",
                    'Top_Alternative_Rolling_Avg': alternative_details[0]['Rolling_Avg'] if alternative_details else "N/A",
                    'Top_Alternative_Fixture_Difficulty': alternative_details[0]['Fixture_Difficulty'] if alternative_details else "N/A",
                    'Top_Alternative_Difficulty_Color': alternative_details[0]['Difficulty_Color'] if alternative_details else "⚫",
                    'All_Alternatives': alternative_details  # Store all alternatives for expander
                })
            
            if comparison_data:
                # Create main comparison table
                comp_df = pd.DataFrame(comparison_data)
                
                # Display main comparison
                main_display_cols = [
                    'Your_Player', 'Your_Team', 'Your_Rolling_Avg', 'Your_Cost', 
                    'Your_Fixture_Difficulty', 'Top_Alternative', 'Top_Alternative_Team',
                    'Top_Alternative_Rolling_Avg', 'Top_Alternative_Cost', 'Top_Alternative_Fixture_Difficulty'
                ]
                
                st.dataframe(comp_df[main_display_cols], use_container_width=True)
                
                # Show detailed alternatives in expanders
                for i, row in enumerate(comparison_data):
                    if row['Alternatives_Count'] > 0:
                        with st.expander(f"🔍 All alternatives for {row['Your_Player']}"):
                            alt_details = row['All_Alternatives']
                            if alt_details:
                                alt_df = pd.DataFrame(alt_details)
                                display_alt_cols = ['Player', 'Team', 'Cost', 'Rolling_Avg', 'Fixture_Difficulty', 'Difficulty_Color', 'Form', 'Points_Per_90']
                                st.dataframe(alt_df[display_alt_cols], use_container_width=True)
                            else:
                                st.info("No detailed alternatives found.")
    
    # Fixture analysis for upcoming weeks
    st.subheader("📅 Upcoming Fixture Analysis")
    
    if fixtures:
        # Get next 3 gameweeks
        current_gw = next((event['id'] for event in bootstrap_data['events'] if event['is_current']), None)
        
        if current_gw:
            upcoming_gws = range(current_gw + 1, min(current_gw + 4, 39))  # Next 3 GWs
            
            fixture_difficulty = {}
            
            for player in team_players:
                player_team_id = next((tid for tid, name in teams.items() if name == player['Team']), None)
                if player_team_id:
                    player_fixtures = [
                        f for f in fixtures 
                        if (f['team_a'] == player_team_id or f['team_h'] == player_team_id) and 
                        f['event'] in upcoming_gws and f.get('finished', False) is False
                    ]
                    
                    if player_fixtures:
                        total_difficulty = 0
                        for fixture in player_fixtures:
                            # Determine if home or away and get difficulty
                            if fixture['team_h'] == player_team_id:
                                difficulty = fixture['team_h_difficulty']
                            else:
                                difficulty = fixture['team_a_difficulty']
                            total_difficulty += difficulty
                        
                        avg_difficulty = total_difficulty / len(player_fixtures)
                        fixture_difficulty[player['Player']] = {
                            'Fixtures': len(player_fixtures),
                            'Avg_Difficulty': avg_difficulty,
                            'Difficulty_Color': '🟢' if avg_difficulty <= 2 else '🟡' if avg_difficulty <= 3 else '🔴'
                        }
                    else:
                        # No upcoming fixtures found
                        fixture_difficulty[player['Player']] = {
                            'Fixtures': 0,
                            'Avg_Difficulty': 'N/A',
                            'Difficulty_Color': '⚫'
                        }
            
            # Display fixture difficulty
            if fixture_difficulty:
                fixture_rows = []
                for player, info in fixture_difficulty.items():
                    fixture_rows.append({
                        'Player': player,
                        'Upcoming_Fixtures': info['Fixtures'],
                        'Avg_Difficulty': info['Avg_Difficulty'],
                        'Outlook': info['Difficulty_Color']
                    })
                
                fixture_df = pd.DataFrame(fixture_rows)
                st.dataframe(fixture_df, use_container_width=True)
            else:
                st.info("No upcoming fixture data available.")
        else:
            st.info("Current gameweek not found.")
    else:
        st.info("Fixture data not available.")

def team_analysis_page(fpl_handler, all_players_df):
    """Team analysis page"""
    st.title("🏠 FPL Team Analysis")
    st.markdown("Analyze your FPL team and compare with alternatives")
    
    st.sidebar.subheader("Team Analysis Settings")
    
    # Weeks selection for team analysis
    weeks = st.sidebar.slider(
        "Analysis Period (Weeks)",
        min_value=2,
        max_value=6,
        value=3,
        key="team_weeks",
        help="Number of recent gameweeks to analyze"
    )
    
    # Team ID input
    st.subheader("Enter Your FPL Team ID")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        team_id = st.number_input(
            "FPL Team ID",
            min_value=1,
            max_value=99999999,
            value=12345,  # Default example
            help="You can find your team ID in the URL of your FPL team page: fantasy.premierleague.com/entry/TEAM_ID/event/X"
        )
    
    with col2:
        st.write("")
        st.write("")
        analyze_clicked = st.button("🔍 Analyze Team", type="primary")
    
    if analyze_clicked and team_id:
        # Check if we need to refresh the data for team analysis
        required_column = f'Rolling_{weeks}_Week_Avg'
        
        if 'Player_ID' not in all_players_df.columns or required_column not in all_players_df.columns:
            st.warning(f"Cached data is outdated or doesn't have {weeks}-week averages. Refreshing data...")
            with st.spinner(f"Refreshing data with {weeks}-week averages..."):
                all_players_df = fpl_handler.calculate_rolling_averages(weeks=weeks, use_progress=False)
        
        analyze_team_performance(team_id, all_players_df, weeks)
    
    # Instructions
    with st.expander("ℹ️ How to find your FPL Team ID"):
        st.markdown("""
        1. Go to the [Fantasy Premier League website](https://fantasy.premierleague.com)
        2. Log in to your account
        3. Go to your team page
        4. Look at the URL in your browser's address bar
        5. You'll see a URL like: `https://fantasy.premierleague.com/entry/1234567/event/25`
        6. The number after `/entry/` is your Team ID (1234567 in this example)
        """)