import simpy
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

# Add project root to sys path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.data_loader import AzureTraceLoader
from data.electricity_maps_client import ElectricityMapsClient
from simulator.config import REGIONS
from simulator.environment import CloudEnvironment
from simulator.job_queue import JobQueueManager
from scheduler.policies import (
    LatencyOptimizedScheduler, 
    CostOptimizedScheduler,
    GreedyCarbonScheduler,
    PredictiveCarbonAwareScheduler
)
from evaluation.metrics import calculate_kpis, print_kpis
from visualization.plotter import plot_pareto_front, plot_emission_bars
from models.forecaster import CarbonIntensityModel

import glob

class DataStore:
    def __init__(self, client: ElectricityMapsClient, start_time: datetime):
        self.history = {}
        self.start_time = start_time
        
        print("Initializing Carbon Data for Simulator...")
        for region, info in REGIONS.items():
            zone = info['electricity_maps_zone']
            
            # Use glob to find ALL CSV files mapping to this zone under data/Historical Data (2021, 2025, etc.)
            pattern = os.path.join("data", "Historical Data", f"*{zone}*.csv")
            files = glob.glob(pattern)
            
            if files:
                print(f"Loading {len(files)} historical datasets across multiple years for {region}...")
                zone_dfs = []
                for csv_path in files:
                    df = pd.read_csv(csv_path)
                    
                    # Parse localized datetime
                    df['datetime'] = pd.to_datetime(df['Datetime (UTC)'])
                    df = df.set_index('datetime')
                    df.index = df.index.tz_localize(None)
                    
                    # Extract 'carbonIntensity' safely
                    target_col = 'Carbon intensity gCO₂eq/kWh (Life cycle)'
                    if target_col in df.columns:
                        df['carbonIntensity'] = df[target_col]
                    else: 
                        col = [c for c in df.columns if 'Carbon intensity' in c][0]
                        df['carbonIntensity'] = df[col]
                        
                    zone_dfs.append(df[['carbonIntensity']])
                    
                # Concatenate all years into a single giant contiguous timeseries, sort, and remove duplicates
                full_history = pd.concat(zone_dfs).sort_index()
                full_history = full_history[~full_history.index.duplicated(keep='last')]
                self.history[region] = full_history
                
            else:
                print(f"No local data found for {region}. Attempting to fetch real data from API...")
                df_api = client.fetch_history(zone)
                
                if df_api is not None and not df_api.empty:
                    dfs = []
                    base_index = df_api.index
                    for day_offset in range(8):
                        df_copy = df_api.copy()
                        df_copy.index = base_index - timedelta(days=day_offset)
                        dfs.append(df_copy)
                    full_df = pd.concat(dfs).sort_index()
                    full_df = full_df[~full_df.index.duplicated(keep='last')]
                    self.history[region] = full_df
                else:
                    print(f"Fallback to mock for {region}")
                    self.history[region] = client.generate_mock_history(zone, days=8)

    def get_real_intensity(self, region: str, sim_time: datetime) -> float:
        df = self.history[region]
        # Find closest hour
        closest_idx = df.index.get_indexer([sim_time], method='nearest')[0]
        return float(df.iloc[closest_idx]['carbonIntensity'])
        
    def get_recent_history(self, region: str, sim_time: datetime, hours: int = 24) -> list:
        df = self.history[region]
        mask = (df.index <= sim_time) & (df.index > (sim_time - timedelta(hours=hours)))
        hist = df.loc[mask]['carbonIntensity'].tolist()
        return hist

def run_simulation(policy_class, traces_df: pd.DataFrame, sim_start_time: datetime, data_store: DataStore, models=None):
    """Runs a complete simulation for a given policy class."""
    env = simpy.Environment()
    cloud_env = CloudEnvironment(env, sim_start_time, REGIONS)
    
    # Overwrite cloud_env's carbon lookup with our realistic datastore
    cloud_env.get_carbon_intensity = data_store.get_real_intensity
    
    if policy_class == PredictiveCarbonAwareScheduler:
        scheduler = policy_class(cloud_env, data_store, models)
    elif policy_class == GreedyCarbonScheduler:
        scheduler = policy_class(cloud_env, data_store)
    else:
        scheduler = policy_class(cloud_env)
        
    queue_manager = JobQueueManager(env, cloud_env, scheduler)
    queue_manager.start_dispatching(traces_df, sim_start_time)
    
    print(f"Running simulation with {policy_class.__name__}...")
    env.run()
    
    return queue_manager.jobs_completed

def main():
    # Force traces to live inside our historical 2021 block to match the real trace file
    simulation_base_time = datetime(2021, 1, 1, 0, 0, 0)
    
    # 1. Load Data
    trace_loader = AzureTraceLoader()
    print("Loading traces...")
    traces_df = trace_loader.load_traces(base_time=simulation_base_time)
    
    if len(traces_df) == 0:
        print("No traces found. Exiting.")
        return
        
    sim_start_time = traces_df['timestamp'].min()
    
    # Trim to run faster for demonstration
    max_jobs = 10000
    if len(traces_df) > max_jobs:
        traces_df = traces_df.head(max_jobs)
        
    print(f"Simulating {len(traces_df)} jobs.")
    
    # 2. Setup Carbon Data Provider
    em_client = ElectricityMapsClient()
    data_store = DataStore(em_client, sim_start_time)
    
    # 3. Load Pre-trained Forecasting Models
    models = {}
    print("Loading Pretrained Forecasting Models...")
    for region in REGIONS.keys():
        models[region] = CarbonIntensityModel(use_lstm=True, sequence_length=24)
        model_path = os.path.join("models", "saved", f"lstm_{region}")
        
        if models[region].load_model(model_path):
            print(f"[{region}] Successfully loaded pre-trained LSTM model from disk!")
        else:
            raise FileNotFoundError(
                f"[{region}] No saved model found at {model_path}. "
                f"You must run 'python3 train_models.py' first before running evaluations!"
            )
        
    # 4. Run Scenarios
    policies = {
        'Baseline (Latency)': LatencyOptimizedScheduler,
        'Cost Optimized': CostOptimizedScheduler,
        'Greedy Carbon': GreedyCarbonScheduler,
        'Predictive Carbon': PredictiveCarbonAwareScheduler
    }
    
    results = {}
    for name, policy_class in policies.items():
        completed_jobs = run_simulation(policy_class, traces_df, sim_start_time, data_store, models)
        kpis = calculate_kpis(completed_jobs)
        results[name] = kpis
        print_kpis(name, kpis)
        
    # 5. Visualize
    print("Generating Visualizations...")
    plot_pareto_front(results)
    plot_emission_bars(results)
    print("Done! Charts are saved in the 'results' folder.")

if __name__ == "__main__":
    main()
