# Target AWS Regions for Simulation
# These regions display distinct carbon characteristics essential for testing predictive load shifting.
# Extended AWS / Global Regions for Unified Training & Simulation
REGIONS = {
    'us-west-1': {
        'electricity_maps_zone': 'US-CAL-CISO', # Northern California (Duck Curve)
        'name': 'Northern California',
        'lat': 37.35, 'lon': -121.96,
        'cost_multiplier': 1.0
    },
    'us-east-1': {
        'electricity_maps_zone': 'US-MIDA-PJM', # Virginia (Massive Hub, Baseline grid)
        'name': 'Virginia',
        'lat': 39.04, 'lon': -77.48,
        'cost_multiplier': 0.8 # Often the cheapest US region
    },
    'us-central': {
        'electricity_maps_zone': 'US-TEX-ERCO', # Texas (Volatile Wind/Gas)
        'name': 'Texas',
        'lat': 32.77, 'lon': -96.79,
        'cost_multiplier': 0.95
    },
    'eu-central-1': {
        'electricity_maps_zone': 'DE', # Frankfurt (Wind/Coal)
        'name': 'Frankfurt',
        'lat': 50.11, 'lon': 8.68,
        'cost_multiplier': 1.05 
    },
    'ap-southeast-2': {
        'electricity_maps_zone': 'AU-NSW', # Sydney (Heavy Coal)
        'name': 'Sydney',
        'lat': -33.86, 'lon': 151.20,
        'cost_multiplier': 1.2
    }
}

# Strict Service Level Agreement (SLA) threshold
# Measured in HOURS. If delaying a job would exceed this SLA, it MUST be executed immediately.
# 12 Hours is the new experimental SLA to test multi-step forecasting efficiency.
SLA_MAX_DELAY_HOURS = 1.0
