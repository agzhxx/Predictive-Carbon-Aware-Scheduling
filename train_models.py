import os
import sys
import glob
from datetime import datetime

# Add project root to sys path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.electricity_maps_client import ElectricityMapsClient
from simulator.config import REGIONS
from evaluation.runner import DataStore
from models.forecaster import CarbonIntensityModel

def main():
    print("=== Deep Learning Model Trainer ===")
    
    # 1. Initialize data store
    client = ElectricityMapsClient()
    # Dummy start time just to initialize the DataStore
    data_store = DataStore(client, datetime.now())
    
    epochs = 150 # High epoch count for accurate convergence
    
    # 2. Train and Save Models
    for region in REGIONS.keys():
        print(f"\n--- Starting Training for {region} ---")
        
        # Check if we successfully loaded historical data for this region
        if region not in data_store.history or data_store.history[region].empty:
            print(f"ERROR: No historical data found for {region}. Cannot train.")
            continue
            
        region_history_series = data_store.history[region]['carbonIntensity']
        print(f"Found {len(region_history_series)} total hours of historical data across all years.")
        
        # Initialize LSTM
        model = CarbonIntensityModel(use_lstm=True, sequence_length=24)
        
        # Train
        model.train(region_history_series, epochs=epochs)
        
        # Save securely to disk under models/saved/
        model_path = os.path.join("models", "saved", f"lstm_{region}")
        model.save_model(model_path)
        print(f"[{region}] Model trained for {epochs} epochs and saved successfully to {model_path}!")

if __name__ == "__main__":
    main()
