import simpy
import pandas as pd
from datetime import datetime
from simulator.environment import CloudEnvironment
from scheduler.policies import BaseScheduler

class JobQueueManager:
    def __init__(self, env: simpy.Environment, cloud_env: CloudEnvironment, scheduler: BaseScheduler):
        self.env = env
        self.cloud_env = cloud_env
        self.scheduler = scheduler
        self.jobs_completed = []

    def start_dispatching(self, traces_df: pd.DataFrame, sim_start_time: datetime):
        """
        Reads jobs from the dataframe and yields SimPy timeout events 
        to trigger job arrivals at the correct simulated times.
        """
        for _, row in traces_df.iterrows():
            job_time = row['timestamp']
            
            # Calculate how many seconds from sim start this job arrives
            arrival_delta = (job_time - sim_start_time).total_seconds()
            
            # If the job is in the past compared to current sim time, dispatch immediately
            wait_time = max(0, arrival_delta - self.env.now)
            
            job_dict = {
                'id': row['function_id'],
                'arrival_time': job_time,
                'execution_time_ms': row['execution_time_ms'],
                'memory_mb': row['memory_mb'],
                'metrics': {} 
            }
            
            # Spin up a concurrent process to handle the delayed arrival and scheduling
            self.env.process(self._handle_job_arrival(wait_time, job_dict))
            
    def _handle_job_arrival(self, wait_time: float, job: dict):
        # Wait until the job actually arrives in the simulation
        if wait_time > 0:
            yield self.env.timeout(wait_time)
            
        # 1. Ask the scheduler: WHERE and WHEN?
        target_region, delay_seconds = self.scheduler.schedule(job)
        
        # 2. Forward to the environment execution process
        yield self.env.process(self.cloud_env.execute_job(job, target_region, delay_seconds))
        
        # 3. Store result
        self.jobs_completed.append(job)

if __name__ == "__main__":
    print("Job queue manager defined.")
