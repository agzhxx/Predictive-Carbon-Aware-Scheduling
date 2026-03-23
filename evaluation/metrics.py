import pandas as pd
from typing import List, Dict, Any

def calculate_kpis(jobs_completed: List[Dict[str, Any]]) -> Dict[str, float]:
    """
    Calculates primary Evaluation Metrics from a completed simulation run.
    """
    if not jobs_completed:
        return {
            'total_emissions_g': 0.0,
            'avg_latency_ms': 0.0,
            'avg_delay_hours': 0.0,
            'total_cost_multiplier_units': 0.0,
            'total_jobs_completed': 0
        }
        
    df = pd.DataFrame([j['metrics'] for j in jobs_completed])
    
    # 1. Total Carbon Emissions (gCO2eq)
    total_emissions = df['emissions_g'].sum()
    
    # 2. Average Network Latency Penalty (ms)
    avg_latency = df['latency_penalty_ms'].mean()
    
    # 3. Average Temporal Delay (hours) - how long did jobs wait for clean energy?
    # Handle cases where 'delayed_seconds' might be missing if 0
    if 'delayed_seconds' in df.columns:
        avg_delay_hrs = (df['delayed_seconds'].fillna(0).mean()) / 3600.0
    else:
        avg_delay_hrs = 0.0
        
    # 4. We can sum cost multipliers roughly as a proxy for total cost.
    # In reality, this would be invocation_time * GB-s price * region_multiplier
    # For now, we omit complex cost modeling, keeping it at a placeholder metrics level
    
    return {
        'total_emissions_g': total_emissions,
        'avg_latency_ms': avg_latency,
        'avg_delay_hours': avg_delay_hrs,
        'total_jobs_completed': len(jobs_completed)
    }

def print_kpis(policy_name: str, kpis: Dict[str, float]):
    print(f"--- Results for {policy_name} ---")
    print(f"Total Jobs Executed: {kpis['total_jobs_completed']}")
    print(f"Total Carbon Emissions: {kpis['total_emissions_g']:.2f} gCO2eq")
    print(f"Avg Geographic Latency: {kpis['avg_latency_ms']:.2f} ms")
    print(f"Avg Temporal Delay: {kpis['avg_delay_hours']:.3f} hours")
    print("-" * 35)

if __name__ == "__main__":
    print("Metrics defined.")
