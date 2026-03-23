import pandas as pd
import numpy as np
import os
from datetime import datetime, timedelta

class AzureTraceLoader:
    def __init__(self, trace_dir="azure_dataset"):
        self.trace_dir = trace_dir
        
    def load_traces(self, base_time=None) -> pd.DataFrame:
        """
        Attempts to load real Azure Function traces format.
        If file is missing, generates a realistic mock trace dataset matching Azure's distribution.
        """
        file_path = os.path.join("data", "azure_dataset", "AzureFunctionsInvocationTraceForTwoWeeksJan2021.txt")
        
        if os.path.exists(file_path):
            print(f"Loading real Azure traces from {file_path}")
            # The file is very large (300MB), read a chunk for simulation speed and memory safety
            df = pd.read_csv(file_path, nrows=150000)
            
            if base_time is None:
                base_time = datetime(2021, 1, 1, 0, 0, 0)
                
            print("Processing Azure Trace timestamps and durations...")
            # Convert 'end_timestamp' seconds to actual datetimes
            df['timestamp'] = base_time + pd.to_timedelta(df['end_timestamp'], unit='s')
            df['execution_time_ms'] = df['duration'] * 1000
            df['function_id'] = df['func']
            df['memory_mb'] = 256 # Default assumption
            
            # Sort chronologically as expected by the queue manager
            df = df[['timestamp', 'function_id', 'execution_time_ms', 'memory_mb']].sort_values('timestamp').reset_index(drop=True)
            return df
        else:
            print(f"File {file_path} not found. Generating structurally similar mock traces.")
            return self.generate_mock_trace(base_time=base_time)
            
    def generate_mock_trace(self, num_functions=100, num_days=7, base_time=None) -> pd.DataFrame:
        """
        Generates a flat log of job arrivals mimicking Azure Function Trace density.
        Returns cols: (timestamp, function_id, execution_time_ms, memory_mb)
        """
        jobs = []
        if base_time is None:
            base_time = datetime.now() - timedelta(days=num_days)
            
        
        for f_id in range(num_functions):
            # Pareto principle: 20% functions receive most of the traffic
            is_frequent = np.random.random() < 0.2 
            base_rate = 15 if is_frequent else 1
            
            exec_time = np.random.exponential(200) # Average exec time across functions
            memory = np.random.choice([128, 256, 512, 1024, 2048])
            
            for h in range(num_days * 24):
                hour_of_day = h % 24
                # Simulate diurnal patterns (peak traffic mid-day)
                diurnal_scale = max(0.1, np.sin((hour_of_day - 6) * np.pi / 12)) + 0.5
                arrivals_this_hour = int(base_rate * diurnal_scale * np.random.poisson(5))
                
                for _ in range(arrivals_this_hour):
                    minute_offset = np.random.randint(0, 60)
                    second_offset = np.random.randint(0, 60)
                    job_time = base_time + timedelta(hours=h, minutes=minute_offset, seconds=second_offset)
                    jobs.append({
                        'timestamp': job_time,
                        'function_id': f"func_{f_id}",
                        'execution_time_ms': max(10, exec_time * np.random.lognormal(0, 0.2)),
                        'memory_mb': memory
                    })
                    
        df = pd.DataFrame(jobs)
        # Sort trace chronologically to mimic an event queue
        df = df.sort_values('timestamp').reset_index(drop=True)
        return df

if __name__ == "__main__":
    loader = AzureTraceLoader()
    df = loader.load_traces()
    print(f"Simulated / Loaded {len(df)} jobs.")
    print(df.head())
