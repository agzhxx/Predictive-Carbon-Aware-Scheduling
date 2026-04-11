import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import os

def plot_pareto_front(results: dict, output_dir: str = "results"):
    """
    Plots the trade-off between Carbon Emissions and Avg Latency/Delay across policies.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    policies = list(results.keys())
    emissions = [results[p]['total_emissions_g'] for p in policies]
    
    # We combine total delay (geographic latency ms -> hours + temporal delay hours)
    # 1 ms = 2.77e-7 hours
    total_delay_hours = [
        results[p]['avg_delay_hours'] + (results[p]['avg_latency_ms'] / 3.6e6) 
        for p in policies
    ]
    
    plt.figure(figsize=(10, 6))
    
    # Calculate relative bounds for dynamic visual offsets
    x_range = max(total_delay_hours) - min(total_delay_hours)
    x_range = x_range if x_range > 0 else 0.1
    y_range = max(emissions) - min(emissions)
    y_range = y_range if y_range > 0 else 1.0
    
    # Plot points with collision detection
    colors = ['blue', 'red', 'green', 'purple', 'orange']
    plotted_coords = {}
    
    for i, policy in enumerate(policies):
        x = total_delay_hours[i]
        y = emissions[i]
        
        # Manual jitter for overlapping points (e.g. Cost and Greedy)
        coord_key = (round(x, 4), round(y, 4))
        if coord_key in plotted_coords:
            count = plotted_coords[coord_key]
            x += (x_range * 0.04) * (count + 1)
            y += (y_range * 0.04) * (count + 1)
            plotted_coords[coord_key] += 1
        else:
            plotted_coords[coord_key] = 0
            
        plt.scatter(x, y, color=colors[i % len(colors)], s=150, label=policy, edgecolors='black')
        
        # Add labels tight to the points computationally
        plt.text(x + (x_range * 0.03), y, policy, fontsize=10, verticalalignment='center')
                 
    plt.title("Carbon vs. Delay Trade-off (Pareto Front)", fontsize=14)
    plt.xlabel("Average Total Delay (Hours)", fontsize=12)
    plt.ylabel("Total Carbon Emissions (gCO2eq)", fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.legend()
    
    output_path = os.path.join(output_dir, "pareto_front.png")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated plot: {output_path}")

def plot_emission_bars(results: dict, output_dir: str = "results"):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    policies = list(results.keys())
    emissions = [results[p]['total_emissions_g'] for p in policies]
    
    plt.figure(figsize=(10, 6))
    bars = plt.bar(policies, emissions, color=['#4C72B0', '#DD8452', '#55A868', '#C44E52'])
    
    plt.title("Total Carbon Emissions by Scheduler Policy")
    plt.ylabel("Emissions (gCO2eq)")
    plt.xticks(rotation=15)
    
    # Add values on top of bars
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + (max(emissions)*0.01), 
                 f"{yval:.2f}", ha='center', va='bottom')
                 
    output_path = os.path.join(output_dir, "emissions_bar.png")
    plt.tight_layout()
    plt.savefig(output_path, dpi=300)
    plt.close()
    print(f"Generated plot: {output_path}")

if __name__ == "__main__":
    print("Plotter defined.")
