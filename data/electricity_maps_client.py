import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class ElectricityMapsClient:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("ELECTRICITY_MAPS_API_KEY")
        if not self.api_key:
            raise ValueError("API Key for Electricity Maps is missing!")
        
        # Base URL for history endpoints.
        self.base_url = "https://api-access.electricitymaps.com/free-tier/carbon-intensity/history"
        self.headers = {"auth-token": self.api_key}

    def fetch_history(self, zone: str, start_date: datetime = None) -> pd.DataFrame:
        """
        Fetches historical data for a specific zone if API permits, 
        or returns mock realistic data based on zone profiles for prototype purposes
        while waiting for data integration or if API rate limits are hit.
        """
        url = f"{self.base_url}?zone={zone}"
        
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            if 'history' in data:
                return self._parse_to_dataframe(data['history'])
        except Exception as e:
            print(f"Warning: Failed to fetch data from API for {zone}. Error: {e}")
            print("Falling back to realistic simulated generation based on zone profile...")
            return self.generate_mock_history(zone, days=7)
            
    def _parse_to_dataframe(self, history):
        df = pd.DataFrame(history)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
        # Remove timezone information to prevent comparison errors with naive datetimes
        df.index = df.index.tz_localize(None)
        return df[['carbonIntensity']]

    def generate_mock_history(self, zone: str, days: int = 7) -> pd.DataFrame:
        """
        Generates structurally accurate hourly carbon intensity trace if API fails.
        """
        import numpy as np
        
        hours = days * 24
        base_time = datetime.now() - timedelta(days=days)
        time_index = [base_time + timedelta(hours=i) for i in range(hours)]
        
        if zone == 'US-CAL-CISO': # California (Duck curve baseline)
            base = 250
            solar_curve = np.sin((np.arange(hours) % 24 - 6) * np.pi / 12) * -150
            noise = np.random.normal(0, 10, hours)
            intensity = np.clip(base + solar_curve + noise, 30, 500)
        elif zone == 'SE-SE3': # Sweden (Hydro/Nuclear baseline - exceedingly clean)
            intensity = np.random.normal(30, 5, hours)
        elif zone == 'DE': # Germany (Wind/Solar + Coal baseline)
            base = 350
            daily_curve = np.sin((np.arange(hours) % 24 - 6) * np.pi / 12) * -100
            wind_variance = np.sin(np.arange(hours) / 48 * np.pi) * 150
            intensity = np.clip(base + daily_curve + wind_variance, 100, 700)
        elif zone == 'AUS-NSW': # Australia NSW (Coal baseline - intensely dirty)
            intensity = np.random.normal(700, 30, hours)
        else:
            intensity = np.random.normal(400, 50, hours)
            
        df = pd.DataFrame({'carbonIntensity': intensity}, index=time_index)
        return df

if __name__ == "__main__":
    client = ElectricityMapsClient()
    df = client.fetch_history("US-CAL-CISO")
    print("California Sample Data:")
    print(df.head())
