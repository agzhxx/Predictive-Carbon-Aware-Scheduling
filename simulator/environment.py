import simpy
from typing import Dict, Any, List
from datetime import datetime, timedelta

class CloudEnvironment:
    def __init__(self, env: simpy.Environment, start_time: datetime, regions_config: Dict[str, Any]):
        self.env = env
        self.virtual_start_time = start_time
        self.regions_config = regions_config
        
        # Resources representing compute instances in each region
        # High capacity to focus on latency and carbon, not queueing theory bottlenecks
        self.region_resources = {
            region: simpy.Resource(env, capacity=1000) 
            for region in regions_config
        }
        
    def get_current_time(self) -> datetime:
        """Returns the virtual datetime in the simulation."""
        # Simulation ticks are 1 second
        return self.virtual_start_time + timedelta(seconds=self.env.now)
    
    def get_carbon_intensity(self, region: str, timestamp: datetime) -> float:
        """
        In a full simulation, this queries the historical dataset.
        For now, mocked with dummy values. Needs integration with DataStore.
        """
        # Placeholder for actual data lookup
        return 200.0
        
    def execute_job(self, job: Dict[str, Any], target_region: str, delay_seconds: int = 0):
        """
        A process modeling the execution of a serverless function.
        """
        # 1. Wait if the scheduler decided to delay the job (temporal shifting)
        if delay_seconds > 0:
            yield self.env.timeout(delay_seconds)
            job['metrics']['delayed_seconds'] = delay_seconds
            
        start_exec_time = self.get_current_time()
        
        # 2. Simulate network latency (geographical shifting penalty)
        # Assuming the 'origin' is us-west-1 for simplicity
        base_latency_ms = 50 
        if target_region != 'us-west-1':
            base_latency_ms += 150 # Mock inter-region latency penalty
            
        yield self.env.timeout(base_latency_ms / 1000.0) # Convert ms to seconds
        
        # 3. Request compute resource in the target region
        with self.region_resources[target_region].request() as req:
            yield req
            
            # 4. Simulate execution time
            exec_time_sec = job['execution_time_ms'] / 1000.0
            yield self.env.timeout(exec_time_sec)
            
            # 5. Record emission and cost metrics upon completion
            end_exec_time = self.get_current_time()
            intensity = self.get_carbon_intensity(target_region, start_exec_time)
            
            # Simple energy model: Energy (kWh) = Power (kW) * Time (hours)
            # Serverless power assumption: ~0.01 kW for a standard invocation
            energy_kwh = 0.01 * (exec_time_sec / 3600.0)
            emissions_g = energy_kwh * intensity
            
            job['metrics']['target_region'] = target_region
            job['metrics']['emissions_g'] = emissions_g
            job['metrics']['completed_at'] = end_exec_time
            job['metrics']['latency_penalty_ms'] = base_latency_ms

if __name__ == "__main__":
    env = simpy.Environment()
    from simulator.config import REGIONS
    cloud_env = CloudEnvironment(env, datetime.now(), REGIONS)
    print("Environment setup successful.")
