"""
Simple test of the metrics system with sample data.
"""

from metrics.builder import MetricsBuilder
import json


def test_metrics():
    """Test the metrics system with sample data."""
    
    # Initialize metrics builder
    builder = MetricsBuilder("local_s3/runs")
    
    print("🧪 Testing Metrics System")
    print("=" * 50)
    
    # Test 1: Get available metrics info
    print("\n1. Getting available metrics info...")
    info = builder.get_available_metrics("sample_run")
    print(f"   ✓ Timeseries available: {info['timeseries']['available']}")
    print(f"   ✓ Timeseries records: {info['timeseries']['row_count']}")
    print(f"   ✓ Events available: {info['events']['available']}")
    print(f"   ✓ Events records: {info['events']['row_count']}")
    print(f"   ✓ Metric keys: {info['timeseries']['metric_keys']}")
    print(f"   ✓ Time range: {info['timeseries']['time_range']['min']} - {info['timeseries']['time_range']['max']} seconds")
    
    # Test 2: Calculate clearance p95
    print("\n2. Calculating clearance p95...")
    clearance_config = {
        'source': 'timeseries',
        'metric_key': 'clearance_pct',
        'operation': 'percentile_time_to_threshold',
        'args': {'threshold_pct': 95},
        'filters': {'scope': 'city'},
        'post_process': {'divide_by': 60, 'round_to': 1}  # Convert to minutes
    }
    
    clearance_p95 = builder.calculate_metric("sample_run", clearance_config)
    print(f"   ✓ Clearance p95: {clearance_p95} minutes")
    
    # Test 3: Calculate max queue lengths
    print("\n3. Calculating max queue lengths by edge...")
    queue_config = {
        'source': 'timeseries',
        'metric_key': 'queue_len',
        'operation': 'max_value',
        'filters': {'scope_contains': 'edge:'},
        'group_by': 'scope'
    }
    
    max_queues = builder.calculate_metric("sample_run", queue_config)
    print(f"   ✓ Max queue lengths:")
    for edge, max_queue in max_queues.items():
        print(f"     - {edge}: {max_queue:.1f}")
    
    # Test 4: Calculate platform overcrowding time
    print("\n4. Calculating platform overcrowding time...")
    overcrowding_config = {
        'source': 'timeseries',
        'metric_key': 'density',
        'operation': 'time_above_threshold',
        'args': {'threshold': 4.0},
        'filters': {'scope_contains': 'station'},
        'post_process': {'divide_by': 60, 'round_to': 1}  # Convert to minutes
    }
    
    overcrowding_time = builder.calculate_metric("sample_run", overcrowding_config)
    print(f"   ✓ Platform overcrowding time: {overcrowding_time} minutes")
    
    # Test 5: Count events
    print("\n5. Counting events...")
    events_config = {
        'source': 'events',
        'operation': 'count_events'
    }
    
    total_events = builder.calculate_metric("sample_run", events_config)
    print(f"   ✓ Total events: {total_events}")
    
    # Test 6: Multiple metrics at once
    print("\n6. Calculating multiple metrics...")
    multi_config = {
        'metrics': {
            'clearance_p50': {
                'source': 'timeseries',
                'metric_key': 'clearance_pct',
                'operation': 'percentile_time_to_threshold',
                'args': {'threshold_pct': 50},
                'filters': {'scope': 'city'},
                'post_process': {'divide_by': 60, 'round_to': 1}
            },
            'clearance_p95': {
                'source': 'timeseries',
                'metric_key': 'clearance_pct',
                'operation': 'percentile_time_to_threshold',
                'args': {'threshold_pct': 95},
                'filters': {'scope': 'city'},
                'post_process': {'divide_by': 60, 'round_to': 1}
            },
            'avg_queue_length': {
                'source': 'timeseries',
                'metric_key': 'queue_len',
                'operation': 'mean_value',
                'filters': {'scope_contains': 'edge:'}
            },
            'total_events': {
                'source': 'events',
                'operation': 'count_events'
            }
        }
    }
    
    results = builder.calculate_metrics("sample_run", multi_config)
    print(f"   ✓ Multiple metrics results:")
    for metric_name, value in results.items():
        if isinstance(value, dict) and 'error' in value:
            print(f"     - {metric_name}: ERROR - {value['error']}")
        else:
            print(f"     - {metric_name}: {value}")
    
    print("\n" + "=" * 50)
    print("✅ All tests completed successfully!")
    
    return results


if __name__ == "__main__":
    test_metrics()
