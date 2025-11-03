import requests
import pandas as pd
import streamlit as st
from datetime import datetime, timedelta
import time
import os
import json

class FPLDataHandler:
    def __init__(self):
        self.base_url = "https://fantasy.premierleague.com/api/"
        self.cache_dir = "fpl_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
    def get_cache_file(self, cache_type):
        return os.path.join(self.cache_dir, f"{cache_type}.json")
    
    def is_cache_valid(self, cache_type, max_age_hours=6):
        """Check if cache is still valid"""
        cache_file = self.get_cache_file(cache_type)
        if not os.path.exists(cache_file):
            return False
        
        file_time = datetime.fromtimestamp(os.path.getmtime(cache_file))
        return (datetime.now() - file_time) < timedelta(hours=max_age_hours)
    
    def load_from_cache(self, cache_type):
        """Load data from cache"""
        try:
            cache_file = self.get_cache_file(cache_type)
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            st.warning(f"Could not load cache: {e}")
        return None
    
    def save_to_cache(self, cache_type, data):
        """Save data to cache"""
        try:
            cache_file = self.get_cache_file(cache_type)
            with open(cache_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            st.warning(f"Could not save cache: {e}")
    
    def get_bootstrap_data(self):
        """Get main FPL data with caching"""
        # Try to load from cache first
        if self.is_cache_valid('bootstrap'):
            cached_data = self.load_from_cache('bootstrap')
            if cached_data:
                return cached_data
        
        # Fetch fresh data if cache is invalid or missing
        try:
            response = requests.get(f"{self.base_url}bootstrap-static/", timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Save to cache
            self.save_to_cache('bootstrap', data)
            return data
            
        except requests.exceptions.RequestException as e:
            st.error(f"❌ Error fetching bootstrap data: {e}")
            # Try to return stale cache if available
            cached_data = self.load_from_cache('bootstrap')
            if cached_data:
                st.warning("Using stale cached data as fallback")
                return cached_data
            return None
    
    def get_player_history(self, player_id, player_name=""):
        """Get individual player history with caching"""
        cache_key = f"player_{player_id}"
        
        # Try cache first
        if self.is_cache_valid(cache_key, max_age_hours=24):
            cached_data = self.load_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        # Fetch fresh data
        try:
            response = requests.get(
                f"{self.base_url}element-summary/{player_id}/", 
                timeout=15
            )
            response.raise_for_status()
            data = response.json()
            
            # Save to cache
            self.save_to_cache(cache_key, data)
            return data
            
        except requests.exceptions.RequestException:
            # Try stale cache as fallback
            cached_data = self.load_from_cache(cache_key)
            if cached_data:
                return cached_data
            return None
    
    def get_team_data(self, team_id, gameweek=None):
        """Get FPL team data for a specific team ID"""
        cache_key = f"team_{team_id}_{gameweek if gameweek else 'current'}"
        
        # Try cache first
        if self.is_cache_valid(cache_key, max_age_hours=2):
            cached_data = self.load_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        # Fetch fresh team data
        try:
            if not gameweek:
                # Get current gameweek from bootstrap
                bootstrap_data = self.get_bootstrap_data()
                if bootstrap_data:
                    for event in bootstrap_data['events']:
                        if event['is_current']:
                            gameweek = event['id']
                            break
            
            if gameweek:
                team_url = f"{self.base_url}entry/{team_id}/event/{gameweek}/picks/"
                response = requests.get(team_url, timeout=15)
                response.raise_for_status()
                team_data = response.json()
                
                # Save to cache
                self.save_to_cache(cache_key, team_data)
                return team_data
                
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching team data: {e}")
        
        return None
    
    def get_fixtures(self):
        """Get fixture data"""
        cache_key = "fixtures"
        
        if self.is_cache_valid(cache_key, max_age_hours=12):
            cached_data = self.load_from_cache(cache_key)
            if cached_data:
                return cached_data
        
        try:
            response = requests.get(f"{self.base_url}fixtures/", timeout=15)
            response.raise_for_status()
            fixtures = response.json()
            
            self.save_to_cache(cache_key, fixtures)
            return fixtures
        except requests.exceptions.RequestException:
            return None
    
    def calculate_rolling_averages(self, weeks=3, use_progress=True):
        """Calculate rolling averages for all players"""
        bootstrap_data = self.get_bootstrap_data()
        if not bootstrap_data:
            st.error("❌ Could not load FPL data. Check your internet connection.")
            return pd.DataFrame()
        
        players = bootstrap_data['elements']
        teams = {team['id']: team['name'] for team in bootstrap_data['teams']}
        positions = {
            1: 'Goalkeeper', 
            2: 'Defender', 
            3: 'Midfielder', 
            4: 'Forward'
        }
        
        # Find current gameweek
        current_gw = None
        for event in bootstrap_data['events']:
            if event['is_current']:
                current_gw = event['id']
                break
        
        if not current_gw:
            st.warning("No current gameweek found - season may be over")
            return pd.DataFrame()
        
        # Setup progress tracking
        if use_progress:
            st.subheader("📊 Data Collection Progress")
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        results = []
        processed_count = 0
        successful_count = 0
        start_time = time.time()
        
        for i, player in enumerate(players):
            player_id = player['id']
            player_name = player['web_name']
            team_name = teams[player['team']]
            position = positions[player['element_type']]
            cost = player['now_cost'] / 10  # Convert to millions
            
            # Update progress
            if use_progress:
                progress = (i + 1) / len(players)
                progress_bar.progress(progress)
                
                elapsed_time = time.time() - start_time
                estimated_total = elapsed_time / progress if progress > 0 else 0
                remaining_time = estimated_total - elapsed_time
                
                status_text.text(
                    f"Processing {player_name}... "
                    f"({i+1}/{len(players)}) | "
                    f"Successful: {successful_count} | "
                    f"ETA: {remaining_time:.0f}s"
                )
            
            history_data = self.get_player_history(player_id, player_name)
            processed_count += 1
            
            if not history_data:
                continue
                
            history = history_data.get('history', [])
            
            # Get last X gameweeks with points
            recent_games = [
                game for game in history 
                if game['round'] <= current_gw and game['minutes'] > 0
            ]
            recent_games.sort(key=lambda x: x['round'], reverse=True)
            
            if len(recent_games) >= weeks:
                last_n_games = recent_games[:weeks]
                total_points = sum(game['total_points'] for game in last_n_games)
                rolling_avg = total_points / weeks
                
                # Calculate points per 90 minutes
                total_minutes = sum(game['minutes'] for game in last_n_games)
                ppm90 = (total_points / total_minutes * 90) if total_minutes > 0 else 0
                
                # Additional metrics
                total_goals = sum(game['goals_scored'] for game in last_n_games)
                total_assists = sum(game['assists'] for game in last_n_games)
                total_bonus = sum(game['bonus'] for game in last_n_games)
                
                results.append({
                    'Player': player_name,
                    'Player_ID': player_id,
                    'Team': team_name,
                    'Position': position,
                    'Cost': f"£{cost:.1f}m",
                    'Cost_Numeric': cost,
                    f'Last_{weeks}_GW_Points': total_points,
                    f'Rolling_{weeks}_Week_Avg': round(rolling_avg, 2),
                    'Points_Per_90': round(ppm90, 2),
                    'Goals': total_goals,
                    'Assists': total_assists,
                    'Bonus_Points': total_bonus,
                    'Total_Minutes': total_minutes,
                    'Form': float(player['form']) if player['form'] else 0,
                    'Selected_By': float(player['selected_by_percent']),
                    'ICT_Index': float(player['ict_index']) if player['ict_index'] else 0
                })
                successful_count += 1
        
        # Clear progress indicators
        if use_progress:
            progress_bar.empty()
            status_text.empty()
        
        total_time = time.time() - start_time
        st.success(f"✅ Data collection complete! Processed {processed_count} players, {successful_count} with sufficient data in {total_time:.1f} seconds")
        
        df = pd.DataFrame(results)
        if not df.empty:
            df = df.sort_values(f'Rolling_{weeks}_Week_Avg', ascending=False)
            
            # Cache the final results
            cache_key = f"results_{weeks}wk"
            self.save_to_cache(cache_key, {
                'data': df.to_dict('records'),
                'timestamp': datetime.now().isoformat(),
                'gameweek': current_gw
            })
            
        return df