import requests
import json

def test_fpl_api():
    print("Testing FPL API connection...")
    
    # Test the main bootstrap endpoint
    bootstrap_url = "https://fantasy.premierleague.com/api/bootstrap-static/"
    
    try:
        print(f"Attempting to connect to: {bootstrap_url}")
        response = requests.get(bootstrap_url, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ SUCCESS: Connected to FPL API")
            print(f"Found {len(data['elements'])} players")
            print(f"Current gameweek: {next((gw for gw in data['events'] if gw['is_current']), 'None')}")
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("❌ FAILED: Request timed out (10 seconds)")
    except requests.exceptions.ConnectionError:
        print("❌ FAILED: Connection error - check internet")
    except Exception as e:
        print(f"❌ FAILED: {type(e).__name__}: {e}")

if __name__ == "__main__":
    test_fpl_api()