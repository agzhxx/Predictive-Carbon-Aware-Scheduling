# Project Report: Predictive Carbon-Aware Scheduling

## Abstract
The rapid growth of cloud computing and serverless architectures has led to a significant increase in the global energy footprint of data centers. While major cloud providers continuously optimize hardware efficiency, the carbon intensity of the electricity powering these data centers varies drastically across different geographical regions and times of the day. This project proposes and evaluates a **Predictive Carbon-Aware Scheduling** system. By leveraging spatial and temporal shifting—routing jobs to geographical regions with greener energy grids or delaying execution until the local grid is cleaner—the system aims to reduce the total carbon emissions of batch processing jobs while strictly adhering to Service Level Agreements (SLAs). Through an event-driven simulation, we demonstrate the efficacy of spatial shifting and evaluate the impact of predictive temporal shifting using an LSTM-based forecasting model.

## Introduction and Context
The environmental impact of computing is an escalating concern. Data centers consume vast amounts of electricity, and the carbon emissions associated with this consumption depend heavily on the local energy mix (e.g., solar and wind vs. coal and gas). 

For delay-tolerant workloads, such as background data processing, machine learning training, or batch analytics, there is a unique opportunity to decouple the execution of tasks from a specific time and place. This project addresses the challenge of **carbon-aware scheduling** for serverless workloads. The core problem is: *How can we intelligently route and schedule compute jobs across a globally distributed cloud infrastructure to minimize carbon emissions ($gCO_{2}eq$) without violating user-defined performance constraints (SLAs)?*

This is a critical problem because blind execution of workloads in Carbon-intensive regions (or during peak fossil-fuel usage hours) unnecessarily inflates the carbon footprint of digital services.

## Methodology
To evaluate carbon-aware scheduling strategies, we developed a custom event-driven simulation environment. The methodology involves the following key components:

1.  **Data Ingestion**: We utilize real-world workload traces (e.g., Azure serverless traces) to simulate realistic job arrival patterns and execution durations. This is combined with historical hourly carbon intensity datasets (measured in $gCO_2eq/kWh$) sourced via the Electricity Maps API for various global cloud regions (e.g., `us-west-1`, `eu-north-1`).
2.  **Simulation Environment (`simulator/`)**: A SimPy-based discrete-event simulator models the cloud infrastructure. It handles job queuing, inter-region network latency penalties (e.g., +150ms for cross-ocean routing), and tracks the simulated timeline. For each executing job, it continuously calculates energy consumption (assuming a standard instance power draw) and multiplies it by the real-time carbon intensity of the selected region to compute total emissions.
3.  **Predictive Modeling (`models/`, `train_models.py`)**: We implemented and trained a Long Short-Term Memory (LSTM) neural network using PyTorch. The model takes a 24-hour lookback window of historical carbon intensity data to predict future carbon intensities across all regions.
4.  **Policy Evaluation (`scheduler/policies.py`, `evaluation/runner.py`)**: The simulator evaluates the workloads against four distinct scheduling policies:
    *   **Latency Optimized (Baseline)**: Executes jobs immediately in the local region, prioritizing speed over emissions and cost.
    *   **Cost Optimized**: Routes jobs to the region with the lowest compute cost.
    *   **Greedy Carbon**: Evaluates current, real-time carbon intensity across all regions and dispatches the job immediately to the cleanest available region (Spatial Shifting).
    *   **Predictive Carbon-Aware (LSTM)**: Compares the current carbon intensity against the LSTM's predicted intensity in the future (within the SLA window). It decides whether to route spatially now or wait temporally for a cleaner grid.

## Code Structure and Main Components
The repository is modularly structured to separate data handling, simulation, predictive modeling, and evaluation:

*   **`data/`**: Contains `data_loader.py` for parsing workload traces and `electricity_maps_client.py` for fetching real-world carbon grid data.
*   **`models/forecaster.py`**: Defines the PyTorch LSTM architecture used for time-series forecasting of carbon intensity.
*   **`train_models.py`**: The entry point for training the LSTM model on historical grid data.
*   **`simulator/`**: The core simulation engine. `environment.py` runs the SimPy environment, `job_queue.py` manages incoming tasks, and `config.py` holds crucial constants like the `SLA_MAX_DELAY_HOURS` and regional power parameters.
*   **`scheduler/policies.py`**: Implements the routing logic for the Baseline, Cost, Greedy, and LSTM schedulers.
*   **`evaluation/`**: `runner.py` ties everything together, running the simulation loops for each policy and collecting metrics (`metrics.py`).
*   **`visualization/plotter.py`**: Generates graphs (Pareto fronts, emission bar charts) to visually compare the trade-offs between latency, cost, and carbon footprints across policies.

## Major Findings and the Greedy vs. LSTM Anomaly
The simulation results clearly demonstrate the value of **spatial shifting**. Routing workloads to regions with consistently green energy grids (like `eu-north-1` or `us-west-2` with high hydro/nuclear penetration) dramatically reduces total carbon emissions compared to the Baseline local execution.

However, an interesting finding emerges when comparing the **Greedy Carbon** policy to the **Predictive Carbon-Aware (LSTM)** policy: **they often produce nearly identical results.**

### Why does the Greedy solution match the Predictive LSTM?
This finding occurs due constraint intersections within the simulation environment and the nature of power grids:

1.  **Short SLA Windows**: The project enforces a strict, short Service Level Agreement (e.g., a 1-hour maximum delay allowance). Within a 1-hour window, the LSTM can only look one step ahead.
2.  **High Autocorrelation of Grid Data**: Carbon intensity typically changes gradually. The carbon intensity *right now* is an incredibly strong predictor of the intensity *one hour from now*. Dramatic, sudden shifts in grid cleanliness (that would justify waiting rather than executing now) are rare on a 1-hour timescale.
3.  **The Dominance of Spatial Shifting**: Because some regions are *consistently* built on green infrastructure (e.g., baseload nuclear or massive hydro), it is almost always mathematically optimal to ship a job to those regions immediately (the Greedy approach) rather than waiting in a dirtier region for a marginal improvement (the Predictive Temporal approach). The LSTM realizes that waiting 1 hour in a sunny region usually still cannot beat the immediate carbon floor of a hydro-powered region.

## Conclusion
The Predictive Carbon-Aware Scheduling project successfully validates that carbon-aware routing can significantly decrease the environmental footprint of cloud workloads. While spatial shifting (Greedy routing to the cleanest global region) proves highly effective and easier to implement, temporal shifting (Predictive delays) requires much wider SLA windows (e.g., 12-24 hours) to out-perform simple geographic routing. Ultimately, embedding carbon metrics into cloud schedulers offers a powerful, software-driven approach to sustainable computing.
