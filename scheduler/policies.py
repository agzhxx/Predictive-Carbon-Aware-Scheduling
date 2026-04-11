from typing import Dict, Any, List
from datetime import datetime
from simulator.config import SLA_MAX_DELAY_HOURS

class BaseScheduler:
    def __init__(self, cloud_env):
        self.cloud_env = cloud_env

    def schedule(self, job: Dict[str, Any]) -> tuple[str, int]:
        """
        Takes a job. Returns (Target Region, Delay in seconds).
        Default behavior: Schedule immediately in the default region.
        """
        return 'us-west-1', 0

class LatencyOptimizedScheduler(BaseScheduler):
    def schedule(self, job: Dict[str, Any]) -> tuple[str, int]:
        # Always run immediately in the local/closest region (us-west-1)
        return 'us-west-1', 0

class CostOptimizedScheduler(BaseScheduler):
    def schedule(self, job: Dict[str, Any]) -> tuple[str, int]:
        # Spatial shifting: Find the cheapest region
        cheapest_region = min(self.cloud_env.regions_config.keys(), key=lambda r: self.cloud_env.regions_config[r]['cost_multiplier'])
        return cheapest_region, 0

class GreedyCarbonScheduler(BaseScheduler):
    def __init__(self, cloud_env, history_data_store):
        super().__init__(cloud_env)
        self.data_store = history_data_store

    def schedule(self, job: Dict[str, Any]) -> tuple[str, int]:
        # Spatial shifting: Send to the cleanest region right NOW
        current_time = self.cloud_env.get_current_time()
        
        best_region = 'us-west-1'
        min_carbon = float('inf')
        
        for region in self.cloud_env.regions_config.keys():
            intensity = self.data_store.get_real_intensity(region, current_time)
            if intensity < min_carbon:
                min_carbon = intensity
                best_region = region
                
        return best_region, 0

class PredictiveCarbonAwareScheduler(BaseScheduler):
    def __init__(self, cloud_env, history_data_store, display_models, sla_max_delay_hours=SLA_MAX_DELAY_HOURS):
        super().__init__(cloud_env)
        self.data_store = history_data_store
        # Expected dict: {'region_name': CarbonIntensityModel}
        self.models = display_models  
        self.sla_max_delay_hours = sla_max_delay_hours

    def schedule(self, job: Dict[str, Any]) -> tuple[str, int]:
        current_time = self.cloud_env.get_current_time()
        
        # We will evaluate two dimensions to find the absolute minimum carbon:
        # 1. Spatially shifting NOW to another region
        # 2. Temporally shifting LATER (within SLA) in any region
        
        best_region = 'us-west-1'
        best_delay = 0
        min_predicted_carbon = float('inf')
        
        # Max delay in seconds
        max_delay_sec = int(self.sla_max_delay_hours * 3600)
        
        # Loop through all possible delay hours within SLA to find the absolute minimum predicted carbon
        for hour_to_wait in range(int(self.sla_max_delay_hours) + 1):
            for region in self.cloud_env.regions_config.keys():
                
                # If wait is 0, we check real-time intensity
                if hour_to_wait == 0:
                    intensity = self.data_store.get_real_intensity(region, current_time)
                else:
                    # Use PyTorch recursive forecasting for future hours
                    recent_hist = self.data_store.get_recent_history(region, current_time, hours=24)
                    if self.models and region in self.models:
                        intensity = self.models[region].predict_multi(recent_hist, steps=hour_to_wait)
                    else:
                        intensity = float('inf') # Fallback if model missing
                
                if intensity < min_predicted_carbon:
                    min_predicted_carbon = intensity
                    best_region = region
                    best_delay = hour_to_wait * 3600
                    
        return best_region, best_delay
