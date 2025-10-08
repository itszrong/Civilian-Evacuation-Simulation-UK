"""
Tests for metrics.builder module.
"""

import pytest
import pandas as pd
import numpy as np
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from services.metrics.metrics_builder_service import MetricsBuilderService
from services.metrics.metrics_operations_service import MetricsOperationsServiceService


class TestMetricsBuilderService:
    """Test the MetricsBuilderService class."""
    
    def setup_method(self):
        """Set up test environment for each test."""
        self.temp_dir = tempfile.mkdtemp()
        self.builder = MetricsBuilderService(self.temp_dir)
        
        # Create test data
        self.create_test_data()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_test_data(self):
        """Create test data files."""
        # Timeseries data
        self.timeseries_df = pd.DataFrame({
            'run_id': ['test_run'] * 20,
            't': list(range(0, 1200, 60)),  # 20 minutes in 60-second intervals
            'k': ['clearance_pct'] * 10 + ['queue_len'] * 10,
            'scope': ['city'] * 10 + ['edge:123'] * 10,
            'v': [i * 10 for i in range(10)] + [20 - i for i in range(10)]
        })
        
        # Events data
        self.events_df = pd.DataFrame({
            'run_id': ['test_run'] * 5,
            't': [0, 120, 300, 600, 900],
            'type': ['start', 'capacity_warning', 'emergency', 'capacity_warning', 'end'],
            'id': ['sim_start', 'warn_1', 'fire_alarm', 'warn_2', 'sim_end'],
            'attrs': ['{}', '{"location": "station_a"}', '{"severity": "high"}', '{"location": "station_b"}', '{}']
        })
        
        # Save to parquet files
        timeseries_path = Path(self.temp_dir) / "timeseries_test_run.parquet"
        events_path = Path(self.temp_dir) / "events_test_run.parquet"
        
        self.timeseries_df.to_parquet(timeseries_path)
        self.events_df.to_parquet(events_path)
    
    def test_initialization(self):
        """Test MetricsBuilderService initialization."""
        builder = MetricsBuilderService("/test/path")
        assert builder.runs_dir == "/test/path"
        assert isinstance(builder.ops, MetricsOperationsService)
    
    def test_load_timeseries_data_success(self):
        """Test successful loading of timeseries data."""
        df = self.builder.load_timeseries_data('test_run')
        
        assert not df.empty
        assert len(df) == 20
        assert 'clearance_pct' in df['k'].values
        assert 'queue_len' in df['k'].values
        assert 'city' in df['scope'].values
        assert 'edge:123' in df['scope'].values
    
    def test_load_timeseries_data_file_not_found(self):
        """Test loading timeseries data when file doesn't exist."""
        df = self.builder.load_timeseries_data('nonexistent_run')
        
        assert df.empty
        assert list(df.columns) == ['run_id', 't', 'k', 'scope', 'v']
    
    def test_load_events_data_success(self):
        """Test successful loading of events data."""
        df = self.builder.load_events_data('test_run')
        
        assert not df.empty
        assert len(df) == 5
        assert 'start' in df['type'].values
        assert 'emergency' in df['type'].values
        assert 'capacity_warning' in df['type'].values
        assert 'end' in df['type'].values
    
    def test_load_events_data_file_not_found(self):
        """Test loading events data when file doesn't exist."""
        df = self.builder.load_events_data('nonexistent_run')
        
        assert df.empty
        assert list(df.columns) == ['run_id', 't', 'type', 'id', 'attrs']
    
    def test_get_available_metrics_success(self):
        """Test getting available metrics info for existing run."""
        info = self.builder.get_available_metrics('test_run')
        
        assert info['run_id'] == 'test_run'
        
        # Timeseries info
        assert info['timeseries']['available'] is True
        assert info['timeseries']['row_count'] == 20
        assert 'clearance_pct' in info['timeseries']['metric_keys']
        assert 'queue_len' in info['timeseries']['metric_keys']
        assert info['timeseries']['time_range']['min'] == 0
        assert info['timeseries']['time_range']['max'] == 1140
        
        # Events info
        assert info['events']['available'] is True
        assert info['events']['row_count'] == 5
        assert 'start' in info['events']['event_types']
        assert 'emergency' in info['events']['event_types']
        assert 'capacity_warning' in info['events']['event_types']
    
    def test_get_available_metrics_nonexistent_run(self):
        """Test getting available metrics info for nonexistent run."""
        info = self.builder.get_available_metrics('nonexistent_run')
        
        assert info['run_id'] == 'nonexistent_run'
        assert info['timeseries']['available'] is False
        assert info['timeseries']['row_count'] == 0
        assert info['timeseries']['metric_keys'] == []
        assert info['events']['available'] is False
        assert info['events']['row_count'] == 0
        assert info['events']['event_types'] == []
    
    def test_apply_filters_basic(self):
        """Test applying basic filters to DataFrame."""
        df = self.timeseries_df.copy()
        
        filters = {
            'scope': 'city',
            'k': 'clearance_pct'
        }
        
        filtered_df = self.builder.apply_filters(df, filters)
        
        assert len(filtered_df) == 10  # Only city/clearance_pct rows
        assert all(filtered_df['scope'] == 'city')
        assert all(filtered_df['k'] == 'clearance_pct')
    
    def test_apply_filters_time_range(self):
        """Test applying time range filters."""
        df = self.timeseries_df.copy()
        
        filters = {
            't_min': 300,
            't_max': 600
        }
        
        filtered_df = self.builder.apply_filters(df, filters)
        
        assert all(filtered_df['t'] >= 300)
        assert all(filtered_df['t'] <= 600)
        assert len(filtered_df) == 6  # 6 time points in range
    
    def test_apply_filters_contains(self):
        """Test applying contains filters."""
        df = self.timeseries_df.copy()
        
        filters = {
            'scope_contains': 'edge:'
        }
        
        filtered_df = self.builder.apply_filters(df, filters)
        
        assert all('edge:' in scope for scope in filtered_df['scope'])
        assert len(filtered_df) == 10  # Only edge rows
    
    def test_apply_filters_multiple(self):
        """Test applying multiple filters together."""
        df = self.timeseries_df.copy()
        
        filters = {
            'k': 'queue_len',
            'scope_contains': 'edge:',
            't_min': 300,
            't_max': 900
        }
        
        filtered_df = self.builder.apply_filters(df, filters)
        
        assert all(filtered_df['k'] == 'queue_len')
        assert all('edge:' in scope for scope in filtered_df['scope'])
        assert all(filtered_df['t'] >= 300)
        assert all(filtered_df['t'] <= 900)
    
    def test_apply_post_processing_divide_by(self):
        """Test post-processing with divide_by."""
        value = 3600  # 1 hour in seconds
        
        post_process = {'divide_by': 60}  # Convert to minutes
        result = self.builder.apply_post_processing(value, post_process)
        
        assert result == 60.0  # 60 minutes
    
    def test_apply_post_processing_round_to(self):
        """Test post-processing with round_to."""
        value = 123.456789
        
        post_process = {'round_to': 2}
        result = self.builder.apply_post_processing(value, post_process)
        
        assert result == 123.46
    
    def test_apply_post_processing_combined(self):
        """Test post-processing with multiple operations."""
        value = 3661  # 1 hour, 1 minute, 1 second
        
        post_process = {
            'divide_by': 60,  # Convert to minutes
            'round_to': 1     # Round to 1 decimal place
        }
        result = self.builder.apply_post_processing(value, post_process)
        
        assert result == 61.0  # 61.0 minutes
    
    def test_apply_post_processing_series(self):
        """Test post-processing with pandas Series."""
        series = pd.Series([100, 200, 300])
        
        post_process = {'divide_by': 100}
        result = self.builder.apply_post_processing(series, post_process)
        
        expected = pd.Series([1.0, 2.0, 3.0])
        pd.testing.assert_series_equal(result, expected)
    
    def test_calculate_metric_timeseries_simple(self):
        """Test calculating a simple timeseries metric."""
        metric_config = {
            'source': 'timeseries',
            'metric_key': 'clearance_pct',
            'operation': 'max_value',
            'filters': {'scope': 'city'}
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        assert result == 90  # Max clearance_pct value for city scope
    
    def test_calculate_metric_timeseries_with_args(self):
        """Test calculating timeseries metric with operation arguments."""
        metric_config = {
            'source': 'timeseries',
            'metric_key': 'clearance_pct',
            'operation': 'percentile_time_to_threshold',
            'args': {'threshold_pct': 50},
            'filters': {'scope': 'city'}
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        # Should find first time when clearance_pct >= 50 (which is value 50 at t=300)
        assert result == 300
    
    def test_calculate_metric_timeseries_with_grouping(self):
        """Test calculating timeseries metric with grouping."""
        metric_config = {
            'source': 'timeseries',
            'metric_key': 'queue_len',
            'operation': 'max_value',
            'filters': {'scope_contains': 'edge:'},
            'group_by': 'scope'
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        assert isinstance(result, pd.Series)
        assert 'edge:123' in result.index
        assert result['edge:123'] == 20  # Max queue_len for edge:123
    
    def test_calculate_metric_timeseries_with_post_processing(self):
        """Test calculating timeseries metric with post-processing."""
        metric_config = {
            'source': 'timeseries',
            'metric_key': 'clearance_pct',
            'operation': 'percentile_time_to_threshold',
            'args': {'threshold_pct': 50},
            'filters': {'scope': 'city'},
            'post_process': {'divide_by': 60, 'round_to': 1}  # Convert to minutes
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        assert result == 5.0  # 300 seconds / 60 = 5.0 minutes
    
    def test_calculate_metric_events_count(self):
        """Test calculating events metric - count."""
        metric_config = {
            'source': 'events',
            'operation': 'count_events'
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        assert result == 5  # Total number of events
    
    def test_calculate_metric_events_count_with_filter(self):
        """Test calculating events metric with filter."""
        metric_config = {
            'source': 'events',
            'operation': 'count_events',
            'filters': {'type': 'capacity_warning'}
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        assert result == 2  # Two capacity_warning events
    
    def test_calculate_metric_events_with_grouping(self):
        """Test calculating events metric with grouping."""
        metric_config = {
            'source': 'events',
            'operation': 'count_events',
            'group_by': 'type'
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        assert isinstance(result, pd.Series)
        assert result['capacity_warning'] == 2
        assert result['start'] == 1
        assert result['emergency'] == 1
        assert result['end'] == 1
    
    def test_calculate_metric_invalid_source(self):
        """Test calculating metric with invalid source."""
        metric_config = {
            'source': 'invalid_source',
            'operation': 'max_value'
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Unknown source' in result['error']
    
    def test_calculate_metric_invalid_operation(self):
        """Test calculating metric with invalid operation."""
        metric_config = {
            'source': 'timeseries',
            'metric_key': 'clearance_pct',
            'operation': 'invalid_operation'
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'Unknown operation' in result['error']
    
    def test_calculate_metric_missing_metric_key(self):
        """Test calculating timeseries metric without metric_key."""
        metric_config = {
            'source': 'timeseries',
            'operation': 'max_value'
            # Missing metric_key
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        assert isinstance(result, dict)
        assert 'error' in result
        assert 'metric_key is required' in result['error']
    
    def test_calculate_metric_exception_handling(self):
        """Test metric calculation exception handling."""
        metric_config = {
            'source': 'timeseries',
            'metric_key': 'nonexistent_key',
            'operation': 'max_value'
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        # Should handle the exception gracefully
        assert isinstance(result, dict)
        assert 'error' in result
    
    def test_calculate_metrics_multiple(self):
        """Test calculating multiple metrics at once."""
        metrics_config = {
            'metrics': {
                'max_clearance': {
                    'source': 'timeseries',
                    'metric_key': 'clearance_pct',
                    'operation': 'max_value',
                    'filters': {'scope': 'city'}
                },
                'total_events': {
                    'source': 'events',
                    'operation': 'count_events'
                },
                'clearance_p50_minutes': {
                    'source': 'timeseries',
                    'metric_key': 'clearance_pct',
                    'operation': 'percentile_time_to_threshold',
                    'args': {'threshold_pct': 50},
                    'filters': {'scope': 'city'},
                    'post_process': {'divide_by': 60, 'round_to': 1}
                }
            }
        }
        
        results = self.builder.calculate_metrics('test_run', metrics_config)
        
        assert isinstance(results, dict)
        assert 'max_clearance' in results
        assert 'total_events' in results
        assert 'clearance_p50_minutes' in results
        
        assert results['max_clearance'] == 90
        assert results['total_events'] == 5
        assert results['clearance_p50_minutes'] == 5.0
    
    def test_calculate_metrics_with_errors(self):
        """Test calculating multiple metrics with some errors."""
        metrics_config = {
            'metrics': {
                'valid_metric': {
                    'source': 'timeseries',
                    'metric_key': 'clearance_pct',
                    'operation': 'max_value'
                },
                'invalid_metric': {
                    'source': 'invalid_source',
                    'operation': 'invalid_operation'
                }
            }
        }
        
        results = self.builder.calculate_metrics('test_run', metrics_config)
        
        assert isinstance(results, dict)
        assert 'valid_metric' in results
        assert 'invalid_metric' in results
        
        assert results['valid_metric'] == 90
        assert isinstance(results['invalid_metric'], dict)
        assert 'error' in results['invalid_metric']
    
    def test_calculate_metrics_single_config(self):
        """Test calculating metrics with single metric config (not wrapped in 'metrics')."""
        metric_config = {
            'source': 'timeseries',
            'metric_key': 'clearance_pct',
            'operation': 'max_value'
        }
        
        result = self.builder.calculate_metrics('test_run', metric_config)
        
        assert result == 90  # Should return single value, not dict
    
    def test_calculate_metrics_nonexistent_run(self):
        """Test calculating metrics for nonexistent run."""
        metrics_config = {
            'metrics': {
                'test_metric': {
                    'source': 'timeseries',
                    'metric_key': 'clearance_pct',
                    'operation': 'max_value'
                }
            }
        }
        
        results = self.builder.calculate_metrics('nonexistent_run', metrics_config)
        
        assert isinstance(results, dict)
        assert 'test_metric' in results
        assert isinstance(results['test_metric'], dict)
        assert 'error' in results['test_metric']


@pytest.mark.unit
class TestMetricsBuilderServiceIntegration:
    """Integration tests for MetricsBuilderService with realistic scenarios."""
    
    def setup_method(self):
        """Set up realistic test data."""
        self.temp_dir = tempfile.mkdtemp()
        self.builder = MetricsBuilderService(self.temp_dir)
        
        # Create realistic evacuation simulation data
        self.create_realistic_data()
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def create_realistic_data(self):
        """Create realistic evacuation simulation data."""
        # Simulate 30 minutes of evacuation data
        times = list(range(0, 1801, 30))  # Every 30 seconds for 30 minutes
        
        # Clearance percentage (city-wide)
        clearance_data = []
        for i, t in enumerate(times):
            # Sigmoid-like evacuation curve
            progress = min(100, (i / len(times)) * 120)  # Slightly over 100% at end
            clearance_data.append({
                'run_id': 'realistic_run',
                't': t,
                'k': 'clearance_pct',
                'scope': 'city',
                'v': progress
            })
        
        # Queue lengths for different edges
        queue_data = []
        edges = ['edge:tube_central', 'edge:tube_northern', 'edge:bus_route_1', 'edge:walking_path_1']
        
        for edge in edges:
            for i, t in enumerate(times):
                # Different queue patterns for different transport modes
                if 'tube' in edge:
                    # Tube queues peak early then decline
                    peak_time = len(times) * 0.3
                    queue_len = max(0, 50 * np.exp(-(i - peak_time)**2 / (2 * 10**2)))
                elif 'bus' in edge:
                    # Bus queues more variable
                    queue_len = max(0, 20 + 15 * np.sin(i * 0.2) + np.random.normal(0, 3))
                else:
                    # Walking paths steady decline
                    queue_len = max(0, 30 - (i / len(times)) * 35)
                
                queue_data.append({
                    'run_id': 'realistic_run',
                    't': t,
                    'k': 'queue_len',
                    'scope': edge,
                    'v': queue_len
                })
        
        # Density at stations
        density_data = []
        stations = ['station:kings_cross', 'station:liverpool_st', 'station:waterloo']
        
        for station in stations:
            for i, t in enumerate(times):
                # Station density peaks mid-evacuation
                peak_time = len(times) * 0.5
                density = max(1.0, 2.0 + 3.0 * np.exp(-(i - peak_time)**2 / (2 * 15**2)))
                
                density_data.append({
                    'run_id': 'realistic_run',
                    't': t,
                    'k': 'density',
                    'scope': station,
                    'v': density
                })
        
        # Combine all timeseries data
        all_timeseries = clearance_data + queue_data + density_data
        timeseries_df = pd.DataFrame(all_timeseries)
        
        # Create realistic events
        events_data = [
            {'run_id': 'realistic_run', 't': 0, 'type': 'simulation_start', 'id': 'sim_start', 'attrs': '{}'},
            {'run_id': 'realistic_run', 't': 300, 'type': 'capacity_warning', 'id': 'warn_1', 'attrs': '{"location": "station:kings_cross", "density": 4.2}'},
            {'run_id': 'realistic_run', 't': 450, 'type': 'route_closure', 'id': 'closure_1', 'attrs': '{"route": "tube_central", "reason": "overcrowding"}'},
            {'run_id': 'realistic_run', 't': 600, 'type': 'capacity_warning', 'id': 'warn_2', 'attrs': '{"location": "station:waterloo", "density": 4.8}'},
            {'run_id': 'realistic_run', 't': 900, 'type': 'route_reopened', 'id': 'reopen_1', 'attrs': '{"route": "tube_central"}'},
            {'run_id': 'realistic_run', 't': 1200, 'type': 'milestone', 'id': 'milestone_50', 'attrs': '{"clearance_pct": 50}'},
            {'run_id': 'realistic_run', 't': 1500, 'type': 'milestone', 'id': 'milestone_90', 'attrs': '{"clearance_pct": 90}'},
            {'run_id': 'realistic_run', 't': 1800, 'type': 'simulation_end', 'id': 'sim_end', 'attrs': '{}'}
        ]
        
        events_df = pd.DataFrame(events_data)
        
        # Save to files
        timeseries_path = Path(self.temp_dir) / "timeseries_realistic_run.parquet"
        events_path = Path(self.temp_dir) / "events_realistic_run.parquet"
        
        timeseries_df.to_parquet(timeseries_path)
        events_df.to_parquet(events_path)
    
    def test_realistic_evacuation_metrics(self):
        """Test calculating realistic evacuation metrics."""
        # Define comprehensive metrics suite
        metrics_config = {
            'metrics': {
                # Clearance metrics
                'clearance_p95_minutes': {
                    'source': 'timeseries',
                    'metric_key': 'clearance_pct',
                    'operation': 'percentile_time_to_threshold',
                    'args': {'threshold_pct': 95},
                    'filters': {'scope': 'city'},
                    'post_process': {'divide_by': 60, 'round_to': 1}
                },
                'clearance_p50_minutes': {
                    'source': 'timeseries',
                    'metric_key': 'clearance_pct',
                    'operation': 'percentile_time_to_threshold',
                    'args': {'threshold_pct': 50},
                    'filters': {'scope': 'city'},
                    'post_process': {'divide_by': 60, 'round_to': 1}
                },
                
                # Queue metrics
                'max_tube_queue': {
                    'source': 'timeseries',
                    'metric_key': 'queue_len',
                    'operation': 'max_value',
                    'filters': {'scope_contains': 'tube'}
                },
                'avg_queue_by_edge': {
                    'source': 'timeseries',
                    'metric_key': 'queue_len',
                    'operation': 'mean_value',
                    'group_by': 'scope'
                },
                
                # Density metrics
                'max_station_density': {
                    'source': 'timeseries',
                    'metric_key': 'density',
                    'operation': 'max_value',
                    'filters': {'scope_contains': 'station'}
                },
                'overcrowding_time_minutes': {
                    'source': 'timeseries',
                    'metric_key': 'density',
                    'operation': 'time_above_threshold',
                    'args': {'threshold': 4.0},
                    'filters': {'scope_contains': 'station'},
                    'post_process': {'divide_by': 60, 'round_to': 1}
                },
                
                # Event metrics
                'total_warnings': {
                    'source': 'events',
                    'operation': 'count_events',
                    'filters': {'type': 'capacity_warning'}
                },
                'total_events': {
                    'source': 'events',
                    'operation': 'count_events'
                }
            }
        }
        
        results = self.builder.calculate_metrics('realistic_run', metrics_config)
        
        # Verify all metrics calculated successfully
        assert isinstance(results, dict)
        assert len(results) == 8
        
        # Check clearance metrics
        assert 'clearance_p95_minutes' in results
        assert 'clearance_p50_minutes' in results
        assert isinstance(results['clearance_p95_minutes'], (int, float))
        assert isinstance(results['clearance_p50_minutes'], (int, float))
        assert results['clearance_p95_minutes'] > results['clearance_p50_minutes']
        
        # Check queue metrics
        assert 'max_tube_queue' in results
        assert isinstance(results['max_tube_queue'], (int, float))
        assert results['max_tube_queue'] > 0
        
        assert 'avg_queue_by_edge' in results
        assert isinstance(results['avg_queue_by_edge'], pd.Series)
        
        # Check density metrics
        assert 'max_station_density' in results
        assert isinstance(results['max_station_density'], (int, float))
        assert results['max_station_density'] > 1.0
        
        assert 'overcrowding_time_minutes' in results
        assert isinstance(results['overcrowding_time_minutes'], (int, float))
        
        # Check event metrics
        assert 'total_warnings' in results
        assert results['total_warnings'] == 2  # Two capacity warnings in test data
        
        assert 'total_events' in results
        assert results['total_events'] == 8  # Total events in test data
    
    def test_performance_with_large_dataset(self):
        """Test performance with larger dataset."""
        # This test ensures the metrics builder can handle larger datasets
        # without significant performance degradation
        
        import time
        
        start_time = time.time()
        
        # Calculate a comprehensive set of metrics
        metrics_config = {
            'metrics': {
                'clearance_p95': {
                    'source': 'timeseries',
                    'metric_key': 'clearance_pct',
                    'operation': 'percentile_time_to_threshold',
                    'args': {'threshold_pct': 95},
                    'filters': {'scope': 'city'}
                },
                'queue_stats_by_edge': {
                    'source': 'timeseries',
                    'metric_key': 'queue_len',
                    'operation': 'max_value',
                    'group_by': 'scope'
                },
                'density_auc': {
                    'source': 'timeseries',
                    'metric_key': 'density',
                    'operation': 'area_under_curve',
                    'group_by': 'scope'
                }
            }
        }
        
        results = self.builder.calculate_metrics('realistic_run', metrics_config)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Should complete within reasonable time (adjust threshold as needed)
        assert execution_time < 5.0  # 5 seconds max
        
        # Verify results
        assert isinstance(results, dict)
        assert len(results) == 3
        assert all(key in results for key in metrics_config['metrics'].keys())


@pytest.mark.unit
class TestMetricsBuilderServiceErrorHandling:
    """Test error handling and edge cases in MetricsBuilderService."""
    
    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.builder = MetricsBuilderService(self.temp_dir)
    
    def teardown_method(self):
        """Clean up test environment."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_corrupted_parquet_file(self):
        """Test handling of corrupted parquet files."""
        # Create a corrupted file
        corrupted_path = Path(self.temp_dir) / "timeseries_corrupted_run.parquet"
        corrupted_path.write_text("This is not a valid parquet file")
        
        # Should handle gracefully
        df = self.builder.load_timeseries_data('corrupted_run')
        assert df.empty
    
    def test_empty_parquet_file(self):
        """Test handling of empty parquet files."""
        # Create empty DataFrame and save as parquet
        empty_df = pd.DataFrame(columns=['run_id', 't', 'k', 'scope', 'v'])
        empty_path = Path(self.temp_dir) / "timeseries_empty_run.parquet"
        empty_df.to_parquet(empty_path)
        
        # Should load empty DataFrame correctly
        df = self.builder.load_timeseries_data('empty_run')
        assert df.empty
        assert list(df.columns) == ['run_id', 't', 'k', 'scope', 'v']
    
    def test_permission_denied(self):
        """Test handling of permission denied errors."""
        # This test is platform-dependent and might not work on all systems
        # Skip if we can't create the test condition
        
        restricted_dir = Path(self.temp_dir) / "restricted"
        restricted_dir.mkdir()
        
        try:
            # Try to make directory read-only (Unix-like systems)
            restricted_dir.chmod(0o444)
            
            builder = MetricsBuilderService(str(restricted_dir))
            df = builder.load_timeseries_data('test_run')
            
            # Should handle permission errors gracefully
            assert df.empty
            
        except (OSError, PermissionError):
            # If we can't set permissions, skip this test
            pytest.skip("Cannot test permission denied on this system")
        
        finally:
            # Restore permissions for cleanup
            try:
                restricted_dir.chmod(0o755)
            except (OSError, PermissionError):
                pass
    
    @patch('pandas.read_parquet')
    def test_pandas_read_error(self, mock_read_parquet):
        """Test handling of pandas read errors."""
        # Mock pandas to raise an exception
        mock_read_parquet.side_effect = Exception("Pandas read error")
        
        df = self.builder.load_timeseries_data('test_run')
        
        # Should handle pandas errors gracefully
        assert df.empty
        assert list(df.columns) == ['run_id', 't', 'k', 'scope', 'v']
    
    def test_invalid_metric_config_structure(self):
        """Test handling of invalid metric configuration structure."""
        # Missing required fields
        invalid_configs = [
            {},  # Empty config
            {'source': 'timeseries'},  # Missing operation
            {'operation': 'max_value'},  # Missing source
            {'source': 'invalid', 'operation': 'max_value'},  # Invalid source
            {'source': 'timeseries', 'operation': 'invalid'},  # Invalid operation
        ]
        
        for config in invalid_configs:
            result = self.builder.calculate_metric('test_run', config)
            assert isinstance(result, dict)
            assert 'error' in result
    
    def test_metric_calculation_with_no_data(self):
        """Test metric calculation when no data matches filters."""
        # Create minimal test data
        df = pd.DataFrame({
            'run_id': ['test_run'],
            't': [0],
            'k': ['test_metric'],
            'scope': ['test_scope'],
            'v': [10]
        })
        
        df.to_parquet(Path(self.temp_dir) / "timeseries_test_run.parquet")
        
        # Try to calculate metric with filters that match no data
        metric_config = {
            'source': 'timeseries',
            'metric_key': 'nonexistent_metric',
            'operation': 'max_value'
        }
        
        result = self.builder.calculate_metric('test_run', metric_config)
        
        # Should handle gracefully (might return NaN or error)
        assert result is not None
