"""
Create sample data for testing the metrics system.
"""

import pandas as pd
import numpy as np
from pathlib import Path


def create_sample_timeseries_data(run_id: str = "sample_run") -> pd.DataFrame:
    """Create realistic sample timeseries data for evacuation simulation."""
    
    # Time points (every 30 seconds for 30 minutes)
    times = list(range(0, 1801, 30))  # 0 to 1800 seconds (30 minutes)
    
    data = []
    
    # City-wide clearance percentage (S-curve)
    for t in times:
        # Logistic growth curve for evacuation
        clearance_pct = 100 / (1 + np.exp(-0.01 * (t - 900)))  # Inflection at 15 minutes
        data.append({
            'run_id': run_id,
            't': t,
            'k': 'clearance_pct',
            'scope': 'city',
            'v': clearance_pct
        })
    
    # Queue lengths for different edges
    edges = ['edge:main_st', 'edge:broadway', 'edge:park_ave', 'edge:river_rd']
    for edge in edges:
        for t in times:
            # Different patterns for different edges
            if 'main_st' in edge:
                # Heavy congestion early, then clearing
                queue_len = max(0, 50 * np.exp(-0.003 * t) + 10 * np.sin(0.01 * t))
            elif 'broadway' in edge:
                # Steady moderate congestion
                queue_len = 25 + 15 * np.sin(0.005 * t) + np.random.normal(0, 3)
            elif 'park_ave' in edge:
                # Light congestion
                queue_len = 10 + 5 * np.sin(0.008 * t) + np.random.normal(0, 2)
            else:  # river_rd
                # Peak congestion in middle
                queue_len = 30 * np.exp(-0.5 * ((t - 900) / 300) ** 2)
            
            queue_len = max(0, queue_len)  # No negative queues
            
            data.append({
                'run_id': run_id,
                't': t,
                'k': 'queue_len',
                'scope': edge,
                'v': queue_len
            })
    
    # Platform densities for stations
    stations = ['node:station_central', 'node:station_north', 'node:station_south']
    for station in stations:
        for t in times:
            # High density early, then decreasing
            if 'central' in station:
                density = 6 * np.exp(-0.002 * t) + np.random.normal(0, 0.5)
            elif 'north' in station:
                density = 4 * np.exp(-0.0015 * t) + np.random.normal(0, 0.3)
            else:  # south
                density = 3 * np.exp(-0.001 * t) + np.random.normal(0, 0.2)
            
            density = max(0, density)  # No negative density
            
            data.append({
                'run_id': run_id,
                't': t,
                'k': 'density',
                'scope': station,
                'v': density
            })
    
    return pd.DataFrame(data)


def create_sample_events_data(run_id: str = "sample_run") -> pd.DataFrame:
    """Create sample events data."""
    
    events = [
        {
            'run_id': run_id,
            't': 0,
            'type': 'simulation_start',
            'id': 'sim_start',
            'attrs': '{"message": "Evacuation simulation started"}'
        },
        {
            'run_id': run_id,
            't': 120,
            'type': 'emergency_alert',
            'id': 'alert_001',
            'attrs': '{"location": "central_district", "severity": "high"}'
        },
        {
            'run_id': run_id,
            't': 300,
            'type': 'route_closure',
            'id': 'closure_001',
            'attrs': '{"route": "main_st", "reason": "congestion"}'
        },
        {
            'run_id': run_id,
            't': 600,
            'type': 'capacity_warning',
            'id': 'warning_001',
            'attrs': '{"location": "station_central", "density": 5.2}'
        },
        {
            'run_id': run_id,
            't': 900,
            'type': 'route_reopened',
            'id': 'reopen_001',
            'attrs': '{"route": "main_st"}'
        },
        {
            'run_id': run_id,
            't': 1800,
            'type': 'simulation_end',
            'id': 'sim_end',
            'attrs': '{"message": "Evacuation simulation completed", "total_evacuated": 95.8}'
        }
    ]
    
    return pd.DataFrame(events)


def main():
    """Create and save sample data files."""
    
    # Create data directory
    data_dir = Path("local_s3/runs")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample data
    print("Creating sample timeseries data...")
    timeseries_df = create_sample_timeseries_data()
    
    print("Creating sample events data...")
    events_df = create_sample_events_data()
    
    # Save as parquet files
    timeseries_path = data_dir / "timeseries_sample_run.parquet"
    events_path = data_dir / "events_sample_run.parquet"
    
    print(f"Saving timeseries data to {timeseries_path}")
    timeseries_df.to_parquet(timeseries_path, index=False)
    
    print(f"Saving events data to {events_path}")
    events_df.to_parquet(events_path, index=False)
    
    # Also save as CSV for easy inspection
    timeseries_df.to_csv(data_dir / "timeseries_sample_run.csv", index=False)
    events_df.to_csv(data_dir / "events_sample_run.csv", index=False)
    
    print("\nSample data created successfully!")
    print(f"Timeseries records: {len(timeseries_df)}")
    print(f"Events records: {len(events_df)}")
    print(f"Time range: {timeseries_df['t'].min()} - {timeseries_df['t'].max()} seconds")
    print(f"Metric keys: {timeseries_df['k'].unique().tolist()}")
    print(f"Scopes: {timeseries_df['scope'].unique().tolist()}")


if __name__ == "__main__":
    main()
